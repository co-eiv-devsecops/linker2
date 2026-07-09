#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_DIR="${APP_DIR:-/opt/linker-python}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"
SERVICE_NAME="${SERVICE_NAME:-linker-python}"
DOMAIN="${DOMAIN:-X.n-la-c.app}"
PORT="${PORT:-8080}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-linker-python}"

if [[ "$EUID" -eq 0 ]]; then
    SUDO=()
else
    SUDO=(sudo)
fi

log() {
    printf "\n[linker-python] %s\n" "$1"
}

fail() {
    printf "\n[linker-python][ERROR] %s\n" "$1" >&2
    exit 1
}

if [[ ! -f "$PROJECT_DIR/app.py" ]]; then
    fail "No se encontro app.py. Ejecuta este script desde el proyecto linker-python."
fi

export DEBIAN_FRONTEND=noninteractive

log "Actualizando indices de paquetes."
"${SUDO[@]}" apt-get update

log "Instalando paquetes requeridos: git, python3 y nginx."
"${SUDO[@]}" apt-get install -y git python3 nginx

log "Copiando archivos de la aplicacion a $APP_DIR."
"${SUDO[@]}" mkdir -p "$APP_DIR"
tar \
    --exclude=".git" \
    --exclude="security-fixtures" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".DS_Store" \
    -C "$PROJECT_DIR" \
    -cf - . | "${SUDO[@]}" tar -xf - -C "$APP_DIR"
"${SUDO[@]}" chown -R "$APP_USER:$APP_USER" "$APP_DIR"

log "Configurando servicio systemd $SERVICE_NAME.service."
"${SUDO[@]}" tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null <<EOF
[Unit]
Description=Linker Python URL Shortener
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PORT=$PORT
Environment=LINKER_DB=$APP_DIR/linker.db
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always
RestartSec=5
KillSignal=SIGINT
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

log "Configurando Nginx para el dominio $DOMAIN."
"${SUDO[@]}" tee "/etc/nginx/sites-available/$NGINX_SITE_NAME" > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

log "Habilitando y reiniciando servicios."
"${SUDO[@]}" ln -sf "/etc/nginx/sites-available/$NGINX_SITE_NAME" "/etc/nginx/sites-enabled/$NGINX_SITE_NAME"

if ! "${SUDO[@]}" nginx -t; then
    fail "La configuracion de Nginx no es valida."
fi

"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable "$SERVICE_NAME"
"${SUDO[@]}" systemctl restart "$SERVICE_NAME"
"${SUDO[@]}" systemctl enable nginx
"${SUDO[@]}" systemctl restart nginx

log "Verificando estado del servicio $SERVICE_NAME."
if ! "${SUDO[@]}" systemctl is-active --quiet "$SERVICE_NAME"; then
    "${SUDO[@]}" systemctl --no-pager --lines=20 status "$SERVICE_NAME" || true
    fail "El servicio $SERVICE_NAME no quedo activo."
fi

log "Verificando endpoint http://localhost:$PORT/health."
health_ok="false"
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if python3 - "$PORT" <<'PY'
import json
import sys
import urllib.request

port = sys.argv[1]
url = f"http://localhost:{port}/health"

try:
    with urllib.request.urlopen(url, timeout=3) as response:
        data = json.loads(response.read().decode("utf-8"))
        if response.status == 200 and data.get("status") == "ok":
            raise SystemExit(0)
except Exception:
    pass

raise SystemExit(1)
PY
    then
        health_ok="true"
        break
    fi

    printf "[linker-python] Esperando respuesta de la aplicacion (%s/10)...\n" "$attempt"
    sleep 1
done

if [[ "$health_ok" != "true" ]]; then
    fail "El endpoint http://localhost:$PORT/health no respondio correctamente."
fi

log "Instalacion finalizada correctamente."
echo "Aplicacion disponible en: http://$DOMAIN"
