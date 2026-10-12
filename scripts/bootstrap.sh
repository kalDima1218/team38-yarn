#!/usr/bin/env bash
set -euo pipefail
VERSION=3.5.0
LAB=/home/team/yarn-lab
mkdir -p "$LAB/cache" "$LAB/logs"
SSH=(ssh -n -i /home/team/.ssh/team_internal -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
install_java='sudo env DEBIAN_FRONTEND=noninteractive apt-get update && sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-17-jdk-headless curl python3 rsync nginx inotify-tools'
for node in team-38-nn team-38-00 team-38-01; do
  "${SSH[@]}" "team@$node" "$install_java" >"$LAB/logs/bootstrap-$node.log" 2>&1 &
  pids+=("$!")
done
bash -c "$install_java" >"$LAB/logs/bootstrap-team-38-en.log" 2>&1 &
pids+=("$!")
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
(( failed == 0 )) || { echo "Bootstrap failed; inspect all node logs" >&2; exit 1; }
echo 'STAGE: Java installed on all nodes'
cd "$LAB/cache"
archive="hadoop-$VERSION.tar.gz"
base="https://downloads.apache.org/hadoop/common/hadoop-$VERSION"
if [[ ! -f "$archive" ]]; then
  curl --fail --location --connect-timeout 20 --speed-time 90 --speed-limit 1024 "$base/$archive" -o "$archive.part"
  mv "$archive.part" "$archive"
fi
curl --fail --silent --show-error --location "$base/$archive.sha512" -o "$archive.sha512"
python3 - "$archive" "$archive.sha512" <<'PY'
import hashlib,re,sys
p, s=sys.argv[1:]
expected=re.search(r'\b[0-9a-fA-F]{128}\b',open(s).read()).group().lower()
h=hashlib.sha512()
with open(p,'rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
assert h.hexdigest()==expected, 'Hadoop checksum mismatch'
print('STAGE: SHA-512 verified:',h.hexdigest())
PY
if [[ ! -d /opt/hadoop-$VERSION ]]; then sudo tar -xzf "$archive" -C /opt; fi
sudo ln -sfn "/opt/hadoop-$VERSION" /opt/hadoop
for node in team-38-nn team-38-00 team-38-01; do
  echo "STAGE: distribute Hadoop to $node"
  rsync -a -e "ssh -i /home/team/.ssh/team_internal -o BatchMode=yes" "$archive" "team@$node:/tmp/$archive"
  "${SSH[@]}" "team@$node" "set -euo pipefail; if [ ! -d /opt/hadoop-$VERSION ]; then sudo tar -xzf /tmp/$archive -C /opt; fi; sudo ln -sfn /opt/hadoop-$VERSION /opt/hadoop; rm -f /tmp/$archive; java -version"
done
echo 'STAGE: bootstrap complete'
