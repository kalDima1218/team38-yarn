#!/usr/bin/env python3

from pathlib import Path
import sys
import json
import xml.etree.ElementTree as ET

PUBLIC = '178.236.27.140'
EDGE, NN, W0, W1 = 'team-38-en', 'team-38-nn', 'team-38-00', 'team-38-01'
IPS = {EDGE:'10.38.0.10', NN:'10.38.0.11', W0:'10.38.0.12', W1:'10.38.0.13'}
ROLES = {EDGE:['secondarynamenode','historyserver','timelineserver','proxyserver'],
         NN:['namenode','resourcemanager'], W0:['datanode','nodemanager'], W1:['datanode','nodemanager']}
BASE = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent/'generated'

def xml(path, values):
    root=ET.Element('configuration')
    for key,value in values.items():
        prop=ET.SubElement(root,'property')
        ET.SubElement(prop,'name').text=key
        ET.SubElement(prop,'value').text=str(value)
    ET.indent(root,space='  ')
    path.write_text('<?xml version="1.0"?>\n'+ET.tostring(root,encoding='unicode')+'\n')

def config(node, single=False):
    directory=BASE/('single' if single else node)/'hadoop'
    directory.mkdir(parents=True,exist_ok=True)
    master=EDGE if single else NN
    workers=[EDGE] if single else [W0,W1]
    data='/var/lib/hadoop/single' if single else '/var/lib/hadoop'
    xml(directory/'core-site.xml',{'fs.defaultFS':f'hdfs://{master}:9000',
         'hadoop.tmp.dir':f'{data}/tmp','hadoop.http.staticuser.user':'team'})
    hdfs={'dfs.replication':1 if single else 2,'dfs.namenode.name.dir':f'file://{data}/hdfs/name',
        'dfs.datanode.data.dir':f'file://{data}/hdfs/data',
        'dfs.namenode.rpc-address':f'{master}:9000','dfs.namenode.http-address':f'{master}:9870',
        'dfs.namenode.secondary.http-address':f'{EDGE}:9868',
        'dfs.namenode.checkpoint.dir':f'file://{data}/hdfs/checkpoint',
        'dfs.namenode.checkpoint.period':300,
        'dfs.datanode.address':f'{node}:9866','dfs.datanode.ipc.address':f'{node}:9867',
        'dfs.datanode.http.address':f'{node}:9864','dfs.webhdfs.enabled':'true',
        'dfs.client.use.datanode.hostname':'true','dfs.datanode.use.datanode.hostname':'true'}
    xml(directory/'hdfs-site.xml',hdfs)
    yarn={'yarn.resourcemanager.hostname':master,
       'yarn.resourcemanager.webapp.address':f'{master}:8088',
       'yarn.resourcemanager.bind-host':IPS[master],
       'yarn.nodemanager.hostname':node,
       'yarn.nodemanager.bind-host':IPS[node],
       'yarn.nodemanager.webapp.address':f'{node}:8042',
       'yarn.nodemanager.aux-services':'mapreduce_shuffle',
       'yarn.nodemanager.env-whitelist':'JAVA_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_MAPRED_HOME,PATH,LANG,TZ',
       'yarn.nodemanager.resource.memory-mb':2048,'yarn.nodemanager.resource.cpu-vcores':2,
       'yarn.scheduler.minimum-allocation-mb':256,'yarn.scheduler.maximum-allocation-mb':2048,
       'yarn.scheduler.minimum-allocation-vcores':1,'yarn.scheduler.maximum-allocation-vcores':2,
       'yarn.nodemanager.vmem-check-enabled':'false',
       'yarn.nodemanager.local-dirs':f'{data}/yarn/local',
       'yarn.nodemanager.log-dirs':f'{data}/yarn/container-logs',
       'yarn.log-aggregation-enable':'true','yarn.log-aggregation.retain-seconds':604800,
       'yarn.nodemanager.remote-app-log-dir':'/tmp/logs',
       'yarn.log.server.url':f'http://{EDGE}:19888/jobhistory/logs'}
    if not single:
        yarn.update({'yarn.web-proxy.address':f'{EDGE}:9099',
         'yarn.timeline-service.enabled':'true','yarn.timeline-service.version':'1.0',
         'yarn.system-metrics-publisher.enabled':'true',
         'yarn.timeline-service.recovery.enabled':'true',
         'yarn.timeline-service.hostname':EDGE,'yarn.timeline-service.bind-host':IPS[EDGE],
         'yarn.timeline-service.webapp.address':f'{EDGE}:8188',
         'yarn.timeline-service.address':f'{EDGE}:10200',
         'yarn.timeline-service.leveldb-timeline-store.path':f'{data}/timeline',
         'yarn.timeline-service.leveldb-state-store.path':f'{data}/timeline-state',
         'yarn.timeline-service.generic-application-history.enabled':'true'})
    xml(directory/'yarn-site.xml',yarn)
    xml(directory/'mapred-site.xml',{
       'mapreduce.framework.name':'yarn',
       'mapreduce.application.classpath':'$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/*:$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/lib/*',
       'mapreduce.jobhistory.address':f'{EDGE}:10020',
       'mapreduce.jobhistory.webapp.address':f'{EDGE}:19888',
       'mapreduce.jobhistory.bind-host':IPS[EDGE],
       'mapreduce.jobhistory.intermediate-done-dir':'/mr-history/tmp',
       'mapreduce.jobhistory.done-dir':'/mr-history/done',
       'yarn.app.mapreduce.am.resource.mb':512,'yarn.app.mapreduce.am.command-opts':'-Xmx384m',
       'mapreduce.map.memory.mb':512,'mapreduce.map.java.opts':'-Xmx384m',
       'mapreduce.reduce.memory.mb':512,'mapreduce.reduce.java.opts':'-Xmx384m',
       'mapreduce.map.cpu.vcores':1,'mapreduce.reduce.cpu.vcores':1,
       'mapreduce.jobhistory.recovery.enable':'true',
       'mapreduce.jobhistory.recovery.store.class':'org.apache.hadoop.mapreduce.v2.hs.HistoryServerLeveldbStateStoreService',
       'mapreduce.jobhistory.recovery.store.leveldb.path':f'{data}/history-state'})
    xml(directory/'capacity-scheduler.xml',{
       'yarn.scheduler.capacity.root.queues':'default',
       'yarn.scheduler.capacity.root.default.capacity':100,
       'yarn.scheduler.capacity.root.default.maximum-capacity':100,
       'yarn.scheduler.capacity.root.default.user-limit-factor':1,
       'yarn.scheduler.capacity.root.default.state':'RUNNING',
       'yarn.scheduler.capacity.root.default.acl_submit_applications':'*',
       'yarn.scheduler.capacity.root.default.acl_administer_queue':'hadoop',
       'yarn.scheduler.capacity.maximum-am-resource-percent':0.5,
       'yarn.scheduler.capacity.resource-calculator':'org.apache.hadoop.yarn.util.resource.DefaultResourceCalculator'})
    (directory/'workers').write_text('\n'.join(workers)+'\n')
    log='/var/log/hadoop/single' if single else '/var/log/hadoop'
    env=f'''export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_COMMON_HOME=/opt/hadoop
export HADOOP_HDFS_HOME=/opt/hadoop
export HADOOP_YARN_HOME=/opt/hadoop
export HADOOP_MAPRED_HOME=/opt/hadoop
export HADOOP_LOG_DIR={log}
export HADOOP_PID_DIR={data}/run
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
'''
    (directory/'hadoop-env.sh').write_text(env)
    for f in ('yarn-env.sh','mapred-env.sh'):
        (directory/f).write_text('')

