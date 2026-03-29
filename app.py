#!/usr/bin/env python3
import io
import os
import re
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from hard_ctf.challenge_engine import (
    CANONICAL_HOST,
    INTERNAL_HOST,
    ChallengeStore,
    RavenChallenge,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(STATIC_DIR))
store = ChallengeStore()
raven = RavenChallenge(store)

TEAM_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
FLAG_RE = re.compile(r"^FLAG\{[A-Za-z0-9_]+\}$")


def _ok(payload: dict, code: int = 200):
    return jsonify({"ok": True, **payload}), code


def _err(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _token() -> str:
    t = request.headers.get("X-Team-Token", "").strip()
    if t:
        return t
    data = _body()
    t = str(data.get("token", "")).strip()
    if t:
        return t
    return request.args.get("token", "").strip()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return _ok({"service": "raven-gate-2026", "snapshot": store.snapshot()})


@app.get("/api/challenge")
def challenge():
    return _ok(
        {
            "name": "Raven Gate 2026",
            "category": "web+stego+crypto",
            "difficulty": "hard",
            "single_flag": True,
            "cve_theme": "CVE-2026-25960 parser differential class",
            "allowed_fetch_host": CANONICAL_HOST,
            "objective": "obtain and submit one final flag",
        }
    )


@app.post("/api/register")
def register():
    data = _body()
    team_name = str(data.get("team_name", "")).strip()
    if not TEAM_RE.match(team_name):
        return _err("team_name must match [A-Za-z0-9_-]{3,32}")
    try:
        sess = store.create_session(team_name)
    except sqlite3.IntegrityError:
        return _err("team already exists", 409)
    return _ok({"session": sess}, 201)


@app.post("/api/fetch")
@app.post("/api/proxy/fetch")
def proxy_fetch():
    token = _token()
    if not token:
        return _err("missing team token", 401)
    sess = store.session_by_token(token)
    if not sess:
        return _err("invalid team token", 401)

    data = _body()
    url = str(data.get("url", "")).strip()
    if not url:
        return _err("url is required")

    guard = raven.parse_guard(url)
    if guard.get("ok") != "1":
        store.add_event(token, "fetch_denied", {"url": url, "reason": guard.get("error", "blocked")})
        return _err(guard.get("error", "blocked"), 403)

    effective = guard["effective_host"]
    if effective == INTERNAL_HOST:
        clue = raven.reveal_internal_bootstrap(token)
        store.add_event(
            token,
            "fetch_internal",
            {"url": url, "validated_host": guard["validated_host"], "effective_host": effective},
        )
        return _ok(
            {
                "validated_host": guard["validated_host"],
                "effective_host": effective,
                "response": {"source": "internal_vault", "clue": clue},
            }
        )

    store.add_event(
        token,
        "fetch_public",
        {"url": url, "validated_host": guard["validated_host"], "effective_host": effective},
    )
    return _ok(
        {
            "validated_host": guard["validated_host"],
            "effective_host": effective,
            "response": {
                "source": "public_docs",
                "data": {
                    "note": "No secrets here. parser differential matters.",
                    "policy": "trusted host only",
                },
            },
        }
    )


@app.get("/api/carrier")
def carrier():
    token = _token()
    if not token:
        return _err("missing token", 401)
    try:
        png_data = raven.team_carrier(token)
    except Exception as exc:
        return _err(str(exc), 403)
    return send_file(io.BytesIO(png_data), mimetype="image/png", download_name="raven_carrier.png")


@app.get("/api/metadata")
def metadata():
    token = _token()
    if not token:
        return _err("missing token", 401)
    meta = raven.metadata(token)
    if not meta:
        return _err("invalid token", 401)
    return _ok(meta)


@app.get("/api/stats")
def stats():
    token = _token()
    if not token:
        return _err("missing token", 401)
    return _ok({"events": store.events(token)})


@app.post("/api/submit")
def submit():
    token = _token()
    if not token:
        return _err("missing team token", 401)
    data = _body()
    candidate = str(data.get("flag", "")).strip()
    if not FLAG_RE.match(candidate):
        return _err("bad flag format")
    if raven.verify(token, candidate):
        return _ok({"solved": True, "message": "challenge solved"})
    return _ok({"solved": False, "message": "incorrect flag"})


@app.get("/api/hint/<int:level>")
def hint(level: int):
    hints = {
        1: "Validator and fetcher parse URL authority differently.",
        2: f"Guard expects {CANONICAL_HOST} but internal host is {INTERNAL_HOST}.",
        3: "Recover pepper from XOR recipe in internal clue.",
        4: "Carrier PNG stores AES-GCM JSON blob in RGB LSB stream.",
    }
    if level not in hints:
        return _err("hint level out of range", 404)
    return _ok({"level": level, "hint": hints[level]})


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=False)
