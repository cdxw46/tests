import json
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from ctf_2026_pipeline.challenge import ChallengeStore, VulnerableRunner


BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
store = ChallengeStore()
runner = VulnerableRunner(store)

TEAM_RE = re.compile(r"^[A-Za-z0-9_\-]{3,40}$")
FLAG_RE = re.compile(r"^FLAG\{[A-Za-z0-9_]+\}$")


def _ok(payload: dict, code: int = 200):
    return jsonify({"ok": True, **payload}), code


def _err(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


def _input_data():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict() if request.form else {}


def _team_from_request():
    token = request.headers.get("X-Team-Token", "").strip()
    if not token:
        token = request.args.get("token", "").strip()
    if not token:
        token = str(_input_data().get("token", "")).strip()
    if not token:
        return None
    return store.get_team_by_token(token)


def _is_loopback_client() -> bool:
    addr = request.remote_addr or ""
    return addr in {"127.0.0.1", "::1"}


@app.get("/")
def index():
    return render_template("index.html", snapshot=store.state_snapshot())


@app.get("/api/health")
def health():
    return _ok(
        {
            "service": "ci-phantom-2026",
            "snapshot": store.state_snapshot(),
            "policy": runner.egress_policy,
            "hint": "branch_name / pr_title are used in shell output during pipeline execution",
        }
    )


@app.post("/api/register")
def register():
    data = _input_data()
    team_name = str(data.get("team_name", "")).strip()
    if not TEAM_RE.match(team_name):
        return _err("team_name must match [A-Za-z0-9_-]{3,40}")
    if store.get_team(team_name):
        return _err("team_name already exists", 409)
    team = store.register_team(team_name)
    store.add_event("team_registered", {"team_name": team["team_name"]})
    return _ok({"team": team}, 201)


@app.post("/api/run")
def trigger_run():
    team = _team_from_request()
    if not team:
        return _err("invalid team token", 401)
    data = _input_data()
    branch_name = str(data.get("branch_name", "")).strip()
    pr_title = str(data.get("pr_title", "")).strip()
    workflow_body = str(data.get("workflow_body", "")).strip()
    if not branch_name or not pr_title:
        return _err("branch_name and pr_title are required")
    if not workflow_body:
        workflow_body = "echo '[+] no release notes provided'"
    if len(branch_name) > 220 or len(pr_title) > 300 or len(workflow_body) > 5000:
        return _err("payload too large")

    # Weak protection: blocks obvious local URL usage in workflow_body only.
    # branch_name and pr_title are still directly interpolated into shell context.
    lowered = workflow_body.lower()
    if "127.0.0.1" in lowered or "localhost" in lowered:
        return _err("workflow_body blocked by release policy")

    rc, run_log = runner.run_pipeline(team, branch_name, pr_title, workflow_body)
    status = "passed" if rc == 0 else "failed"
    store.add_run(team["id"], branch_name, pr_title, workflow_body, run_log, status)
    store.add_event(
        "pipeline_run",
        {
            "team_name": team["team_name"],
            "status": status,
            "branch_name": branch_name,
        },
    )
    return _ok({"status": status, "return_code": rc, "run_log": run_log})


@app.get("/api/runs")
def runs():
    team = _team_from_request()
    if not team:
        return _err("invalid team token", 401)
    return _ok({"runs": store.recent_runs(team["id"])})


@app.get("/api/events")
def events():
    team = _team_from_request()
    if not team:
        return _err("invalid team token", 401)
    return _ok({"events": store.recent_events()})


@app.post("/api/runner/dns-tcp")
def dns_tcp_exfil():
    # Simulated egress-policy bypass over DNS TCP. Local runner only.
    if not _is_loopback_client():
        return _err("runner only endpoint", 403)
    data = _input_data()
    supplied_token = str(data.get("token", ""))
    if supplied_token != runner.pipeline_token:
        return _err("invalid runner token", 401)

    team_name = str(data.get("team_name", "")).strip()
    qname = str(data.get("qname", "exfil.challenge.local")).strip()[:255]
    team = store.get_team(team_name)
    if not team:
        return _err("unknown team", 404)
    runner.exfil_dns_tcp(team, qname)
    return _ok({"accepted": True, "qname": qname}, 201)


@app.get("/internal/vault/root")
def internal_root_flag():
    if not _is_loopback_client():
        return _err("internal only", 403)
    password = request.args.get("password", "")
    if password != store.get_vault("admin_password"):
        return _err("bad password", 401)
    return _ok({"flag": store.get_vault("flag_root")})


@app.get("/internal/vault/user")
def internal_user_flag():
    if not _is_loopback_client():
        return _err("internal only", 403)
    supplied_token = request.args.get("token", "")
    if supplied_token != runner.pipeline_token:
        return _err("bad token", 401)
    return _ok({"flag": store.get_vault("flag_user")})


@app.post("/api/submit")
def submit_flags():
    team = _team_from_request()
    if not team:
        return _err("invalid team token", 401)
    data = _input_data()
    user_flag = str(data.get("user_flag", "")).strip()
    root_flag = str(data.get("root_flag", "")).strip()
    if not FLAG_RE.match(user_flag) or not FLAG_RE.match(root_flag):
        return _err("invalid flag format")

    solved = (
        user_flag == store.get_vault("flag_user")
        and root_flag == store.get_vault("flag_root")
    )
    if not solved:
        return _ok({"solved": False, "message": "incorrect flags"}, 200)
    store.add_event("challenge_solved", {"team_name": team["team_name"]})
    return _ok(
        {
            "solved": True,
            "final_flag": "FLAG{2026_ci_phantom_dualpath_master}",
            "team_name": team["team_name"],
        }
    )


@app.get("/api/challenge")
def challenge_info():
    return _ok(
        {
            "name": "CI Phantom 2026",
            "difficulty": "hard",
            "category": "web",
            "inspired_by": ["CVE-2026-33475", "CVE-2026-27938", "CVE-2026-32946"],
            "win_condition": "exfiltrate both flags via different paths and submit",
        }
    )


@app.get("/api/debug/snapshot")
def debug_snapshot():
    # Public but harmless metadata that helps players reason about state.
    snapshot = store.state_snapshot()
    return _ok({"snapshot": snapshot, "now": json.dumps(snapshot)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
