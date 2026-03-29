import base64
import hashlib
import hmac
import json
import random
import sqlite3
import string
import time
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


DB_PATH = Path(__file__).resolve().parent / "challenge.db"
MASTER_FLAG = "FLAG{2026_web_stego_crypto_polychain_master}"
CANONICAL_HOST = "trusted.raven-ctf.local"
INTERNAL_HOST = "vault.raven-ctf.local"


def now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def randstr(n: int = 16) -> str:
    alpha = string.ascii_letters + string.digits
    return "".join(random.choice(alpha) for _ in range(n))


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64u_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + pad)


def derive_key(passphrase: str, salt: bytes, rounds: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, rounds, dklen=32)


def aes_gcm_encrypt(plain: bytes, passphrase: str, rounds: int = 410000) -> Dict[str, str]:
    salt = hashlib.sha256((passphrase + "::salt").encode()).digest()[:16]
    nonce = hashlib.sha256((passphrase + "::nonce").encode()).digest()[:12]
    key = derive_key(passphrase, salt, rounds)
    ct = AESGCM(key).encrypt(nonce, plain, None)
    return {
        "alg": "AES-256-GCM",
        "kdf": "PBKDF2-HMAC-SHA256",
        "rounds": rounds,
        "salt_b64u": b64u(salt),
        "nonce_b64u": b64u(nonce),
        "ciphertext_b64u": b64u(ct),
    }


def aes_gcm_decrypt(payload: Dict[str, str], passphrase: str) -> bytes:
    salt = b64u_decode(payload["salt_b64u"])
    nonce = b64u_decode(payload["nonce_b64u"])
    ct = b64u_decode(payload["ciphertext_b64u"])
    rounds = int(payload["rounds"])
    key = derive_key(passphrase, salt, rounds)
    return AESGCM(key).decrypt(nonce, ct, None)


def xor_bytes(data: bytes, key: bytes) -> bytes:
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return bytes(out)


def png_crc(chunk_type: bytes, chunk_data: bytes) -> bytes:
    import zlib

    return zlib.crc32(chunk_type + chunk_data).to_bytes(4, "big")


def simple_png(width: int, height: int, rgb: Tuple[int, int, int]) -> bytes:
    import struct
    import zlib

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = len(ihdr_data).to_bytes(4, "big") + b"IHDR" + ihdr_data + png_crc(b"IHDR", ihdr_data)
    row = bytes([rgb[0], rgb[1], rgb[2]]) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    idat_data = zlib.compress(raw, level=9)
    idat = len(idat_data).to_bytes(4, "big") + b"IDAT" + idat_data + png_crc(b"IDAT", idat_data)
    iend = (0).to_bytes(4, "big") + b"IEND" + b"" + png_crc(b"IEND", b"")
    return sig + ihdr + idat + iend


