#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Portable source launcher. Uses host GTK/package APIs; installs nothing."""
import hashlib
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
try:
    if os.geteuid()==0: raise RuntimeError('Run without sudo.')
    from system_info import detect
    system=detect()
    import gi
    gi.require_version('Gtk','4.0')
    from gi.repository import Gtk
    if system['manager']=='apt': import apt
    if system['manager']=='portage': import portage
    machine=hashlib.sha256(Path('/etc/machine-id').read_bytes().strip()).hexdigest()[:24]
    data=HERE/'portable-data'/machine
    data.mkdir(parents=True,exist_ok=True)
    test=data/'.write-check';test.write_text('');test.unlink()
    os.environ['XDG_DATA_HOME']=str(data)
except Exception as exc:
    sys.exit('Linux fresh point: '+str(exc)+'\nRequires Python 3, PyGObject, GTK 4, native package manager and a writable portable folder. See PORTABLE.md.')
os.execv(sys.executable,[sys.executable,'-I',str(HERE/'app.py'),*sys.argv[1:]])
