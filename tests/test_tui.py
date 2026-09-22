import unittest
from unittest.mock import Mock, patch

try:
    import tui
except ModuleNotFoundError as exc:
    if exc.name != '_curses':
        raise
    tui = None


@unittest.skipIf(tui is None, 'curses is provided by the target Linux runtime')
class TuiTests(unittest.TestCase):
    @patch('tui.curses.curs_set')
    def test_arrow_navigation_opens_selected_menu_and_wraps(self, _cursor):
        screen = Mock()
        screen.getch.side_effect = [tui.curses.KEY_DOWN, 10, tui.curses.KEY_UP,
                                   tui.curses.KEY_UP, tui.curses.KEY_ENTER, ord('q')]
        ui = tui.TerminalUI(screen)
        ui.data = {'system': {'pretty': 'Test Linux', 'manager': 'apt'}}
        ui.load = Mock()
        ui.frame = Mock()
        ui.write = Mock()
        ui.package_browser = Mock()
        ui.about = Mock()
        ui.run()
        ui.package_browser.assert_called_once_with(False)
        ui.about.assert_called_once_with()

    @patch('tui.os.geteuid', return_value=0, create=True)
    @patch('tui.sys.stdin.isatty', return_value=True)
    @patch('tui.sys.stdout.isatty', return_value=True)
    @patch('tui.configure_portable')
    @patch('tui.curses.wrapper')
    def test_root_can_start_terminal_interface(self, wrapper, portable, _stdout, _stdin, _uid):
        tui.main()
        portable.assert_called_once_with()
        wrapper.assert_called_once()

    @patch('tui.os.geteuid', return_value=0, create=True)
    @patch('tui.shutil.which')
    @patch('tui.subprocess.run')
    def test_root_apply_does_not_require_sudo(self, run, which, _uid):
        run.return_value.returncode = 0
        run.return_value.stdout = '{"ok": true, "data": {"removed": 1}}'
        run.return_value.stderr = ''
        payload = {'request': {'mode': 'remove', 'selected': ['example']}, 'hash': 'reviewed-plan'}
        self.assertEqual(tui.backend('apply', payload, privileged=True), {'removed': 1})
        which.assert_not_called()
        self.assertEqual(run.call_args.args[0], ['/usr/bin/python3', '-I', str(tui.HERE / 'backend.py'), 'apply'])

    def test_size_text(self):
        self.assertEqual(tui.size_text(25_000_000), '25.0 MB')
        self.assertEqual(tui.size_text(2_500_000_000), '2.5 GB')

    def test_clip(self):
        self.assertEqual(tui.clip('abcdef', 4), 'abc…')
        self.assertEqual(tui.clip('ab\ncd', 10), 'ab cd')

    @patch('tui.subprocess.run')
    @patch('tui.os.geteuid', return_value=1000, create=True)
    @patch('tui.shutil.which', side_effect=lambda name: '/usr/bin/sudo' if name == 'sudo' else None)
    def test_privileged_backend_uses_terminal_sudo(self, _which, _geteuid, run):
        run.return_value.returncode = 0
        run.return_value.stdout = '{"ok": true, "data": {"removed": 1}}'
        run.return_value.stderr = ''
        self.assertEqual(tui.backend('apply', {'hash': 'x'}, privileged=True), {'removed': 1})
        self.assertEqual(run.call_args.args[0][0], '/usr/bin/sudo')


if __name__ == '__main__':
    unittest.main()
