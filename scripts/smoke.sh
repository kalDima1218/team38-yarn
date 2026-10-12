#!/usr/bin/env bash
set -euo pipefail
export HADOOP_CONF_DIR=${1:-/etc/hadoop}
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_MAPRED_HOME=/opt/hadoop
export PATH=$PATH:/opt/hadoop/bin
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RUN="/user/team/yarn-check-$(date +%Y%m%d-%H%M%S)"
INPUT=$(mktemp)
EXPECTED=$(mktemp)
ACTUAL=$(mktemp)
trap 'rm -f "$INPUT" "$EXPECTED" "$ACTUAL"' EXIT
printf 'hello yarn\nhello hadoop\n' >"$INPUT"
printf 'hadoop\t1\nhello\t2\nyarn\t1\n' >"$EXPECTED"
hdfs dfs -mkdir -p "$RUN/input"
hdfs dfs -put "$INPUT" "$RUN/input/text.txt"
timeout 180 hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.5.0.jar wordcount "$RUN/input" "$RUN/wordcount"
hdfs dfs -cat "$RUN/wordcount/part-r-*" | LC_ALL=C sort >"$ACTUAL"
diff -u "$EXPECTED" "$ACTUAL"
echo "PASS WordCount: $RUN/wordcount"
if [[ "$HADOOP_CONF_DIR" == /etc/hadoop ]]; then
  timeout 180 hadoop jar /opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.5.0.jar \
    -D mapreduce.job.reduces=1 -files "$ROOT/examples/mapper.py,$ROOT/examples/reducer.py" \
    -input "$RUN/input" -output "$RUN/streaming" \
    -mapper 'python3 mapper.py' -reducer 'python3 reducer.py'
  hdfs dfs -cat "$RUN/streaming/part-*" | LC_ALL=C sort >"$ACTUAL"
  diff -u "$EXPECTED" "$ACTUAL"
  echo "PASS Streaming: $RUN/streaming"
fi
yarn node -list
MODE=multi
if [[ "$HADOOP_CONF_DIR" == /etc/hadoop-single ]]; then MODE=single; fi
python3 "$ROOT/scripts/assert-cluster.py" "$MODE" "$RUN"
echo "PASS RUN=$RUN"
