# SPDX-License-Identifier: GPL-3.0-only
"""Conservative native adapters. No shell, force flags, downgrades or file deletion.
Native managers ask for final confirmation in a terminal. RPM removal is additionally
checked with rpm --test; dependency analysis over-approximates alternative providers.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from system_info import identity

SAFE = re.compile(r'^(base|filesystem|basesystem|glibc|musl|linux|kernel|firmware|grub|shim|systemd|udev|openrc|sysvinit|bash|coreutils|util-linux|sudo|polkit|python|pacman|portage|dnf|rpm|zypper|libzypp|gtk|pygobject|gobject-introspection|networkmanager|NetworkManager|dbus|cinnamon|plasma|gnome-shell|lightdm|gdm|sddm|xorg-server|wayland)(?:[-0-9.]|$)')
KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9+_.:/@-]*\Z')

def run(argv, accepted=(0,)):
    env = dict(os.environ, LC_ALL='C', LANG='C')
    p = subprocess.run(argv, text=True, capture_output=True, env=env)
    if p.returncode not in accepted:
        raise RuntimeError((p.stderr or p.stdout or 'Command failed: '+argv[0])[-16000:])
    return p.stdout

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def closure(rows, roots):
    keep = set(roots) & rows.keys()
    todo = list(keep)
    while todo:
        for dep in rows[todo.pop()]['deps']:
            if dep in rows and dep not in keep:
                keep.add(dep); todo.append(dep)
    return keep

def row(key, version, description='', size=0, manual=True, files=()):
    if not KEY.fullmatch(key): raise RuntimeError('Unsupported package identifier: '+key)
    return dict(key=key, package=key, title=key, version=version, description=description,
                size=int(size), manual=manual, app=False, protected=False, external=False,
                icon='application-x-executable-symbolic', deps=[], files=list(files))

def pacman_fields(text):
    parts = re.split(r'^%([A-Z0-9_]+)%\s*$', text, flags=re.M)
    return {parts[i]:parts[i+1].strip().splitlines() for i in range(1,len(parts),2)}

def capability(s):
    return re.split(r'[<>=]',s,1)[0].strip()

def pacman_inventory(system):
    db = Path(run(['pacman-conf','DBPath']).strip())/'local'
    rows, providers, needs = {}, {}, {}
    for path in db.glob('*/desc'):
        d = pacman_fields(path.read_text())
        name = d['NAME'][0]
        files = pacman_fields((path.parent/'files').read_text()).get('FILES',[])
        rows[name] = row(name,d['VERSION'][0],d.get('DESC',[''])[0],d.get('ISIZE',['0'])[0],
                         d.get('REASON',['0'])[0]=='0',['/'+f for f in files])
        for cap in [name]+d.get('PROVIDES',[]): providers.setdefault(capability(cap),set()).add(name)
        # Keep optional dependencies too, so restoration preserves updated apps' features.
        needs[name] = d.get('DEPENDS',[])+[x.split(': ',1)[0] for x in d.get('OPTDEPENDS',[])]
    for name in rows:
        rows[name]['deps'] = sorted(set().union(*(providers.get(capability(x),set()) for x in needs[name])))
    ignored = set(run(['pacman-conf','IgnorePkg']).split()) | set(run(['pacman-conf','HoldPkg']).split())
    import fnmatch
    for name in rows:
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in ignored): rows[name]['protected']=True
    return rows

def rpm_inventory(system):
    fmt = '%{NAME}\x1f%{ARCH}\x1f%{EVR}\x1f%{SIZE}\x1f%{SUMMARY}\x1f[%{REQUIRENAME}\n][%{RECOMMENDNAME}\n][%{SUGGESTNAME}\n]\x1f[%{PROVIDENAME}\n]\x1f[%{FILENAMES}\n]\x1e'
    rows, providers, needs = {}, {}, {}
    for record in run(['rpm','-qa','--qf',fmt]).split('\x1e'):
        if not record: continue
        name,arch,version,size,desc,reqs,provs,files = record.split('\x1f')
        key = name+'.'+arch
        if key in rows:
            rows[key]['version'] += ', '+version
            rows[key]['size'] += int(size)
            rows[key]['files'] += files.splitlines()
        else: rows[key] = row(key,version,desc,size,True,files.splitlines())
        for cap in [name]+provs.splitlines()+files.splitlines(): providers.setdefault(cap,set()).add(key)
        needs.setdefault(key,set()).update(reqs.splitlines())
    for key, reqs in needs.items():
        deps = set()
        for req in reqs:
            deps.update(providers.get(req,()))
            # Rich dependencies: conservatively retain every mentioned installed provider.
            if req.startswith('('):
                for token in re.findall(r'[A-Za-z0-9_/+.:@-]+(?:\([^()]*\))?',req):
                    deps.update(providers.get(token,()))
        rows[key]['deps'] = sorted(deps)
    # RPM lacks a shared explicit-install database. Do not guess orphan status.
    return rows

def portage_inventory(system):
    import portage
    db = portage.db[portage.root]['vartree'].dbapi
    cpvs = db.cpv_all()
    rows, mapping, metadata = {}, {}, {}
    for cpv in cpvs:
        slot, desc, use, rdep, pdep, dep, bdep, idep = db.aux_get(cpv,['SLOT','DESCRIPTION','USE','RDEPEND','PDEPEND','DEPEND','BDEPEND','IDEPEND'])
        key = portage.cpv_getkey(cpv)+':'+slot.split('/')[0]
        mapping[cpv] = key
        files = []
        contents = Path(portage.root)/'var/db/pkg'/cpv/'CONTENTS'
        if contents.exists():
            for line in contents.read_text(errors='replace').splitlines():
                if line.startswith('obj '): files.append(line[4:].rsplit(' ',2)[0])
        if key not in rows: rows[key]=row(key,cpv,desc,files=files)
        else:
            rows[key]['version'] += ', '+cpv
            rows[key]['files'] += files
        metadata[cpv]=(use, ' '.join([rdep,pdep,dep,bdep,idep]))
    for cpv,(use,expr) in metadata.items():
        atoms = portage.dep.use_reduce(expr,uselist=use.split(),flat=True,token_class=portage.dep.Atom)
        deps = set(rows[mapping[cpv]]['deps'])
        for atom in atoms:
            if not isinstance(atom,portage.dep.Atom) or atom.blocker: continue
            deps.update(mapping[p] for p in db.match(str(atom)) if p in mapping)
        rows[mapping[cpv]]['deps']=sorted(deps)
    # System set is protected in addition to explicit boot/runtime protections.
    from portage._sets import load_default_config
    sets=load_default_config(portage.settings,portage.db[portage.root])
    for atom in sets.getSetAtoms('system'):
        for cpv in db.match(str(atom)):
            if cpv in mapping: rows[mapping[cpv]]['protected']=True
    return rows

def snapshot(system):
    rows = {'pacman':pacman_inventory,'dnf':rpm_inventory,'zypper':rpm_inventory,'portage':portage_inventory}[system['manager']](system)
    if not rows: raise RuntimeError('Installed package database is empty.')
    roots = {k for k,r in rows.items() if r['protected'] or SAFE.match(k.split('/')[-1].split(':')[0])}
    for key in closure(rows,roots): rows[key]['protected']=True
    owners = {f:k for k,r in rows.items() for f in r['files'] if f.endswith('.desktop')}
    # Desktop apps are matched to installed package file lists, never guessed by name.
    if os.environ.get('LINUX_FRESH_POINT_HEADLESS') == '1':
        from desktop_info import entries
        for app in entries():
            if app['path'] in owners:
                r=rows[owners[app['path']]]; r['app']=True; r['title']=app['title']; r['icon']=app['icon']
    else:
        import gi
        from gi.repository import Gio
        for app in Gio.AppInfo.get_all():
            path = app.get_filename() if hasattr(app,'get_filename') else None
            if app.should_show() and path in owners:
                r=rows[owners[path]]; r['app']=True; r['title']=app.get_display_name()
                if app.get_icon(): r['icon']=app.get_icon().to_string()
    return rows

def data_dir():
    return Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'linux-tvarka/points'

def validate_point(point,system):
    if not isinstance(point,dict) or point.get('format')!=2 or point.get('system')!=identity(system):
        raise RuntimeError('This point belongs to another system or package manager.')
    packages=point.get('packages')
    if not isinstance(packages,dict) or not packages or not all(isinstance(k,str) and KEY.fullmatch(k) and isinstance(v,str) for k,v in packages.items()):
        raise RuntimeError('Invalid package list in restore point.')
    return point

def get_point(ident,system):
    if not re.fullmatch('[0-9a-f]{32}',ident): raise RuntimeError('Invalid point identifier.')
    return validate_point(json.loads((data_dir()/(ident+'.json')).read_text()),system)

def points(system):
    values=[]
    for path in data_dir().glob('*.json'):
        try:
            p=get_point(path.stem,system)
            values.append(dict(id=path.stem,name=p['name'],created=p['created'],count=len(p['packages'])))
        except (OSError,ValueError,RuntimeError): pass
    return sorted(values,key=lambda p:p['created'],reverse=True)

def state(rows):
    return digest({k:{f:r[f] for f in ('version','size','manual','protected','deps')} for k,r in rows.items()})

def plan_for(request,system,rows):
    if request.get('mode') not in ('remove','point'): raise RuntimeError('Invalid mode.')
    safe={k for k,r in rows.items() if r['protected']}
    missing=[]
    if request['mode']=='point':
        p=validate_point(request.get('point'),system)
        baseline=set(p['packages'])
        missing=sorted(baseline-rows.keys())
        remove=set(rows)-closure(rows,baseline|safe)
    else:
        selected=request.get('selected')
        if not isinstance(selected,list) or not all(isinstance(x,str) for x in selected): raise RuntimeError('Invalid selection.')
        remove=set(selected)
        if remove-rows.keys(): raise RuntimeError('Package list changed. Refresh the list.')
        if remove & safe: raise RuntimeError('System packages are protected.')
        if request.get('dependencies'):
            candidates={k for k in closure(rows,remove)-remove if not rows[k]['manual'] and k not in safe}
            remove |= candidates-closure(rows,set(rows)-remove-candidates)
        blockers=closure(rows,set(rows)-remove)&remove
        if blockers: raise RuntimeError('Other installed packages still require: '+', '.join(sorted(blockers)))
    if remove&safe: raise RuntimeError('System packages are protected.')
    value=dict(mode=request['mode'],removed=sorted(remove),rows=[dict(package=k,size=rows[k]['size'],reason='Pasirinkta') for k in sorted(remove)],missing=missing,
               bytes=sum(rows[k]['size'] for k in remove),clean_cache=False,state=state(rows),system=identity(system),request_hash=digest(request),native=True)
    value['hash']=digest(value)
    return value

def command(system,packages,preview=False):
    if not packages or not all(KEY.fullmatch(x) for x in packages): raise RuntimeError('Invalid removal targets.')
    tool=system['command']; manager=system['manager']
    if manager=='pacman': return [tool,'--remove']+(['--print','--print-format','%n'] if preview else [])+['--']+packages
    if manager=='dnf': return [tool,'--setopt=clean_requirements_on_remove=False']+(['--assumeno'] if preview else ['--setopt=assumeno=False','--setopt=assumeyes=False'])+['remove','--']+packages
    if manager=='zypper': return [tool,'--no-refresh','remove','--no-clean-deps']+(['--dry-run'] if preview else [])+['--']+packages
    return [tool,'--depclean','--verbose','--color=n','--deselect=n']+(['--pretend'] if preview else ['--ask'])+packages

def apply(payload,system):
    if os.geteuid()!=0: raise RuntimeError('Administrator privileges are required.')
    request=payload['request']; rows=snapshot(system); plan=plan_for(request,system,rows)
    if plan['hash']!=payload.get('hash'): raise RuntimeError('Package state changed. Preview again.')
    if not plan['removed']: return dict(removed=0,log='No changes')
    if system['manager'] in ('dnf','zypper'):
        run(['rpm','-e','--test','--']+plan['removed'])
    # Require a real controlling terminal. Package managers provide final solver confirmation.
    with open('/dev/tty','r+') as tty:
        result=subprocess.run(command(system,plan['removed']),stdin=tty,stdout=tty,stderr=tty,
                              env=dict(os.environ,LC_ALL='C',LANG='C'))
    after=snapshot(system)
    removed=set(rows)-after.keys()
    folder=Path('/var/log/linux-fresh-point'); folder.mkdir(mode=0o700,exist_ok=True)
    log=folder/(uuid.uuid4().hex+'.json')
    log.write_text(json.dumps(dict(plan=plan,removed=sorted(removed),exit_code=result.returncode),indent=2))
    if result.returncode or set(plan['removed'])&after.keys():
        raise RuntimeError('Removal cancelled or incomplete. Log: '+str(log))
    if removed-set(plan['removed']): raise RuntimeError('Native transaction changed additional packages. Log: '+str(log))
    return dict(removed=len(removed),log=str(log))

def main(system):
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['inventory','points','point-create','point-get','preview','apply']); parser.add_argument('--name',default=''); parser.add_argument('--id',default='')
    args=parser.parse_args()
    if args.action in ('preview','apply'):
        raw=sys.stdin.read(2_000_001)
        if len(raw)>2_000_000: raise RuntimeError('Request too large.')
        request=json.loads(raw)
        if args.action=='apply': value=apply(request,system)
        else:
            value=plan_for(request,system,snapshot(system))
            if value['removed']:
                value['native_output']=run(command(system,value['removed'],True),accepted=(0,1) if system['manager']=='dnf' else (0,))
    elif args.action=='points': value=points(system)
    elif args.action=='point-get': value=get_point(args.id,system)
    else:
        rows=snapshot(system)
        if args.action=='inventory':
            value=dict(items=[{k:v for k,v in r.items() if k not in ('files','deps')} for r in rows.values()],packages=len(rows),apps=sum(r['app'] for r in rows.values()),points=points(system),release=system['release'],system=system)
        else:
            if not 1<=len(args.name.strip())<=100: raise RuntimeError('Point name must contain 1–100 characters.')
            p=dict(format=2,system=identity(system),name=args.name.strip(),created=dt.datetime.now(dt.timezone.utc).isoformat(),packages={k:r['version'] for k,r in rows.items()})
            if state(rows)!=state(snapshot(system)): raise RuntimeError('Package state changed. Try again.')
            data_dir().mkdir(parents=True,exist_ok=True,mode=0o700); ident=uuid.uuid4().hex
            with (data_dir()/(ident+'.json')).open('x') as f: json.dump(p,f,indent=2)
            value=dict(id=ident,count=len(rows))
    print(json.dumps(dict(ok=True,data=value),ensure_ascii=False))
