#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
sudo mkdir -p /var/www/yarn-lab
sudo cp "$ROOT/generated/team-38-en/nginx/"*.html /var/www/yarn-lab/
sudo cp "$ROOT/generated/team-38-en/nginx/yarn-lab.conf" /etc/nginx/sites-available/yarn-lab
sudo ln -sfn /etc/nginx/sites-available/yarn-lab /etc/nginx/sites-enabled/yarn-lab
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo 'STAGE: Nginx web gateway ready; verify external ingress or SSH access'
