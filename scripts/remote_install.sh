#!/usr/bin/env bash
# Instala y arranca Linker en la VM destino. Se ejecuta en la instancia
# (efimera, blue o green) a traves de la accion oci-bastion-deploy, que
# define DEPLOY_PATH con la ruta donde quedo copiado el artefacto.
#
# El archivo .env de la aplicacion debe existir en $DEPLOY_PATH antes de
# llamar este script (lo escribe el workflow, porque contiene secretos).
#
# Variables opcionales:
#   APP_DIR       (default: /opt/linker-python)
#   SERVICE_NAME  (default: linker-python)
#   APP_PORT      (default: 8080)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/linker-python}"
SERVICE_NAME="${SERVICE_NAME:-linker-python}"
APP_PORT="${APP_PORT:-8080}"
SRC_DIR="${DEPLOY_PATH:-$(pwd)}"

log() { printf '\n[remote-install] %s\n' "$1"; }

log "Copiando artefacto de $SRC_DIR a $APP_DIR..."
sudo mkdir -p "$APP_DIR"
sudo rm -rf "${APP_DIR:?}"/*
sudo cp -r "$SRC_DIR"/. "$APP_DIR"/
sudo chown -R "$(whoami):$(whoami)" "$APP_DIR"
if [[ -f "$APP_DIR/.env" ]]; then
  sudo chmod 600 "$APP_DIR/.env"
fi

log "Validando artefacto desplegado..."
test -f "$APP_DIR/web.py"
grep -n "healthz" "$APP_DIR/web.py"
if grep -n '@app.get("/<short_id>")' "$APP_DIR/web.py"; then
  echo "[remote-install][ERROR] La version desplegada contiene @app.get(\"/<short_id>\")" >&2
  exit 1
fi

log "Instalando dependencias del sistema (idempotente)..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip psmisc

cd "$APP_DIR"

log "Creando entorno virtual limpio..."
rm -rf .venv
python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

log "Validando rutas Flask antes de crear el servicio..."
.venv/bin/python - <<'PY'
from web import create_app
app = create_app(config={"TESTING": True})
routes = sorted(str(rule) for rule in app.url_map.iter_rules())
print("\n".join(routes))
if "/healthz" not in routes:
    raise SystemExit("ERROR: /healthz no esta registrado")
if "/<short_id>" in routes:
    raise SystemExit("ERROR: /<short_id> sigue registrado")
if "/r/<short_id>" not in routes:
    raise SystemExit("ERROR: /r/<short_id> no esta registrado")
PY

log "Creando servicio systemd $SERVICE_NAME..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF_SERVICE
[Unit]
Description=Linker Python URL Shortener
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$APP_DIR
EnvironmentFile=-$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/app.py
Restart=always
RestartSec=5
KillSignal=SIGINT
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF_SERVICE

log "Reiniciando servicio..."
sudo systemctl stop "$SERVICE_NAME" || true
sudo fuser -k "${APP_PORT}/tcp" || true
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

log "Esperando a que la aplicacion responda en el puerto $APP_PORT..."
for attempt in $(seq 1 30); do
  if curl --fail --silent "http://localhost:${APP_PORT}/health" > /dev/null; then
    log "La aplicacion respondio en el intento $attempt."
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "[remote-install][ERROR] La aplicacion no respondio /health." >&2
    sudo systemctl status "$SERVICE_NAME" --no-pager || true
    sudo journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
    exit 1
  fi
  sleep 2
done

log "Healthcheck basico..."
curl --fail --silent "http://localhost:${APP_PORT}/health" && echo
log "Healthcheck con base de datos..."
curl --fail --silent "http://localhost:${APP_PORT}/healthz" && echo

log "Instalacion remota finalizada correctamente."
