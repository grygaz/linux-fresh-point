#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Unprivileged terminal bridge; the privileged helper derives its own command."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent

def launch(payload):
    choices=[('gnome-terminal',['--wait','--']),('konsole',['--nofork','-e']),
             ('xfce4-terminal',['--disable-server','--execute']),('mate-terminal',['--disable-factory','-x']),
             ('xterm',['-e'])]
    terminal=next(([shutil.which(name),*args] for name,args in choices if shutil.which(name)),None)
    if terminal is None: raise RuntimeError('A terminal is required: gnome-terminal, konsole, xfce4-terminal, mate-terminal or xterm.')
    with tempfile.TemporaryDirectory(prefix='linux-fresh-point-') as folder:
        request=Path(folder)/'request.json'; result=Path(folder)/'result.json'
        request.write_text(json.dumps(payload))
        subprocess.run([*terminal,'/usr/bin/python3','-I',str(HERE/'terminal_apply.py'),str(request),str(result)],check=False)
        if not result.exists(): raise RuntimeError('Terminal closed before removal finished.')
        data=json.loads(result.read_text())
        if not data.get('ok'): raise RuntimeError(data.get('error','Removal failed.'))
        return data['data']

if __name__=='__main__':
    request,result=map(Path,sys.argv[1:])
    try:
        print('Linux fresh point — review the native transaction and confirm below.',flush=True)
        p=subprocess.run(['pkexec','--disable-internal-agent','/usr/bin/python3','-I',str(HERE/'backend.py'),'apply'],
                         input=request.read_text(),text=True,capture_output=True)
        try: data=json.loads(p.stdout)
        except ValueError: data=dict(ok=False,error=p.stderr or 'Administrator authorization cancelled.')
        if p.returncode and data.get('ok'): data=dict(ok=False,error='Removal failed.')
    except Exception as e: data=dict(ok=False,error=str(e))
    result.write_text(json.dumps(data))
    print(json.dumps(data,ensure_ascii=False,indent=2),flush=True)
