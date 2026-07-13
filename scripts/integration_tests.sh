#!/usr/bin/env bash
# Pruebas de integracion y funcionalidad de Linker contra una URL base.
# Se usan en el entorno efimero (localhost en la VM efimera), en el
# ambiente inactivo del Blue/Green antes del switchover, y como smoke
# test despues del switchover.
#
# Uso: integration_tests.sh <BASE_URL>
#   ej: integration_tests.sh http://localhost:8080
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-http://localhost:8080}}"
BASE_URL="${BASE_URL%/}"
TARGET_URL="https://www.example.com/"

PASS=0
FAIL=0

log()  { printf '\n[integration] %s\n' "$1"; }
ok()   { PASS=$((PASS + 1)); printf '  ✅ %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf '  ❌ %s\n' "$1"; }

log "Ejecutando pruebas de integracion contra $BASE_URL"

# Esperar disponibilidad del servicio (hasta 60s)
for attempt in $(seq 1 30); do
  if curl --silent --max-time 5 -o /dev/null "$BASE_URL/health"; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "[integration][ERROR] El servicio no respondio en $BASE_URL" >&2
    exit 1
  fi
  sleep 2
done

# 1. Pagina principal
STATUS="$(curl --silent -o /dev/null -w '%{http_code}' "$BASE_URL/")"
[[ "$STATUS" == "200" ]] && ok "GET / responde 200" || bad "GET / respondio $STATUS (esperado 200)"

# 2. Healthcheck de aplicacion
STATUS="$(curl --silent -o /dev/null -w '%{http_code}' "$BASE_URL/health")"
[[ "$STATUS" == "200" ]] && ok "GET /health responde 200" || bad "GET /health respondio $STATUS (esperado 200)"

# 3. Healthcheck con base de datos
STATUS="$(curl --silent -o /dev/null -w '%{http_code}' "$BASE_URL/healthz")"
[[ "$STATUS" == "200" ]] && ok "GET /healthz responde 200" || bad "GET /healthz respondio $STATUS (esperado 200)"

# 4. Crear URL corta
HEADERS_FILE="$(mktemp)"
STATUS="$(curl --silent -o /dev/null -w '%{http_code}' -D "$HEADERS_FILE" \
  -X POST "$BASE_URL/link" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "url=$TARGET_URL")"
LOCATION="$(grep -i '^Location:' "$HEADERS_FILE" | tr -d '\r' | awk '{print $2}' || true)"

if [[ "$STATUS" == "201" && "$LOCATION" == *"/r/"* ]]; then
  ok "POST /link responde 201 con Location $LOCATION"
else
  bad "POST /link respondio $STATUS con Location '$LOCATION' (esperado 201 y /r/...)"
fi

# 5. La URL corta redirecciona a la URL original
if [[ -n "$LOCATION" ]]; then
  SHORT_PATH="/r/${LOCATION##*/r/}"
  REDIRECT_HEADERS="$(mktemp)"
  STATUS="$(curl --silent -o /dev/null -w '%{http_code}' -D "$REDIRECT_HEADERS" "$BASE_URL$SHORT_PATH")"
  REDIRECT_TO="$(grep -i '^Location:' "$REDIRECT_HEADERS" | tr -d '\r' | awk '{print $2}' || true)"
  if [[ "$STATUS" == "301" && "$REDIRECT_TO" == "$TARGET_URL" ]]; then
    ok "GET $SHORT_PATH redirecciona (301) a $TARGET_URL"
  else
    bad "GET $SHORT_PATH respondio $STATUS hacia '$REDIRECT_TO' (esperado 301 hacia $TARGET_URL)"
  fi
else
  bad "No se obtuvo URL corta, se omite la prueba de redireccion"
fi

# 6. URL corta inexistente responde 404
STATUS="$(curl --silent -o /dev/null -w '%{http_code}' "$BASE_URL/r/noexiste000")"
[[ "$STATUS" == "404" ]] && ok "GET /r/noexiste000 responde 404" || bad "GET /r/noexiste000 respondio $STATUS (esperado 404)"

# 7. URL invalida es rechazada con 400
STATUS="$(curl --silent -o /dev/null -w '%{http_code}' \
  -X POST "$BASE_URL/link" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "url=esto-no-es-una-url")"
[[ "$STATUS" == "400" ]] && ok "POST /link con URL invalida responde 400" || bad "POST /link invalido respondio $STATUS (esperado 400)"

log "Resultado: $PASS pruebas exitosas, $FAIL fallidas."

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi

log "Todas las pruebas de integracion pasaron. ✅"
