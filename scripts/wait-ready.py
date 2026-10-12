#!/usr/bin/env python3

import ctypes, os, select, struct, sys, time, urllib.request, json
from pathlib import Path
url=sys.argv[1]
directory=sys.argv[2]
predicate=sys.argv[3] if len(sys.argv)>3 else 'http'
libc=ctypes.CDLL(None,use_errno=True)
fd=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
if fd<0: raise OSError(ctypes.get_errno(),'inotify_init1')
watch=libc.inotify_add_watch(fd,directory.encode(),0x00000002|0x00000100|0x00000080|0x00000008)
if watch<0: raise OSError(ctypes.get_errno(),'inotify_add_watch')
offsets={p:p.stat().st_size for p in Path(directory).glob('*.log')}
def relevant_event(data):
    relevant=False
    while data:
        _,mask,_,size=struct.unpack_from('iIII',data)
        name=data[16:16+size].split(b'\0',1)[0].decode(errors='replace')
        data=data[16+size:]
        path=Path(directory)/name
        if not name.endswith('.log') or not path.is_file(): continue
        old=offsets.get(path,0)
        length=path.stat().st_size
        if length<old: old=0
        with path.open('rb') as f:
            f.seek(old)
            text=f.read().decode(errors='replace')
            offsets[path]=f.tell()
        
        
        if any(line.strip() and 'http.requests.' not in line and 'Python-urllib/' not in line and 'requests.applicationhistory:' not in line for line in text.splitlines()): relevant=True
    return relevant
def ready():
    try:
        request=urllib.request.Request(url,headers={'Accept':'application/json'})
        with urllib.request.urlopen(request,timeout=3) as r:
            payload=r.read()
        if predicate=='nodes2':
            info=json.loads(payload)
            nodes=(info.get('nodes') or {}).get('node',[])
            return len([n for n in nodes if n.get('state')=='RUNNING'])==2
        if predicate=='nodes1':
            nodes=(json.loads(payload).get('nodes') or {}).get('node',[])
            return len([n for n in nodes if n.get('state')=='RUNNING'])==1
        return True
    except (OSError,ValueError): return False
deadline=time.monotonic()+90
try:
    if ready():
        print('READY:',url,predicate);sys.exit(0)
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0: raise TimeoutError('Readiness safety deadline exceeded; no timer polling was used')
        event,_,_=select.select([fd],[],[],remaining)
        if not event: raise TimeoutError('No new log event before readiness deadline; inspect logs')
        if relevant_event(os.read(fd,65536)) and ready():
            print('READY after log event:',url,predicate);break
finally:
    os.close(fd)
