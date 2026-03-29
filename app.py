#!/usr/bin/env python3
import io
import os
import re
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from abyss_ctf.engine import (
    FINAL_FLAG,
    INTERNAL_HOST,
    ALLOWED_HOST,
    AbyssEngine,
    AbyssStore,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(STATIC_DIR))
store = AbyssStore()
engine = AbyssEngine(store)

TEAM_RE = re.compile(r"^[A-Za-z0-9_-]{3,36}$")
FLAG_RE = re.compile(r"^FLAG\{[A-Za-z0-9_]+\}$")


def ok(payload: dict, code: int = 200):
    return jsonify({"ok": True, **payload}), code


def err(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


def body() -> dict:
    return request.get_json(silent=True) or {}


def token() -> str:
    t = request.headers.get("X-Team-Token", "").strip()
    if t:
        return t
    d = body()
    t = str(d.get("token", "")).strip()
    if t:
        return t
    return request.args.get("token", "").strip()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return ok({"service": "abyss-gate-2026", "snapshot": store.snapshot()})


@app.get("/api/challenge")
def challenge():
    return ok(
        {
            "name": "AbyssGate 2026",
            "difficulty": "hard++",
            "category": "web+stego+crypto+supply-chain",
            "single_flag": True,
            "cve_inspiration": ["CVE-2026-25960", "CVE-2026-31976", "CVE-2026-33634"],
            "allowed_host": ALLOWED_HOST,
            "objective": "solve all stages and submit one final flag",
        }
    )


@app.post("/api/register")
def register():
    d = body()
    name = str(d.get("team_name", "")).strip()
    if not TEAM_RE.match(name):
        return err("team_name must match [A-Za-z0-9_-]{3,36}")
    try:
        sess = store.add_team(name)
    except sqlite3.IntegrityError:
        return err("team already exists", 409)
    return ok({"session": sess}, 201)


@app.post("/api/fetch")
@app.post("/api/gateway/fetch")
def gateway_fetch():
    t = token()
    if not t:
        return err("missing token", 401)
    if not store.team(t):
        return err("invalid token", 401)
    d = body()
    url = str(d.get("url", "")).strip()
    if not url:
        return err("url is required")
    out = engine.gateway_fetch(t, url)
    if not out.get("ok"):
        return err(out.get("error", "blocked"), 403)
    return ok(out)


@app.post("/api/pipeline/run")
def pipeline_run():
    t = token()
    if not t:
        return err("missing token", 401)
    if not store.team(t):
        return err("invalid token", 401)
    d = body()
    mutable_tag = str(d.get("mutable_tag", "v5")).strip()
    pin = str(d.get("pin_sha", "")).strip() or None
    out = engine.repo_artifact(t, mutable_tag, pin)
    if not out.get("ok"):
        return err(out.get("error", "pipeline error"), 403)
    return ok(out)


@app.get("/api/artifact/carrier")
@app.get("/api/repo/artifact")
def repo_artifact():
    t = token()
    tag_digest = request.args.get("tag_digest", "").strip()
    if not t:
        return err("missing token", 401)
    if not tag_digest:
        return err("tag_digest required")
    if not store.team(t):
        return err("invalid token", 401)
    try:
        png = engine.artifact(t, tag_digest)
    except Exception as exc:
        return err(str(exc), 403)
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="abyss_carrier.png")


@app.get("/api/carrier")
def carrier():
    t = token()
    if not t:
        return err("missing token", 401)
    try:
        png = engine.carrier_png(t)
    except Exception as exc:
        return err(str(exc), 403)
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="abyss_carrier.png")


@app.get("/api/metadata")
def metadata():
    t = token()
    if not t:
        return err("missing token", 401)
    if not store.team(t):
        return err("invalid token", 401)
    data = engine.metadata(t)
    if not data:
        return err("not ready", 403)
    if "next" in data:
        return err(data["next"], 403)
    return ok(data)


@app.get("/api/events")
def events():
    t = token()
    if not t:
        return err("missing token", 401)
    return ok({"events": store.events(t)})


@app.post("/api/submit")
def submit():
    t = token()
    if not t:
        return err("missing token", 401)
    d = body()
    candidate = str(d.get("flag", "")).strip()
    if not FLAG_RE.match(candidate):
        return err("bad flag format")
    solved = engine.verify(t, candidate)
    return ok({"solved": solved, "expected_single_flag": True})


@app.get("/api/hint/<int:level>")
def hint(level: int):
    hints = {
        1: "Stage-1: authority parser mismatch allows internal bootstrap fetch.",
        2: "Stage-2: mutable tags are trust boundaries; resolve the effective artifact.",
        3: "Stage-3: carrier PNG hides JSON in RGB LSB with prefixed length.",
        4: "Stage-4: decrypt chain requires secret from stage-1 and key material from stage-2.",
    }
    if level not in hints:
        return err("hint level out of range", 404)
    return ok({"level": level, "hint": hints[level]})


@app.get("/api/debug/final")
def debug_final():
    # not a bypass: only reveals flag hash
    return ok({"flag_sha256": __import__("hashlib").sha256(FINAL_FLAG.encode()).hexdigest()})


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=False)
