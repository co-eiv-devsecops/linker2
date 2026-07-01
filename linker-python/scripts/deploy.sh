#!/usr/bin/env bash
set -euo pipefail

TEAM_NUMBER="${TEAM_NUMBER:-X}"
SERVER_USER="${SERVER_USER:-ubuntu}"
SERVER_HOST="${SERVER_HOST:-$TEAM_NUMBER.n-la-c.app}"
REMOTE_DIR="${REMOTE_DIR:-/tmp/linker-python}"
DOMAIN="${DOMAIN:-$TEAM_NUMBER.n-la-c.app}"

ssh "$SERVER_USER@$SERVER_HOST" "rm -rf $REMOTE_DIR && mkdir -p $REMOTE_DIR/scripts"
scp app.py requirements.txt "$SERVER_USER@$SERVER_HOST:$REMOTE_DIR/"
scp scripts/install_vm.sh "$SERVER_USER@$SERVER_HOST:$REMOTE_DIR/scripts/"
ssh "$SERVER_USER@$SERVER_HOST" "cd $REMOTE_DIR && chmod +x scripts/install_vm.sh && DOMAIN=$DOMAIN scripts/install_vm.sh"

echo "Despliegue finalizado: https://$DOMAIN"
