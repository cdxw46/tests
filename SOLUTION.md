# GameLoader - HTB Challenge Solution

## Flag

```
HTB{Und3t3ct3d_GD_M@lw4r3_PCB29543}
```

- **Part 1** (`HTB{Und3t3ct3d_`): Found in the HTTP response header `X-Half-Flag` when downloading the stage 2 binary from the C2 server.
- **Part 2** (`GD_M@lw4r3_PCB29543}`): Encoded as base64 within the obfuscated GDScript in `player.gd`, used as input to an MD5 hash passed as argument to the stage 2 executable.

## Analysis

### Stage 1: Godot Game (Platformer 2D)

- **Engine**: Godot Engine v4.1.1.stable.custom_build
- **Files**: `Platformer 2D.exe` (44MB) + `Platformer 2D.pck` (2.4MB, encrypted)
- **PCK Encryption Key**: `f2f44f0aaa282c6b66065b1ca437abae05e20a55a0f6b2fd85f5b90576f0c88f`
  - Found by scanning the PE binary for 32-byte sequences that successfully decrypt the PCK directory using AES-256-CFB.
- **Malicious Code**: Located in `player.gd` - the Player class contains heavily obfuscated code that:
  1. Constructs a C2 URL via base64-encoded character arrays: `http://g4m3l0ad3r-network.htb`
  2. Sends system info (OS, CPU, locale, user dir) via POST to `/enum`
  3. Downloads a second-stage executable from `/p47l0ad_binary` with a crafted cookie
  4. Saves it as `new_level_mod.exe` in the user data directory
  5. Executes it via PowerShell with an MD5 hash argument derived from the base64-decoded string `GD_M@lw4r3_PCB29543}`

### Stage 2: Info Stealer (new_level_mod.exe)

- **Compiler**: MinGW-W64 x86_64-ucrt-posix-seh (GCC 12.1.0)
- **Behavior**: Creates `C:\Temp\system_report.txt` containing:
  - Computer name, username
  - Windows version and build number
  - CPU info (processors, architecture)
  - Current directory, system uptime
  - PATH environment variable
  - Timestamp

### C2 Server Communication

- **Host**: `g4m3l0ad3r-network.htb` (requires correct Host header)
- **POST /enum**: Accepts JSON system info, returns `{"status":"success"}`
- **GET /p47l0ad_binary**: Requires specific cookie (derived from obfuscated int arrays in GDScript). Returns the stage 2 binary with `X-Half-Flag` header containing the first half of the flag.
