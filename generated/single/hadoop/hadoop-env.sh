export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_COMMON_HOME=/opt/hadoop
export HADOOP_HDFS_HOME=/opt/hadoop
export HADOOP_YARN_HOME=/opt/hadoop
export HADOOP_MAPRED_HOME=/opt/hadoop
export HADOOP_LOG_DIR=/var/log/hadoop/single
export HADOOP_PID_DIR=/var/lib/hadoop/single/run
export HADOOP_HEAPSIZE_MAX=512
if [[ $(id -un) == hadoop ]]; then
  export HADOOP_ROOT_LOGGER=INFO,console,RFA
else
  export HADOOP_ROOT_LOGGER=INFO,console
fi
export HDFS_NAMENODE_OPTS="-Xmx512m"
export HDFS_DATANODE_OPTS="-Xmx256m"
export HDFS_SECONDARYNAMENODE_OPTS="-Xmx256m"
export YARN_RESOURCEMANAGER_OPTS="-Xmx512m"
export YARN_NODEMANAGER_OPTS="-Xmx256m"
export YARN_TIMELINESERVER_OPTS="-Xmx384m"
export YARN_PROXYSERVER_OPTS="-Xmx256m"
export MAPRED_HISTORYSERVER_OPTS="-Xmx384m"
