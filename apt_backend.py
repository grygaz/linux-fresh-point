#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""JSON interface; apply is the only privileged operation. No shell commands."""
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apt
import apt_pkg
import apt.progress.base
import cleanup_core as core
import point_store
from system_info import detect, identity

HERE = Path(__file__).resolve().parent
RUNTIME = re.compile(r'^(cinnamon(?!-desktop-environment)|muffin|lightdm|gdm3|sddm|network-manager|polkitd|pkexec|python3-gi|gir1.2-gtk-4.0|libgtk-4-)')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def state_token():
    return digest([Path(p).read_text() if Path(p).exists() else '' for p in
                   ['/var/lib/dpkg/status', '/var/lib/apt/extended_states']])


def protected(cache):
    current = core.installed(cache)
    roots = {n for n, p in current.items() if core.is_protected(p) or RUNTIME.match(p.name)}
    # Optional recommended apps may be removed; only mandatory runtime deps are protected.
    todo = list(roots)
    while todo:
        package = current[todo.pop()]
        for group in package.installed.get_dependencies('PreDepends', 'Depends'):
            for dependency in group.or_dependencies:
                for version in dependency.installed_target_versions:
                    name = version.package.fullname
                    if name in current and name not in roots:
                        roots.add(name)
                        todo.append(name)
    return roots


def validate_point(point):
    if not isinstance(point, dict) or point.get('format') != 1:
        core.fail('Netinkamas atkūrimo taškas.')
    if point.get('machine') != core.machine() or point.get('release') != core.release():
        core.fail('Taškas priklauso kitam kompiuteriui arba Debian leidimui.')
    if 'system' in point and point['system'] != identity(detect()):
        core.fail('Taškas priklauso kitam kompiuteriui arba Debian leidimui.')
    packages = point.get('packages')
    if not isinstance(packages, dict) or len(packages) < 20:
        core.fail('Taške nėra tinkamo paketų sąrašo.')
    if not all(isinstance(n, str) and core.NAME.fullmatch(n) and isinstance(v, str)
               for n, v in packages.items()):
        core.fail('Taško paketų sąrašas netinkamas.')
    return point


def data_dir():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'linux-tvarka'


def points():
    result = []
    paths = ([] if point_store.initial_deleted() else [HERE / 'initial-point.json']) + sorted((data_dir() / 'points').glob('*.json'))
    for path in paths:
        try:
            point = validate_point(json.loads(path.read_text()))
            result.append({'id': path.stem, 'name': point.get('name', 'Švari sistema be žaidimų'),
                           'created': point.get('created', ''), 'count': len(point['packages'])})
        except (ValueError, OSError, RuntimeError):
            continue
    return sorted(result, key=lambda p: p['created'], reverse=True)


def get_point(ident):
    if ident == 'initial-point':
        if point_store.initial_deleted():
            raise ValueError('Invalid point identifier.')
        path = HERE / 'initial-point.json'
    elif isinstance(ident, str) and re.fullmatch(r'[0-9a-f]{32}', ident):
        path = data_dir() / 'points' / (ident + '.json')
    else:
        core.fail('Netinkamas taško identifikatorius.')
    return validate_point(json.loads(path.read_text()))


def create_point(name):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        core.fail('Taško pavadinimas turi būti nuo 1 iki 100 simbolių.')
    before = state_token()
    core.audit()
    cache = apt.Cache()
    if cache.broken_count:
        core.fail('Pirmiausia sutvarkykite APT priklausomybes.')
    point = {'format': 1, 'system': identity(detect()), 'name': name.strip(), 'machine': core.machine(), 'release': core.release(),
             'created': dt.datetime.now(dt.timezone.utc).isoformat(),
             'packages': {n: p.installed.version for n,p in core.installed(cache).items()}}
    if before != state_token():
        core.fail('Paketų būsena pasikeitė. Bandykite dar kartą.')
    folder = data_dir() / 'points'
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    ident = uuid.uuid4().hex
    with (folder / (ident + '.json')).open('x') as f:
        json.dump(point, f, indent=2, ensure_ascii=False)
    return {'id': ident, 'count': len(point['packages'])}


