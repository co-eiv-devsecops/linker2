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
oci compute instance terminate \
  --instance-id "$INSTANCE_ID" \
  --preserve-boot-volume false \
  --force \
  --wait-for-state TERMINATED \
  --wait-interval-seconds 15

log "Instancia eliminada."
