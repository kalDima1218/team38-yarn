#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SSH=(ssh -i /home/team/.ssh/team_internal -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15)
"${SSH[@]}" team@team-38-nn 'set -e; if ! sudo -u hadoop test -f /var/lib/hadoop/hdfs/name/current/VERSION; then sudo -u hadoop /opt/hadoop/bin/hdfs --config /etc/hadoop namenode -format -nonInteractive > /home/team/format-namenode.log 2>&1; fi; sudo systemctl enable --now hadoop-namenode hadoop-resourcemanager'
for node in team-38-00 team-38-01; do
  "${SSH[@]}" "team@$node" 'sudo systemctl enable --now hadoop-datanode hadoop-nodemanager'
done
"${SSH[@]}" team@team-38-nn "python3 - http://team-38-nn:8088/ws/v1/cluster/nodes /var/log/hadoop nodes2" <"$ROOT/scripts/wait-ready.py"
"${SSH[@]}" team@team-38-nn 'sudo -u hadoop /opt/hadoop/bin/hdfs --config /etc/hadoop dfsadmin -safemode wait; sudo -u hadoop /opt/hadoop/bin/hdfs --config /etc/hadoop dfs -mkdir -p /user/team /tmp /tmp/logs /mr-history/tmp /mr-history/done; sudo -u hadoop /opt/hadoop/bin/hdfs --config /etc/hadoop dfs -chown team /user/team; sudo -u hadoop /opt/hadoop/bin/hdfs --config /etc/hadoop dfs -chmod 1777 /tmp /tmp/logs /mr-history/tmp'
sudo systemctl enable --now hadoop-secondarynamenode hadoop-historyserver hadoop-timelineserver hadoop-proxyserver
python3 "$ROOT/scripts/wait-ready.py" http://team-38-en:19888 /var/log/hadoop
python3 "$ROOT/scripts/wait-ready.py" http://team-38-en:8188/ws/v1/timeline /var/log/hadoop
echo 'STAGE: multi-node cluster ready'
