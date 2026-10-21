import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PackageTests(unittest.TestCase):
    def preview(self, distro, like):
        with tempfile.TemporaryDirectory() as folder:
            fake_sed = Path(folder)/'sed'
            fake_sed.write_text('#!/bin/sh\ncase "$2" in\n *ID_LIKE*) printf "%s\\n" "$TEST_OS_LIKE" ;;\n *) printf "%s\\n" "$TEST_OS_ID" ;;\nesac\n')
            fake_sed.chmod(0o755)
            result = subprocess.run(['bash', str(ROOT/'scripts/packages.sh'), '--dry-run'],
                env={**os.environ, 'PATH': folder+os.pathsep+os.environ['PATH'],
                     'TEST_OS_ID': distro, 'TEST_OS_LIKE': like}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

    def test_fedora(self):
        output = self.preview('fedora', '')
        self.assertIn('sudo dnf install', output)
        self.assertIn('Thunar', output)
        self.assertIn('xorg-x11-server-Xorg', output)

    def test_ubuntu(self):
        output = self.preview('ubuntu', 'debian')
        self.assertIn('sudo apt-get update', output)
        self.assertIn('sudo apt-get install', output)
        self.assertIn('xfce4-whiskermenu-plugin', output)

    def test_cachyos(self):
        output = self.preview('cachyos', 'arch')
        self.assertIn('sudo pacman -Syu --needed', output)
        self.assertIn('xorg-server', output)
        self.assertIn(' thunar ', output)

if __name__ == '__main__':
    unittest.main()
