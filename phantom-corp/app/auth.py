"""
Phantom Corp — Autenticación JWT Vulnerable

Implementa el patrón vulnerable de CVE-2026-29000 (pac4j JWT Auth Bypass):
- Los tokens legítimos son JWS (firmados con RS256) envueltos en JWE (RSA-OAEP-256 + A256GCM)
- El servidor descifra el JWE y luego intenta parsear como JWS
- BUG: Si el payload interior es un PlainJWT (alg: none), el parseo como JWS devuelve None
- El null check hace que se SALTE toda la verificación de firma
- Resultado: Un atacante con la clave pública puede forjar tokens admin
"""
import json
import time
import base64
import functools
from flask import request, redirect, url_for, flash, g, make_response
from jwcrypto import jwk, jws, jwe


def _load_jwk_private():
    """Carga la clave privada como JWK."""
    from app.config import KEYS_DIR
    pem = (KEYS_DIR / 'private.pem').read_bytes()
    return jwk.JWK.from_pem(pem)


def _load_jwk_public():
    """Carga la clave pública como JWK."""
    from app.config import KEYS_DIR
    pem = (KEYS_DIR / 'public.pem').read_bytes()
    return jwk.JWK.from_pem(pem)


def get_jwks_json():
    """Devuelve la clave pública en formato JWKS (JSON Web Key Set)."""
    pub_key = _load_jwk_public()
    pub_json = json.loads(pub_key.export(private_key=False))
    pub_json['kid'] = 'phantom-corp-key-1'
    pub_json['use'] = 'enc'
    pub_json['alg'] = 'RSA-OAEP-256'
    return {'keys': [pub_json]}


def create_token(username, role):
    """
    Crea un token JWT legítimo:
    1. Genera JWS firmado con RS256
    2. Lo envuelve en JWE con RSA-OAEP-256 + A256GCM
    """
    priv_key = _load_jwk_private()
    pub_key = _load_jwk_public()

    # Claims del token
    now = int(time.time())
    claims = {
        'sub': username,
        'role': role,
        'iat': now,
        'exp': now + 86400,  # 24 horas
        'iss': 'phantom-corp-auth'
    }

    # Paso 1: Crear JWS firmado con RS256
    jws_token = jws.JWS(json.dumps(claims).encode('utf-8'))
    jws_token.add_signature(
        priv_key,
        alg='RS256',
        protected=json.dumps({'alg': 'RS256', 'typ': 'JWT', 'kid': 'phantom-corp-key-1'})
    )
    signed_compact = jws_token.serialize(compact=True)

    # Paso 2: Envolver en JWE con clave pública
    jwe_token = jwe.JWE(
        signed_compact.encode('utf-8'),
        recipient=pub_key,
        protected=json.dumps({
            'alg': 'RSA-OAEP-256',
            'enc': 'A256GCM',
            'kid': 'phantom-corp-key-1'
        })
    )
    return jwe_token.serialize(compact=True)


def _b64url_decode(data):
    """Decodifica base64url con padding."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def _try_parse_as_jws(payload_str):
    """
    Intenta parsear el payload como un JWS (JWT firmado).

    VULNERABLE (CVE-2026-29000):
    Si el payload es un PlainJWT (header con alg: none),
    esta función devuelve None en lugar de un JWS válido.
    El caller debe verificar si el resultado es None antes de confiar en los claims.
    """
    try:
        parts = payload_str.split('.')
        if len(parts) < 2:
            return None

        # Decodificar header para ver el algoritmo
        header = json.loads(_b64url_decode(parts[0]))

        # Si es alg: none → es un PlainJWT, no un JWS
        # En la implementación vulnerable original (pac4j), toSignedJWT() devuelve null
        # para PlainJWTs, lo cual causa que se salte la verificación
        if header.get('alg', '').lower() == 'none':
            return None  # ← EL BUG: devuelve None para PlainJWT

        # Parsear como JWS válido
        jws_obj = jws.JWS()
        jws_obj.deserialize(payload_str)
        return jws_obj

    except Exception:
        return None


def verify_token(token_str):
    """
    Verifica un token JWE y extrae los claims.

    VULNERABLE (CVE-2026-29000):
    Cuando el JWS interior es un PlainJWT (alg: none),
    _try_parse_as_jws() devuelve None, y el código SALTA
    la verificación de firma, aceptando claims no verificados.
    """
    try:
        priv_key = _load_jwk_private()
        pub_key = _load_jwk_public()

        # Paso 1: Descifrar JWE con clave privada
        jwe_obj = jwe.JWE()
        jwe_obj.deserialize(token_str, key=priv_key)
        inner_payload = jwe_obj.payload.decode('utf-8')

        # Paso 2: Intentar parsear como JWS (JWT firmado)
        signed_jwt = _try_parse_as_jws(inner_payload)

        # ╔══════════════════════════════════════════════════════════╗
        # ║  CVE-2026-29000: EL BUG ESTÁ AQUÍ                      ║
        # ║  Si signed_jwt es None (PlainJWT), NO verifica firma    ║
        # ║  y extrae claims directamente del payload sin validar   ║
        # ╚══════════════════════════════════════════════════════════╝
        if signed_jwt is not None:
            # Ruta normal: verificar firma con clave pública
            signed_jwt.verify(pub_key)
            verified_payload = signed_jwt.payload.decode('utf-8')
            claims = json.loads(verified_payload)
        else:
            # VULNERABLE: PlainJWT — extrae claims sin verificar firma
            parts = inner_payload.split('.')
            if len(parts) >= 2:
                claims_json = _b64url_decode(parts[1])
                claims = json.loads(claims_json)
            else:
                return None

        # Verificar expiración (se mantiene esta comprobación)
        if 'exp' in claims and claims['exp'] < int(time.time()):
            return None

        return claims

    except Exception:
        return None


def require_auth(f):
    """Decorador que requiere autenticación JWT."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token:
            flash('Authentication required. Please log in.', 'error')
            return redirect(url_for('public.login'))

        claims = verify_token(token)
        if claims is None:
            flash('Invalid or expired session. Please log in again.', 'error')
            resp = make_response(redirect(url_for('public.login')))
            resp.delete_cookie('session_token')
            return resp

        g.current_user = claims
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorador que requiere rol de administrador."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token:
            flash('Authentication required. Please log in.', 'error')
            return redirect(url_for('public.login'))

        claims = verify_token(token)
        if claims is None:
            flash('Invalid or expired session. Please log in again.', 'error')
            resp = make_response(redirect(url_for('public.login')))
            resp.delete_cookie('session_token')
            return resp

        if claims.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('public.index'))

        g.current_user = claims
        return f(*args, **kwargs)
    return decorated
