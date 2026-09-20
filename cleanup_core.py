#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Debian baseline cleanup preserving installed updates; no system backups."""
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import subprocess
import sys

try:
    import apt
    import apt_pkg
    import apt.progress.text
except ImportError:
    sys.exit('Reikia sisteminio /usr/bin/python3 ir Debian paketo python3-apt.')

HERE = Path(__file__).resolve().parent
NAME = re.compile(r'[a-z0-9][a-z0-9+.-]*:[a-z0-9][a-z0-9-]*\Z')
BOOT = re.compile(r'^(linux-image|linux-headers|linux-base|linux-kbuild|linux-modules|firmware-|.*-microcode$|grub|shim|systemd|initramfs|dracut)')
RETIRED_KERNEL = re.compile(r'^linux-(image|headers|modules|kbuild)-[0-9]')


def fail(message):
    raise RuntimeError(message)


def machine():
    return hashlib.sha256(Path('/etc/machine-id').read_bytes().strip()).hexdigest()


def release():
    return platform.freedesktop_os_release()['VERSION_ID']


def installed(cache):
    return {p.fullname: p for p in cache if p.is_installed}


def audit():
    result = subprocess.run(['/usr/bin/dpkg', '--audit'], capture_output=True, text=True, check=True)
    if result.stdout.strip() or result.stderr.strip():
        fail('dpkg turi neužbaigtų operacijų:\n' + result.stdout + result.stderr)


def status_digest():
    return hashlib.sha256(Path('/var/lib/dpkg/status').read_bytes()).hexdigest()


def save_baseline(path):
    before = status_digest()
    audit()
    cache = apt.Cache()
    if cache.broken_count:
        fail('APT priklausomybės pažeistos. Pirmiausia sutvarkykite paketų būseną.')
    data = {'format': 1, 'machine': machine(), 'release': release(),
            'created': dt.datetime.now(dt.timezone.utc).isoformat(),
            'packages': {n: p.installed.version for n, p in installed(cache).items()}}
    if before != status_digest():
        fail('Paketų būsena išsaugojimo metu pasikeitė. Bandykite dar kartą.')
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')
    print(f'Išsaugota {len(data["packages"])} paketų: {path}')


def read_baseline(path):
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get('format') != 1 or data.get('machine') != machine():
        fail('Netinkamas pradinis taškas arba tai kitas kompiuteris.')
    if data.get('release') != release():
        fail('Pasikeitė Debian leidimas. Reikia peržiūrėti ir atnaujinti pradinį tašką.')
    packages = data.get('packages')
    if not isinstance(packages, dict) or len(packages) < 20:
        fail('Pradinis paketų sąrašas netinkamas.')
    if not all(NAME.fullmatch(n) and isinstance(v, str) for n, v in packages.items()):
        fail('Netinkami paketų vardai arba versijos.')
    return data


def closure(packages, roots):
    keep, todo = set(roots), list(roots)
    while todo:
        package = packages[todo.pop()]
        for group in package.installed.get_dependencies('PreDepends', 'Depends', 'Recommends'):
            for dep in group.or_dependencies:
                # Includes version constraints, virtual providers and alternatives.
                for version in dep.installed_target_versions:
                    name = version.package.fullname
                    if name in packages and name not in keep:
                        keep.add(name)
                        todo.append(name)
    return keep


def is_protected(p):
    name = p.name.split(':')[0]
    return (p.essential or p.installed.priority in ('required', 'important')
            or p.installed.record.get('Protected', 'no') == 'yes'
            or p._pkg.selected_state == apt_pkg.SELSTATE_HOLD
            or BOOT.match(name) is not None
            or name in ('apt', 'dpkg', 'python3', 'python3-apt', 'sudo'))


def prepare(cache, data):
    if cache.broken_count:
        fail('APT priklausomybės pažeistos; nieko nešalinama.')
    current = installed(cache)
    baseline = set(data['packages'])
    missing = sorted(n for n in baseline - current.keys() if not RETIRED_KERNEL.match(n))
    if missing:
        fail('Trūksta pradinių paketų. Nieko nešalinama. Atkurkite juos dabartinėmis\n'
             'versijomis, peržiūrėję sudo apt-get --no-remove install PAKETAS planą:\n'
             + '\n'.join(missing))
    roots = (baseline & current.keys()) | {n for n, p in current.items() if is_protected(p)}
    keep = closure(current, roots)
    extras = sorted(current.keys() - keep)
    for name in extras:
        cache[name].mark_delete(auto_fix=False, purge=True)
    changes = cache.get_changes()
    if cache.broken_count:
        fail('Šalinimas pažeistų priklausomybes. Nieko nešalinama.')
    if any(not p.marked_delete or p.fullname not in extras for p in changes):
        fail('APT planas turi neleistinų pakeitimų. Nieko nešalinama.')
    if {p.fullname for p in changes} != set(extras):
        fail('APT šalinimo sąrašas nesutampa. Nieko nešalinama.')
    return extras, sorted(keep - baseline)


