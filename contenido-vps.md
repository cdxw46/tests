# Contenido de la VPS

## Sistema Operativo
- **OS:** Ubuntu 24.04.4 LTS (Noble Numbat)
- **Kernel:** Linux 6.1.147 x86_64
- **Arquitectura:** x86_64

## Recursos de Hardware
| Recurso | Valor |
|---------|-------|
| CPUs | 4 cores |
| RAM Total | 15 Gi |
| RAM Disponible | ~14 Gi |
| Disco Total | 126 GB |
| Disco Usado | 7.6 GB (7%) |
| Disco Disponible | 112 GB |
| Swap | 0 B |

## Herramientas y Lenguajes Instalados

| Herramienta | Versión |
|-------------|---------|
| Python | 3.12.3 |
| Node.js | 22.22.1 |
| npm | (incluido con Node) |
| Go | 1.22.2 |
| Rust (rustc) | 1.83.0 |
| GCC | 13.3.0 |
| Java (OpenJDK) | 21.0.10 |

**No encontrados:** Docker, docker-compose, Ruby.

## Paquetes del Sistema
- ~780 paquetes dpkg instalados

## Contenido del Workspace (`/workspace`)
El workspace contiene un repositorio Git con lo siguiente:

- **`aa`** — Archivo de texto pequeño (contenido: `aaaa`), 4 KB.
- **`.git/`** — Directorio del repositorio Git.

### Historial Git
Un solo commit en la rama `main`:
```
2750c3a Create aa
```

### Ramas Remotas
| Rama | Descripción (por nombre) |
|------|--------------------------|
| `main` | Rama principal |
| `cursor/archivos-del-vps-6831` | Archivos del VPS |
| `cursor/compromiso-equipo-s7comm-715d` | Compromiso equipo S7Comm |
| `cursor/contenido-de-la-vps-185e` | Contenido de la VPS (esta rama) |
| `cursor/cves-para-reto-ctf-b3f9` | CVEs para reto CTF |
| `cursor/development-environment-setup-865d` | Configuración entorno desarrollo |
| `cursor/hack-the-box-funkynator-efcc` | Hack The Box Funkynator |
| `cursor/investigaci-n-gameloader-a0ff` | Investigación Gameloader |
| `cursor/reto-picoctf-disko-2339` | Reto PicoCTF Disko |
| `cursor/sokobanhtb-challenge-solution-e170` | Sokoban HTB challenge |
| `cursor/steel-mountain-vulnerabilities-626a` | Steel Mountain vulnerabilities |

## Home del usuario (`/home/ubuntu/`)
- Configuración estándar de bash (`.bashrc`, `.profile`, `.bash_logout`)
- **Go** workspace en `~/go/`
- **Node.js** vía NVM en `~/.nvm/` (v22.22.1)
- **npm** cache en `~/.npm/`
- **Rust/Cargo** en `/usr/local/cargo/`
- Cursor IDE config en `~/.cursor/`
- VNC server configurado en `~/.vnc/`
- Git configurado (`.gitconfig`)
