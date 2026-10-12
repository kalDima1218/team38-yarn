#!/usr/bin/env bash
set -euo pipefail
KEY=${1:?Usage: bash scripts/access.sh /path/to/your/ssh_private_key}
OPTIONS=()
if [[ -n ${2:-} ]]; then OPTIONS+=(-o "UserKnownHostsFile=$2"); fi
if [[ ${OPEN_BROWSER:-0} == 1 ]]; then
  OPTIONS+=(-o PermitLocalCommand=yes -o 'LocalCommand=/usr/bin/open http://127.0.0.1:18080/')
fi
exec ssh "${OPTIONS[@]}" -i "$KEY" -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -N \
  -L 127.0.0.1:18080:127.0.0.1:80 \
  -L 127.0.0.1:18088:127.0.0.1:18088 \
  -L 127.0.0.1:18042:127.0.0.1:18042 \
  -L 127.0.0.1:18043:127.0.0.1:18043 \
  -L 127.0.0.1:19880:127.0.0.1:19880 \
  -L 127.0.0.1:18188:127.0.0.1:18188 \
  -L 127.0.0.1:19099:127.0.0.1:19099 \
  -L 127.0.0.1:19870:127.0.0.1:19870 \
  -L 127.0.0.1:19864:127.0.0.1:19864 \
  -L 127.0.0.1:19865:127.0.0.1:19865 \
  -L 127.0.0.1:19868:127.0.0.1:19868 \
  team@178.236.27.140
