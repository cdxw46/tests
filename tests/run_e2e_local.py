#!/usr/bin/env python3
import random
import string
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY = str(ROOT / ".venv" / "bin" / "python")
APP = str(ROOT / "app.py")
SOLVER = str(ROOT / "solve" / "solve_full_chain.py")
BASE = "http://127.0.0.1:5000"


def wait_health():
    end = time.time() + 20
    while time.time() < end:
        try:
            r = requests.get(f"{BASE}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("health timeout")


def rid(n=8):
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def run_solver():
    team = f"local_{rid()}"
    proc = subprocess.run(
        [PY, SOLVER, "--base-url", BASE, "--team", team],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError("solver failed")
    if "FLAG{2026_web_stego_crypto_polychain_master}" not in proc.stdout:
        raise RuntimeError("final flag missing in solver output")


def main():
    app_proc = subprocess.Popen(
        [PY, APP],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_health()
        run_solver()
        print("[+] local E2E passed")
    finally:
        app_proc.terminate()
        try:
            app_proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            app_proc.kill()
        if app_proc.stdout:
            tail = app_proc.stdout.read()
            if tail:
                print("----- app tail -----")
                print(tail)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] local E2E failed: {exc}")
        sys.exit(1)
