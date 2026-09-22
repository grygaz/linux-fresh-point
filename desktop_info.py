# SPDX-License-Identifier: GPL-3.0-only
"""Read freedesktop application metadata without requiring a graphical session."""
import configparser
import os
from pathlib import Path


def entries(folders=None):
    if folders is None:
        folders = [Path('/usr/share/applications'), Path('/usr/local/share/applications')]
        folders.append(Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'applications')
    else:
        folders = [Path(folder) for folder in folders]
    result = []
    seen = set()
    for folder in reversed(folders):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob('*.desktop')):
            if path.name in seen:
                continue
            seen.add(path.name)
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(path, encoding='utf-8')
                item = parser['Desktop Entry']
                if (item.get('Type', 'Application') != 'Application'
                        or item.getboolean('Hidden', fallback=False)
                        or item.getboolean('NoDisplay', fallback=False)):
                    continue
                result.append({'path': str(path), 'title': item.get('Name', path.stem),
                               'description': item.get('Comment', ''),
                               'icon': item.get('Icon', 'application-x-executable')})
            except (OSError, UnicodeError, configparser.Error, ValueError):
                continue
    return result
