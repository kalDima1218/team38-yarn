#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_CONF_DIR=/etc/hadoop-single
if systemctl is-active --quiet hadoop-secondarynamenode; then
  echo 'Stop the multi-node edge services before running the single-node demo.' >&2; exit 1
fi
sudo mkdir -p /etc/hadoop-single /var/lib/hadoop/single/{hdfs/name,hdfs/data,tmp,run,yarn/local,yarn/container-logs} /var/log/hadoop/single
sudo chown -R hadoop:hadoop /var/lib/hadoop/single /var/log/hadoop/single
sudo cp -a /opt/hadoop/etc/hadoop/. /etc/hadoop-single/
sudo cp "$ROOT/generated/single/hadoop/"* /etc/hadoop-single/
sudo cp "$ROOT/generated/single/systemd/"* /etc/systemd/system/
sudo systemctl daemon-reload
cleanup() {
  sudo systemctl stop hadoop-single-nodemanager hadoop-single-resourcemanager hadoop-single-datanode hadoop-single-namenode
}
trap cleanup EXIT
if ! sudo -u hadoop test -f /var/lib/hadoop/single/hdfs/name/current/VERSION; then
  sudo -u hadoop env HADOOP_CONF_DIR="$HADOOP_CONF_DIR" JAVA_HOME="$JAVA_HOME" /opt/hadoop/bin/hdfs namenode -format -nonInteractive > /home/team/yarn-lab/logs/format-single.log 2>&1
fi
sudo systemctl start hadoop-single-namenode hadoop-single-datanode hadoop-single-resourcemanager hadoop-single-nodemanager
python3 "$ROOT/scripts/wait-ready.py" http://team-38-en:8088/ws/v1/cluster/nodes /var/log/hadoop/single nodes1
sudo -u hadoop env HADOOP_CONF_DIR="$HADOOP_CONF_DIR" JAVA_HOME="$JAVA_HOME" /opt/hadoop/bin/hdfs dfsadmin -safemode wait
sudo -u hadoop env HADOOP_CONF_DIR="$HADOOP_CONF_DIR" JAVA_HOME="$JAVA_HOME" /opt/hadoop/bin/hdfs dfs -mkdir -p /user/team /tmp /mr-history/tmp /mr-history/done
sudo -u hadoop env HADOOP_CONF_DIR="$HADOOP_CONF_DIR" JAVA_HOME="$JAVA_HOME" /opt/hadoop/bin/hdfs dfs -chown team /user/team
sudo -u hadoop env HADOOP_CONF_DIR="$HADOOP_CONF_DIR" JAVA_HOME="$JAVA_HOME" /opt/hadoop/bin/hdfs dfs -chmod 1777 /tmp /mr-history/tmp
echo 'STAGE: single-node ready'
bash "$ROOT/scripts/smoke.sh" /etc/hadoop-single
echo 'STAGE: single-node verified, stopping isolated demo'
touch /home/team/yarn-lab/logs/single-node.passed
