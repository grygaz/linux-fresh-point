#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Terminal interface for Linux fresh point."""
import curses
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ['LINUX_FRESH_POINT_HEADLESS'] = '1'

import i18n
from i18n import tr


def size_text(value):
    if value >= 1_000_000_000:
        return f'{value / 1_000_000_000:.1f} GB'
    return f'{value / 1_000_000:.1f} MB'


def backend(action, payload=None, extra=(), privileged=False):
    command = ['/usr/bin/python3', '-I', str(HERE / 'backend.py'), action, *extra]
    if privileged and os.geteuid() != 0:
        helper = next((shutil.which(name) for name in ('sudo', 'doas') if shutil.which(name)), None)
        if not helper:
            raise RuntimeError('Administrator authorization requires sudo or doas in terminal mode.')
        command.insert(0, helper)
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else '',
                            capture_output=True, text=True)
    try:
        message = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError((result.stderr or result.stdout or 'Package manager failed.')[-5000:])
    if result.returncode or not message.get('ok'):
        raise RuntimeError(message.get('error', result.stderr[-5000:]))
    return message['data']


def clip(text, width):
    value = str(text).replace('\n', ' ')
    return value if len(value) <= width else value[:max(0, width - 1)] + '…'


class TerminalUI:
    def __init__(self, screen):
        self.screen = screen
        self.data = None
        self.selected = set()
        self.dependencies = True
        self.clean_cache = True
        self.status = 'Loading installed packages…'

    def write(self, row, col, text, style=0):
        height, width = self.screen.getmaxyx()
        if 0 <= row < height and col < width:
            try:
                self.screen.addnstr(row, col, str(text), max(0, width - col - 1), style)
            except curses.error:
                pass

    def frame(self, title, help_text=''):
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        self.write(0, 0, ' Linux fresh point ', curses.A_REVERSE | curses.A_BOLD)
        self.write(0, 20, clip(title, width - 21), curses.A_REVERSE)
        self.write(height - 2, 0, clip(self.status, width - 1), curses.A_DIM)
        self.write(height - 1, 0, clip(help_text, width - 1), curses.A_REVERSE)

    def message(self, title, text):
        lines = []
        width = max(20, self.screen.getmaxyx()[1] - 4)
        for source in str(text).splitlines() or ['']:
            lines.extend(textwrap.wrap(source, width=width) or [''])
        offset = 0
        while True:
            self.frame(title, '↑/↓ scroll · Enter/Esc return')
            height = self.screen.getmaxyx()[0]
            for index, line in enumerate(lines[offset:offset + height - 4], 1):
                self.write(index, 1, line)
            key = self.screen.getch()
            if key in (10, 13, 27, ord('q')):
                return
            if key in (curses.KEY_DOWN, ord('j')) and offset < max(0, len(lines) - height + 4):
                offset += 1
            elif key in (curses.KEY_UP, ord('k')):
                offset = max(0, offset - 1)
            elif key == curses.KEY_NPAGE:
                offset = min(max(0, len(lines) - height + 4), offset + height - 4)
            elif key == curses.KEY_PPAGE:
                offset = max(0, offset - height + 4)

    def prompt(self, title, label, default=''):
        self.frame(title, 'Enter accept · Esc cancel')
        self.write(2, 1, label)
        curses.echo()
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        try:
            self.screen.move(3, 1)
            self.screen.clrtoeol()
            if default:
                self.write(3, 1, default)
            value = self.screen.getstr(3, 1, 100).decode(errors='replace').strip()
        finally:
            curses.noecho()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
        return value or default

    def confirm(self, title, question):
        self.frame(title, 'Y confirm · any other key cancel')
        self.write(2, 1, question, curses.A_BOLD)
        return self.screen.getch() in (ord('y'), ord('Y'))

    def load(self):
        self.status = 'Reading installed package database…'
        self.frame('Loading')
        self.screen.refresh()
        self.data = backend('inventory')
        removable = {row['key'] for row in self.data['items'] if not row['protected'] and not row['external']}
        self.selected &= removable
        self.clean_cache = self.data['system']['manager'] == 'apt'
        self.dependencies = self.data['system']['manager'] in ('apt', 'pacman')
        self.status = f"Ready · {self.data['packages']} packages · {self.data['apps']} applications"

    def run(self):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.screen.keypad(True)
        self.load()
        cursor = 0
        while True:
            system = self.data['system']
            self.frame('Main menu', '↑/↓ move · Enter open · 1–5 shortcuts · R refresh · Q quit')
            self.write(2, 2, f"{system['pretty']} · {system['manager'].upper()}", curses.A_BOLD)
            options = ('1  ' + tr('Programos'), '2  ' + tr('Visi paketai'), '3  ' + tr('Atkūrimo taškai'),
                       '4  ' + tr('Kalba'), '5  ' + tr('Apie programą'))
            for index, option in enumerate(options, 4):
                self.write(index, 4, option, curses.A_REVERSE if index - 4 == cursor else 0)
            key = self.screen.getch()
            if key in (curses.KEY_DOWN, ord('j'), 9):
                cursor = (cursor + 1) % len(options)
                continue
            if key in (curses.KEY_UP, ord('k'), curses.KEY_BTAB):
                cursor = (cursor - 1) % len(options)
                continue
            if key in (10, 13, curses.KEY_ENTER):
                key = ord('1') + cursor
            elif ord('1') <= key <= ord('5'):
                cursor = key - ord('1')
            try:
                if key == ord('1'):
                    self.package_browser(True)
                elif key == ord('2'):
                    self.package_browser(False)
                elif key == ord('3'):
                    self.points()
                elif key == ord('4'):
                    self.languages()
                elif key == ord('5'):
                    self.about()
                elif key in (ord('r'), ord('R')):
                    self.load()
                elif key in (ord('q'), ord('Q'), 27):
                    return
            except Exception as exc:
                self.status = 'Operation failed.'
                self.message('Error', i18n.translate_error(str(exc)))

    def package_browser(self, apps_only):
        query, cursor, offset = '', 0, 0
        while True:
            rows = [row for row in self.data['items'] if (not apps_only or row['app']) and
                    (not query or query.casefold() in ' '.join((row['title'], row['package'], row['description'])).casefold())]
            cursor = min(cursor, max(0, len(rows) - 1))
            height = self.screen.getmaxyx()[0]
            visible = max(1, height - 6)
            if cursor < offset: offset = cursor
            if cursor >= offset + visible: offset = cursor - visible + 1
            title = tr('Įdiegtos programos') if apps_only else tr('Visi sistemos paketai')
            self.frame(title, '↑/↓ move · Space select · / search · P preview · D deps · C clear · Esc back')
            self.write(1, 1, f"Search: {query or '—'} · {len(rows)} results · {len(self.selected)} selected · dependencies: {'on' if self.dependencies else 'off'}")
            for line, row in enumerate(rows[offset:offset + visible], 3):
                marker = '!' if row['protected'] else 'x' if row['key'] in self.selected else ' '
                text = f"[{marker}] {row['title']}  ({row['package']})  {size_text(row['size'])}"
                self.write(line, 1, text, curses.A_REVERSE if offset + line - 3 == cursor else 0)
            key = self.screen.getch()
            if key in (27, ord('q')): return
            if key in (curses.KEY_DOWN, ord('j')): cursor = min(max(0, len(rows)-1), cursor + 1)
            elif key in (curses.KEY_UP, ord('k')): cursor = max(0, cursor - 1)
            elif key == curses.KEY_NPAGE: cursor = min(max(0, len(rows)-1), cursor + visible)
            elif key == curses.KEY_PPAGE: cursor = max(0, cursor - visible)
            elif key == ord('/'):
                query = self.prompt(title, 'Search packages:')
                cursor = offset = 0
            elif key == ord(' ') and rows:
                row = rows[cursor]
                if not row['protected'] and not row['external']:
                    if row['key'] in self.selected: self.selected.remove(row['key'])
                    else: self.selected.add(row['key'])
            elif key in (ord('c'), ord('C')): self.selected.clear()
            elif key in (ord('d'), ord('D')) and self.data['system']['manager'] in ('apt', 'pacman'):
                self.dependencies = not self.dependencies
            elif key in (ord('p'), ord('P')):
                if not self.selected:
                    self.message('Nothing selected', 'Select at least one removable package first.')
                else:
                    request = {'mode': 'remove', 'selected': sorted(self.selected),
                               'dependencies': self.dependencies, 'clean_cache': False}
                    self.preview_and_apply(request)
                    self.load()

    def points(self):
        cursor, offset = 0, 0
        while True:
            values = backend('points')
            cursor = min(cursor, max(0, len(values)-1))
            visible = max(1, self.screen.getmaxyx()[0] - 5)
            if cursor < offset: offset = cursor
            if cursor >= offset + visible: offset = cursor - visible + 1
            self.frame(tr('Atkūrimo taškai'), '↑/↓ move · N new · P preview cleanup · D delete · C cache · Esc back')
            self.write(1, 1, f"APT cache cleanup: {'on' if self.clean_cache else 'off'}")
            for line, point in enumerate(values[offset:offset + visible], 3):
                try: created = dt.datetime.fromisoformat(point['created']).astimezone().strftime('%Y-%m-%d %H:%M')
                except ValueError: created = point['created']
                text = f"{point['name']} · {created} · {point['count']} packages"
                self.write(line, 1, text, curses.A_REVERSE if offset + line - 3 == cursor else 0)
            if not values: self.write(3, 1, 'No restore points. Press N to create one.')
            key = self.screen.getch()
            if key in (27, ord('q')): return
            if key in (curses.KEY_DOWN, ord('j')): cursor = min(max(0, len(values)-1), cursor + 1)
            elif key in (curses.KEY_UP, ord('k')): cursor = max(0, cursor - 1)
            elif key in (ord('n'), ord('N')):
                name = self.prompt('New restore point', 'Name:', 'Clean system ' + dt.date.today().isoformat())
                if name:
                    result = backend('point-create', extra=['--name', name])
                    self.status = f"Restore point saved: {result['count']} packages"
            elif key in (ord('d'), ord('D')) and values:
                point = values[cursor]
                if self.confirm('Delete restore point', f"Delete '{point['name']}' package list?"):
                    backend('point-delete', extra=['--id', point['id']])
                    self.status = 'Restore point deleted; installed packages were not changed.'
            elif key in (ord('c'), ord('C')) and self.data['system']['manager'] == 'apt':
                self.clean_cache = not self.clean_cache
            elif key in (ord('p'), ord('P')) and values:
                point = backend('point-get', extra=['--id', values[cursor]['id']])
                request = {'mode': 'point', 'point': point, 'clean_cache': self.clean_cache}
                self.preview_and_apply(request)
                self.load()

    def preview_and_apply(self, request):
        self.status = 'Preparing removal plan…'
        plan = backend('preview', request)
        details = [f"{len(plan['removed'])} packages · about {size_text(plan['bytes'])}", '']
        details.extend(f"{row['package']} — {tr(row['reason'])}" for row in plan['rows'])
        if plan['missing']:
            details.extend(['', 'Missing point packages (not reinstalled):', *plan['missing']])
        if plan.get('native_output'):
            details.extend(['', 'Native package-manager preview:', plan['native_output']])
        if plan['clean_cache']:
            details.extend(['', 'The APT download cache will also be cleared.'])
        self.message('Removal preview — no changes made', '\n'.join(details) or 'Nothing to remove.')
        if not plan['removed'] and not plan['clean_cache']:
            return
        if not self.confirm('Final confirmation', 'Apply exactly this reviewed plan?'):
            self.status = 'Removal cancelled.'
            return
        payload = {'request': request, 'hash': plan['hash']}
        result = backend('apply', payload, privileged=True)
        self.selected.clear()
        self.status = f"Cleanup complete · {result['removed']} removed · log: {result['log']}"
        self.message('Cleanup complete', self.status)

    def languages(self):
        cursor = [code for code, _ in i18n.LANGUAGES].index(i18n.language())
        while True:
            self.frame(tr('Kalba'), '↑/↓ move · Enter select · Esc return')
            for index, (code, name) in enumerate(i18n.LANGUAGES):
                self.write(index + 2, 2, f"{index + 1}  {name}" + ('  *' if code == i18n.language() else ''),
                           curses.A_REVERSE if index == cursor else 0)
            key = self.screen.getch()
            if key in (27, ord('q')):
                return
            if key in (curses.KEY_DOWN, ord('j'), 9):
                cursor = (cursor + 1) % len(i18n.LANGUAGES)
            elif key in (curses.KEY_UP, ord('k'), curses.KEY_BTAB):
                cursor = (cursor - 1) % len(i18n.LANGUAGES)
            elif key in (10, 13, curses.KEY_ENTER) or ord('1') <= key < ord('1') + len(i18n.LANGUAGES):
                if ord('1') <= key < ord('1') + len(i18n.LANGUAGES):
                    cursor = key - ord('1')
                i18n.set_language(i18n.LANGUAGES[cursor][0])
                self.status = 'Language preference saved.'
                return

    def about(self):
        description = HERE / 'descriptions' / (i18n.language() + '.md')
        self.message(tr('Apie programą'), description.read_text(encoding='utf-8') +
                     '\n\nLicense: GNU GPL v3 only\nhttps://www.gnu.org/')


def configure_portable():
    if os.environ.get('LINUX_FRESH_POINT_PORTABLE') != '1' and not (HERE / 'portable.mode').exists():
        return
    import hashlib
    machine = hashlib.sha256(Path('/etc/machine-id').read_bytes().strip()).hexdigest()[:24]
    data = HERE / 'portable-data' / machine
    data.mkdir(parents=True, exist_ok=True)
    os.environ['XDG_DATA_HOME'] = str(data)


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        sys.exit('Linux fresh point TUI requires an interactive terminal. For SSH, use ssh -t.')
    configure_portable()
    curses.wrapper(lambda screen: TerminalUI(screen).run())


if __name__ == '__main__':
    main()
