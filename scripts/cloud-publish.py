#!/usr/bin/env python3

import ctypes,json,os,re,select,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
LOGS=Path('/home/team/yarn-lab/logs/tunnels')
LOGS.mkdir(parents=True,exist_ok=True)
PORTS={'portal':80,'rm':18088,'nm0':18042,'nm1':18043,'history':19880,
       'timeline':18188,'proxy':19099,'nn':19870,'dn0':19864,'dn1':19865,'snn':19868}
libc=ctypes.CDLL(None,use_errno=True)
fd=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
if fd<0: raise OSError(ctypes.get_errno(),'inotify_init1')
if libc.inotify_add_watch(fd,str(LOGS).encode(),0x2|0x100|0x80|0x8)<0:
    raise OSError(ctypes.get_errno(),'inotify_add_watch')
for name,port in PORTS.items():
    unit=f'''[Unit]
Description=Public HTTPS tunnel for YARN {name}
After=network-online.target nginx.service
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3
[Service]
User=team
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:{port}
StandardOutput=append:{LOGS}/{name}.log
StandardError=append:{LOGS}/{name}.log
Restart=no
MemoryMax=150M
[Install]
WantedBy=multi-user.target
'''
    temp=ROOT/f'.tunnel-{name}.service'
    temp.write_text(unit)
    subprocess.run(['sudo','cp',str(temp),f'/etc/systemd/system/yarn-tunnel-{name}.service'],check=True)
    temp.unlink()
subprocess.run(['sudo','systemctl','daemon-reload'],check=True)
units=[f'yarn-tunnel-{n}.service' for n in PORTS]


subprocess.run(['sudo','systemctl','stop',*units],check=True)
for n in PORTS:
    subprocess.run(['sudo','truncate','-s','0',str(LOGS/f'{n}.log')],check=True)
subprocess.run(['sudo','systemctl','disable',*units],check=True)
subprocess.run(['sudo','systemctl','start',*units],check=True)
def collect():
    found={}
    for n in PORTS:
        p=LOGS/f'{n}.log'
        if p.exists():
            text=p.read_text(errors='replace')
            matches=list(re.finditer(r'https://[a-z0-9-]+\.trycloudflare\.com',text))
            if matches and 'Registered tunnel connection' in text[matches[-1].end():]:
                found[n]=matches[-1].group()
    return found
deadline=time.monotonic()+60
try:
    urls=collect()
    while len(urls)<len(PORTS):
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError(f'Tunnel URL event deadline; discovered {list(urls)}')
        events,_,_=select.select([fd],[],[],left)
        if not events: raise TimeoutError('No tunnel log event; inspect the saved service logs')
        os.read(fd,65536)
        urls=collect()
    (ROOT/'public-links.json').write_text(json.dumps(urls,indent=2)+'\n')
    for n,url in urls.items(): print(n,url,flush=True)
finally: os.close(fd)
subprocess.run(['python3',str(ROOT/'scripts/generate.py')],check=True)
subprocess.run(['bash',str(ROOT/'scripts/publish.sh')],check=True)
