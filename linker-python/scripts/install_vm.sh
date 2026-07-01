#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/linker-python"
APP_USER="${APP_USER:-$USER}"
DOMAIN="${DOMAIN:-X.n-la-c.app}"
PORT="${PORT:-8080}"

sudo apt-get update
sudo apt-get install -y python3 nginx

sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

cp app.py requirements.txt "$APP_DIR/"
cd "$APP_DIR"

sudo tee /etc/systemd/system/linker-python.service > /dev/null <<EOF
[Unit]
Description=Linker Python URL Shortener
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PORT=$PORT
Environment=LINKER_DB=$APP_DIR/linker.db
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/nginx/sites-available/linker-python > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/linker-python /etc/nginx/sites-enabled/linker-python
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl daemon-reload
sudo systemctl enable linker-python
sudo systemctl restart linker-python

echo "Aplicación instalada. Revisa: http://$DOMAIN"