def read_png_rgb(png_bytes: bytes) -> Tuple[int, int, List[Tuple[int, int, int]]]:
    import struct
    import zlib

    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not png")
    pos = 8
    width = height = 0
    idat_parts = []
    while pos < len(png_bytes):
        if pos + 8 > len(png_bytes):
            break
        length = int.from_bytes(png_bytes[pos : pos + 4], "big")
        ctype = png_bytes[pos + 4 : pos + 8]
        cdata = png_bytes[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bitd, color_type, _, _, _ = struct.unpack(">IIBBBBB", cdata)
            if bitd != 8 or color_type != 2:
                raise ValueError("unsupported png format")
        elif ctype == b"IDAT":
            idat_parts.append(cdata)
        elif ctype == b"IEND":
            break
    raw = zlib.decompress(b"".join(idat_parts))
    pixels = []
    stride = width * 3 + 1
    for y in range(height):
        row = raw[y * stride : (y + 1) * stride]
        if not row or row[0] != 0:
            raise ValueError("unsupported filter")
        body = row[1:]
        for x in range(width):
            i = x * 3
            pixels.append((body[i], body[i + 1], body[i + 2]))
    return width, height, pixels


def write_png_rgb(width: int, height: int, pixels: List[Tuple[int, int, int]]) -> bytes:
    import struct
    import zlib

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = len(ihdr_data).to_bytes(4, "big") + b"IHDR" + ihdr_data + png_crc(b"IHDR", ihdr_data)
    rows = []
    idx = 0
    for _ in range(height):
        row = bytearray()
        for _ in range(width):
            r, g, b = pixels[idx]
            idx += 1
            row.extend([r, g, b])
        rows.append(b"\x00" + bytes(row))
    idat_data = zlib.compress(b"".join(rows), level=9)
    idat = len(idat_data).to_bytes(4, "big") + b"IDAT" + idat_data + png_crc(b"IDAT", idat_data)
    iend = (0).to_bytes(4, "big") + b"IEND" + b"" + png_crc(b"IEND", b"")
    return sig + ihdr + idat + iend


def lsb_embed(png_bytes: bytes, payload: bytes) -> bytes:
    width, height, pixels = read_png_rgb(png_bytes)
    data = len(payload).to_bytes(4, "big") + payload
    bits = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    capacity = len(pixels) * 3
    if len(bits) > capacity:
        raise ValueError("payload too large")
    out = []
    bi = 0
    for r, g, b in pixels:
        channels = [r, g, b]
        for ci in range(3):
            if bi < len(bits):
                channels[ci] = (channels[ci] & 0xFE) | bits[bi]
                bi += 1
        out.append((channels[0], channels[1], channels[2]))
    return write_png_rgb(width, height, out)


def lsb_extract(png_bytes: bytes) -> bytes:
    _w, _h, pixels = read_png_rgb(png_bytes)
    bits = []
    for r, g, b in pixels:
        bits.extend([r & 1, g & 1, b & 1])
    data = bytearray()
    for i in range(0, len(bits), 8):
        if i + 8 > len(bits):
            break
        v = 0
        for bit in bits[i : i + 8]:
            v = (v << 1) | bit
        data.append(v)
    if len(data) < 4:
        raise ValueError("missing lsb payload")
    size = int.from_bytes(data[:4], "big")
    blob = bytes(data[4 : 4 + size])
    if len(blob) != size:
        raise ValueError("truncated lsb payload")
    return blob


class ChallengeStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.bootstrap()

    def conn(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def bootstrap(self):
        with self.conn() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT UNIQUE NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    phase INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS secrets (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            if con.execute("SELECT value FROM secrets WHERE key='pepper'").fetchone() is None:
                con.execute("INSERT INTO secrets(key, value) VALUES('pepper', ?)", (randstr(24),))
            con.commit()

    def create_session(self, team_name: str) -> Dict[str, str]:
        token = b64u(hashlib.sha256((team_name + "|" + randstr(10)).encode()).digest())[:36]
        with self.conn() as con:
            con.execute(
                "INSERT INTO sessions(team_name, token, phase, created_at) VALUES (?, ?, 0, ?)",
                (team_name, token, now_ts()),
            )
            con.commit()
            row = con.execute(
                "SELECT team_name, token, phase, created_at FROM sessions WHERE team_name=?",
                (team_name,),
            ).fetchone()
            return dict(row)

    def session_by_token(self, token: str) -> Dict[str, str] | None:
        with self.conn() as con:
            row = con.execute(
                "SELECT team_name, token, phase, created_at FROM sessions WHERE token=?",
                (token,),
            ).fetchone()
            return dict(row) if row else None

    def get_secret(self, key: str) -> str:
        with self.conn() as con:
            row = con.execute("SELECT value FROM secrets WHERE key=?", (key,)).fetchone()
            return row["value"] if row else ""

    def set_phase(self, token: str, phase: int):
        with self.conn() as con:
            con.execute("UPDATE sessions SET phase=? WHERE token=?", (phase, token))
            con.commit()

    def add_event(self, token: str, action: str, detail: Dict):
        with self.conn() as con:
            con.execute(
                "INSERT INTO events(token, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (token, action, json.dumps(detail, sort_keys=True), now_ts()),
            )
            con.commit()

    def events(self, token: str) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute(
                "SELECT action, detail, created_at FROM events WHERE token=? ORDER BY id DESC LIMIT 30",
                (token,),
            ).fetchall()
            return [dict(r) for r in rows]

    def snapshot(self) -> Dict[str, int]:
        with self.conn() as con:
            s = con.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
        return {"sessions": s}


class RavenChallenge:
    def __init__(self, store: ChallengeStore):
        self.store = store

    def parse_guard(self, candidate_url: str) -> Dict[str, str]:
        raw = candidate_url.strip()
        if not raw.lower().startswith("https://"):
            return {"ok": "0", "error": "https only"}
        if " " in raw or "\n" in raw:
            return {"ok": "0", "error": "invalid whitespace"}
        # Vulnerable validation parser (normalizes backslash first).
        parsed = urlparse(raw.replace("\\", "/"))
        host = parsed.netloc.split("@")[0].split(":")[0].lower()
        if host != CANONICAL_HOST:
            return {"ok": "0", "error": "host blocked"}
        # Effective parser used by downstream client.
        eff = urlparse(raw).netloc
        if "@" in eff:
            effective_host = eff.split("@", 1)[1].split(":")[0].lower()
        else:
            effective_host = eff.split(":")[0].lower()
        return {"ok": "1", "validated_host": host, "effective_host": effective_host}

    def _pepper_crypt(self, token: str, salt: str) -> str:
        pepper = self.store.get_secret("pepper").encode()
        stream = hashlib.sha256((token + "|" + salt).encode()).digest()
        return b64u(xor_bytes(pepper, stream))

    def reveal_internal_bootstrap(self, token: str) -> Dict:
        salt = b64u(hashlib.sha256(("salt|" + token).encode()).digest()[:12])
        pepper_ct = self._pepper_crypt(token, salt)
        self.store.set_phase(token, 1)
        return {
            "asset_url": f"/api/carrier?token={token}",
            "salt": salt,
            "pepper_ct_b64u": pepper_ct,
            "recipe": "pepper = XOR(b64u_decode(pepper_ct), SHA256(token|salt)); passphrase = rvn::sha256(pepper|token|2026)[:24]::aes",
            "theme": "CVE-2026-25960 parser differential class",
        }

    def compose_passphrase(self, token: str) -> str:
        pepper = self.store.get_secret("pepper")
        digest = hashlib.sha256((pepper + "|" + token + "|2026").encode()).hexdigest()[:24]
        return f"rvn::{digest}::aes"

    def team_carrier(self, token: str) -> bytes:
        sess = self.store.session_by_token(token)
        if not sess or int(sess["phase"]) < 1:
            raise ValueError("carrier unavailable")
        passphrase = self.compose_passphrase(token)
        plain = json.dumps(
            {
                "flag": MASTER_FLAG,
                "origin": "raven_gate_2026",
                "chain": "parser_diff+lsb+aes_gcm",
            },
            separators=(",", ":"),
        ).encode()
        encrypted = aes_gcm_encrypt(plain, passphrase)
        blob = json.dumps(encrypted, separators=(",", ":")).encode()
        base = simple_png(320, 320, (16, 22, 38))
        return lsb_embed(base, blob)

    def metadata(self, token: str) -> Dict:
        sess = self.store.session_by_token(token)
        if not sess:
            return {}
        pepper = self.store.get_secret("pepper")
        return {
            "phase": sess["phase"],
            "kdf": "PBKDF2-HMAC-SHA256",
            "cipher": "AES-256-GCM",
            "pepper_hash": hashlib.sha256(("meta|" + pepper).encode()).hexdigest(),
            "cve_ref": "CVE-2026-25960 inspired parser differential",
        }

    def verify(self, token: str, flag: str) -> bool:
        sess = self.store.session_by_token(token)
        if not sess:
            return False
        ok = hmac.compare_digest(flag, MASTER_FLAG)
        self.store.add_event(token, "submit", {"ok": ok})
        if ok:
            self.store.set_phase(token, 3)
        return ok
