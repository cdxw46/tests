#!/usr/bin/env python3
import random
import string
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python")
APP = str(ROOT / "app.py")
SOLVER_A = str(ROOT / "solve" / "solve_variant_a.py")
SOLVER_B = str(ROOT / "solve" / "solve_variant_b.py")
BASE = "http://127.0.0.1:5000"
FLAG = "FLAG{2026_ultra_hard_web_stego_crypto_supplychain_abyss}"


def rid(n: int = 8) -> str:
    alpha = string.ascii_lowercase + string.digits
    return "".join(random.choice(alpha) for _ in range(n))


def wait_health():
    end = time.time() + 25
    while time.time() < end:
        try:
            r = requests.get(f"{BASE}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.35)
    raise RuntimeError("health timeout")


def run_solver(path: str, team: str):
    proc = subprocess.run(
        [PY, path, "--base-url", BASE, "--team", team],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"solver failed: {path}")
    if FLAG not in proc.stdout:
        raise RuntimeError(f"final flag missing for solver: {path}")


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
        run_solver(SOLVER_A, f"local_a_{rid()}")
        run_solver(SOLVER_B, f"local_b_{rid()}")
        print("[+] local E2E all variants passed")
    finally:
        app_proc.terminate()
        try:
            app_proc.wait(timeout=5)
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
