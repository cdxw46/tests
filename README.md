# AbyssGate 2026 - Ultra Hard CTF (single flag)

`AbyssGate 2026` is a harder replacement challenge with a strict one-flag poly-chain inspired by 2026 vulnerability classes:

- Parser-differential SSRF bypass (CVE-2026-25960 class).
- Mutable tag poisoning/trust abuse in CI artifact resolution (CVE-2026-31976 / CVE-2026-33634 class).
- PNG LSB steganography with checksum framing.
- ChaCha20-Poly1305 decryption with PBKDF2-derived key tied to prior artifacts.

## Final objective

Recover exactly one final flag:

- `FLAG{2026_ultra_hard_web_stego_crypto_supplychain_single}`

## Setup

1. `sudo apt-get update && sudo apt-get install -y python3-venv`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python3 app.py`

Open `http://127.0.0.1:5000`.

## End-to-end tests

### Local E2E (two independent solver variants)

- `./.venv/bin/python tests/run_e2e_local.py`

### Public URL E2E (Pinggy)

- `./.venv/bin/python solve/solve_variant_a.py --base-url "https://your-subdomain.free.pinggy.link" --team "team_a"`
- `./.venv/bin/python solve/solve_variant_b.py --base-url "https://your-subdomain.free.pinggy.link" --team "team_b"`

## Stages (intended chain)

1. Register team and obtain token.
2. Use `/api/gateway/fetch` with parser differential URL to hit internal vault and get bootstrap `seed`.
3. Abuse mutable tag in `/api/repo/artifact` (`v5`) to force poisoned artifact resolution and obtain `tag_digest`.
4. Pull key-material from `/api/metadata`, recover `vault_pepper` from `vault_cipher`.
5. Download `/api/carrier` (PNG), extract LSB payload (JSON blob).
6. Derive key and decrypt ChaCha20-Poly1305 payload, then submit the one final flag.

## Security note

This challenge is intentionally vulnerable and only for CTF/training use.
