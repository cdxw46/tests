# CI Phantom 2026 - Hard Web CTF Challenge

`CI Phantom 2026` is a deliberately vulnerable web challenge modeled after real 2026 CI/CD classes of flaws:

- Context-variable shell injection in CI workflows (CVE-2026-33475 / CVE-2026-27938 style).
- DNS TCP egress-policy bypass behavior in runners (CVE-2026-32946 style).

## What is included

- Full Flask web challenge with frontend + API.
- Two different intended exploit paths.
- Automated local end-to-end test harness.
- Public URL solvers for Pinggy-deployed instance.

## Setup

1. Install prerequisites (if needed):
   - `sudo apt-get update && sudo apt-get install -y python3-venv`
2. Create virtual environment and install deps:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Run service:
   - `python3 app.py`
4. Open:
   - `http://127.0.0.1:5000`

## End-to-end testing

### Local complete E2E

- `python3 tests/run_e2e_local.py`

This starts the app, runs solve method A and B, and verifies final flag submission.

### Public URL E2E (Pinggy)

Run against your exposed URL:

- `python3 solve/method_a_internal_api.py --base-url "https://your-subdomain.free.pinggy.link"`
- `python3 solve/method_b_dns_tcp.py --base-url "https://your-subdomain.free.pinggy.link"`

## Solve paths

- **Method A (context injection path):**
  - Exploit shell interpolation through `branch_name`.
  - Read internal `/internal/vault/user` using pipeline token.
  - Capture user flag.

- **Method B (dns tcp path):**
  - Leak `GITHUB_TOKEN` and `ADMIN_PASS` from vulnerable run context.
  - Call local `/api/runner/dns-tcp` from runner context.
  - Use leaked admin password to read `/internal/vault/root`.
  - Submit both flags and recover final master flag.

## Files

- `app.py`: Flask app and challenge endpoints.
- `ctf_2026_pipeline/challenge.py`: DB + vulnerable runner logic.
- `solve/method_a_internal_api.py`: solver for path A.
- `solve/method_b_dns_tcp.py`: solver for path B.
- `tests/run_e2e_local.py`: automated end-to-end local verifier.

## Security notice

This project is intentionally vulnerable and for CTF/training only. Do not deploy in production.