for node in IPS: config(node)
config(EDGE,True)
for node,roles in ROLES.items():
    units=BASE/node/'systemd'
    units.mkdir(exist_ok=True)
    for role in roles:
        binary='hdfs' if role in ['namenode','datanode','secondarynamenode'] else 'mapred' if role=='historyserver' else 'yarn'
        unit=f'''[Unit]
Description=Hadoop {role} (team-38)
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=120
StartLimitBurst=3

[Service]
Type=simple
User=hadoop
Group=hadoop
Environment=HADOOP_CONF_DIR=/etc/hadoop
Environment=JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
WorkingDirectory=/var/lib/hadoop
ExecStart=/opt/hadoop/bin/{binary} --config /etc/hadoop {role}
Restart=on-failure
RestartSec=5
TimeoutStopSec=45
KillSignal=SIGTERM
SuccessExitStatus=143
LimitNOFILE=65536
MemoryMax={'3400M' if role=='nodemanager' else '900M' if role in ['namenode','resourcemanager'] else '700M'}

[Install]
WantedBy=multi-user.target
'''
        (units/f'hadoop-{role}.service').write_text(unit)
singleunits=BASE/'single'/'systemd'
singleunits.mkdir(exist_ok=True)
for role in ('namenode','datanode','resourcemanager','nodemanager'):
    owner=NN if role in ('namenode','resourcemanager') else W0
    unit=(BASE/owner/'systemd'/f'hadoop-{role}.service').read_text()
    unit=unit.replace('/etc/hadoop','/etc/hadoop-single').replace('Description=Hadoop','Description=Single-node Hadoop')
    (singleunits/f'hadoop-single-{role}.service').write_text(unit)

SERVICES=[('rm','ResourceManager',NN,8088,18088),
 ('nm0','NodeManager 0',W0,8042,18042),('nm1','NodeManager 1',W1,8042,18043),
 ('history','MapReduce JobHistory',EDGE,19888,19880),('timeline','YARN Timeline / Application History',EDGE,8188,18188),
 ('proxy','YARN Web Application Proxy',EDGE,9099,19099),('nn','HDFS NameNode',NN,9870,19870),
 ('dn0','HDFS DataNode 0',W0,9864,19864),('dn1','HDFS DataNode 1',W1,9864,19865),
 ('snn','HDFS SecondaryNameNode',EDGE,9868,19868)]
