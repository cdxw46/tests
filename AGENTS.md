# AGENTS.md

## Cursor Cloud specific instructions

### Repository structure

This is a CTF (Capture The Flag) challenges repository. The `main` branch contains only a placeholder file. All application code lives on **separate feature branches**, each representing an independent CTF challenge:

| Branch | App | Type |
|--------|-----|------|
| `cursor/-bc-fb3e776b-8225-4d66-a058-91d81f78afcf-391e` | **Phantom Corp** | Flask web app (JWT + SQLi + SSRF) |
| `cursor/cves-para-reto-ctf-b3f9` | **AbyssGate 2026** | Flask web app (SSRF + stego + crypto + supply-chain) |
| Other branches | Solver scripts / writeups | Standalone Python scripts or docs |

### Running the Flask apps

Both deployable apps use **Python 3.12 + Flask + SQLite** (no external DB needed). To work on a specific app, check out or create a worktree from its branch:

```bash
git worktree add /tmp/phantom-corp remotes/origin/cursor/-bc-fb3e776b-8225-4d66-a058-91d81f78afcf-391e
git worktree add /tmp/abyssgate remotes/origin/cursor/cves-para-reto-ctf-b3f9
```

**Phantom Corp** (port 5000):
```bash
source /workspace/.venv/bin/activate
cd /tmp/phantom-corp/phantom-corp
python run.py
```
- Login: `employee` / `corp2026!` (user role)
- DB is pre-seeded in the committed `instance/phantom.db`; running `init_db.py` again will fail with a UNIQUE constraint (safe to skip)

**AbyssGate 2026** (port 5000):
```bash
source /workspace/.venv/bin/activate
cd /tmp/abyssgate
python app.py
```
- Has E2E tests: `python tests/run_e2e_local.py` (requires `.venv` symlink at the app root pointing to `/workspace/.venv`)

### Key caveats

- Only one Flask app can run on port 5000 at a time. Kill the current one before starting another, or override the port via `PORT=5001 python app.py`.
- The AbyssGate E2E test script (`tests/run_e2e_local.py`) expects a venv at `<app_root>/.venv/bin/python`. Create a symlink: `ln -sf /workspace/.venv /tmp/abyssgate/.venv`.
- No linter or type checker is configured in this repository.
- Solver scripts on other branches target remote HTB/PicoCTF infrastructure and cannot be tested locally.
