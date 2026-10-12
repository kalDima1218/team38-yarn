#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$ROOT/scripts/generate.py" "$ROOT/generated"
SSH=(ssh -n -i /home/team/.ssh/team_internal -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15)
install_host() {
  local source=$1
  sudo python3 - <<'PY'
from pathlib import Path
nodes={'team-38-en':'10.38.0.10','team-38-nn':'10.38.0.11','team-38-00':'10.38.0.12','team-38-01':'10.38.0.13'}
p=Path('/etc/hosts')
backup=Path('/etc/hosts.pre-yarn')
if not backup.exists(): backup.write_text(p.read_text())
lines=[]
for line in p.read_text().splitlines():
    content,sep,comment=line.partition('#')
    fields=content.split()
    if len(fields)>1:
        aliases=[t for t in fields[1:] if t not in nodes and t.removesuffix('.hse.c.mws') not in nodes]
        if len(aliases)!=len(fields)-1:
            if aliases: lines.append(' '.join([fields[0],*aliases])+(' #'+comment if sep else ''))
            elif sep: lines.append('#'+comment)
            continue
    lines.append(line)
lines.extend(f'{ip} {name} {name}.hse.c.mws' for name,ip in nodes.items())
p.write_text('\n'.join(lines)+'\n')
PY
  id hadoop >/dev/null 2>&1 || sudo useradd --system --create-home --home-dir /var/lib/hadoop --shell /bin/bash hadoop
  sudo mkdir -p /etc/hadoop /var/lib/hadoop/{hdfs/name,hdfs/data,hdfs/checkpoint,yarn/local,yarn/container-logs,timeline,timeline-state,history-state,run,tmp} /var/log/hadoop
  sudo chown -R hadoop:hadoop /var/lib/hadoop /var/log/hadoop
  if [[ -d /etc/hadoop && -f /etc/hadoop/yarn-site.xml ]]; then
    sudo cp -a /etc/hadoop "/etc/hadoop.backup.$(date +%s)"
  fi
  sudo cp -a /opt/hadoop/etc/hadoop/. /etc/hadoop/
  sudo cp "$source"/hadoop/* /etc/hadoop/
  sudo cp "$source"/systemd/* /etc/systemd/system/
  sudo tee /etc/profile.d/hadoop.sh >/dev/null <<'ENV'
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_COMMON_HOME=/opt/hadoop
export HADOOP_HDFS_HOME=/opt/hadoop
export HADOOP_YARN_HOME=/opt/hadoop
export HADOOP_MAPRED_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/etc/hadoop
export PATH=$PATH:/opt/hadoop/bin:/opt/hadoop/sbin
ENV
  sudo systemctl daemon-reload
}
install_host "$ROOT/generated/team-38-en"
for node in team-38-nn team-38-00 team-38-01; do
  rsync -a -e 'ssh -i /home/team/.ssh/team_internal -o BatchMode=yes' "$ROOT/generated/$node/" "team@$node:/home/team/yarn-config/"
  "${SSH[@]}" "team@$node" "set -euo pipefail; $(declare -f install_host); install_host /home/team/yarn-config"
done
echo 'STAGE: all configurations installed'
