#!/usr/bin/env python3

import datetime,json,subprocess,sys,threading,urllib.request,urllib.error
from pathlib import Path
ports=[(18080,80),(18088,18088),(18042,18042),(18043,18043),(19880,19880),(18188,18188),(19099,19099),(19870,19870),(19864,19864),(19865,19865),(19868,19868)]
cmd=['ssh','-v','-i',sys.argv[1],'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ExitOnForwardFailure=yes','-N']
if len(sys.argv)>3: cmd+=['-o','UserKnownHostsFile='+sys.argv[3]]
for local,remote in ports: cmd+=['-L',f'127.0.0.1:{local}:127.0.0.1:{remote}']
cmd+=['team@178.236.27.140']
proc=subprocess.Popen(cmd,stderr=subprocess.PIPE,text=True)
ready=threading.Event();errors=[]
def events():
    for line in proc.stderr:
        if 'Entering interactive session' in line: ready.set()
        if any(error in line for error in ('Permission denied','Address already in use','Host key verification failed')): errors.append(line.strip());ready.set()
    if not ready.is_set(): errors.append('SSH exited before forwarding became ready');ready.set()
threading.Thread(target=events,daemon=True).start()
results={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'transport':'external client -> SSH 178.236.27.140:22 -> edge Nginx','checks':[]}
def get(port,path='/',as_json=False):
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',headers={'Accept':'application/json'} if as_json else {})
    with urllib.request.urlopen(req,timeout=20) as response:
        body=response.read();status=response.status;url=response.url
    assert status==200,(port,path,status)
    results['checks'].append({'port':port,'path':path,'status':status,'final_url':url})
    print(f'PASS HTTP {port}{path}',flush=True)
    return json.loads(body) if as_json else body
try:
    assert ready.wait(30),'No SSH readiness event before safety deadline'
    assert not errors,errors
    for local,_ in ports: get(local)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    try: urllib.request.build_opener(NoRedirect).open('http://127.0.0.1:18188/',timeout=10)
    except urllib.error.HTTPError as response:
        assert response.code==302 and response.headers['Location']=='/applicationhistory/',response.headers
        results['checks'].append({'port':18188,'path':'/ (redirect header)','status':302,'location':response.headers['Location']})
    else: raise AssertionError('Missing Timeline landing redirect')
    nodes=get(18088,'/ws/v1/cluster/nodes',True)['nodes']['node']
    assert len(nodes)==2 and all(n['state']=='RUNNING' for n in nodes),nodes
    apps=get(18088,'/ws/v1/cluster/apps',True)['apps']['app']
    succeeded=[a for a in apps if a['finalStatus']=='SUCCEEDED']
    assert len(succeeded)>=2,apps
    jobs=get(19880,'/ws/v1/history/mapreduce/jobs',True)['jobs']['job']
    assert len([j for j in jobs if j['state']=='SUCCEEDED'])>=2,jobs
    get(18188,'/ws/v1/timeline',True)
    get(18188,'/ws/v1/applicationhistory/about',True)
    timeline=get(18188,'/ws/v1/applicationhistory/apps',True)
    history_apps=(timeline.get('apps') or {}).get('app',[])
    assert len([a for a in history_apps if a['finalAppStatus']=='SUCCEEDED'])>=2,history_apps
    results['timeline_applications']=history_apps
    for p in (18042,18043): get(p,'/ws/v1/node/info',True)
    for p in (19870,19864,19865,19868): get(p,'/jmx',True)
    app=succeeded[-1];get(19099,'/proxy/'+app['id']+'/')
    directories=get(19870,'/webhdfs/v1/user/team?op=LISTSTATUS&user.name=team',True)['FileStatuses']['FileStatus']
    checks=[d for d in directories if d['pathSuffix'].startswith('yarn-check-') and d['type']=='DIRECTORY']
    assert checks,'No smoke test directory in /user/team'
    run='/user/team/'+max(checks,key=lambda d:d['modificationTime'])['pathSuffix']
    content=get(19870,'/webhdfs/v1'+run+'/input/text.txt?op=OPEN&user.name=team')
    assert content==b'hello yarn\nhello hadoop\n',content
    for p in (18088,18042,19880,19870):
        try: urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{p}/',data=b'',method='POST'),timeout=10)
        except urllib.error.HTTPError as e: assert e.code==403,e;results['checks'].append({'port':p,'method':'POST','status':403})
        else: raise AssertionError(f'POST accepted on {p}')
    results.update(nodes=nodes,applications=apps,jobs=jobs,status='PASS')
    if len(sys.argv)>2: Path(sys.argv[2]).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print('PASS: all native UIs, APIs, job history, WebProxy, WebHDFS download and read-only gateway')
finally:
    proc.terminate()
    try: proc.wait(timeout=10)
    except subprocess.TimeoutExpired: proc.kill();proc.wait()
