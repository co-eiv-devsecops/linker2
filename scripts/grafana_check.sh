#!/usr/bin/env bash
# Chequeo post-despliegue usando OpenTelemetry.
#
# Este script no usa la API HTTP de Grafana.
# En su lugar:
# 1. Valida que producción responda /health y /healthz.
# 2. Ejecuta una prueba funcional creando un enlace corto.
# 3. Genera tráfico observado.
# 4. Emite un span OpenTelemetry del despliegue para verlo en Grafana.

set -euo pipefail

: "${PROD_BASE_URL:?PROD_BASE_URL es requerido}"
: "${OTEL_EXPORTER_OTLP_ENDPOINT:?OTEL_EXPORTER_OTLP_ENDPOINT es requerido}"
: "${OTEL_EXPORTER_OTLP_HEADERS:?OTEL_EXPORTER_OTLP_HEADERS es requerido}"

PROD_BASE_URL="${PROD_BASE_URL%/}"

log() {
  printf '\n[otel-post-deploy] %s\n' "$1"
}

log "1/4 Validando healthchecks de produccion..."

curl --fail --silent --show-error --max-time 15 "$PROD_BASE_URL/health"
echo

curl --fail --silent --show-error --max-time 15 "$PROD_BASE_URL/healthz"
echo

log "2/4 Ejecutando prueba funcional de creacion de enlace..."

RESPONSE_HEADERS="$(mktemp)"
RESPONSE_BODY="$(mktemp)"

TEST_TARGET_URL="${LINKER_TEST_TARGET_URL:-${PROD_BASE_URL}/health}"

curl --fail --silent --show-error -i -X POST "$PROD_BASE_URL/link" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "url=${TEST_TARGET_URL}" \
  -D "$RESPONSE_HEADERS" \
  -o "$RESPONSE_BODY"

SHORT_LOCATION="$(awk 'tolower($1) == "location:" {print $2}' "$RESPONSE_HEADERS" | tr -d '\r' | tail -1)"

if [[ -z "$SHORT_LOCATION" ]]; then
  echo "[otel-post-deploy][ERROR] No se obtuvo header Location al crear el enlace." >&2
  cat "$RESPONSE_HEADERS" >&2
  cat "$RESPONSE_BODY" >&2
  exit 1
fi

echo "Short URL creada: $SHORT_LOCATION"

log "3/4 Generando trafico para trazas en Grafana..."

for attempt in $(seq 1 5); do
  curl --fail --silent --show-error --max-time 15 "$PROD_BASE_URL/healthz" > /dev/null
done

curl --fail --silent --show-error --max-time 15 "$SHORT_LOCATION" > /dev/null || true

log "4/4 Emitiendo span OpenTelemetry del despliegue..."

python3 - <<'PY'
import os
import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

service_name = os.environ.get("OTEL_SERVICE_NAME", "linker-post-deploy-check")

resource = Resource.create({
    "service.name": service_name,
    "deployment.environment": "production",
    "linker.component": "post-deploy-check",
})

provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

exporter = OTLPSpanExporter()
provider.add_span_processor(BatchSpanProcessor(exporter))

tracer = trace.get_tracer("linker.post_deploy")

with tracer.start_as_current_span("linker.deployment.post_deploy_check") as span:
    span.set_attribute("linker.deploy.sha", os.environ.get("DEPLOY_SHA", "unknown"))
    span.set_attribute("linker.deploy.run_id", os.environ.get("DEPLOY_RUN_ID", "unknown"))
    span.set_attribute("linker.deploy.repository", os.environ.get("GITHUB_REPOSITORY", "unknown"))
    span.set_attribute("linker.deploy.base_url", os.environ.get("PROD_BASE_URL", "unknown"))
    span.set_attribute("linker.deploy.strategy", "blue-green")
    span.set_attribute("linker.deploy.validation", "success")
    span.set_attribute("linker.monitoring.backend", "grafana-cloud-otlp")
    time.sleep(1)

provider.shutdown()

print("Span linker.deployment.post_deploy_check enviado por OpenTelemetry.")
PY

log "Chequeo post-despliegue finalizado correctamente."