nginx=BASE/EDGE/'nginx'
nginx.mkdir(exist_ok=True)
links_file=BASE.parent/'public-links.json'
PUBLIC_LINKS=json.loads(links_file.read_text()) if links_file.exists() else {}
def public_url(slug,port):
    return PUBLIC_LINKS.get(slug,f'http://{PUBLIC}:{port}')
replacements=[]
maps=[]
for slug,title,host,internal,external in SERVICES:
    public=public_url(slug,external)
    maps.append(f'''map $host $public_{slug} {{
  default "{public}";
  localhost "http://localhost:{external}";
  127.0.0.1 "http://127.0.0.1:{external}";
}}
map $host $address_{slug} {{
  default "{public.split('://',1)[1]}";
  localhost "localhost:{external}";
  127.0.0.1 "127.0.0.1:{external}";
}}''')
    for address in (host,IPS[host],host+'.hse.c.mws'):
        replacements.append(f"    sub_filter 'http://{address}:{internal}' '$public_{slug}';")
        replacements.append(f"    sub_filter '{address}:{internal}' '$address_{slug}';")
filters='\n'.join(replacements)
redirects=[]
for dest,_,host,internal,_ in SERVICES:
    for address in (host,IPS[host],host+'.hse.c.mws'):
        redirects.append(f'    proxy_redirect http://{address}:{internal}/ $public_{dest}/;')
redirect_filters='\n'.join(redirects)
servers=['''server {
  listen 80 default_server;
  server_name _;
  root /var/www/yarn-lab;
  index index.html;
  location / { try_files $uri $uri/ =404; }
}''']
for slug,title,host,internal,external in SERVICES:
    public=public_url(slug,external)
    proxy_landing=''
    if slug=='proxy':
        proxy_landing='location = / { root /var/www/yarn-lab; try_files /proxy.html =404; }'
    if slug=='timeline':
        proxy_landing='location = / { absolute_redirect off; return 302 /applicationhistory/; }'
    servers.append(f'''server {{
  listen {external};
  server_name _;
  {proxy_landing}
  location / {{
    proxy_pass http://{host}:{internal};
    proxy_http_version 1.1;
    proxy_set_header Host $proxy_host;
    proxy_set_header Accept-Encoding "";
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
{redirect_filters}
    proxy_read_timeout 60s;
    limit_except GET HEAD {{ deny all; }}
    sub_filter_once off;
    sub_filter_types application/json application/javascript text/css;
{filters}
  }}
}}''')
(nginx/'yarn-lab.conf').write_text('\n\n'.join(maps+servers)+'\n')
links='\n'.join(f'<li><a data-port="{port}" href="{public_url(slug,port)}/">{title}</a> <small>{host}:{upstream}</small></li>' for slug,title,host,upstream,port in SERVICES)
(nginx/'index.html').write_text(f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>team-38 — Hadoop / YARN</title><style>body{{font:18px system-ui;margin:48px auto;max-width:920px;padding:0 24px;background:#f5f7fb;color:#17233d}}h1{{font-size:36px}}li{{margin:18px 0}}a{{color:#1655b8}}small{{color:#64748b;margin-left:14px}}.box{{padding:24px;background:white;border-radius:16px}}</style>
<h1>team-38 · Hadoop / YARN</h1><p>Учебный кластер: Hadoop 3.5.0 · Java 17 · 2 рабочих узла.</p>
<div class="box"><ul>{links}</ul></div><p>История завершённых MapReduce-заданий находится в JobHistory. Application Master работает только во время выполнения приложения; его интерфейс доступен через Tracking URL и Web Application Proxy.</p>
<script>if(['localhost','127.0.0.1'].includes(location.hostname)){{document.querySelectorAll('a[data-port]').forEach(a=>a.href='http://'+location.hostname+':'+a.dataset.port+'/');}}</script></html>''')
(nginx/'proxy.html').write_text(f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>YARN Web Application Proxy</title><style>body{{font:18px system-ui;max-width:900px;margin:60px auto;padding:24px}}</style><h1>YARN Web Application Proxy</h1><p>Служба работает на {EDGE}:9099 и публикует интерфейсы Application Master по пути <code>/proxy/application_…/</code>. У самого Web Application Proxy нет страницы со списком приложений.</p><p>Откройте ResourceManager и выберите Tracking UI нужного приложения. Для завершённых MapReduce-заданий доступна история.</p><p><a data-port="18088" data-path="/cluster/apps" href="{public_url('rm',18088)}/cluster/apps">ResourceManager: приложения</a> · <a data-port="19880" data-path="/jobhistory" href="{public_url('history',19880)}/jobhistory">JobHistory</a></p><script>if(['localhost','127.0.0.1'].includes(location.hostname)){{document.querySelectorAll('a[data-port]').forEach(a=>a.href='http://'+location.hostname+':'+a.dataset.port+a.dataset.path);}}</script></html>''')
print('Generated configurations:',BASE)