def prepare_residuals(cache, data, extras):
    """Purge only uninstalled, non-baseline packages with registered conffiles."""
    residuals = sorted(p.fullname for p in cache
                       if not p.is_installed and p.has_config_files
                       and p.fullname not in data['packages']
                       and not BOOT.match(p.name.split(':')[0])
                       and p._pkg.selected_state != apt_pkg.SELSTATE_HOLD)
    for name in residuals:
        cache[name].mark_delete(auto_fix=False, purge=True)
    expected = set(extras) | set(residuals)
    changes = cache.get_changes()
    if (cache.broken_count or {p.fullname for p in changes} != expected
            or any(not p.marked_delete for p in changes)):
        fail('Konfigūracijos likučių šalinimo planas netinkamas. Nieko nešalinama.')
    return residuals


def reset(path, apply):
    if apply and os.geteuid() != 0:
        fail('Valymui reikia sudo. Peržiūrai jo nereikia.')
    data = read_baseline(path)
    # Native APT lock spans planning, confirmation and commit of the same cache.
    with apt_pkg.SystemLock() if apply else contextlib.nullcontext():
        audit()
        before = status_digest()
        cache = apt.Cache()
        extras, retained = prepare(cache, data)
        residuals = prepare_residuals(cache, data, extras)
        print(f'Pradinis taškas: {data["created"]}; paketų: {len(data["packages"])}')
        print(f'Šalinti: {len(extras)} paketų su jų sistemine konfigūracija.')
        for name in extras:
            print('  ŠALINTI  ' + name)
        print(f'Pašalintų programų sisteminės konfigūracijos likučiai: {len(residuals)}')
        for name in residuals:
            print('  LIKUČIAI ' + name)
        print(f'Papildomai išsaugoti dėl sistemos apsaugos / priklausomybių: {len(retained)}')
        for name in retained:
            print('  PALIKTI  ' + name)
        print('\nBus išvalyta APT atsisiuntimų ir paketų podėlio laikinoji atmintis (apt-get clean).')
        print('Tai APT / .deb paketų valymas pagal pradinį sąrašą. Atsarginės kopijos nekuriamos.')
        print('Flatpak, Snap, AppImage, pip/npm, Docker ir rankiniai diegimai nevalomi.')
        print('Asmeniniai failai ir išsaugotų programų nustatymai neatkuriami.')
        if not apply:
            print('\nTik peržiūra. Sistema nepakeista.')
            return
        print('\nPaketų pašalinimo scenarijai gali pašalinti ir jų paslaugų duomenis.')
        print('Atnaujintos versijos išliks. Bendras autoremove nebus vykdomas.')
        if not sys.stdin.isatty():
            fail('Valymą paleiskite interaktyviame terminale.')
        if input('Įrašykite VALYTI, kad vykdyti parodytą planą: ').strip() != 'VALYTI':
            print('Atšaukta.')
            return
        if before != status_digest():
            fail('Paketų būsena pasikeitė. Paleiskite iš naujo.')
        logdir = Path('/var/log/debian-reset')
        logdir.mkdir(mode=0o700, parents=True, exist_ok=True)
        log = logdir / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        record = {'baseline': str(path), 'remove': extras, 'residuals': residuals, 'retained': retained,
                  'apt_cache': 'pending',
                  'status': 'started', 'before': {n:p.installed.version for n,p in installed(cache).items()}}
        def save_log():
            log.write_text(json.dumps(record, indent=2) + '\n')
        save_log()
        try:
            if (extras or residuals) and not cache.commit(apt.progress.text.AcquireProgress(), apt.progress.base.InstallProgress()):
                fail('APT nebaigė operacijos.')
            fresh = apt.Cache()
            if fresh.broken_count or set(extras) & installed(fresh).keys():
                fail('Patikra po šalinimo nepavyko. Tikrinkite APT / dpkg žurnalus.')
            if any(p.fullname in set(extras + residuals) and p.has_config_files for p in fresh):
                fail('Liko nepašalintų konfigūracijos failų. Tikrinkite dpkg žurnalą.')
            audit()
            record['status'] = 'packages-completed'
        except BaseException:
            record['status'] = 'failed-or-interrupted'
            raise
        finally:
            save_log()
    # apt-get must acquire its own locks; release the python-apt lock first.
    try:
        subprocess.run(['/usr/bin/apt-get', 'clean'], check=True)
        record['apt_cache'] = 'completed'
        record['status'] = 'completed'
    except BaseException:
        record['apt_cache'] = 'failed-or-interrupted'
        record['status'] = 'packages-completed-cache-failed'
        raise
    finally:
        save_log()
    print(f'Valymas baigtas. Žurnalas: {log}')


def main():
    apt_pkg.init()
    parser = argparse.ArgumentParser(description='Debian paketų ir likučių valymas, išsaugant atnaujintas versijas.')
    parser.add_argument('command', nargs='?', default='plan', choices=['save', 'plan', 'clean', 'reset'])
    parser.add_argument('--baseline', type=Path, default=HERE / 'baseline.json')
    args = parser.parse_args()
    if args.command == 'save':
        save_baseline(args.baseline.resolve())
    else:
        reset(args.baseline.resolve(), args.command in ('clean', 'reset'))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f'KLAIDA: {exc}', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nNutraukta. Jei šalinimas jau vyko, tikrinkite sudo dpkg --audit.', file=sys.stderr)
        sys.exit(130)
