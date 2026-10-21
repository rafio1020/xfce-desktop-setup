import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup', ROOT / 'scripts/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.root = Path(cls.storage.name)
        cls.stage = cls.root / 'stage'
        cls.stage.mkdir()
        cls.source = cls.root / 'source'
        cls.source.mkdir()
        settings = cls.source / setup.CHANNEL_DIR / 'xsettings.xml'
        settings.parent.mkdir(parents=True)
        settings.write_text('<channel name="xsettings"><property name="Xft" type="empty"><property name="DPI" type="int" value="144"/></property></channel>')
        with patch.object(setup, 'app_command', side_effect=lambda candidates, flatpak_id=None, fallback=None: fallback):
            setup.prepare(cls.stage, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def new_home(self):
        return Path(tempfile.mkdtemp(dir=self.root))

    def test_assets_and_portable_config(self):
        for relative in setup.TARGETS:
            self.assertTrue(setup.exists(self.stage / relative), relative)
        for path in self.stage.rglob('*'):
            if path.is_symlink():
                self.assertTrue(path.exists(), str(path))
                self.assertTrue(path.resolve().is_relative_to(self.stage))
        for file in (self.stage / setup.CHANNEL_DIR).glob('*.xml'):
            ET.parse(file)
            self.assertNotIn('/home/rafio', file.read_text())
        settings = ET.parse(self.stage / setup.CHANNEL_DIR / 'xsettings.xml')
        self.assertEqual(settings.find("./property[@name='Xft']/property[@name='DPI']").get('value'), '144')
        panel = (self.stage / setup.CHANNEL_DIR / 'xfce4-panel.xml').read_text()
        self.assertNotIn('known-legacy-items', panel)
        self.assertNotIn('background-image', panel)
        self.assertEqual(ET.fromstring(panel).findall("./property[@name='panels']/value")[0].get('value'), '1')

    def test_install_restore_preserves_unrelated_files(self):
        home = self.new_home()
        css = home / '.config/gtk-3.0/gtk.css'
        css.parent.mkdir(parents=True)
        css.write_text('my previous CSS')
        unrelated = home / '.config/gtk-3.0/bookmarks'
        unrelated.write_text('private bookmarks')
        backup = setup.apply(home, self.stage, home / 'backups')
        self.assertNotEqual(css.read_text(), 'my previous CSS')
        self.assertTrue((home / '.themes/IndigoMagic').exists())
        setup.restore(home, backup)
        self.assertEqual(css.read_text(), 'my previous CSS')
        self.assertEqual(unrelated.read_text(), 'private bookmarks')
        self.assertFalse((home / '.themes/IndigoMagic').exists())

    def test_failed_apply_rolls_back(self):
        home = self.new_home()
        old = home / setup.CHANNEL_DIR / 'xsettings.xml'
        old.parent.mkdir(parents=True)
        old.write_text('original')
        original_copy = setup.copy
        failed = False
        def failing_copy(src, dst):
            nonlocal failed
            if src == self.stage / '.config/gtk-3.0/gtk.css' and not failed:
                failed = True
                raise OSError('simulated disk failure')
            return original_copy(src, dst)
        with patch.object(setup, 'copy', side_effect=failing_copy):
            with self.assertRaisesRegex(OSError, 'simulated'):
                setup.apply(home, self.stage, home / 'backups')
        self.assertEqual(old.read_text(), 'original')
        self.assertFalse((home / '.config/xfce4/panel').exists())

    def test_symlink_parent_rejected_before_backup(self):
        home = self.new_home()
        outside = self.new_home()
        (home / '.config').symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, 'Symlinked parent'):
            setup.apply(home, self.stage, home / 'backups')
        self.assertFalse((home / 'backups').exists())

    def test_existing_leaf_symlink_restored(self):
        home = self.new_home()
        target = home / 'old.css'
        target.write_text('untouched')
        css = home / '.config/gtk-3.0/gtk.css'
        css.parent.mkdir(parents=True)
        css.symlink_to(target)
        backup = setup.apply(home, self.stage, home / 'backups')
        self.assertFalse(css.is_symlink())
        self.assertEqual(target.read_text(), 'untouched')
        setup.restore(home, backup)
        self.assertTrue(css.is_symlink())

    def test_dry_run_does_not_write(self):
        home = self.new_home()
        result = subprocess.run([sys.executable, str(ROOT/'scripts/setup.py'), '--dry-run'],
                                env={**os.environ, 'HOME': str(home)}, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(home.iterdir()), [])

    def test_running_xfce_rejected(self):
        with patch.object(setup.os, 'geteuid', return_value=1000), patch.object(setup.shutil, 'which', return_value='/usr/bin/pgrep'), patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaisesRegex(RuntimeError, 'Log out of XFCE'):
                setup.require_offline()

    def test_tampered_asset_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo/'assets').mkdir()
            (repo/'assets/SHA256SUMS').write_text('0'*64+'  indigomagic.tar.gz\n')
            (repo/'assets/indigomagic.tar.gz').write_bytes(b'broken')
            with patch.object(setup, 'REPO', repo):
                with self.assertRaisesRegex(RuntimeError, 'checksum'):
                    setup.extract_assets(repo/'stage')

    def test_backup_from_different_user_rejected(self):
        home = self.new_home()
        backup = setup.backup(home, home/'backups')
        with self.assertRaisesRegex(RuntimeError, 'does not match'):
            setup.restore(self.new_home(), backup)

    def test_desktop_exec_escapes_special_characters(self):
        self.assertEqual(setup.desktop_quote('/home/a b%/file'), '"/home/a b%%/file"')


if __name__ == '__main__':
    unittest.main()
