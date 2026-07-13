#!/usr/bin/env bash
# Switchover de trafico Blue/Green. Soporta dos mecanismos, segun las
# variables configuradas en el repositorio:
#
#   1. IP privada flotante (recomendado con el proxy del curso):
#      El dominio del equipo apunta a una IP privada fija. Esa IP se mantiene
#      como IP secundaria y se mueve entre la VNIC del ambiente azul y verde.
#      Requiere: OCI_FLOATING_IP_ADDRESS y OCI_SUBNET_OCID.
#
#   2. OCI Load Balancer:
#      Se registra el nuevo backend y se retiran los demas del backend set.
#      Requiere: OCI_LB_OCID y OCI_LB_BACKEND_SET.
#
# Entradas:
#   TARGET_VNIC_ID       VNIC del ambiente que recibira el trafico (modo IP flotante)
#   TARGET_PRIVATE_IP    IP privada del ambiente nuevo (modo Load Balancer)
#   APP_PORT             Puerto de la aplicacion (default: 8080)
set -euo pipefail

APP_PORT="${APP_PORT:-8080}"

log() { printf '\n[switch-traffic] %s\n' "$1"; }

if [[ -n "${OCI_FLOATING_IP_ADDRESS:-}" ]]; then
  : "${TARGET_VNIC_ID:?TARGET_VNIC_ID es requerido en modo IP flotante}"
  : "${OCI_SUBNET_OCID:?OCI_SUBNET_OCID es requerido en modo IP flotante}"

  log "Modo IP flotante: moviendo $OCI_FLOATING_IP_ADDRESS hacia la VNIC nueva..."
  oci network vnic assign-private-ip \
    --vnic-id "$TARGET_VNIC_ID" \
    --ip-address "$OCI_FLOATING_IP_ADDRESS" \
    --unassign-if-already-assigned

  log "Switchover completado: el trafico ahora llega al ambiente nuevo."

elif [[ -n "${OCI_LB_OCID:-}" ]]; then
  : "${TARGET_PRIVATE_IP:?TARGET_PRIVATE_IP es requerido en modo Load Balancer}"
  : "${OCI_LB_BACKEND_SET:?OCI_LB_BACKEND_SET es requerido en modo Load Balancer}"

  log "Modo Load Balancer: registrando backend $TARGET_PRIVATE_IP:$APP_PORT..."
  oci lb backend create \
    --load-balancer-id "$OCI_LB_OCID" \
    --backend-set-name "$OCI_LB_BACKEND_SET" \
    --ip-address "$TARGET_PRIVATE_IP" \
    --port "$APP_PORT" \
    --weight 1 \
    --wait-for-state SUCCEEDED || log "El backend ya existia, continuando."

  log "Retirando los backends anteriores del backend set..."
  OLD_BACKENDS="$(oci lb backend list \
    --load-balancer-id "$OCI_LB_OCID" \
    --backend-set-name "$OCI_LB_BACKEND_SET" \
    --query 'data[].name' | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin)))')"

  while IFS= read -r backend; do
    [[ -z "$backend" ]] && continue
    if [[ "$backend" == "$TARGET_PRIVATE_IP:$APP_PORT" ]]; then
      continue
    fi
    log "Eliminando backend anterior: $backend"
    oci lb backend delete \
      --load-balancer-id "$OCI_LB_OCID" \
      --backend-set-name "$OCI_LB_BACKEND_SET" \
      --backend-name "$backend" \
      --force \
      --wait-for-state SUCCEEDED
  done <<< "$OLD_BACKENDS"

  log "Switchover completado: el Load Balancer apunta al ambiente nuevo."

else
  echo "[switch-traffic][ERROR] Configure OCI_FLOATING_IP_ADDRESS (IP flotante) u OCI_LB_OCID + OCI_LB_BACKEND_SET (Load Balancer)." >&2
  exit 1
fi
