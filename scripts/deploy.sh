#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p /home/team/yarn-lab/logs
exec > >(tee -a /home/team/yarn-lab/logs/deploy.log) 2>&1
trap 'echo "FAILED at line $LINENO" >&2' ERR
bash "$ROOT/scripts/bootstrap.sh"
bash "$ROOT/scripts/install-config.sh"
if [[ ${RUN_SINGLE_DEMO:-auto} == 1 || ( ${RUN_SINGLE_DEMO:-auto} == auto && ! -f /home/team/yarn-lab/logs/single-node.passed ) ]]; then bash "$ROOT/scripts/single-node.sh"; fi
bash "$ROOT/scripts/start-cluster.sh"
bash "$ROOT/scripts/publish.sh"
bash "$ROOT/scripts/smoke.sh"
echo 'PASS: full deployment complete'
