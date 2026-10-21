#!/usr/bin/env python3
"""Apply the bundled wallpaper to the destination's XFCE monitor properties once."""
import shutil
from pathlib import Path
import subprocess
import time


def run(*args):
    return subprocess.run(args, text=True, capture_output=True, timeout=10)


def main():
    home = Path.home()
    marker = home / '.local/share/xfce-desktop-setup/wallpaper-pending'
    if not marker.exists():
        return
    wallpaper = home / '.local/share/xfce-desktop-setup/wallpapers/Sprinkle.png'
    # xfdesktop creates monitor properties during session startup.
    for _ in range(30):
        result = run('xfconf-query', '-c', 'xfce4-desktop', '-l')
        properties = result.stdout.splitlines()
        bases = sorted({p.rsplit('/', 1)[0] for p in properties
                        if p.startswith('/backdrop/') and '/workspace' in p})
        if bases:
            break
        time.sleep(1)
    else:
        # A fresh profile may not have stored any backdrop properties yet.
        # XFCE 4.20 on X11 names its monitor nodes after RandR connectors.
        bases = []
        if shutil.which('xrandr'):
            monitors = run('xrandr', '--listmonitors')
            names = [line.split()[-1] for line in monitors.stdout.splitlines()[1:] if line.split()]
            bases = [f'/backdrop/screen0/monitor{name}/workspace{workspace}'
                     for name in names for workspace in range(4)]
        if not bases:
            print('No XFCE monitors yet. Wallpaper will retry at the next login.')
            return
    success = True
    for base in bases:
        for name, kind, value in [('last-image', 'string', str(wallpaper)),
                                  ('image-style', 'int', '2'),
                                  ('backdrop-cycle-enable', 'bool', 'false')]:
            prop = base + '/' + name
            args = ['xfconf-query', '-c', 'xfce4-desktop', '-p', prop, '-s', value]
            if prop not in properties:
                args += ['--create', '-t', kind]
            result = run(*args)
            if result.returncode:
                success = False
                print(result.stderr)
    if success:
        marker.unlink(missing_ok=True)
        print('IndigoMagic wallpaper applied.')


if __name__ == '__main__':
    main()
