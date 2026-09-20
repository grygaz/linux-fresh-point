# SPDX-License-Identifier: GPL-3.0-only
"""Detect the host family, never select a foreign manager just because installed."""
import hashlib
import platform
import shutil
from pathlib import Path

FAMILIES = {'debian':'apt','ubuntu':'apt','linuxmint':'apt','pop':'apt','kali':'apt',
            'arch':'pacman','manjaro':'pacman','endeavouros':'pacman',
            'gentoo':'portage','funtoo':'portage',
            'fedora':'dnf','rhel':'dnf','centos':'dnf','rocky':'dnf','almalinux':'dnf',
            'opensuse':'zypper','opensuse-leap':'zypper','opensuse-tumbleweed':'zypper',
            'suse':'zypper','sles':'zypper'}
COMMANDS = {'apt':'apt-get','pacman':'pacman','portage':'emerge','dnf':'dnf','zypper':'zypper'}

def os_release(path='/etc/os-release'):
    import shlex
    result = {}
    for line in Path(path).read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            parts = shlex.split(value)
            result[key] = ' '.join(parts)
    return result

def detect(info=None, which=shutil.which):
    if info is None and Path('/run/ostree-booted').exists():
        raise RuntimeError('Atomic OSTree systems are not supported.')
    info = os_release() if info is None else info
    candidates = [info.get('ID','')] + info.get('ID_LIKE','').split()
    manager = next((FAMILIES[x] for x in candidates if x in FAMILIES), None)
    if manager is None:
        raise RuntimeError('Unsupported Linux distribution: ' + info.get('ID','unknown'))
    command = which(COMMANDS[manager])
    if not command:
        raise RuntimeError('Native package manager is missing: ' + COMMANDS[manager])
    return {'manager':manager, 'command':command, 'distro':info.get('ID',''),
            'release':info.get('VERSION_ID','rolling'),
            'pretty':info.get('PRETTY_NAME',info.get('ID','Linux')), 'arch':platform.machine()}

def identity(system):
    return {k:system[k] for k in ('manager','distro','release','arch')} | {
        'machine':hashlib.sha256(Path('/etc/machine-id').read_bytes().strip()).hexdigest()}
