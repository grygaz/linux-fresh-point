#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Check runtime libraries and install missing distro packages on startup."""
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PACKAGE_MAP = {
    'apt': {
        'gi': ('python3-gi',),
        'Gtk': ('gir1.2-gtk-4.0',),
        'GdkPixbuf': ('gir1.2-gdkpixbuf-2.0',),
        'apt': ('python3-apt',),
    },
    'pacman': {
        'gi': ('python-gobject',),
        'Gtk': ('gtk4',),
        'GdkPixbuf': ('gdk-pixbuf2',),
    },
    'portage': {
        'gi': ('dev-python/pygobject',),
        'Gtk': ('gui-libs/gtk:4',),
        'GdkPixbuf': ('x11-libs/gdk-pixbuf',),
        'portage': ('sys-apps/portage',),
    },
    'dnf': {
        'gi': ('python3-gobject',),
        'Gtk': ('gtk4',),
        'GdkPixbuf': ('gdk-pixbuf2',),
    },
    'zypper': {
        'gi': ('python3-gobject',),
        'Gtk': ('typelib-1_0-Gtk-4_0',),
        'GdkPixbuf': ('typelib-1_0-GdkPixbuf-2_0',),
    },
}


def missing_libraries(manager, graphical=True):
    """Return import/typelib names that the application cannot currently load."""
    missing = []
    if graphical:
        try:
            gi = importlib.import_module('gi')
        except (ImportError, ValueError):
            missing.extend(('gi', 'Gtk', 'GdkPixbuf'))
        else:
            for namespace, version in (('Gtk', '4.0'), ('GdkPixbuf', '2.0')):
                try:
                    gi.require_version(namespace, version)
                    importlib.import_module('gi.repository.' + namespace)
                except (ImportError, ValueError):
                    missing.append(namespace)
    if manager in ('apt', 'portage'):
        try:
            importlib.import_module(manager)
        except ImportError:
            missing.append(manager)
    return missing


def packages_for(manager, missing):
    packages = []
    for library in missing:
        for package in PACKAGE_MAP[manager].get(library, ()):
            if package not in packages:
                packages.append(package)
    return packages


def install_command(manager, command, packages):
    if manager == 'apt':
        return [command, 'install', '-y', *packages]
    if manager == 'pacman':
        return [command, '-S', '--needed', '--noconfirm', *packages]
    if manager == 'portage':
        return [command, '--noreplace', *packages]
    if manager == 'dnf':
        return [command, 'install', '-y', *packages]
    return [command, '--non-interactive', 'install', '--no-recommends', *packages]


def elevate(command, graphical=True):
    if os.geteuid() == 0:
        return command
    helpers = ('pkexec', 'sudo', 'doas') if graphical else ('sudo', 'doas')
    for helper in helpers:
        path = shutil.which(helper)
        if path:
            return [path, *command]
    raise RuntimeError('Administrator authorization is required, but pkexec, sudo, and doas are unavailable.')


def ensure_dependencies(graphical=True):
    from system_info import detect
    system = detect()
    missing = missing_libraries(system['manager'], graphical)
    if not missing:
        return
    packages = packages_for(system['manager'], missing)
    if not packages:
        raise RuntimeError('No installation packages are known for: ' + ', '.join(missing))
    print('Linux fresh point: missing required libraries: ' + ', '.join(missing), file=sys.stderr)
    print('Linux fresh point: installing: ' + ', '.join(packages), file=sys.stderr)
    result = subprocess.run(elevate(install_command(system['manager'], system['command'], packages), graphical))
    if result.returncode:
        raise RuntimeError('Dependency installation was cancelled or failed.')
    importlib.invalidate_caches()
    still_missing = missing_libraries(system['manager'], graphical)
    if still_missing:
        raise RuntimeError('Libraries are still unavailable after installation: ' + ', '.join(still_missing))


if __name__ == '__main__':
    try:
        ensure_dependencies('--tui' not in sys.argv)
    except Exception as exc:
        sys.exit('Linux fresh point: ' + str(exc))