def desktop_names(cache):
    import gi
    from gi.repository import Gio
    infos = [a for a in Gio.AppInfo.get_all() if a.should_show() and hasattr(a, 'get_filename') and a.get_filename()]
    paths = sorted({a.get_filename() for a in infos})
    owners = {}
    for offset in range(0, len(paths), 100):
        result = subprocess.run(['/usr/bin/dpkg-query', '-S', *paths[offset:offset+100]],
                                text=True, capture_output=True)
        for line in result.stdout.splitlines():
            if ': ' not in line:
                continue
            pkgs, file = line.split(': ', 1)
            for name in pkgs.split(', '):
                if name in cache and cache[name].is_installed:
                    owners[file] = cache[name].fullname
                    break
    apps, external = {}, []
    for info in infos:
        item = {'title': info.get_display_name(), 'icon': info.get_icon().to_string() if info.get_icon() else 'application-x-executable',
                'description': info.get_description() or ''}
        owner = owners.get(info.get_filename())
        if owner:
            apps.setdefault(owner, item)
        else:
            external.append(dict(item, key='desktop:' + info.get_filename(), package='', version='',
                                 size=0, manual=True, app=True, protected=True, external=True))
    return apps, external


def inventory():
    cache = apt.Cache()
    safe = protected(cache)
    apps, external = desktop_names(cache)
    rows = []
    for name, package in core.installed(cache).items():
        info = apps.get(name, {})
        rows.append({'key': name, 'package': name, 'title': info.get('title', package.name),
                     'description': info.get('description') or package.installed.summary,
                     'icon': info.get('icon', 'application-x-addon-symbolic'),
                     'version': package.installed.version, 'size': package.installed.installed_size,
                     'manual': not package.is_auto_installed, 'app': name in apps,
                     'protected': name in safe, 'external': False})
    rows += external
    return {'items': sorted(rows, key=lambda r: r['title'].casefold()), 'points': points(),
            'packages': sum(not r['external'] for r in rows),
            'apps': sum(r['app'] for r in rows), 'release': core.release()}


def build_plan(cache, request):
    if cache.broken_count:
        core.fail('APT turi pažeistų priklausomybių. Pirmiausia jas sutvarkykite.')
    current = core.installed(cache)
    safe = protected(cache)
    mode = request.get('mode')
    residuals, missing = [], []
    if mode == 'remove':
        selected = request.get('selected', [])
        if (not isinstance(selected, list) or not selected or len(selected) > 4000
                or not all(isinstance(n, str) and core.NAME.fullmatch(n) for n in selected)):
            core.fail('Pasirinkite bent vieną įdiegtą paketą.')
        selected = sorted(set(selected))
        if any(n not in current for n in selected):
            core.fail('Pasirinktų paketų būsena pasikeitė. Atnaujinkite sąrašą.')
        if set(selected) & safe:
            core.fail('Pasirinktas apsaugotas sistemos paketas arba jo priklausomybė.')
        old_orphans = {p.fullname for p in cache if p.is_installed and p.is_auto_removable}
        selected_dependencies = core.closure(current, set(selected)) - set(selected)
        for name in selected:
            cache[name].mark_delete(auto_fix=False, purge=True)
        # A removal-only solution: don't install replacement applications.
        # Display reverse dependents (including desktop metapackages) in the plan.
        while cache.broken_count:
            dependents = [p for p in cache if p.is_installed and p.is_inst_broken and not p.marked_delete]
            if not dependents or any(p.fullname in safe for p in dependents):
                core.fail('Šalinimas paliestų apsaugotą sistemos priklausomybę.')
            for package in dependents:
                package.mark_delete(auto_fix=False, purge=True)
        if request.get('dependencies', True):
            while True:
                newly_unused = [p for p in cache if p.is_installed and p.is_auto_removable
                                and not p.marked_delete and p.fullname not in old_orphans
                                and p.fullname not in safe and p.fullname in selected_dependencies]
                if not newly_unused:
                    break
                # APT's garbage set may also contain other apps that we deliberately
                # keep after removing a metapackage. Preserve their dependencies.
                remaining = {n: p for n,p in current.items() if not p.marked_delete}
                candidates = {p.fullname for p in newly_unused}
                needed_by_kept = core.closure(remaining, remaining.keys() - candidates)
                newly_unused = [p for p in newly_unused if p.fullname not in needed_by_kept]
                if not newly_unused:
                    break
                for package in newly_unused:
                    package.mark_delete(auto_fix=False, purge=True)
    elif mode == 'point':
        point = validate_point(request.get('point'))
        missing = sorted(set(point['packages']) - current.keys())
        # This is a restore point, not reinstall or downgrade.
        baseline_roots = (set(point['packages']) & current.keys()) | safe
        keep = core.closure(current, baseline_roots)
        selected = sorted(current.keys() - keep)
        for name in selected:
            cache[name].mark_delete(auto_fix=False, purge=True)
        residuals = core.prepare_residuals(cache, point, selected)
    else:
        core.fail('Nežinomas veiksmas.')
    changes = cache.get_changes()
    if cache.broken_count or any(not p.marked_delete for p in changes):
        core.fail('Šalinimas pažeistų priklausomybes arba keistų kitų paketų versijas.')
    if any(p.fullname in safe for p in changes):
        core.fail('APT planas paliestų apsaugotus sistemos komponentus. Šalinimas sustabdytas.')
    removed = sorted(p.fullname for p in changes)
    rows = [{'package': n, 'size': current[n].installed.installed_size if n in current else 0,
             'reason': 'Konfigūracijos likučiai' if n in residuals else
                       'Pasirinkta' if n in selected else 'APT priklausomybės'} for n in removed]
    plan = {'mode': mode, 'removed': removed, 'rows': rows, 'missing': missing,
            'bytes': sum(row['size'] for row in rows), 'state': state_token(),
            'clean_cache': bool(request.get('clean_cache', False)),
            'request_hash': digest(request)}
    plan['hash'] = digest(plan)
    return plan


