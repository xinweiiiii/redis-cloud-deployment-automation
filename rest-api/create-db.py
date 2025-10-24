#!/usr/bin/env/python3
import os
import sys
import time
import json
from typing import Dict, Any, List, Optional

import requests

# Configuration via environment variable
BASE_URL = os.getenv("REDIS_CLOUD_BASE_URL", "https://api.redis.com/v1")
API_KEY = os.getenv("REDIS_CLOUD_API_KEY")
ACCOUNT_ID = os.getenv("REDIS_CLOUD_ACCOUNT_ID")
CLOUD_PROVIDER = os.getenv("REDIS_CLOUD_PROVIDER")
CLOUD_REGION = os.getenv("REDIS_CLOUD_REGION")
AUTH_STYLE = os.getenv("REDIS_CLOUD_AUTH_HEADER", "bearer").lower()  # 'bearer' or 'x-api-key'

if not all([API_KEY, ACCOUNT_ID, CLOUD_PROVIDER, CLOUD_REGION]):
    sys.stderr.write(
        "Missing one or more required env vars: "
        "REDIS_CLOUD_API_KEY, REDIS_CLOUD_ACCOUNT_ID, REDIS_CLOUD_PROVIDER, "
        "REDIS_CLOUD_REGION, REDIS_CLOUD_PAYMENT_METHOD_ID\n"
    )
    sys.exit(1)

def auth_headers() -> Dict[str, str]:
    if AUTH_STYLE == "x-api-key":
        return {"x-api-key": API_KEY}
    return {"Authorisation": f"Bearer {API_KEY}"}

SESSION = requests.Session()
SESSION.headers.update({
    "Content-Type": "application/json",
    **auth_headers()
})

# ------- Helpders --------
def die_http(resp: requests.Response, msg: str):
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    raise SystemExit(f"{msg}: HTTP {resp.status_code} = {body}")


def post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    r = SESSION.post(url, data=json.dumps(payload), timeout=30)
    if not r.ok:
        die_http(r, f"POST {path} failed")
    return r.json()   


def get(path: str) -> Dict[str, Any]:
    url = f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    r = SESSION.get(url, timeout=30)
    if not r.ok:
        die_http(r, f"GET {path} failed")
    return r.json()

def wait_for_subscription_active(sub_id: str, timeout_s: int = 900, poll_s: float = 5.0):
    """Poll the subscription until it becomes 'active' (or similar terminal good state)."""
    start = time.time()
    while True:
        sub = get(f"/subscription/{sub_id}")
        status = (sub.get("status") or sub.get("state") or "").lower()
        if status in {"active", "activated", "running", "ready"}:
            return sub
        if status in {"error", "failed"}:
            raise SystemExit(f"Subscription {sub_id} entered failure state {status}")
        if time.time() - start > timeout_s:
            raise SystemExit(f"Timeout waiting for subscription {sub_id} to become active (last status={status})")
        time.sleep(poll_s)

# ------ Core Provisioning -------
def create_subscription_from_plan(plan: Dict[str, Any]) -> str:
    """
    Creates a subscription using the minimal fields + your env-provided infra.
    Depending on your tenant, the required schema may include additional fields
    (e.g., networking, support plan). Add them below if your API returns 400.
    """
    payload = {
        "account_id": ACCOUNT_ID,
        "cloud_provider": CLOUD_PROVIDER,
        "region": CLOUD_REGION,
        "creation_plan": plan.get("creation_plan")
    }

    res = post("/subscription", payload)
    sub_id = res.get("subscription_id") or res.get("id")
    if not sub_id:
        raise SystemExit(f"Could not find subscription id in response: {res}")
    return sub_id

def create_database(sub_id: str, db: Dict[str, Any]) -> str:
    payload = {
        "name": db["name"],
        "dataset_size_in_gb": db["dataset_size_in_gb"],
        "replication": db.get("replication", False),
        "throughput_measurement_by": db.get("throughput_measurement_by", "operations-per-second"),
        "throughput_measurement_value": db.get("throughput_measurement_value", 100),
        "modules": db.get("modules", []),
        "support_oss_cluster_api": db.get("support_oss_cluster_api", False)
    }

    res = post(f"/subscription/{sub_id}/databases", payload)
    db_id = res.get("database_id") or res.get("id")
    if not db_id:
        raise SystemExit(f"Could not find database id in response: {res}")
    return db_id

# Entry Point
def main():
    if sys.stdin.isatty():
        sys.stderr.write(
            "Pipe or pass the JSON into stdin. Example: \n"
            " cat payload.json | python provision_redis_cloud.py\n"
        )
        sys.exit(2)
    spec = json.load(sys.stdin)

    # 1) Create subscription from the block
    sub_spec = spec.get("subscription") or {}
    if not sub_spec:
        raise SystemExit("Missing Subscription in input payload")
    print("Createing subscription..")
    sub_id = create_subscription_from_plan(sub_spec)
    print(f"Subscription requested: {sub_id}. Waiting for activation...")
    wait_for_subscription_active(sub_id)
    print(f"Subscription {sub_id} is active")

    # 2) Create Database
    dbs: List[Dict[str, Any]] = spec.get("databases", []) 
    for db in dbs:
        print(f"Creating database '{db.get("database"), []}")
        db_id = create_database(sub_id, db)
        print(f"Createdn database id: {db_id}")

    print("Provisionig complete")

if __name__ == "__main__":
    main()




