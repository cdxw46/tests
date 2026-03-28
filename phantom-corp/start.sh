#!/bin/bash
# ═══════════════════════════════════════════════════
#  Phantom Corp — Script de arranque para producción
# ═══════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔═════════════════════════════════════════╗"
echo "║  🔒 Phantom Corp — CTF Challenge        ║"
echo "║  Arrancando servicios...                 ║"
echo "╚═════════════════════════════════════════╝"

# 1. Verificar flag
if [ ! -f /opt/phantom/flag.txt ]; then
    echo "[*] Creando flag..."
    sudo mkdir -p /opt/phantom
    echo -n 'flag{ph4nt0m_c0rp_jw3_sql1_ssrf_2026_m4st3r}' | sudo tee /opt/phantom/flag.txt > /dev/null
    sudo chmod 644 /opt/phantom/flag.txt
fi

# 2. Inicializar DB si no existe
if [ ! -f instance/phantom.db ]; then
    echo "[*] Inicializando base de datos..."
    python3 init_db.py
fi

# 3. Matar procesos anteriores si existen
echo "[*] Limpiando procesos anteriores..."
pkill -f "gunicorn.*run:app" 2>/dev/null || true
sleep 1

# 4. Arrancar Gunicorn
echo "[*] Arrancando Gunicorn (2 workers, puerto 5000)..."
export PATH="$HOME/.local/bin:$PATH"
gunicorn -w 2 -b 127.0.0.1:5000 --timeout 60 --access-logfile /tmp/phantom-access.log --error-logfile /tmp/phantom-error.log -D run:app

# 5. Configurar Nginx
echo "[*] Configurando Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/phantom-corp
sudo ln -sf /etc/nginx/sites-available/phantom-corp /etc/nginx/sites-enabled/phantom-corp
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Verificar config Nginx
if sudo nginx -t 2>&1; then
    sudo nginx -s reload 2>/dev/null || sudo nginx
    echo "[+] Nginx configurado y arrancado"
else
    echo "[-] Error en config Nginx"
    exit 1
fi

echo ""
echo "╔═════════════════════════════════════════╗"
echo "║  ✅ Phantom Corp listo!                  ║"
echo "║                                         ║"
echo "║  Local:  http://localhost:5000           ║"
echo "║  Web:    http://urdadistribuciones.es    ║"
echo "║                                         ║"
echo "║  Logs:   /tmp/phantom-access.log         ║"
echo "║          /tmp/phantom-error.log           ║"
echo "╚═════════════════════════════════════════╝"