def preview(request):
    before = state_token()
    core.audit()
    plan = build_plan(apt.Cache(), request)
    if before != state_token():
        core.fail('Paketų būsena pasikeitė rengiant planą. Bandykite dar kartą.')
    return plan


class NonInteractiveInstall(apt.progress.base.InstallProgress):
    def conffile(self, current, new):
        # Fail safe: stdin is /dev/null; dpkg will abort rather than await input.
        pass


def apply_request(payload):
    if os.geteuid() != 0:
        core.fail('Šalinimui reikalingas administratoriaus patvirtinimas.')
    request, expected = payload['request'], payload['hash']
    with apt_pkg.SystemLock():
        core.audit()
        cache = apt.Cache()
        plan = build_plan(cache, request)
        if plan['hash'] != expected:
            core.fail('Sistema arba planas pasikeitė. Iš naujo peržiūrėkite pakeitimus.')
        logdir = Path('/var/log/linux-tvarka')
        logdir.mkdir(parents=True, mode=0o700, exist_ok=True)
        log = logdir / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        record = {'plan': plan, 'status': 'started'}
        def save():
            log.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        save()
        try:
            os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
            os.environ['NEEDRESTART_MODE'] = 'l'
            # Keep stdout solely for our JSON response; package script output goes to stderr.
            original = os.dup(1)
            try:
                os.dup2(2, 1)
                if plan['removed'] and not cache.commit(install_progress=NonInteractiveInstall()):
                    core.fail('Paketų šalinimas nebaigtas.')
            finally:
                os.dup2(original, 1)
                os.close(original)
            fresh = apt.Cache()
            if fresh.broken_count or any((p.is_installed or p.has_config_files) and p.fullname in plan['removed'] for p in fresh):
                core.fail('Patikra po šalinimo nepavyko. Tikrinkite dpkg žurnalą.')
            core.audit()
            record['status'] = 'packages-completed'
        except BaseException:
            record['status'] = 'failed-or-interrupted'
            raise
        finally:
            save()
    try:
        if plan['clean_cache']:
            subprocess.run(['/usr/bin/apt-get', 'clean'], check=True, stdout=sys.stderr)
        record['status'] = 'completed'
    except BaseException:
        record['status'] = 'packages-completed-cache-failed'
        raise
    finally:
        save()
    return {'removed': len(plan['removed']), 'log': str(log)}


def main():
    apt_pkg.init()
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['inventory', 'points', 'point-create', 'point-get', 'preview', 'apply'])
    parser.add_argument('--name', default='')
    parser.add_argument('--id', default='')
    args = parser.parse_args()
    if args.action in ('preview', 'apply'):
        raw = sys.stdin.read(2_000_001)
        if len(raw) > 2_000_000:
            core.fail('Užklausa per didelė.')
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            core.fail('Netinkama užklausa.')
        if args.action == 'apply':
            with open(os.devnull) as null:
                os.dup2(null.fileno(), 0)
            value = apply_request(payload)
        else:
            value = preview(payload)
    elif args.action == 'inventory': value = inventory()
    elif args.action == 'points': value = points()
    elif args.action == 'point-get': value = get_point(args.id)
    else: value = create_point(args.name)
    print(json.dumps({'ok': True, 'data': value}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
