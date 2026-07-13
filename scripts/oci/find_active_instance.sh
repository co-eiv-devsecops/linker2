#!/usr/bin/env bash
# Encuentra la instancia de Linker actualmente ACTIVA en produccion.
#
# El pipeline marca la instancia activa con el tag freeform linker-role=active
# y su color con linker-color=blue|green. Con eso se decide el color del
# proximo despliegue (el ambiente inactivo).
#
# Entradas:
#   OCI_COMPARTMENT_OCID   Compartment del equipo (requerido)
#
# Salidas (a $GITHUB_OUTPUT si existe, y por stdout):
#   active_id, active_name, active_color, active_ip, active_vnic_id
#   next_color   (color del nuevo ambiente a desplegar)
set -euo pipefail

: "${OCI_COMPARTMENT_OCID:?OCI_COMPARTMENT_OCID es requerido}"

log() { printf '\n[find-active] %s\n' "$1"; }

ACTIVE_JSON="$(oci compute instance list \
  --compartment-id "$OCI_COMPARTMENT_OCID" \
  --lifecycle-state RUNNING \
  --all \
  --query 'data[?"freeform-tags"."linker-role"==`active`] | [0]')"

ACTIVE_ID=""
ACTIVE_NAME=""
ACTIVE_COLOR=""
ACTIVE_IP=""
ACTIVE_VNIC_ID=""

if [[ -n "$ACTIVE_JSON" && "$ACTIVE_JSON" != "null" ]]; then
  ACTIVE_ID="$(printf '%s' "$ACTIVE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  ACTIVE_NAME="$(printf '%s' "$ACTIVE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["display-name"])')"
  ACTIVE_COLOR="$(printf '%s' "$ACTIVE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("freeform-tags", {}).get("linker-color", "blue"))')"

  VNIC_JSON="$(oci compute instance list-vnics --instance-id "$ACTIVE_ID" --query 'data[0]')"
  ACTIVE_IP="$(printf '%s' "$VNIC_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["private-ip"])')"
  ACTIVE_VNIC_ID="$(printf '%s' "$VNIC_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

  log "Instancia activa: $ACTIVE_NAME ($ACTIVE_COLOR) ip=$ACTIVE_IP"
else
  log "No hay instancia activa etiquetada (primer despliegue Blue/Green)."
fi

if [[ "$ACTIVE_COLOR" == "blue" ]]; then
  NEXT_COLOR="green"
else
  NEXT_COLOR="blue"
fi

log "Proximo ambiente a desplegar: $NEXT_COLOR"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "active_id=$ACTIVE_ID"
    echo "active_name=$ACTIVE_NAME"
    echo "active_color=$ACTIVE_COLOR"
    echo "active_ip=$ACTIVE_IP"
    echo "active_vnic_id=$ACTIVE_VNIC_ID"
    echo "next_color=$NEXT_COLOR"
  } >> "$GITHUB_OUTPUT"
fi
