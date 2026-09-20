#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Linux fresh point: GTK4 package manager and restore points for Debian."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import re

sys.path.insert(0, str(Path(__file__).resolve().parent))
from about_content import SEND_MONEY_URL
import terminal_apply
import i18n
from i18n import tr

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango, GdkPixbuf

HERE = Path(__file__).resolve().parent


def backend(action, payload=None, extra=(), privileged=False):
    cmd = ['/usr/bin/python3', '-I', str(HERE / 'backend.py'), action, *extra]
    if privileged:
        cmd = ['/usr/bin/pkexec', '--disable-internal-agent', *cmd]
    result = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else '',
                            capture_output=True, text=True)
    try:
        message = json.loads(result.stdout)
    except ValueError:
        if privileged and result.returncode in (126, 127):
            raise RuntimeError(tr('Administratoriaus patvirtinimas atšauktas arba neprieinamas. '
                               'Paleiskite programą savo Linux darbalaukio sesijoje.'))
        raise RuntimeError((result.stderr or result.stdout or tr('Nepavyko paleisti paketų valdiklio.'))[-5000:])
    if not message.get('ok') or result.returncode:
        raise RuntimeError(message.get('error', result.stderr[-5000:]))
    return message['data']


def label(text, css=None, wrap=False):
    item = Gtk.Label(label=text, xalign=0)
    item.set_wrap(wrap)
    if css:
        item.add_css_class(css)
    return item


def box(vertical=False, spacing=0, css=None):
    item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)
    if css:
        item.add_css_class(css)
    return item


def button(text, callback, css=None):
    item = Gtk.Button(label=text)
    if css:
        item.add_css_class(css)
    item.connect('clicked', callback)
    return item


def size_text(value):
    if value >= 1_000_000_000:
        return f'{value / 1_000_000_000:.1f} GB'
    return f'{value / 1_000_000:.1f} MB'


