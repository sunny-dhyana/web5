#!/usr/bin/env python3
"""
Mercury Lab — Unified PoC Runner
Run any of the 20 vulnerability PoCs from a single interactive menu.

Usage:
    python run_pocs.py
    python run_pocs.py --url http://target:8000
"""

import argparse
import os
import subprocess
import sys

# ─────────────────────────────────────────────
# ANSI colours (auto-disabled when not a tty)
# ─────────────────────────────────────────────
_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _c(text, code): return f"\033[{code}m{text}\033[0m" if _COLOR else text

RED    = lambda t: _c(t, "31")
GREEN  = lambda t: _c(t, "32")
YELLOW = lambda t: _c(t, "33")
BLUE   = lambda t: _c(t, "34")
CYAN   = lambda t: _c(t, "36")
BOLD   = lambda t: _c(t, "1")
DIM    = lambda t: _c(t, "2")

# ─────────────────────────────────────────────
# PoC registry — (vuln_id, display_name, filename)
# ─────────────────────────────────────────────
CATEGORIES = [
    ("INJECTION", [
        ("VULN-001", "OS Command Injection",                              "poc_001_os_command_injection.py"),
        ("VULN-002", "File Upload Bypass",                                "poc_002_file_upload_bypass.py"),
        ("VULN-003", "SSRF via Profile Picture URL",                      "poc_003_ssrf_profile_picture.py"),
        ("SQLI-1",   "UNION-Based SQL Injection via Product Search",      "poc_016_sqli_product_search.py"),
        ("SQLI-2",   "Second-Order SQL Injection via Product Category",   "poc_017_second_order_sqli.py"),
        ("SSTI-1",   "SSTI via Product Thank-You Message (Jinja2 RCE)",   "poc_019_ssti_order_confirmation.py"),
    ]),
    ("BROKEN ACCESS CONTROL", [
        ("BAC-1",    "Mass Assignment → Role Escalation",                 "poc_005_mass_assignment_role_escalation.py"),
        ("BAC-2",    "IDOR on Wallet Transaction History",                "poc_006_idor_transaction_history.py"),
        ("BAC-3",    "BOLA: Any Seller Ships Any Order",                  "poc_007_bola_ship_any_order.py"),
        ("BAC-4",    "Horizontal BAC: Any User Reads Any Order",          "poc_008_bola_order_detail.py"),
        ("BAC-5",    "Function-Level AuthZ: Admin Stats Exposed",         "poc_009_function_level_authz_stats.py"),
        ("BAC-6",    "Wallet Transfer: IDOR + Self-Transfer Inflation",   "poc_018_wallet_transfer_idor_selftransfer.py"),
    ]),
    ("BUSINESS LOGIC", [
        ("VULN-004", "Partial Refund Accumulation",                       "poc_004_partial_refund_accumulation.py"),
        ("BL-1",     "Negative Quantity → Wallet Inflation",              "poc_010_negative_quantity_wallet_inflation.py"),
        ("BL-2",     "Negative Payout → Pending Balance Inflation",       "poc_011_negative_payout_balance_inflation.py"),
        ("BL-3",     "TOCTOU Race Condition on Inventory",                "poc_012_toctou_inventory_race.py"),
        ("BL-4",     "Float Precision: Zero-Total Order",                 "poc_013_float_precision_zero_total.py"),
        ("BL-5",     "Frozen Escrow via Seller-Cancelled Shipped Order",  "poc_014_frozen_escrow_shipped_cancel.py"),
    ]),
    ("XSS", [
        ("XSS-1",    "Stored XSS via Product Description",                "poc_015_stored_xss_product_description.py"),
    ]),
    ("AUTHENTICATION", [
        ("AUTHN-1",  "JWT kid Path Traversal → Admin Privilege Escalation","poc_020_jwt_kid_path_traversal.py"),
    ]),
]

POCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

# Build flat indexed list
FLAT: list[tuple[str, str, str]] = []
for _, entries in CATEGORIES:
    FLAT.extend(entries)

W = 68  # menu width


# ─────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────

