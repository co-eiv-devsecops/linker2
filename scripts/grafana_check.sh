#!/usr/bin/env bash
# Chequeo de Grafana despues de un despliegue (bono del taller).
#
# 1. Verifica que Grafana este arriba y su base de datos sana (/api/health).
# 2. Con GRAFANA_API_TOKEN ademas:
#    - Verifica que existan dashboards de Linker (busqueda por 'linker').
#    - Registra una anotacion del despliegue, para correlacionar en los
#      dashboards cualquier cambio de metricas con este despliegue.
#
# Entradas:
#   GRAFANA_URL        URL base de Grafana, ej: https://xxxx.grafana.net (requerido)
#   GRAFANA_API_TOKEN  Service account token (opcional pero recomendado)
#   DEPLOY_SHA         SHA del commit desplegado (opcional)
#   DEPLOY_RUN_URL     URL de la corrida del pipeline (opcional)
set -euo pipefail

: "${GRAFANA_URL:?GRAFANA_URL es requerido (variable de repositorio)}"
GRAFANA_URL="${GRAFANA_URL%/}"

log() { printf '\n[grafana-check] %s\n' "$1"; }

log "1/3 Verificando salud de Grafana en $GRAFANA_URL/api/health ..."
HEALTH_JSON="$(curl --fail --silent --max-time 15 "$GRAFANA_URL/api/health")"
echo "$HEALTH_JSON"

DB_STATUS="$(printf '%s' "$HEALTH_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("database", "unknown"))')"
if [[ "$DB_STATUS" != "ok" ]]; then
  echo "[grafana-check][ERROR] La base de datos de Grafana no esta sana: $DB_STATUS" >&2
  exit 1
fi
log "Grafana esta arriba y su base de datos responde ok."

if [[ -z "${GRAFANA_API_TOKEN:-}" ]]; then
  log "GRAFANA_API_TOKEN no configurado: se omiten dashboards y anotacion."
  log "Chequeo basico de Grafana finalizado."
  exit 0
fi

AUTH_HEADER="Authorization: Bearer $GRAFANA_API_TOKEN"

log "2/3 Verificando dashboards de Linker..."
DASHBOARDS_JSON="$(curl --fail --silent --max-time 15 -H "$AUTH_HEADER" \
  "$GRAFANA_URL/api/search?query=linker&type=dash-db")"
DASHBOARD_COUNT="$(printf '%s' "$DASHBOARDS_JSON" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"

if [[ "$DASHBOARD_COUNT" -eq 0 ]]; then
  echo "[grafana-check][ERROR] No se encontro ningun dashboard de Linker en Grafana." >&2
  exit 1
fi
printf '%s' "$DASHBOARDS_JSON" | python3 -c 'import json,sys; [print("  -", d["title"]) for d in json.load(sys.stdin)]'
log "Se encontraron $DASHBOARD_COUNT dashboards de Linker."

log "3/3 Registrando anotacion del despliegue..."
ANNOTATION_PAYLOAD="$(python3 - <<PY
import json, os
print(json.dumps({
    "tags": ["deployment", "linker", "blue-green"],
    "text": "Despliegue Blue/Green de Linker<br>commit: {}<br><a href=\"{}\">Pipeline</a>".format(
        os.environ.get("DEPLOY_SHA", "desconocido"),
        os.environ.get("DEPLOY_RUN_URL", "#"),
    ),
}))
PY
)"

curl --fail --silent --max-time 15 \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -X POST "$GRAFANA_URL/api/annotations" \
  -d "$ANNOTATION_PAYLOAD" && echo

log "Anotacion creada: el despliegue quedara visible en los dashboards."
log "Chequeo de Grafana post-despliegue finalizado correctamente. ✅"
