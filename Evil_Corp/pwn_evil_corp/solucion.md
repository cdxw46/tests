# Evil Corp - Solución

## Flag
`HTB{45c11_15_N07_4L0000n3}`

## Resumen
Reto de explotación binaria (pwn) que involucra un desbordamiento de buffer en la pila (stack buffer overflow) combinado con inyección de shellcode en una región de memoria RWX (lectura/escritura/ejecución).

## Análisis del Binario

**Protecciones:**
- PIE: Habilitado (direcciones base aleatorias)
- NX: Habilitado (pila no ejecutable)
- Stack Canary: **NO** (sin protección de pila)
- RELRO: Parcial

**Credenciales hardcodeadas:** `eliot` / `4007`

## Vulnerabilidades Identificadas

### 1. Regiones mmap con direcciones fijas (MAP_FIXED)
- `SupportMsg` en `0x10000`, tamaño `0x4b0`, permisos RW
- `AssemblyTestPage` en `0x11000`, tamaño `0x800`, permisos **RWX** (ejecutable!)

### 2. Desbordamiento de buffer en `ContactSupport`
- Buffer en la pila: `0x3E80` bytes (16000 bytes = 4000 wchar_t)
- `fgetws(buf, 0x1000, stdin)` lee hasta 4095 wchar_t = 16380 bytes
- **Overflow de 380 bytes** más allá del buffer, suficiente para sobrescribir `rbx` guardado y la dirección de retorno

### 3. Overflow en `wcharToChar16`
- Copia hasta `0x1000` elementos de wchar_t (4 bytes) a uint16_t (2 bytes)
- Destino: `SupportMsg` en `0x10000`
- El overflow escribe desde `0x10000` hasta `0x12000`, cubriendo `AssemblyTestPage` en `0x11000`

## Estrategia de Explotación

### Codificación de Shellcode
El truco clave es que `wcharToChar16` toma los **16 bits inferiores** de cada wchar_t. Usando codepoints Unicode `>= U+10000`, podemos codificar cualquier par de bytes sin restricciones de null o newline:
- Para bytes `(b0, b1)`: `wchar = 0x10000 | (b1 << 8) | b0`

### Payload Único (4003 wchars)
1. **wchar[0..2047]**: Relleno para llenar la página de SupportMsg
2. **wchar[2048..2068]**: Shellcode (open + sendfile de `/flag.txt`)
3. **wchar[2069..3999]**: Más relleno hasta llegar al rbx guardado
4. **wchar[4000..4001]**: rbx guardado (no importa el valor)
5. **wchar[4002]**: Dirección de retorno = `0x11000` (la página RWX)
6. **[EOF]**: El terminador null de fgetws coloca `0x00000000` en wchar[4003], completando los 32 bits superiores de la dirección de retorno

### Ejecución
- `wcharToChar16` escribe el shellcode en la página RWX (`0x11000`)
- Al retornar `ContactSupport`, la dirección de retorno es `0x11000`
- El shellcode se ejecuta: abre `/flag.txt` y envía su contenido por stdout (el socket)
