#!/usr/bin/env bash
# Carga infra/linker.env (OCIDs versionados en el repo, ej. subred y Load
# Balancer del equipo) al entorno de los pasos siguientes del job.
#
# Los OCIDs no son secretos por si solos (requieren credenciales OCI para
# usarse), asi que el equipo los versiona en infra/linker.env en vez de
# copiarlos a mano en GitHub Actions. Este script es la unica fuente de
# verdad: si el archivo cambia, el pipeline lo recoge automaticamente.
set -euo pipefail

INFRA_ENV_FILE="${INFRA_ENV_FILE:-infra/linker.env}"

if [[ ! -f "$INFRA_ENV_FILE" ]]; then
  echo "[load-infra-env][ERROR] No existe $INFRA_ENV_FILE" >&2
  exit 1
fi

echo "[load-infra-env] Cargando variables desde $INFRA_ENV_FILE..."

set -a
# shellcheck disable=SC1090
source "$INFRA_ENV_FILE"
set +a

while IFS='=' read -r key _ || [[ -n "$key" ]]; do
  [[ -z "$key" || "$key" == \#* ]] && continue
  printf '%s=%s\n' "$key" "${!key}" >> "$GITHUB_ENV"
  echo "[load-infra-env]   $key cargado."
done < "$INFRA_ENV_FILE"
