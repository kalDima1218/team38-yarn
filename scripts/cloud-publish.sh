#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [[ ! -x /usr/local/bin/cloudflared ]]; then
  curl --fail --location --connect-timeout 20 --speed-time 60 --speed-limit 1024 \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /home/team/yarn-lab/cache/cloudflared-linux-amd64
  sudo install -m 0755 /home/team/yarn-lab/cache/cloudflared-linux-amd64 /usr/local/bin/cloudflared
fi
/usr/local/bin/cloudflared --version
python3 "$ROOT/scripts/cloud-publish.py"
