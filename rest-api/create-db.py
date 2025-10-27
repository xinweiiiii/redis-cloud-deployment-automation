#!/usr/bin/env/python3
import os
import sys
import time
import json
import re
import math
from typing import Dict, Any, List, Optional

import requests
from dotenv import load_dotenv
load_dotenv()

# ----------------- Config -----------------
BASE_URL = os.getenv("REDIS_CLOUD_BASE_URL", "https://api.redislabs.com/v1").rstrip("/")
ACCOUNT_API_KEY = os.getenv("REDIS_CLOUD_ACCOUNT_KEY")
USER_API_KEY = os.getenv("REDIS_CLOUD_API_KEY")
ACCOUNT_ID = os.getenv("REDIS_CLOUD_ACCOUNT_ID")
CLOUD_PROVIDER = os.getenv("REDIS_CLOUD_PROVIDER")
CLOUD_REGION = os.getenv("REDIS_CLOUD_REGION")
PAYMENT_METHOD_ID = int(os.getenv("REDIS_CLOUD_PAYMENT_METHOD_ID"))
SUBSCRIPTION_NAME = os.getenv("REDIS_CLOUD_SUBSCRIPTION_NAME", f"auto-sub-{int(time.time())}")
DEPLOYMENT_CIDR = os.getenv("REDIS_CLOUD_DEPLOYMENT_CIDR", "10.0.1.0/24")

REQUIRED_ENV = [ACCOUNT_API_KEY, USER_API_KEY, ACCOUNT_ID, CLOUD_PROVIDER, CLOUD_REGION]
if not all(REQUIRED_ENV):
    sys.stderr.write(
        "Missing one or more required env vars:\n"
        "- REDIS_CLOUD_ACCOUNT_KEY\n"
        "- REDIS_CLOUD_API_KEY\n"
        "- REDIS_CLOUD_ACCOUNT_ID\n"
        "- REDIS_CLOUD_PROVIDER\n"
        "- REDIS_CLOUD_REGION\n"
        "- REDIS_CLOUD_PAYMENT_METHOD_ID\n"
    )
    sys.exit(1)

def auth_headers() -> Dict[str, str]:
    # Redis Cloud requires BOTH the account key and the user (secret) key
    return {
        "x-api-key": ACCOUNT_API_KEY,
        "x-api-secret-key": USER_API_KEY,
        "Content-Type": "application/json",
    }

SESSION = requests.Session()
SESSION.headers.update(auth_headers())

# ----------------- HTTP helpers -----------------
def http_error(resp: requests.Response, msg: str):
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    raise SystemExit(f"{msg}: HTTP {resp.status_code} = {body}")

def post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    r = SESSION.post(url, data=json.dumps(payload), timeout=60)
    if not r.ok:
        http_error(r, f"POST {path} failed")
    return r.json()

