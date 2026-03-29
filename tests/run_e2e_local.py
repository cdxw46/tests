#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python")
APP = str(ROOT / "app.py")
SOLVE_A = str(ROOT / "solve" / "method_a_internal_api.py")
SOLVE_B = str(ROOT / "solve" / "method_b_dns_tcp.py")
BASE_URL = "http://127.0.0.1:5000"


def wait_health(url: str, timeout: float = 20.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.get(f"{url}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("service did not become healthy in time")


def run_cmd(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}")


def main():
    app_proc = subprocess.Popen([PY, APP], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_health(BASE_URL)
        print("[+] service healthy")
        run_cmd([PY, SOLVE_A, "--base-url", BASE_URL])
        run_cmd([PY, SOLVE_B, "--base-url", BASE_URL, "--team", "team_dns_local_2026"])
        print("[+] Local E2E completed for both solve paths")
    finally:
        app_proc.terminate()
        try:
            app_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app_proc.kill()
        if app_proc.stdout:
            remaining = app_proc.stdout.read()
            if remaining:
                print("----- app log tail -----")
                print(remaining)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] E2E failed: {exc}")
        sys.exit(1)
