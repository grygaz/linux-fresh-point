# SPDX-License-Identifier: GPL-3.0-only
"""Small offline translation catalog. English is always the first-run default."""
import json
import os
from pathlib import Path
import tempfile

LANGUAGES = [('en', 'English'), ('ru', 'Русский'), ('lt', 'Lietuvių'),
             ('zh', '简体中文'), ('it', 'Italiano')]
_catalog = json.loads((Path(__file__).parent / 'translations.json').read_text(encoding='utf-8'))
_language = 'en'


def preferences_path():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'linux-tvarka/preferences.json'


def load_language():
    global _language
    try:
        value = json.loads(preferences_path().read_text()).get('language', 'en')
    except (OSError, ValueError, AttributeError):
        value = 'en'
    _language = value if value in dict(LANGUAGES) else 'en'
    return _language


def language():
    return _language


def set_language(value, persist=True):
    global _language
    if value not in dict(LANGUAGES):
        raise ValueError('Unsupported language')
    if persist:
        path = preferences_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            settings = json.loads(path.read_text())
            if not isinstance(settings, dict): settings = {}
        except (OSError, ValueError):
            settings = {}
        settings['language'] = value
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
                temp = Path(f.name)
                json.dump(settings, f, ensure_ascii=False, indent=2)
                f.write('\n')
            temp.replace(path)
        finally:
            if temp and temp.exists(): temp.unlink()
    _language = value


def tr(source, **values):
    if _language == 'lt':
        text = source
    else:
        item = _catalog.get(source, {})
        text = item.get(_language, item.get('en', source))
    return text.format(**values) if values else text


def translate_error(message):
    if message in _catalog:
        return tr(message)
    # Preserve diagnostic detail after a known application-owned error prefix.
    for source in sorted(_catalog, key=len, reverse=True):
        if len(source) > 15 and message.startswith(source):
            return tr(source) + message[len(source):]
    return message


load_language()
