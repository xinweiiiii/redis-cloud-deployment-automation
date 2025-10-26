#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv
load_dotenv()

BASE_URL = os.getenv("REDIS_CLOUD_BASE_URL", "https://api.redislabs.com/v1")
ACCOUNT_API_KEY = os.getenv("REDIS_CLOUD_ACCOUNT_KEY")
USER_API_KEY = os.getenv("REDIS_CLOUD_API_KEY")

def auth_headers():
    return {
        "x-api-key": ACCOUNT_API_KEY,
        "x-api-secret-key": USER_API_KEY,
        "Content-Type": "application/json"
    }

def list_payment_methods():
    url = f"{BASE_URL.rstrip('/')}/payment-methods"
    r = requests.get(url, headers=auth_headers(), timeout=30)
    if not r.ok:
        raise SystemExit(f"HTTP {r.status_code}: {r.text}")
    data = r.json()
    print(json.dumps(data, indent=2))
    return data

if __name__ == "__main__":
    import json
    pm_list = list_payment_methods()
    print("\nAvailable payment method IDs:")
    for pm in pm_list.get("paymentMethods", pm_list):
        print(f"- {pm.get('id')} ({pm.get('type')})")