#!/usr/bin/env bash
# Lanza una instancia de computo OCI para Linker y espera a que este lista.
#
# Requiere el OCI CLI configurado (en GitHub Actions se prepara con
# oracle-actions/run-oci-cli-command y las variables OCI_CLI_*).
#
# Entradas (variables de entorno):
#   DISPLAY_NAME              Nombre de la instancia (requerido)
#   OCI_COMPARTMENT_OCID      Compartment donde crearla (requerido)
#   OCI_LINKER_SUBNET_OCID           Subred privada de la instancia (requerido)
#   OCI_IMAGE_OCID            Imagen Ubuntu a usar (requerido)
#   OCI_AVAILABILITY_DOMAIN   Availability domain (requerido)
#   DEPLOYMENT_PUBLIC_KEY     Llave publica SSH autorizada (requerido)
#   OCI_INSTANCE_SHAPE        Shape (default: VM.Standard.E2.1.Micro)
#   OCI_SHAPE_OCPUS           OCPUs si el shape es Flex (default: 1)
#   OCI_SHAPE_MEMORY_GB       Memoria si el shape es Flex (default: 6)
#   FREEFORM_TAGS             JSON de tags freeform (default: {})
#   CLOUD_INIT_FILE           cloud-init (default: scripts/oci/cloud-init-linker.yaml)
#
# Salidas (a $GITHUB_OUTPUT si existe, y por stdout):
#   instance_id, private_ip, vnic_id
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

: "${DISPLAY_NAME:?DISPLAY_NAME es requerido}"
: "${OCI_COMPARTMENT_OCID:?OCI_COMPARTMENT_OCID es requerido}"
: "${OCI_LINKER_SUBNET_OCID:?OCI_LINKER_SUBNET_OCID es requerido}"
: "${OCI_IMAGE_OCID:?OCI_IMAGE_OCID es requerido}"
: "${OCI_AVAILABILITY_DOMAIN:?OCI_AVAILABILITY_DOMAIN es requerido}"
: "${DEPLOYMENT_PUBLIC_KEY:?DEPLOYMENT_PUBLIC_KEY es requerido}"

SHAPE="${OCI_INSTANCE_SHAPE:-VM.Standard.E2.1.Micro}"
FREEFORM_TAGS="${FREEFORM_TAGS:-}"
[[ -z "$FREEFORM_TAGS" ]] && FREEFORM_TAGS='{}'
CLOUD_INIT_FILE="${CLOUD_INIT_FILE:-$SCRIPT_DIR/cloud-init-linker.yaml}"

log() { printf '\n[launch-instance] %s\n' "$1"; }

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

USER_DATA_B64="$(base64 < "$CLOUD_INIT_FILE" | tr -d '\n')"
python3 - "$WORK_DIR/metadata.json" <<PY
import json, os, sys
with open(sys.argv[1], "w") as fh:
    json.dump({
        "ssh_authorized_keys": os.environ["DEPLOYMENT_PUBLIC_KEY"],
        "user_data": "$USER_DATA_B64",
    }, fh)
PY

# El plugin Bastion es obligatorio para las sesiones managed SSH del pipeline.
cat > "$WORK_DIR/agent-config.json" <<'JSON'
{
  "isMonitoringDisabled": false,
  "isManagementDisabled": false,
  "pluginsConfig": [
    {"name": "Bastion", "desiredState": "ENABLED"}
  ]
}
JSON

SHAPE_CONFIG_ARGS=()
if [[ "$SHAPE" == *Flex* ]]; then
  printf '{"ocpus": %s, "memoryInGBs": %s}' \
    "${OCI_SHAPE_OCPUS:-1}" "${OCI_SHAPE_MEMORY_GB:-6}" > "$WORK_DIR/shape-config.json"
  SHAPE_CONFIG_ARGS=(--shape-config "file://$WORK_DIR/shape-config.json")
fi

log "Lanzando instancia '$DISPLAY_NAME' (shape: $SHAPE)..."
INSTANCE_ID="$(oci compute instance launch \
  --compartment-id "$OCI_COMPARTMENT_OCID" \
  --availability-domain "$OCI_AVAILABILITY_DOMAIN" \
  --subnet-id "$OCI_LINKER_SUBNET_OCID" \
  --image-id "$OCI_IMAGE_OCID" \
  --shape "$SHAPE" \
  "${SHAPE_CONFIG_ARGS[@]}" \
  --display-name "$DISPLAY_NAME" \
  --assign-public-ip false \
  --metadata "file://$WORK_DIR/metadata.json" \
  --agent-config "file://$WORK_DIR/agent-config.json" \
  --freeform-tags "$FREEFORM_TAGS" \
  --wait-for-state RUNNING \
  --wait-interval-seconds 15 \
  --query 'data.id' \
  --raw-output)"

log "Instancia creada y RUNNING: $INSTANCE_ID"

VNIC_JSON="$(oci compute instance list-vnics --instance-id "$INSTANCE_ID" --query 'data[0]')"
PRIVATE_IP="$(printf '%s' "$VNIC_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["private-ip"])')"
VNIC_ID="$(printf '%s' "$VNIC_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

log "IP privada: $PRIVATE_IP"
log "VNIC: $VNIC_ID"

log "Esperando a que el plugin Bastion del agente este RUNNING (hasta 15 min)..."
DEADLINE=$(( $(date +%s) + 900 ))
while true; do
  STATUS="$(oci instance-agent plugin get \
    --instanceagent-id "$INSTANCE_ID" \
    --compartment-id "$OCI_COMPARTMENT_OCID" \
    --plugin-name Bastion \
    --query 'data.status' --raw-output 2>/dev/null || echo "PENDING")"
  log "Estado plugin Bastion: $STATUS"
  [[ "$STATUS" == "RUNNING" ]] && break
  if (( $(date +%s) > DEADLINE )); then
    echo "[launch-instance][ERROR] El plugin Bastion no quedo RUNNING a tiempo." >&2
    exit 1
  fi
  sleep 20
done

# Margen para que el plugin se registre con el servicio Bastion. El estado
# RUNNING del agente no garantiza que el servicio ya acepte sesiones para
# esta VM: pedir la sesion demasiado pronto la deja atascada en CREATING.
BASTION_SETTLE_SECONDS="${BASTION_SETTLE_SECONDS:-180}"
log "Esperando ${BASTION_SETTLE_SECONDS}s a que el plugin se registre con el servicio Bastion..."
sleep "$BASTION_SETTLE_SECONDS"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "instance_id=$INSTANCE_ID"
    echo "private_ip=$PRIVATE_IP"
    echo "vnic_id=$VNIC_ID"
  } >> "$GITHUB_OUTPUT"
fi

log "Instancia lista para despliegue via Bastion."
