#!/usr/bin/env bash
# Termina (elimina) una instancia de computo OCI y su boot volume.
# Se usa tanto para destruir el entorno efimero como para retirar la
# version anterior (o la nueva, si fallo) en el despliegue Blue/Green.
#
# Entradas:
#   INSTANCE_ID   OCID de la instancia. Si esta vacio, no hace nada.
set -euo pipefail

log() { printf '\n[terminate-instance] %s\n' "$1"; }

if [[ -z "${INSTANCE_ID:-}" ]]; then
  log "INSTANCE_ID vacio: no hay instancia que eliminar."
  exit 0
fi

STATE="$(oci compute instance get --instance-id "$INSTANCE_ID" \
  --query 'data."lifecycle-state"' --raw-output 2>/dev/null || echo "NOT_FOUND")"

if [[ "$STATE" == "NOT_FOUND" || "$STATE" == "TERMINATED" || "$STATE" == "TERMINATING" ]]; then
  log "La instancia $INSTANCE_ID ya no existe o esta terminandose ($STATE)."
  exit 0
fi

log "Terminando instancia $INSTANCE_ID (estado actual: $STATE)..."
# Sin --wait-for-state: en las versiones recientes del CLI ese flag espera
# estados del work request (SUCCEEDED, ...), no del ciclo de vida de la
# instancia, y TERMINATED lo rechaza. Confirmamos el estado con un poll.
oci compute instance terminate \
  --instance-id "$INSTANCE_ID" \
  --preserve-boot-volume false \
  --force

log "Esperando confirmacion de la terminacion..."
for attempt in $(seq 1 40); do
  STATE="$(oci compute instance get --instance-id "$INSTANCE_ID" \
    --query 'data."lifecycle-state"' --raw-output 2>/dev/null || echo "NOT_FOUND")"
  if [[ "$STATE" == "TERMINATING" || "$STATE" == "TERMINATED" || "$STATE" == "NOT_FOUND" ]]; then
    log "Instancia en estado $STATE. Eliminacion confirmada."
    exit 0
  fi
  sleep 15
done

echo "[terminate-instance][ERROR] La instancia $INSTANCE_ID sigue en estado $STATE." >&2
exit 1
