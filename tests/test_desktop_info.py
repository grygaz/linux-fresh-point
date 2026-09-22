import tempfile
import unittest
from pathlib import Path

import desktop_info


class DesktopInfoTests(unittest.TestCase):
    def test_reads_visible_application_and_skips_hidden_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'visible.desktop').write_text(
                '[Desktop Entry]\nType=Application\nName=Example\nComment=Example app\nIcon=example\n',
                encoding='utf-8',
            )
            (root / 'hidden.desktop').write_text(
                '[Desktop Entry]\nType=Application\nName=Hidden\nNoDisplay=true\n',
                encoding='utf-8',
            )
            self.assertEqual(desktop_info.entries([root]), [{
                'path': str(root / 'visible.desktop'), 'title': 'Example',
                'description': 'Example app', 'icon': 'example',
            }])


if __name__ == '__main__':
    unittest.main()
