#!/usr/bin/env python3

import datetime,html,json,os,re,subprocess,sys,urllib.request
from pathlib import Path
os.environ.update(HADOOP_CONF_DIR='/etc/hadoop',JAVA_HOME='/usr/lib/jvm/java-17-openjdk-amd64',HADOOP_MAPRED_HOME='/opt/hadoop')
listing=subprocess.check_output(['/opt/hadoop/bin/hdfs','dfs','-ls','/user/team'],text=True)
paths=re.findall(r'/user/team/yarn-check-[0-9-]+',listing)
assert paths,'Run smoke.sh first'
source=max(paths)+'/input'
out='/user/team/proxy-check-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
cmd=['timeout','180','/opt/hadoop/bin/hadoop','jar','/opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.5.0.jar','wordcount',source,out]
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
app=None;result=None
try:
    for line in p.stdout:
        print(line,end='',flush=True)
        match=re.search(r'Submitted application (application_[0-9_]+)',line)
        if match:app=match.group(1)
        if app and result is None and re.search(r'map \d+% reduce \d+%',line):
            url='http://127.0.0.1:19099/proxy/'+app+'/'
            with urllib.request.urlopen(url,timeout=15) as response:
                body=response.read().decode();status=response.status;final=response.url
            assert status==200 and '/proxy/'+app in final,(status,final)
            assert 'MapReduce' in body and app in body,body[:500]
            title=re.search(r'<title>(.*?)</title>',body,re.S)
            result={'application_id':app,'status':status,'url':final,'title':html.unescape(title.group(1)) if title else '', 'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'trigger':'MapReduce progress log event while Application Master is running'}
            print('PASS: live Application Master via Web Application Proxy',flush=True)
    assert p.wait()==0,'WordCount failed'
    assert result,'No running Application Master progress event'
    actual=subprocess.check_output(['/opt/hadoop/bin/hdfs','dfs','-cat',out+'/part-r-*'],text=True)
    assert actual=='hadoop\t1\nhello\t2\nyarn\t1\n',actual
    result.update(job_result='SUCCEEDED; exact WordCount output',hdfs_output=out)
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASS: live WebProxy and completed WordCount')
except BaseException:
    if app: subprocess.run(['/opt/hadoop/bin/yarn','application','-kill',app],check=False)
    raise
finally:
    if p.poll() is None:p.terminate();p.wait(timeout=10)
