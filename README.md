# Raven Gate 2026 - Hard CTF (single flag)

`Raven Gate 2026` is a hard challenge with one final flag and a mandatory poly-chain:

- **Web:** parser-differential bypass (2026-inspired, CVE-2026-25960 class behavior).
- **Stego:** LSB extraction from a dynamically generated PNG carrier.
- **Crypto:** AES-256-GCM with PBKDF2-HMAC-SHA256 key derivation.

## Final objective

Recover exactly one final flag:

- `FLAG{2026_web_stego_crypto_polychain_master}`

## Local setup

1. `sudo apt-get update && sudo apt-get install -y python3-venv`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python3 app.py`

Open `http://127.0.0.1:5000`.

## End-to-end tests

### Local E2E

- `./.venv/bin/python tests/run_e2e_local.py`

### Public URL E2E (Pinggy)

- `./.venv/bin/python solve/solve_full_chain.py --base-url "https://your-subdomain.free.pinggy.link" --team "team_name"`

## Intended solve chain

1. Register team to obtain token.
2. Exploit parser differential in `/api/proxy/fetch` using URL userinfo host confusion.
3. Obtain bootstrap package from internal vault route.
4. Recover `pepper` via XOR recipe (`pepper_ct_b64u`, `token`, `salt`).
5. Derive passphrase.
6. Download team carrier PNG.
7. Extract LSB payload -> encrypted JSON.
8. Decrypt AES-GCM payload and recover final flag.
9. Submit to `/api/submit`.

## Security note

This is intentionally vulnerable and only for CTF/training.
