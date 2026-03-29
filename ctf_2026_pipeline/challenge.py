import base64
import hashlib
import json
import os
import random
import sqlite3
import string
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "challenge.db"


def _rand_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


class ChallengeStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._bootstrap()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _bootstrap(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT UNIQUE NOT NULL,
                    api_token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    branch_name TEXT NOT NULL,
                    pr_title TEXT NOT NULL,
                    workflow_body TEXT NOT NULL,
                    run_log TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(team_id) REFERENCES teams(id)
                );

                CREATE TABLE IF NOT EXISTS vault (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

            cur = conn.execute("SELECT value FROM vault WHERE key = 'flag_user'")
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO vault(key, value) VALUES('flag_user', ?)",
                    ("FLAG{2026_ci_context_injection_user_path}",),
                )
            cur = conn.execute("SELECT value FROM vault WHERE key = 'flag_root'")
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO vault(key, value) VALUES('flag_root', ?)",
                    ("FLAG{2026_dns_tcp_egress_bypass_root_path}",),
                )
            cur = conn.execute("SELECT value FROM vault WHERE key = 'admin_password'")
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO vault(key, value) VALUES('admin_password', ?)",
                    (_rand_token(24),),
                )
            conn.commit()

    def register_team(self, team_name: str) -> dict:
        token = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO teams(team_name, api_token, created_at) VALUES (?, ?, ?)",
                (team_name, token, _now()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, team_name, api_token, created_at FROM teams WHERE team_name = ?",
                (team_name,),
            ).fetchone()
        return dict(row)

    def get_team_by_token(self, api_token: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, team_name, api_token, created_at FROM teams WHERE api_token = ?",
                (api_token,),
            ).fetchone()
        return dict(row) if row else None

    def get_team(self, team_name: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, team_name, api_token, created_at FROM teams WHERE team_name = ?",
                (team_name,),
            ).fetchone()
        return dict(row) if row else None

    def add_event(self, event_type: str, detail: dict):
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO events(event_type, detail, created_at) VALUES (?, ?, ?)",
                (event_type, json.dumps(detail, sort_keys=True), _now()),
            )
            conn.commit()

    def recent_events(self, limit: int = 15):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event_type, detail, created_at FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_run(self, team_id: int, branch_name: str, pr_title: str, workflow_body: str, run_log: str, status: str):
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs(team_id, branch_name, pr_title, workflow_body, run_log, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (team_id, branch_name, pr_title, workflow_body, run_log, status, _now()),
            )
            conn.commit()

    def recent_runs(self, team_id: int, limit: int = 20):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, team_id, branch_name, pr_title, workflow_body, run_log, status, created_at
                FROM runs
                WHERE team_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (team_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_vault(self, key: str) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM vault WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else ""

    def state_snapshot(self):
        with self._connect() as conn:
            team_count = conn.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
            run_count = conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]
        return {"teams": team_count, "runs": run_count}


class VulnerableRunner:
    """
    Deliberately vulnerable CI runner emulation.
    """

    def __init__(self, store: ChallengeStore):
        self.store = store
        self.egress_policy = {
            "mode": "block",
            "allowed_endpoints": ["github.com:443", "api.github.com:443"],
        }
        self.pipeline_token = hashlib.sha256(_rand_token(18).encode()).hexdigest()[:24]

    def _build_env(self, team: dict, branch_name: str, pr_title: str, workflow_body: str):
        env = os.environ.copy()
        env["GITHUB_HEAD_REF"] = branch_name
        env["GITHUB_PR_TITLE"] = pr_title
        env["GITHUB_PR_BODY"] = workflow_body
        env["CHALLENGE_TEAM"] = team["team_name"]
        env["GITHUB_TOKEN"] = self.pipeline_token
        env["FLAG_USER"] = self.store.get_vault("flag_user")
        env["ADMIN_PASS"] = self.store.get_vault("admin_password")
        env["EGR_POLICY"] = json.dumps(self.egress_policy)
        return env

    def run_pipeline(self, team: dict, branch_name: str, pr_title: str, workflow_body: str):
        # Vulnerable interpolation akin to 2026 CI injection incidents.
        # Intentionally uses untrusted branch/title/body inside shell script.
        with tempfile.TemporaryDirectory(prefix="ci-phantom-") as td:
            script = Path(td) / "pipeline.sh"
            script.write_text(
                f"""#!/usr/bin/env bash
set -euo pipefail
echo "[+] CI Phantom 2026 Runner"
echo "[+] Team: {team['team_name']}"
echo "[+] Branch: {branch_name}"
echo "[+] PR title: {pr_title}"
echo "[+] Policy mode: block (DNS TCP gap intentionally present)"
echo "[+] Running release checks..."
echo "[+] Lint ok"
echo "[+] Unit tests ok"
echo "[+] Publishing artifacts..."
{workflow_body}
echo "[+] Done"
""",
                encoding="utf-8",
            )
            os.chmod(script, 0o755)
            env = self._build_env(team, branch_name, pr_title, workflow_body)
            proc = subprocess.run(
                ["/bin/bash", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                timeout=20,
            )
            return proc.returncode, proc.stdout

    def exfil_dns_tcp(self, team: dict, qname: str):
        # Simulated DNS TCP egress bypass: if mode block, this path still "works".
        token = self.pipeline_token
        root_flag = self.store.get_vault("flag_root")
        msg = {
            "team": team["team_name"],
            "qname": qname,
            "token_fragment": token[:10],
            "root_flag": root_flag,
            "ts": _now(),
        }
        self.store.add_event("dns_tcp_exfil", msg)
        return msg
