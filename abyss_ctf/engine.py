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

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


DB_PATH = Path(__file__).resolve().parent / "state.db"
FINAL_FLAG = "FLAG{2026_ultra_hard_web_stego_crypto_supplychain_abyss}"
ALLOWED_HOST = "registry.ctf-trusted.local"
INTERNAL_HOST = "artifact-vault.ctf.local"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def randstr(n: int = 12) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(n))


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * ((4 - len(text) % 4) % 4))


def xor_bytes(data: bytes, key: bytes) -> bytes:
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return bytes(out)


def blake(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()


def kdf(team_token: str, vault_pepper: str, tag_digest: str) -> bytes:
    mat = f"{team_token}|{vault_pepper}|{tag_digest}|2026".encode()
    return hashlib.pbkdf2_hmac("sha256", mat, blake(mat)[:16], 380000, 32)


def chacha_encrypt(plain: bytes, key: bytes, aad: bytes) -> Dict[str, str]:
    nonce = blake(key + aad)[:12]
    ct = ChaCha20Poly1305(key).encrypt(nonce, plain, aad)
    return {"alg": "CHACHA20-POLY1305", "nonce_b64u": b64u(nonce), "ct_b64u": b64u(ct)}


def chacha_decrypt(blob: Dict[str, str], key: bytes, aad: bytes) -> bytes:
    nonce = b64u_decode(blob["nonce_b64u"])
    ct = b64u_decode(blob["ct_b64u"])
    return ChaCha20Poly1305(key).decrypt(nonce, ct, aad)


def png_crc(chunk_type: bytes, chunk_data: bytes) -> bytes:
    import zlib

    return zlib.crc32(chunk_type + chunk_data).to_bytes(4, "big")


def png_build(width: int, height: int, rgb: Tuple[int, int, int]) -> bytes:
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


def png_read_rgb(png_bytes: bytes) -> Tuple[int, int, List[Tuple[int, int, int]]]:
    import struct
    import zlib

    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not png")
    pos = 8
    width = height = 0
    idat_parts = []
    while pos < len(png_bytes):
        length = int.from_bytes(png_bytes[pos : pos + 4], "big")
        ctype = png_bytes[pos + 4 : pos + 8]
        cdata = png_bytes[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bitd, color_type, _, _, _ = struct.unpack(">IIBBBBB", cdata)
            if bitd != 8 or color_type != 2:
                raise ValueError("unsupported format")
        elif ctype == b"IDAT":
            idat_parts.append(cdata)
        elif ctype == b"IEND":
            break
    raw = zlib.decompress(b"".join(idat_parts))
    pixels = []
    stride = width * 3 + 1
    for y in range(height):
        row = raw[y * stride : (y + 1) * stride]
        if row[0] != 0:
            raise ValueError("unsupported filter")
        body = row[1:]
        for x in range(width):
            i = x * 3
            pixels.append((body[i], body[i + 1], body[i + 2]))
    return width, height, pixels


def png_write_rgb(width: int, height: int, pixels: List[Tuple[int, int, int]]) -> bytes:
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


def lsb_embed_rgb(png_bytes: bytes, payload: bytes) -> bytes:
    w, h, pixels = png_read_rgb(png_bytes)
    data = len(payload).to_bytes(4, "big") + payload + blake(payload)[:8]
    bits = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    if len(bits) > len(pixels) * 3:
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
    return png_write_rgb(w, h, out)


def lsb_extract_rgb(png_bytes: bytes) -> bytes:
    _, _, pixels = png_read_rgb(png_bytes)
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
    if len(data) < 12:
        raise ValueError("stego data too short")
    size = int.from_bytes(data[:4], "big")
    payload = bytes(data[4 : 4 + size])
    chk = bytes(data[4 + size : 4 + size + 8])
    if chk != blake(payload)[:8]:
        raise ValueError("checksum mismatch")
    return payload


class AbyssStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.bootstrap()

    def conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def bootstrap(self):
        with self.conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT UNIQUE NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    stage INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kv (
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
            if c.execute("SELECT value FROM kv WHERE key='vault_pepper'").fetchone() is None:
                c.execute("INSERT INTO kv(key, value) VALUES('vault_pepper', ?)", (randstr(28),))
            c.commit()

    def add_team(self, team_name: str) -> Dict:
        token = b64u(hashlib.sha256((team_name + "|" + randstr(9)).encode()).digest())[:44]
        with self.conn() as c:
            c.execute(
                "INSERT INTO teams(team_name, token, stage, created_at) VALUES (?, ?, 0, ?)",
                (team_name, token, now()),
            )
            c.commit()
            row = c.execute("SELECT team_name, token, stage, created_at FROM teams WHERE token=?", (token,)).fetchone()
            return dict(row)

    def team(self, token: str) -> Dict | None:
        with self.conn() as c:
            row = c.execute("SELECT team_name, token, stage, created_at FROM teams WHERE token=?", (token,)).fetchone()
            return dict(row) if row else None

    def set_stage(self, token: str, stage: int):
        with self.conn() as c:
            c.execute("UPDATE teams SET stage=? WHERE token=?", (stage, token))
            c.commit()

    def get_kv(self, key: str) -> str:
        with self.conn() as c:
            row = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            return row["value"] if row else ""

    def event(self, token: str, action: str, detail: Dict):
        with self.conn() as c:
            c.execute(
                "INSERT INTO events(token, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (token, action, json.dumps(detail, sort_keys=True), now()),
            )
            c.commit()

    def events(self, token: str) -> List[Dict]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT action, detail, created_at FROM events WHERE token=? ORDER BY id DESC LIMIT 50",
                (token,),
            ).fetchall()
            return [dict(r) for r in rows]

    def snapshot(self) -> Dict:
        with self.conn() as c:
            teams = c.execute("SELECT COUNT(*) c FROM teams").fetchone()["c"]
        return {"teams": teams}


class AbyssEngine:
    """
    Ultra-hard single-flag chain:
      A) parser differential fetch bypass (CVE-2026-25960 class)
      B) mutable-tag poison simulation (CVE-2026-31976/33634 class)
      C) stego extraction with checksum block
      D) AEAD decryption with KDF bound to prior artifacts
    """

    def __init__(self, store: AbyssStore):
        self.store = store

    def guard_parse(self, url: str) -> Dict[str, str]:
        raw = url.strip()
        if not raw.startswith("https://"):
            return {"ok": "0", "error": "https only"}
        # vulnerable validator normalizes backslash then picks host before '@'
        parsed = urlparse(raw.replace("\\", "/"))
        host = parsed.netloc.split("@")[0].split(":")[0].lower()
        if host != ALLOWED_HOST:
            return {"ok": "0", "error": "host blocked"}
        eff_netloc = urlparse(raw).netloc
        if "@" in eff_netloc:
            eff_host = eff_netloc.split("@", 1)[1].split(":")[0].lower()
        else:
            eff_host = eff_netloc.split(":")[0].lower()
        return {"ok": "1", "validated_host": host, "effective_host": eff_host}

    def gateway_fetch(self, token: str, url: str) -> Dict:
        g = self.guard_parse(url)
        if g.get("ok") != "1":
            self.store.event(token, "fetch_denied", {"url": url, "reason": g.get("error")})
            return {"ok": False, "error": g.get("error", "blocked")}
        if g["effective_host"] == INTERNAL_HOST:
            self.store.set_stage(token, 1)
            seed = b64u(blake(("seed|" + token).encode())[:18])
            self.store.event(token, "vault_hit", {"seed": seed})
            return {
                "ok": True,
                "source": "internal_vault",
                "clue": {
                    "seed": seed,
                    "pipeline": "/api/repo/manifest",
                    "msg": "Tag pinning prevents poison. Unless you still trust mutable aliases.",
                },
            }
        self.store.event(token, "fetch_public", {"url": url})
        return {"ok": True, "source": "public_docs", "data": {"note": "No secret"}}

    def _resolve_tag(self, mutable_tag: str, pin: str | None) -> Tuple[str, str]:
        poisoned_sha = "9f3ab8d7e6c5f4a1b2d3e4f50987654321abcde0"
        safe_sha = "2d6b48af0f2f5a0a4f2c1ad1f001b13afeed9876"
        effective_sha = pin if pin else (poisoned_sha if mutable_tag in {"v5", "latest"} else safe_sha)
        return effective_sha, poisoned_sha

    def manifest(self, token: str) -> Dict:
        team = self.store.team(token)
        if not team:
            return {"ok": False, "error": "invalid token"}
        if int(team["stage"]) < 1:
            return {"ok": False, "error": "vault stage not completed"}
        mutable_tag = "v5"
        effective_sha, poisoned_sha = self._resolve_tag(mutable_tag, None)
        tag_digest = hashlib.sha256(effective_sha.encode()).hexdigest()[:24]
        self.store.event(
            token,
            "manifest_view",
            {"mutable_tag": mutable_tag, "effective_sha": effective_sha, "tag_digest": tag_digest},
        )
        return {
            "mutable_tag": mutable_tag,
            "tag_digest_hint": tag_digest,
            "safe_pin_example": "2d6b48af0f2f5a0a4f2c1ad1f001b13afeed9876",
            "poison_window": "2026-03 simulated",
        }

    def repo_artifact(self, token: str, mutable_tag: str, pin: str | None = None) -> Dict:
        team = self.store.team(token)
        if not team:
            return {"ok": False, "error": "invalid token"}
        if int(team["stage"]) < 1:
            return {"ok": False, "error": "vault stage not completed"}
        effective_sha, poisoned_sha = self._resolve_tag(mutable_tag, pin)
        tag_digest = hashlib.sha256(effective_sha.encode()).hexdigest()[:24]
        poisoned = effective_sha == poisoned_sha
        if poisoned:
            self.store.set_stage(token, 2)
        self.store.event(
            token,
            "artifact_resolution",
            {
                "mutable_tag": mutable_tag,
                "pin": pin or "",
                "effective_sha": effective_sha,
                "tag_digest": tag_digest,
                "poisoned": poisoned,
            },
        )
        return {
            "ok": True,
            "mutable_tag": mutable_tag,
            "effective_sha": effective_sha,
            "tag_digest": tag_digest,
            "poisoned": poisoned,
            "artifact_url": f"/api/carrier?token={token}&tag_digest={tag_digest}",
        }

    def _artifact_payload(self, token: str, tag_digest: str) -> bytes:
        team = self.store.team(token)
        if not team:
            raise ValueError("bad token")
        if int(team["stage"]) < 2:
            raise ValueError("poison stage incomplete")
        pepper = self.store.get_kv("vault_pepper")
        key = kdf(token, pepper, tag_digest)
        aad = f"{token}|{tag_digest}|abyss-2026".encode()
        plain = json.dumps(
            {
                "flag": FINAL_FLAG,
                "meta": {"chain": "ssrf->tagpoison->stego->aead", "year": 2026},
            },
            separators=(",", ":"),
        ).encode()
        enc = chacha_encrypt(plain, key, aad)
        blob = json.dumps(enc, separators=(",", ":")).encode()
        return blob

    def artifact(self, token: str, tag_digest: str) -> bytes:
        return self.carrier_png(token, tag_digest=tag_digest)

    def carrier_png(self, token: str, tag_digest: str | None = None) -> bytes:
        if tag_digest is None:
            team = self.store.team(token)
            if not team:
                raise ValueError("invalid token")
            # default to poisoned mutable v5 digest
            eff, _ = self._resolve_tag("v5", None)
            tag_digest = hashlib.sha256(eff.encode()).hexdigest()[:24]
        blob = self._artifact_payload(token, tag_digest)
        base = png_build(420, 260, (11, 20, 39))
        return lsb_embed_rgb(base, blob)

    def metadata(self, token: str) -> Dict:
        team = self.store.team(token)
        if not team:
            return {}
        if int(team["stage"]) < 2:
            return {
                "phase": int(team["stage"]),
                "next": "complete poison artifact stage first",
                "aead": "ChaCha20-Poly1305",
            }
        pepper = self.store.get_kv("vault_pepper")
        pepper_mask = pepper[:4] + "*" * (len(pepper) - 8) + pepper[-4:]
        h = hashlib.sha256(("meta|" + pepper).encode()).hexdigest()
        return {
            "phase": int(team["stage"]),
            "kdf_recipe": "PBKDF2-HMAC-SHA256(token|vault_pepper|tag_digest|2026)",
            "aead": "ChaCha20-Poly1305",
            "aad_recipe": "token|tag_digest|abyss-2026",
            "pepper_hash_meta": h,
            "pepper_mask": pepper_mask,
            "vault_cipher": b64u(xor_bytes(pepper.encode(), blake(("vault|" + token).encode()))),
        }

    def verify(self, token: str, flag: str) -> bool:
        team = self.store.team(token)
        if not team:
            return False
        ok = hmac.compare_digest(flag, FINAL_FLAG)
        self.store.event(token, "submit", {"ok": ok})
        if ok:
            self.store.set_stage(token, 3)
        return ok
