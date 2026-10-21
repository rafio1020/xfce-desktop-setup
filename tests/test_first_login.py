import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('first_login', Path(__file__).resolve().parents[1]/'scripts/first-login.py')
first_login = importlib.util.module_from_spec(spec)
spec.loader.exec_module(first_login)

class WallpaperTests(unittest.TestCase):
    def test_destination_monitor_names_and_one_shot_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            marker = home/'.local/share/xfce-desktop-setup/wallpaper-pending'
            marker.parent.mkdir(parents=True); marker.touch()
            props = '/backdrop/screen0/monitorHDMI-2/workspace0/last-image\n/backdrop/screen0/monitorDP-1/workspace0/image-style\n'
            def fake_run(*args):
                return subprocess.CompletedProcess(args, 0, props if '-l' in args else '', '')
            with patch.object(first_login.Path, 'home', return_value=home), patch.object(first_login, 'run', side_effect=fake_run) as run:
                first_login.main()
                self.assertFalse(marker.exists())
                calls = [call.args for call in run.call_args_list]
                self.assertTrue(any('/backdrop/screen0/monitorHDMI-2/workspace0/last-image' in c for c in calls))
                self.assertTrue(any('/backdrop/screen0/monitorDP-1/workspace0/last-image' in c and '--create' in c for c in calls))
                first_login.main()
                self.assertEqual(run.call_count, 7)

    def test_fresh_profile_uses_randr_monitor_names(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            marker = home/'.local/share/xfce-desktop-setup/wallpaper-pending'
            marker.parent.mkdir(parents=True); marker.touch()
            def fake_run(*args):
                output = 'Monitors: 1\n 0: +*DP-2 1920/510x1080/290+0+0 DP-2\n' if args[0] == 'xrandr' else ''
                return subprocess.CompletedProcess(args, 0, output, '')
            with patch.object(first_login.Path, 'home', return_value=home), patch.object(first_login, 'run', side_effect=fake_run) as run, patch.object(first_login.time, 'sleep'), patch.object(first_login.shutil, 'which', return_value='/usr/bin/xrandr'):
                first_login.main()
                self.assertFalse(marker.exists())
                self.assertTrue(any('/backdrop/screen0/monitorDP-2/workspace3/last-image' in c.args for c in run.call_args_list))

    def test_failure_keeps_retry_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            marker = home/'.local/share/xfce-desktop-setup/wallpaper-pending'
            marker.parent.mkdir(parents=True); marker.touch()
            def fake_run(*args):
                return subprocess.CompletedProcess(args, 0 if '-l' in args else 1, '/backdrop/screen0/monitorDP-1/workspace0/last-image\n', '')
            with patch.object(first_login.Path, 'home', return_value=home), patch.object(first_login, 'run', side_effect=fake_run):
                first_login.main()
            self.assertTrue(marker.exists())

if __name__ == '__main__':
    unittest.main()
