#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TEAM_NUMBER="${TEAM_NUMBER:-X}"
SERVER_USER="${SERVER_USER:-ubuntu}"
SERVER_HOST="${SERVER_HOST:-$TEAM_NUMBER.n-la-c.app}"
REMOTE_DIR="${REMOTE_DIR:-/tmp/linker-python}"
DOMAIN="${DOMAIN:-$TEAM_NUMBER.n-la-c.app}"
PORT="${PORT:-8080}"
APP_DIR="${APP_DIR:-/opt/linker-python}"
SERVICE_NAME="${SERVICE_NAME:-linker-python}"

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

log "Preparando directorio remoto $REMOTE_DIR en $SERVER_HOST."
ssh "$SERVER_USER@$SERVER_HOST" "rm -rf '$REMOTE_DIR' && mkdir -p '$REMOTE_DIR'"

log "Copiando el proyecto completo a la VM."
tar \
    --exclude=".git" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".DS_Store" \
    -C "$PROJECT_DIR" \
    -cf - . | ssh "$SERVER_USER@$SERVER_HOST" "tar -xf - -C '$REMOTE_DIR'"

log "Ejecutando instalacion automatizada en la VM."
ssh "$SERVER_USER@$SERVER_HOST" "cd '$REMOTE_DIR' && chmod +x scripts/install_vm.sh && DOMAIN='$DOMAIN' PORT='$PORT' APP_DIR='$APP_DIR' SERVICE_NAME='$SERVICE_NAME' scripts/install_vm.sh"

log "Despliegue finalizado correctamente."
echo "Aplicacion disponible en: http://$DOMAIN"