def print_banner(base_url: str):
    print()
    print(BOLD("╔" + "═" * (W - 2) + "╗"))
    print(BOLD("║") + BOLD("  Mercury Lab — Unified PoC Runner".center(W - 2)) + BOLD("║"))
    print(BOLD("╚" + "═" * (W - 2) + "╝"))
    print(f"  Target  :  {CYAN(base_url)}")
    print(f"  PoCs    :  {len(FLAT)} vulnerabilities loaded")
    print()


def print_menu(base_url: str):
    print_banner(base_url)

    idx = 1
    for cat_name, entries in CATEGORIES:
        label = f"  ── {cat_name} "
        print(YELLOW(label + "─" * (W - len(label))))
        for vuln_id, name, _ in entries:
            num   = BOLD(f"[{idx:>2}]")
            vid   = DIM(f"{vuln_id:<10}")
            print(f"   {num}  {vid}  {name}")
            idx += 1
        print()

    print(f"   {BOLD('[all]')}  Run all PoCs sequentially")
    print(f"   {BOLD('[  0]')}  Exit")
    print()
    print(DIM("─" * W))
    print()


def run_poc(vuln_id: str, name: str, poc_file: str, base_url: str, extra_args: list[str]):
    path = os.path.join(POCS_DIR, poc_file)
    cmd  = [sys.executable, path, "--url", base_url] + extra_args

    print()
    print(BOLD("┌" + "─" * (W - 2) + "┐"))
    print(BOLD("│") + f"  {CYAN(vuln_id)}  {name}".ljust(W - 2) + BOLD("│"))
    print(BOLD("└" + "─" * (W - 2) + "┘"))
    print(DIM(f"  cmd: {' '.join(cmd)}"))
    print()

    result = subprocess.run(cmd)

    print()
    if result.returncode == 0:
        print(GREEN(f"  ✓  Completed (exit 0)"))
    else:
        print(RED(f"  ✗  Completed (exit {result.returncode})"))
    print(DIM("─" * W))


def ask_extra_args(vuln_id: str, poc_file: str) -> list[str]:
    print(DIM(f"  Extra args for {vuln_id}? (Enter to use defaults)"))
    print(DIM(f"  e.g. --cmd whoami   --exploit self   --payload \"<img src=x>\""))
    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return []
    import shlex
    return shlex.split(raw) if raw else []


def pause():
    try:
        input(f"\n  {DIM('Press Enter to return to menu...')}")
    except (EOFError, KeyboardInterrupt):
        pass


# ─────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mercury Lab — Unified PoC Runner")
    parser.add_argument("--url", default="http://192.168.1.34:8005/",
                        help="Target base URL (default: http://192.168.1.34:8005/)")
    args       = parser.parse_args()
    base_url   = args.url.rstrip("/")

    print_menu(base_url)

    while True:
        try:
            raw = input(f"  {BOLD('Select')} (1-{len(FLAT)}, all, 0): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Bye.")
            sys.exit(0)

        # ── exit ──────────────────────────────
        if raw in ("0", "q", "exit", "quit"):
            print("  Bye.")
            sys.exit(0)

        # ── redraw menu ───────────────────────
        if raw in ("m", "menu", ""):
            print_menu(base_url)
            continue

        # ── run all ───────────────────────────
        if raw == "all":
            print(f"\n  {YELLOW(f'Running all {len(FLAT)} PoCs sequentially...')}")
            passed = failed = 0
            for vuln_id, name, poc_file in FLAT:
                run_poc(vuln_id, name, poc_file, base_url, [])
                # small visual gap between runs
                print()
            print(BOLD(f"\n  All PoCs finished."))
            pause()
            print_menu(base_url)
            continue

        # ── single selection ──────────────────
        try:
            choice = int(raw)
        except ValueError:
            print(RED("  Invalid input. Enter a number, 'all', or 0."))
            continue

        if not (1 <= choice <= len(FLAT)):
            print(RED(f"  Out of range. Enter 1–{len(FLAT)}."))
            continue

        vuln_id, name, poc_file = FLAT[choice - 1]
        print(f"\n  Selected: {BOLD(vuln_id)} — {name}")
        extra = ask_extra_args(vuln_id, poc_file)
        run_poc(vuln_id, name, poc_file, base_url, extra)
        pause()
        print_menu(base_url)


if __name__ == "__main__":
    main()