def get(path: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    r = SESSION.get(url, timeout=60)
    if not r.ok:
        http_error(r, f"GET {path} failed")
    return r.json()

# ----------------- Polling helpers -----------------
def wait_for_subscription_active(sub_id: str, timeout_s: int = 900, poll_s: float = 5.0):
    start = time.time()
    while True:
        sub = get(f"/subscriptions/{sub_id}")
        status = (sub.get("status") or sub.get("state") or "").lower()
        if status in {"active", "activated", "running", "ready"}:
            return sub
        if status in {"error", "failed"}:
            raise SystemExit(f"Subscription {sub_id} entered failure state {status}")
        if time.time() - start > timeout_s:
            raise SystemExit(f"Timeout waiting for subscription {sub_id} to become active (last status={status})")
        time.sleep(poll_s)

def wait_for_task(task_id: str, timeout_s: int = 900, poll_s: float = 3.0) -> Dict[str, Any]:
    """
    Poll /tasks/{taskId} until it reaches a terminal state.
    Logs and raises detailed info on failure.
    """
    start = time.time()
    while True:
        task = get(f"/tasks/{task_id}")
        status = (task.get("status") or "").lower()

        # --- SUCCESS STATES ---
        if status in {"succeeded", "success", "completed", "done"}:
            print(f"✅ Task {task_id} completed successfully.")
            return task

        # --- FAILURE STATES ---
        if status in {"failed", "error", "aborted", "canceled", "cancelled", "processing-error"}:
            print(f"❌ Task {task_id} ended with status={status}")
            # Try to extract deeper error context
            err_msg = (
                task.get("errorMessage")
                or task.get("message")
                or task.get("details")
                or "No additional error message provided."
            )
            print("\n--- TASK DEBUG INFO ---")
            print(json.dumps(task, indent=2))
            print("-----------------------\n")
            raise SystemExit(f"Task {task_id} failed: {err_msg}")

        # --- TIMEOUT ---
        if time.time() - start > timeout_s:
            print("\n--- TASK DEBUG INFO (timeout) ---")
            print(json.dumps(task, indent=2))
            print("-----------------------\n")
            raise SystemExit(f"Timeout waiting for task {task_id} to complete (last status={status})")

        time.sleep(poll_s)


def _extract_subscription_id_from_task(task: Dict[str, Any]) -> Optional[str]:
    for keypath in [
        ("result", "subscriptionId"),
        ("response", "subscriptionId"),
        ("subscriptionId",),
        ("resourceId",),
        ("result", "id"),
        ("response", "id"),
    ]:
        obj = task
        ok = True
        for k in keypath:
            if isinstance(obj, dict) and k in obj:
                obj = obj[k]
            else:
                ok = False
                break
        if ok and isinstance(obj, (str, int)):
            return str(obj)

    # Fallback: parse from resource link
    for link in task.get("links", []):
        rel = (link.get("rel") or "").lower()
        href = link.get("href") or ""
        if rel in {"resource", "subscription"} and href:
            m = re.search(r"/subscriptions/([^/]+)", href)
            if m:
                return m.group(1)
    return None

# ----------------- Normalization -----------------
def _to_gb_int(x: Any) -> int:
    try:
        val = float(x)
        return max(1, int(math.ceil(val)))
    except Exception:
        return 1

def _normalize_db_from_input(db: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts snake_case input and returns PRO/REST camelCase DB payload.
    - Rounds dataset size to whole GB (min 1).
    - Accepts 'modules' or misspelled 'modulexs'.
    """
    modules = db.get("modules")
    if modules is None:
        modules = db.get("modulexs", [])  # accept typo
    return {
        "name": db.get("name", "redis-db"),
        "protocol": db.get("protocol", "redis"),
        "datasetSizeInGb": _to_gb_int(db.get("dataset_size_in_gb", 1)),
        "replication": bool(db.get("replication", False)),
        "throughputMeasurementBy": db.get("throughput_measurement_by", "operations-per-second"),
        "throughputMeasurementValue": int(db.get("throughput_measurement_value", 100)),
        "modules": modules,
        "supportOSSClusterApi": bool(db.get("support_oss_cluster_api", False)),
    }

def _dbs_from_payload(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    dbs = spec.get("databases") or []
    normed = []
    if dbs:
        for d in dbs:
            normed.append(_normalize_db_from_input(d))
        return normed

    # If no explicit databases but creation_plan exists, synthesize minimal DB(s)
    creation_plan = (spec.get("subscription") or {}).get("creation_plan") or []
    if creation_plan:
        for i, item in enumerate(creation_plan, start=1):
            normed.append(_normalize_db_from_input({
                "name": f"redis-db-{i}",
                "dataset_size_in_gb": item.get("dataset_size_in_gb", 1),
                "replication": item.get("replication", False),
                "throughput_measurement_by": item.get("throughput_measurement_by", "operations-per-second"),
                "throughput_measurement_value": item.get("throughput_measurement_value", 100),
                "modules": [],  # creation_plan has no modules; use empty
                "support_oss_cluster_api": False,
            }))
    return normed

# ----------------- PRO (Flexible) creation -----------------
def build_pro_subscription_payload(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts your snake_case input (with 'creation_plan') into a valid PRO payload:
    POST /v1/subscriptions
    """
    dbs = _dbs_from_payload(spec)
    if not dbs:
        raise SystemExit("No databases specified or derivable from 'creation_plan'")

    payload = {
        "name": SUBSCRIPTION_NAME,
        "paymentMethodId": PAYMENT_METHOD_ID,
        "cloudProviders": [
            {
                "provider": CLOUD_PROVIDER,
                "regions": [
                    {
                        "region": CLOUD_REGION,
                        "networking": {"deploymentCIDR": DEPLOYMENT_CIDR}
                    }
                ]
            }
        ],
        "databases": dbs
    }
    return payload

def create_pro_subscription(spec: Dict[str, Any]) -> str:
    payload = build_pro_subscription_payload(spec)
    res = post("/subscriptions", payload)

    # Direct id (rare) or task flow (common)
    sub_id = res.get("subscriptionId") or res.get("id")
    if not sub_id:
        task_id = res.get("taskId") or res.get("task_id")
        if not task_id:
            raise SystemExit(f"Subscription create returned no id or taskId: {res}")
        print(f"Create subscription queued as task {task_id}. Polling task...")
        final_task = wait_for_task(task_id)
        sub_id = _extract_subscription_id_from_task(final_task)
        if not sub_id:
            raise SystemExit(f"Task {task_id} completed but no subscription id found: {final_task}")
    return str(sub_id)

def create_database(sub_id: str, db: Dict[str, Any]) -> str:
    payload = _normalize_db_from_input(db)
    res = post(f"/subscriptions/{sub_id}/databases", payload)
    db_id = res.get("databaseId") or res.get("id") or res.get("database_id")
    if not db_id:
        raise SystemExit(f"Could not find database id in response: {res}")
    return str(db_id)

# ----------------- Entry Point -----------------
def main():
    if sys.stdin.isatty():
        sys.stderr.write(
            "Pipe the JSON into stdin. Example:\n"
            "cat payload.json | python provision_redis_cloud_pro.py\n"
        )
        sys.exit(2)

    # Read user payload (snake_case, includes 'creation_plan' and possibly 'modulexs')
    spec = json.load(sys.stdin)

    print("Creating PRO subscription...")
    sub_id = create_pro_subscription(spec)
    print(f"Subscription requested: {sub_id}. Waiting for activation...")
    wait_for_subscription_active(sub_id)
    print(f"Subscription {sub_id} is active")

    # Create explicit databases if provided (we already created via subscription payload,
    # but this loop supports the case where you want to create more DBs afterward).
    dbs: List[Dict[str, Any]] = spec.get("databases", [])
    for db in dbs:
        print(f"Creating database '{db.get('name', 'redis-db')}'")
        db_id = create_database(sub_id, db)
        print(f"Created database id: {db_id}")

    print("Provisioning complete")

if __name__ == "__main__":
    main()
