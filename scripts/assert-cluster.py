#!/usr/bin/env python3

import json,re,subprocess,sys,urllib.request,os
single=sys.argv[1]=='single'
run=sys.argv[2]
expected=1 if single else 2
master='team-38-en' if single else 'team-38-nn'
request=urllib.request.Request(f'http://{master}:8088/ws/v1/cluster/nodes',headers={'Accept':'application/json'})
with urllib.request.urlopen(request,timeout=10) as r: nodes=(json.load(r).get('nodes') or {}).get('node',[])
running=[n for n in nodes if n['state']=='RUNNING']
assert len(running)==expected, f'Expected {expected} RUNNING NodeManagers, got {running}'
conf=os.environ.get('HADOOP_CONF_DIR','/etc/hadoop')
command=['sudo','-u','hadoop','env',f'HADOOP_CONF_DIR={conf}','JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64','/opt/hadoop/bin/hdfs']
report=subprocess.check_output(command+['dfsadmin','-report'],text=True)
print(report)
assert f'Live datanodes ({expected}):' in report, 'Wrong live DataNode count'
for marker in ('Blocks with corrupt replicas: 0','Missing blocks: 0'):
    assert marker in report, f'HDFS health failure: missing {marker}'
fsck=subprocess.check_output(command+['fsck',run,'-files','-blocks','-locations'],text=True,stderr=subprocess.STDOUT)
print(fsck)
assert 'Status: HEALTHY' in fsck, 'Test files are not HEALTHY'
assert re.search(r'Under-replicated blocks:\s+0\b',fsck), 'Test files are under-replicated'
replicas=re.findall(r'Live_repl=(\d+)',fsck)
assert replicas and all(int(n)==expected for n in replicas), f'Wrong actual replicas for test blocks: {replicas}'
print(f'PASS: {expected} NM, {expected} DN, healthy blocks, replication={expected}')
