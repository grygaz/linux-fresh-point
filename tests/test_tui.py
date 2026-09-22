import unittest
from unittest.mock import patch

try:
    import tui
except ModuleNotFoundError as exc:
    if exc.name != '_curses':
        raise
    tui = None


@unittest.skipIf(tui is None, 'curses is provided by the target Linux runtime')
class TuiTests(unittest.TestCase):
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
