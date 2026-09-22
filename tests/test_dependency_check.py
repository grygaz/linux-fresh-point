import unittest
from unittest.mock import patch

import dependency_check as dc


class DependencyCheckTests(unittest.TestCase):
    def test_apt_packages_are_deduplicated_in_check_order(self):
        self.assertEqual(
            dc.packages_for('apt', ['gi', 'Gtk', 'GdkPixbuf', 'apt', 'Gtk']),
            ['python3-gi', 'gir1.2-gtk-4.0', 'gir1.2-gdkpixbuf-2.0', 'python3-apt'],
        )

    def test_builds_native_install_commands(self):
        self.assertEqual(
            dc.install_command('apt', '/usr/bin/apt-get', ['python3-gi']),
            ['/usr/bin/apt-get', 'install', '-y', 'python3-gi'],
        )
        self.assertEqual(
            dc.install_command('pacman', '/usr/bin/pacman', ['gtk4']),
            ['/usr/bin/pacman', '-S', '--needed', '--noconfirm', 'gtk4'],
        )

    @patch('dependency_check.os.geteuid', return_value=0, create=True)
    def test_root_does_not_add_privilege_helper(self, _geteuid):
        command = ['/usr/bin/dnf', 'install', '-y', 'gtk4']
        self.assertEqual(dc.elevate(command), command)

    @patch.object(dc.shutil, 'which', side_effect=lambda name: '/usr/bin/pkexec' if name == 'pkexec' else None)
    @patch('dependency_check.os.geteuid', return_value=1000, create=True)
    def test_regular_user_prefers_pkexec(self, _geteuid, _which):
        self.assertEqual(dc.elevate(['apt-get', 'install']), ['/usr/bin/pkexec', 'apt-get', 'install'])


if __name__ == '__main__':
    unittest.main()
