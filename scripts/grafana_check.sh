#!/usr/bin/env bash
# Chequeo de Grafana después de un despliegue.
#
# Este script:
# 1. Verifica que Grafana esté arriba y que su base de datos esté sana.
# 2. Verifica que existan dashboards de Linker.
# 3. Registra una anotación del despliegue para correlacionar métricas con cambios.
#
# Entradas requeridas:
#   GRAFANA_URL        URL base de Grafana, por ejemplo: <GRAFANA_URL>
#   GRAFANA_API_TOKEN  Service account token de Grafana
#
# Entradas opcionales:
#   DEPLOY_SHA         SHA del commit desplegado
#   DEPLOY_RUN_URL     URL de la corrida del pipeline
#
# Nota:
# No se incluyen enlaces http reales en este archivo para cumplir el requisito
# de que todo enlace externo del repositorio debe estar acortado en Linker.

set -euo pipefail

: "${GRAFANA_URL:?GRAFANA_URL es requerido como variable del repositorio}"
: "${GRAFANA_API_TOKEN:?GRAFANA_API_TOKEN es requerido como secret del repositorio}"

GRAFANA_URL="${GRAFANA_URL%/}"

log() {
  printf '\n[grafana-check] %s\n' "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[grafana-check][ERROR] El comando '$1' no está disponible." >&2
    exit 1
  fi
}

require_command curl
require_command python3

AUTH_HEADER="Authorization: Bearer ${GRAFANA_API_TOKEN}"

log "1/3 Verificando salud de Grafana..."

HEALTH_JSON="$(curl --fail --silent --show-error --max-time 15 \
  -H "$AUTH_HEADER" \
  "${GRAFANA_URL}/api/health")"

echo "$HEALTH_JSON"

DB_STATUS="$(printf '%s' "$HEALTH_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("database", "unknown"))')"

if [[ "$DB_STATUS" != "ok" ]]; then
  echo "[grafana-check][ERROR] La base de datos de Grafana no está sana: $DB_STATUS" >&2
  exit 1
fi

log "Grafana está arriba y su base de datos responde ok."

log "2/3 Verificando dashboards de Linker..."

DASHBOARDS_JSON="$(curl --fail --silent --show-error --max-time 15 \
  -H "$AUTH_HEADER" \
  "${GRAFANA_URL}/api/search?query=linker&type=dash-db")"

DASHBOARD_COUNT="$(printf '%s' "$DASHBOARDS_JSON" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"

if [[ "$DASHBOARD_COUNT" -eq 0 ]]; then
  echo "[grafana-check][ERROR] No se encontró ningún dashboard de Linker en Grafana." >&2
  exit 1
fi

printf '%s' "$DASHBOARDS_JSON" | python3 -c 'import json,sys; [print("  -", d.get("title", "sin titulo")) for d in json.load(sys.stdin)]'

log "Se encontraron $DASHBOARD_COUNT dashboards de Linker."

log "3/3 Registrando anotación del despliegue..."

ANNOTATION_PAYLOAD="$(python3 - <<'PY'
import json
import os

deploy_sha = os.environ.get("DEPLOY_SHA", "desconocido")
deploy_run_url = os.environ.get("DEPLOY_RUN_URL", "no-disponible")

payload = {
    "tags": ["deployment", "linker", "blue-green"],
    "text": f"Despliegue Blue/Green de Linker - commit: {deploy_sha} - pipeline: {deploy_run_url}",
}

print(json.dumps(payload))
PY
)"

curl --fail --silent --show-error --max-time 15 \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -X POST "${GRAFANA_URL}/api/annotations" \
  -d "$ANNOTATION_PAYLOAD" >/dev/null

log "Anotación creada: el despliegue quedará visible en los dashboards."
log "Chequeo de Grafana post-despliegue finalizado correctamente."