class Window(Gtk.ApplicationWindow):
    def __init__(self, app, smoke=False, state=None):
        super().__init__(application=app, title='Linux fresh point', default_width=1120, default_height=780)
        self.set_size_request(850, 600)
        self.items, self.point_items, self.selected = [], [], set()
        self.view, self.limit, self.busy, self.smoke = 'apps', 160, False, smoke
        self.active_point_id = None
        self.nav_buttons = {}
        self.connect('close-request', self.on_close)

        header = Gtk.HeaderBar()
        header.set_title_widget(label('Linux fresh point', 'window-title'))
        self.spinner = Gtk.Spinner()
        header.pack_end(self.spinner)
        self.language_menu = Gtk.DropDown.new_from_strings([name for code, name in i18n.LANGUAGES])
        self.language_menu.set_selected([code for code, name in i18n.LANGUAGES].index(i18n.language()))
        self.language_menu.set_tooltip_text(tr('Kalba'))
        self.language_menu.connect('notify::selected', self.change_language)
        self.settings_menu = Gtk.MenuButton(label=tr('Nustatymai'))
        settings_popover = Gtk.Popover()
        settings_body = box(True, 10, 'settings-content')
        settings_body.append(label(tr('Kalba'), 'package-title'))
        settings_body.append(self.language_menu)
        def open_about(_):
            settings_popover.popdown()
            self.show_about()
        settings_body.append(button(tr('Apie programą'), open_about, 'secondary'))
        settings_popover.set_child(settings_body)
        self.settings_menu.set_popover(settings_popover)
        header.pack_end(self.settings_menu)
        self.set_titlebar(header)
        root = box()
        self.set_child(root)

        sidebar = box(True, 12, 'sidebar')
        sidebar.set_size_request(216, -1)
        logo_row = box(spacing=8)
        gnu = Gtk.LinkButton(uri='https://www.gnu.org/')
        gnu.set_tooltip_text(tr('GNU projektas'))
        gnu.add_css_class('gnu-link')
        emblem = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(HERE / 'gnu-logo.svg'), 104, 104, True))
        emblem.set_pixel_size(52)
        gnu.set_child(emblem)
        logo_row.append(gnu)
        logo_row.append(label('FRESH POINT', 'logo'))
        sidebar.append(logo_row)
        sidebar.append(label('Linux fresh point', 'brand'))
        sidebar.append(label(tr('Mažiau pertekliaus.\nDaugiau tvarkos.'), 'sidebar-muted'))
        nav = box(True, 2, 'navigation')
        for ident, title in [('apps', tr('Programos')), ('packages', tr('Visi paketai')), ('points', tr('Atkūrimo taškai'))]:
            item = button(title, lambda _, k=ident: self.navigate(k), 'nav-button')
            self.nav_buttons[ident] = item
            nav.append(item)
        sidebar.append(nav)
        filler = box()
        filler.set_vexpand(True)
        sidebar.append(filler)
        self.system_label = label('Linux', 'eyebrow', True)
        sidebar.append(self.system_label)
        sidebar.append(label(tr('Atnaujinimai išsaugomi'), 'sidebar-muted', True))
        sidebar.append(label(tr('Administratoriaus teisės\ntik šalinant paketus.'), 'sidebar-muted', True))
        root.append(sidebar)

        self.main = box(True, 18, 'main')
        self.main.set_hexpand(True)
        root.append(self.main)
        heading = box(spacing=12)
        title_box = box(True, 5)
        title_box.set_hexpand(True)
        self.title = label(tr('Įdiegtos programos'), 'page-title')
        self.subtitle = label(tr('Nuskaitomas sistemos paketų sąrašas…'), 'muted', True)
        title_box.append(self.title)
        title_box.append(self.subtitle)
        heading.append(title_box)
        heading.append(button(tr('Atnaujinti'), lambda _: self.refresh(), 'secondary'))
        self.main.append(heading)

        stats = box(spacing=12)
        self.stats_labels = []
        for title in [tr('PROGRAMOS'), tr('PAKETAI'), tr('PASIRINKTA')]:
            card = box(True, 7, 'stat-card')
            card.set_hexpand(True)
            card.append(label(title, 'stat-title'))
            value = label('—', 'stat-value')
            card.append(value)
            self.stats_labels.append(value)
            stats.append(card)
        self.main.append(stats)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.main.append(self.stack)
        self.build_packages()
        self.build_points()

        footer = box(spacing=12)
        self.status = label('Tikrinama sistema…', 'muted', True)
        self.status.set_hexpand(True)
        footer.append(self.status)
        self.main.append(footer)
        if state:
            self.selected = set(state['selected'])
            self.active_point_id = state['point']
            self.search.set_text(state['search'])
            self.point_name.set_text(state['name'])
            self.dependencies.set_active(state['dependencies'])
            self.clean_cache.set_active(state['clean_cache'])
        self.navigate(state['view'] if state else 'apps')
        self.refresh()

    def change_language(self, dropdown, _):
        code = i18n.LANGUAGES[dropdown.get_selected()][0]
        if code == i18n.language() or self.busy:
            return
        try:
            i18n.set_language(code)
        except (OSError, ValueError) as exc:
            dropdown.set_selected([code for code, name in i18n.LANGUAGES].index(i18n.language()))
            self.show_message(tr('Kalbos pasirinkimo nepavyko išsaugoti.'), str(exc))
            return
        state = {'view': self.view, 'search': self.search.get_text(), 'selected': self.selected,
                 'point': self.active_point_id, 'name': self.point_name.get_text(),
                 'dependencies': self.dependencies.get_active(), 'clean_cache': self.clean_cache.get_active()}
        new_window = Window(self.get_application(), self.smoke, state)
        new_window.present()
        self.destroy()

    def build_packages(self):
        page = box(True, 12)
        tools = box(spacing=10)
        self.search = Gtk.SearchEntry(placeholder_text=tr('Ieškoti programos arba paketo…'))
        self.search.set_hexpand(True)
        self.search.connect('search-changed', lambda _: self.filter_changed())
        tools.append(self.search)
        tools.append(button(tr('Pažymėti matomas'), lambda _: self.select_visible(), 'secondary'))
        tools.append(button(tr('Atžymėti'), lambda _: self.clear_selection(), 'secondary'))
        page.append(tools)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.add_css_class('list-frame')
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class('package-list')
        scroller.set_child(self.list)
        page.append(scroller)
        self.more = button(tr('Rodyti daugiau'), self.show_more, 'secondary')
        page.append(self.more)
        self.dependencies = Gtk.CheckButton(label=tr('Pašalinti ir šioms programoms nebereikalingas bibliotekas'))
        self.dependencies.set_active(True)
        page.append(self.dependencies)
        bottom = box(spacing=12, css='selection-bar')
        self.selection_info = label(tr('Pasirink vieną ar kelias programas.'), 'muted', True)
        self.selection_info.set_hexpand(True)
        bottom.append(self.selection_info)
        self.remove_button = button(tr('Peržiūrėti šalinimą'), lambda _: self.preview_remove(), 'danger')
        self.remove_button.set_sensitive(False)
        bottom.append(self.remove_button)
        page.append(bottom)
        self.stack.add_named(page, 'packages')

    def build_points(self):
        page = box(True, 16)
        explainer = box(True, 8, 'info-card')
        explainer.append(label(tr('Restore point = išsaugotas paketų sąrašas'), 'section-title'))
        explainer.append(label(tr('Valant pagal tašką pašalinami vėliau įdiegti paketai. '
                              'Esamų programų atnaujinimai išsaugomi. Atsarginė kopija nekuriama; '
                              'failai, nustatymai ir pašalintos programos neatkuriami.'), 'muted', True))
        page.append(explainer)
        create_row = box(spacing=10)
        self.point_name = Gtk.Entry(placeholder_text=tr('Pavadinimas, pvz. Švari sistema'))
        self.point_name.set_max_length(100)
        self.point_name.set_hexpand(True)
        create_row.append(self.point_name)
        create_row.append(button(tr('Sukurti tašką'), lambda _: self.create_point(), 'primary'))
        page.append(create_row)
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add_css_class('list-frame')
        self.points_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        scroller.set_child(self.points_list)
        page.append(scroller)
        self.clean_cache = Gtk.CheckButton(label=tr('Taip pat išvalyti APT atsisiuntimų podėlį'))
        self.clean_cache.set_active(True)
        page.append(self.clean_cache)
        self.point_button = button(tr('Peržiūrėti valymą pagal pasirinktą tašką'), lambda _: self.preview_point(), 'primary')
        page.append(self.point_button)
        self.stack.add_named(page, 'points')

    def on_close(self, _):
        if self.busy:
            self.status.set_text(tr('Palaukite, kol operacija baigsis. Paketų šalinimo nepertraukite.'))
            return True
        return False

    def set_busy(self, value, text=''):
        self.busy = value
        self.main.set_sensitive(not value)
        self.language_menu.set_sensitive(not value)
        self.settings_menu.set_sensitive(not value)
        for item in self.nav_buttons.values():
            item.set_sensitive(not value)
        self.spinner.set_spinning(value)
        if text:
            self.status.set_text(text)

    def run_job(self, work, success, message):
        if self.busy:
            return
        self.set_busy(True, message)
        def worker():
            try:
                result = work()
            except Exception as exc:
                GLib.idle_add(self.job_error, str(exc))
            else:
                GLib.idle_add(self.job_done, success, result)
        threading.Thread(target=worker, daemon=True).start()

    def job_error(self, message):
        self.set_busy(False, tr('Veiksmas nebaigtas. Peržiūrėkite pranešimą.'))
        self.show_message(tr('Nepavyko atlikti veiksmo'), i18n.translate_error(message))
        return False

    def job_done(self, callback, result):
        self.set_busy(False)
        callback(result)
        return False

    def refresh(self):
        self.run_job(lambda: backend('inventory'), self.loaded, tr('Skaitomas įdiegtų programų sąrašas…'))

    def loaded(self, data):
        self.items, self.point_items = data['items'], data['points']
        system = data['system']
        self.system_label.set_text(system['pretty'] + '\n' + {'apt':'APT','pacman':'Pacman','portage':'Portage','dnf':'DNF','zypper':'Zypper'}[system['manager']])
        self.clean_cache.set_sensitive(system['manager'] == 'apt')
        if system['manager'] != 'apt': self.clean_cache.set_active(False)
        self.dependencies.set_sensitive(system['manager'] in ('apt', 'pacman'))
        if system['manager'] not in ('apt', 'pacman'): self.dependencies.set_active(False)
        self.selected &= {r['key'] for r in self.items if not r['protected']}
        self.stats_labels[0].set_text(str(data['apps']))
        self.stats_labels[1].set_text(f'{data["packages"]:,}'.replace(',', ' '))
        self.rebuild_list()
        self.rebuild_points()
        self.status.set_text(tr('Paruošta. Asmeniniai failai tiesiogiai netrinami.'))
        if self.smoke:
            GLib.timeout_add(600, self.smoke_check)

    def navigate(self, view):
        self.view, self.limit = view, 160
        for ident, item in self.nav_buttons.items():
            if ident == view: item.add_css_class('active')
            else: item.remove_css_class('active')
        titles = {'apps': (tr('Įdiegtos programos'), tr('Programos su meniu įrašais. Pasirink, ką pašalinti.')),
                  'packages': (tr('Visi sistemos paketai'), tr('Programos ir bibliotekos. Sistemos komponentai apsaugoti.')),
                  'points': (tr('Atkūrimo taškai'), tr('Užfiksuok tvarkingą būseną ir vėliau pašalink papildomus paketus.'))}
        self.title.set_text(titles[view][0])
        self.subtitle.set_text(titles[view][1])
        self.stack.set_visible_child_name('points' if view == 'points' else 'packages')
        if view != 'points': self.rebuild_list()

    def filtered(self):
        query = self.search.get_text().strip().casefold()
        return [r for r in self.items if (self.view != 'apps' or r['app'])
                and (not query or query in ' '.join([r['title'], r['package'], r['description']]).casefold())]

    def filter_changed(self):
        self.limit = 160
        self.rebuild_list()

    def clear_box(self, container):
        while container.get_first_child():
            container.remove(container.get_first_child())

    def rebuild_list(self):
        self.clear_box(self.list)
        rows = self.filtered()
        for row in rows[:self.limit]:
            line = box(spacing=14, css='package-row')
            check = Gtk.CheckButton()
            check.set_active(row['key'] in self.selected)
            check.set_sensitive(not row['protected'])
            check.connect('toggled', self.toggled, row['key'])
            line.append(check)
            try:
                icon = Gtk.Image.new_from_gicon(Gio.Icon.new_for_string(row['icon']))
            except Exception:
                icon = Gtk.Image.new_from_icon_name('application-x-executable')
            icon.set_pixel_size(32)
            line.append(icon)
            details = box(True, 4)
            details.set_hexpand(True)
            title = label(row['title'], 'package-title')
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(42)
            details.append(title)
            summary = label(row['package'] or row['description'] or tr('Meniu įrašas be sistemos paketo'), 'muted')
            summary.set_ellipsize(Pango.EllipsizeMode.END)
            summary.set_max_width_chars(48)
            details.append(summary)
            line.append(details)
            meta = box(True, 4)
            meta.append(label(tr('Išorinis') if row['external'] else tr('Apsaugota') if row['protected'] else size_text(row['size']),
                              'badge' if row['protected'] else 'muted'))
            version = label(row['version'], 'tiny')
            version.set_ellipsize(Pango.EllipsizeMode.END)
            version.set_max_width_chars(22)
            meta.append(version)
            line.append(meta)
            line.set_tooltip_text(row['description'] + (tr('\nŠis įrašas rodomas informaciniais tikslais; jo nevaldo sistemos paketų valdiklis.') if row['external'] else ''))
            self.list.append(line)
        if not rows:
            empty = label(tr('Programų nerasta. Pakeisk paiešką arba pasirink „Visi paketai“.'), 'empty', True)
            self.list.append(empty)
        self.more.set_visible(len(rows) > self.limit)
        self.more.set_label(tr('Rodyti daugiau · {shown} iš {total}', shown=min(len(rows), self.limit), total=len(rows)))
        self.update_selection()

    def show_more(self, _):
        self.limit += 160
        self.rebuild_list()

    def toggled(self, item, key):
        if item.get_active(): self.selected.add(key)
        else: self.selected.discard(key)
        self.update_selection()

    def update_selection(self):
        count = len(self.selected)
        self.stats_labels[2].set_text(str(count))
        self.remove_button.set_sensitive(count > 0)
        self.selection_info.set_text(tr('Pasirinkta paketų: {count}. Prieš šalinimą bus parodytas planas.', count=count) if count else
                                     tr('Pasirink vieną ar kelias programas.'))

    def select_visible(self):
        self.selected.update(r['key'] for r in self.filtered()[:self.limit] if not r['protected'])
        self.rebuild_list()

    def clear_selection(self):
        self.selected.clear()
        self.rebuild_list()

    def rebuild_points(self):
        self.clear_box(self.points_list)
        ids = {p['id'] for p in self.point_items}
        if self.active_point_id not in ids:
            self.active_point_id = self.point_items[0]['id'] if self.point_items else None
        group = None
        for point in self.point_items:
            line = box(spacing=14, css='package-row')
            radio = Gtk.CheckButton()
            if group is None: group = radio
            else: radio.set_group(group)
            radio.set_active(point['id'] == self.active_point_id)
            radio.connect('toggled', self.point_selected, point['id'])
            line.append(radio)
            details = box(True, 5)
            details.set_hexpand(True)
            title = label(tr(point['name']) if point['id'] == 'initial-point' else point['name'], 'package-title')
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(50)
            details.append(title)
            try:
                created = dt.datetime.fromisoformat(point['created']).astimezone().strftime('%Y-%m-%d %H:%M')
            except ValueError: created = point['created']
            details.append(label(tr('{created}  ·  {count} paketų', created=created, count=point['count']), 'muted'))
            line.append(details)
            line.append(button(tr('Ištrinti tašką'), lambda _, p=point: self.delete_point(p), 'secondary'))
            self.points_list.append(line)
        if not self.point_items:
            self.points_list.append(label(tr('Dar nėra atkūrimo taškų. Sukurk pirmąjį aukščiau.'), 'empty', True))
        self.point_button.set_sensitive(bool(self.point_items))

    def delete_point(self, point):
        win, content = self.dialog(tr('Ištrinti atkūrimo tašką?'))
        content.append(label(point['name'], 'package-title', True))
        content.append(label(tr('Bus ištrintas tik išsaugotas paketų sąrašas. Įdiegtos programos nebus keičiamos.'), 'muted', True))
        actions = box(spacing=10)
        actions.append(button(tr('Atšaukti'), lambda _: win.close(), 'secondary'))
        def confirm(_):
            win.close()
            def work():
                backend('point-delete', extra=['--id', point['id']])
                return backend('points')
            def done(values):
                self.point_items = values
                self.rebuild_points()
                self.status.set_text(tr('Atkūrimo taškas ištrintas.'))
            self.run_job(work, done, tr('Atnaujinami taškai…'))
        actions.append(button(tr('Ištrinti tašką'), confirm, 'danger'))
        content.append(actions)
        win.present()

    def point_selected(self, radio, ident):
        if radio.get_active(): self.active_point_id = ident

    def create_point(self):
        name = self.point_name.get_text().strip() or tr('Švari sistema ') + dt.date.today().isoformat()
        def created(result):
            self.active_point_id = result['id']
            self.point_name.set_text('')
            self.status.set_text(tr('Išsaugotas naujas taškas: {count} paketų.', count=result['count']))
            self.run_job(lambda: backend('points'), self.points_loaded, tr('Atnaujinami taškai…'))
        self.run_job(lambda: backend('point-create', extra=['--name', name]), created, tr('Išsaugomas paketų sąrašas…'))

    def points_loaded(self, values):
        self.point_items = values
        self.rebuild_points()
        self.status.set_text(tr('Atkūrimo taškas išsaugotas. Programų failų kopijos nekurtos.'))

    def preview_remove(self):
        request = {'mode': 'remove', 'selected': sorted(self.selected),
                   'dependencies': self.dependencies.get_active(), 'clean_cache': False}
        self.run_job(lambda: (request, backend('preview', request)), self.show_plan, tr('Tikrinamas šalinimo planas…'))

    def preview_point(self):
        ident, clean = self.active_point_id, self.clean_cache.get_active()
        def work():
            point = backend('point-get', extra=['--id', ident])
            request = {'mode': 'point', 'point': point, 'clean_cache': clean}
            return request, backend('preview', request)
        self.run_job(work, self.show_plan, tr('Rengiamas valymo planas…'))

    def dialog(self, title, width=650, height=260):
        win = Gtk.Window(title=title, transient_for=self, modal=True, default_width=width, default_height=height)
        content = box(True, 16, 'dialog-content')
        win.set_child(content)
        content.append(label(title, 'section-title'))
        return win, content

    def show_about(self):
        win, content = self.dialog(tr('Apie programą'), 720, 660)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=260)
        body = box(True, 14)
        body.append(label('Linux fresh point', 'stat-value'))
        body.append(label(tr('Programos aprašymas'), 'section-title'))
        note = box(True, 8, 'info-card')
        note.append(label(tr('Dabartinės versijos galimybės'), 'package-title'))
        note.append(label(tr('Toliau pateikiamas siekiamo veikimo aprašymas. Ši versija remiasi tavo sukurtu paketų sąrašu: ji nenustato gamyklinės instaliacijos ar oficialių atnaujinimų kilmės, neatkuria trūkstamų programų ir nustatymų bei automatiškai netaiso paketų duomenų bazės. Konfigūracijų išsaugojimo parinkties dar nėra. Kitų valdiklių nei APT palaikymas eksperimentinis.'), 'muted', True))
        body.append(note)
        description = (HERE / 'descriptions' / (i18n.language() + '.md')).read_text()
        for block in description.split('\n\n'):
            block = block.strip()
            if not block: continue
            style = 'section-title' if block.startswith('#') else 'muted'
            if block.startswith('#'): block = block.lstrip('# ').strip()
            if block.startswith('> '): block = block[2:]
            block = '\n'.join('• ' + line[2:] if line.startswith('- ') else line for line in block.splitlines())
            paragraph = label('', style, True)
            escaped = GLib.markup_escape_text(block)
            paragraph.set_markup(re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped, flags=re.S))
            paragraph.set_selectable(True)
            body.append(paragraph)
        body.append(Gtk.LinkButton.new_with_label('https://www.gnu.org/', tr('GNU projektas')))
        body.append(label('GNU head — Etienne Suvasa · Simple Icons · CC BY-SA 2.0', 'muted', True))
        body.append(label(tr('Licencija') + ' — GNU GPL v3', 'section-title'))
        body.append(label(tr('Laisvoji programinė įranga pagal GNU GPL v3. Be garantijos. Pilnas licencijos tekstas pateikiamas kartu su programos kodu.'), 'muted', True))
        body.append(button(tr('Rodyti licenciją'), lambda _: self.show_message('GNU General Public License v3', (HERE / 'LICENSE').read_text(), parent=win), 'secondary'))
        body.append(label(tr('Parama savanoriška. Gavėjas: grygas@gmail.com.'), 'muted', True))
        scroll.set_child(body)
        content.append(scroll)
        donate = Gtk.LinkButton.new_with_label(SEND_MONEY_URL, tr('Paremti per PayPal'))
        donate.add_css_class('primary')
        content.append(donate)
        content.append(button(tr('Uždaryti'), lambda _: win.close(), 'secondary'))
        win.present()

    def show_message(self, title, message, parent=None):
        win, content = self.dialog(title)
        if parent is not None: win.set_transient_for(parent)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=100, max_content_height=380)
        scroll.set_child(label(message, 'muted', True))
        content.append(scroll)
        content.append(button(tr('Uždaryti'), lambda _: win.close(), 'secondary'))
        win.present()

    def show_plan(self, result):
        request, plan = result
        self.status.set_text(tr('Planas paruoštas. Sistema dar nepakeista.'))
        if not plan['removed'] and not plan['clean_cache']:
            self.show_message(tr('Nėra ką šalinti'), tr('Pagal šį pasirinkimą papildomų šalintinų paketų nėra.'))
            return
        win, content = self.dialog(tr('Peržiūrėk pakeitimus'), 700, 580)
        content.append(label(tr('{count} paketų  ·  apie {size}', count=len(plan['removed']), size=size_text(plan['bytes'])), 'stat-value'))
        content.append(label(tr('Bus pašalinti toliau išvardyti paketai. Konfigūracijos šalinimas priklauso nuo paketų valdiklio. '
                             'Paketo pašalinimo scenarijai gali pašalinti ir jo paslaugos duomenis.'), 'muted', True))
        text = '\n'.join(f'{r["package"]}  —  {tr(r["reason"])}' for r in plan['rows']) or tr('Papildomų šalintinų paketų nėra.')
        if plan['missing']:
            text += tr('\n\nTaško paketai, kurių dabar nėra (nebus įdiegti iš naujo):\n') + '\n'.join(plan['missing'])
        if plan.get('native'):
            text += '\n\n' + tr('Galutinį paketų valdiklio planą reikės patvirtinti terminale.')
            text += '\n\n' + plan.get('native_output', '')
        view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(text)
        view.add_css_class('plan-text')
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(view)
        content.append(scroll)
        if plan['clean_cache']:
            content.append(label(tr('Taip pat bus išvalytas APT atsisiuntimų podėlis.'), 'muted', True))
        actions = box(spacing=10)
        actions.set_halign(Gtk.Align.END)
        actions.append(button(tr('Atšaukti'), lambda _: win.close(), 'secondary'))
        def confirm(_):
            win.close()
            payload = {'request': request, 'hash': plan['hash']}
            self.run_job(lambda: terminal_apply.launch(payload) if plan.get('native') else backend('apply', payload, privileged=True),
                         self.applied, tr('Laukiama administratoriaus patvirtinimo / vykdomas šalinimas…'))
        actions.append(button(tr('Patvirtinti valymą') if plan['mode'] == 'point' else tr('Pašalinti pasirinktus paketus'), confirm, 'danger'))
        content.append(actions)
        win.present()

    def applied(self, result):
        self.selected.clear()
        self.show_message(tr('Valymas baigtas'), tr('Pašalinta paketų: {count}.\nŽurnalas: {log}', count=result['removed'], log=result['log']))
        self.refresh()

    def smoke_check(self):
        assert self.items and self.list.get_first_child()
        self.navigate('packages')
        self.search.set_text('python3')
        self.rebuild_list()
        assert self.filtered()
        self.navigate('points')
        assert self.points_list.get_first_child()
        self.search.set_text('')
        self.navigate('apps')
        print(json.dumps({'gtk_smoke': 'passed', 'items': len(self.items), 'points': len(self.point_items)}), flush=True)
        self.get_application().quit()
        return False


class App(Gtk.Application):
    def __init__(self, smoke=False):
        super().__init__(application_id='lt.local.LinuxTvarka', flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.smoke = smoke

    def do_activate(self):
        settings = Gtk.Settings.get_default()
        settings.set_property('gtk-application-prefer-dark-theme', False)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(HERE / 'style.css'))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Window(self, self.smoke).present()


if __name__ == '__main__':
    if os.geteuid() == 0:
        sys.exit(tr('Grafinę programą paleiskite be sudo. Teisių ji paprašys tik šalinant.'))
    if not Gdk.Display.get_default():
        sys.exit(tr('Nėra ryšio su grafine sesija. Paleiskite programą savo Linux darbalaukio terminale.'))
    smoke = '--smoke' in sys.argv
    App(smoke).run([sys.argv[0]])
