# SPDX-License-Identifier: GPL-3.0-only
"""Delete user points only; never remove packages or follow arbitrary paths."""
import os
from pathlib import Path
import re

def folder():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'linux-tvarka/points'

def initial_deleted():
    return (folder()/'.initial-point-deleted').exists()

def delete(ident):
    if ident == 'initial-point':
        folder().mkdir(parents=True, exist_ok=True)
        (folder()/'.initial-point-deleted').touch()
    elif isinstance(ident, str) and re.fullmatch(r'[0-9a-f]{32}',ident):
        (folder()/(ident+'.json')).unlink()
    else:
        raise ValueError('Invalid point identifier.')
    return {'deleted':ident}
