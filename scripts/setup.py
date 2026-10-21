#!/usr/bin/env python3
"""Offline, per-user XFCE setup with scoped backups and rollback. Python 3.10+."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
CHANNEL_DIR = '.config/xfce4/xfconf/xfce-perchannel-xml'
CHANNELS = ['xsettings', 'xfwm4', 'xfce4-panel', 'xfce4-desktop', 'xfce4-keyboard-shortcuts']
TARGETS = [f'{CHANNEL_DIR}/{c}.xml' for c in CHANNELS] + [
    '.config/xfce4/panel', '.config/gtk-3.0/gtk.css',
    '.themes/IndigoMagic', '.icons/sgi-elementary-xfce', '.icons/redSGI',
    '.icons/IndigoMagic-Panel', '.local/share/fonts/indigomagic',
    '.local/share/xfce-desktop-setup', '.config/autostart/xfce-desktop-setup.desktop',
    '.config/fontconfig/conf.d/99-indigo-screen-font.conf',
]


def exists(path):
    return path.exists() or path.is_symlink()


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def validate_parents(home, relative_paths):
    for relative in relative_paths:
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise RuntimeError(f'Unsafe target: {relative}')
        for parent in path.parents:
            if (home / parent).is_symlink():
                raise RuntimeError(f'Symlinked parent needs manual installation: {home / parent}')


def require_offline():
    if os.geteuid() == 0:
        raise RuntimeError('Run as your normal desktop user, without sudo.')
    if not shutil.which('pgrep'):
        raise RuntimeError('Install procps/procps-ng first; required to check XFCE processes.')
    for process in ['xfce4-session', 'xfce4-panel', 'xfconfd', 'xfdesktop']:
        result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', process],
                                stdout=subprocess.DEVNULL)
        if result.returncode == 0:
            raise RuntimeError('Log out of XFCE completely, press Ctrl+Alt+F3, sign in, and rerun this command. '
                               f'{process} is still running; no settings were changed.')
        if result.returncode != 1:
            raise RuntimeError('Could not verify that XFCE is stopped.')
    for key, expected in [('XDG_CONFIG_HOME', Path.home()/'.config'),
                          ('XDG_DATA_HOME', Path.home()/'.local/share')]:
        if os.environ.get(key) and Path(os.environ[key]) != expected:
            raise RuntimeError(f'Custom {key} requires manual installation; see README.')


def extract_assets(destination):
    archive = REPO / 'assets/indigomagic.tar.gz'
    expected = (REPO / 'assets/SHA256SUMS').read_text().split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Asset checksum mismatch; get a clean copy of the repository.')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        # Validate the complete archive before writing; directories/files then internal symlinks.
        symlinks = {m.name for m in members if m.issym()}
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isdir() or member.isfile() or member.issym()):
                raise RuntimeError(f'Unsafe archive member: {member.name}')
            if any(str(p) in symlinks for p in path.parents):
                raise RuntimeError('Archive contains a symlink parent.')
            if member.issym():
                target = destination / path.parent / member.linkname
                if Path(member.linkname).is_absolute() or not target.resolve().is_relative_to(destination.resolve()):
                    raise RuntimeError(f'Unsafe archive symlink: {member.name}')
        for member in members:
            out = destination / member.name
            if member.isdir():
                out.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                out.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, out.open('wb') as target:
                    shutil.copyfileobj(source, target)
                out.chmod(0o644)
        for member in members:
            if member.issym():
                out = destination / member.name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.symlink_to(member.linkname)


def desktop_quote(value):
    # Desktop Entry Exec has its own quoting, distinct from shell quoting.
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def app_command(candidates, flatpak_id=None, fallback=None):
    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
    if flatpak_id and shutil.which('flatpak'):
        found = subprocess.run(['flatpak', 'info', flatpak_id], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=15)
        if found.returncode == 0:
            return f'flatpak run {flatpak_id}'
    return fallback


def prepare(stage, home, dpi=None):
    extract_assets(stage)
    for channel in CHANNELS:
        target = stage / CHANNEL_DIR / f'{channel}.xml'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / 'config/xfce4' / f'{channel}.xml', target)
    # Retain the destination's DPI unless an explicit value is requested.
    xsettings = stage / CHANNEL_DIR / 'xsettings.xml'
    tree = ET.parse(xsettings)
    if dpi is None:
        original = home / CHANNEL_DIR / 'xsettings.xml'
        if original.exists():
            node = ET.parse(original).find("./property[@name='Xft']/property[@name='DPI']")
            if node is not None and node.get('value'):
                dpi = int(node.get('value'))
    if dpi is not None:
        group = tree.find("./property[@name='Xft']")
        ET.SubElement(group, 'property', name='DPI', type='int', value=str(dpi))
    ET.indent(tree); tree.write(xsettings, encoding='UTF-8', xml_declaration=True)
    css = stage / '.config/gtk-3.0/gtk.css'; css.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / 'config/gtk-3.0/gtk.css', css)
    browser = 'exo-open --launch WebBrowser'
    launchers = [
        (11, '17925314092.desktop', 'Web Browser', app_command(['google-chrome-stable','google-chrome','chromium','chromium-browser'], fallback=browser), 'web-browser'),
        (4, '17925314001.desktop', 'ChatGPT', app_command(['chatgpt'], fallback='exo-open https://chatgpt.com'), 'applications-internet'),
        (12, '17925314223.desktop', 'Code Editor', app_command(['code','code-oss','codium'], 'com.visualstudio.code', 'exo-open --launch FileManager'), 'accessories-text-editor'),
        (14, '17925316835.desktop', 'Terminal', app_command(['gnome-terminal','xfce4-terminal'], fallback='exo-open --launch TerminalEmulator'), 'utilities-terminal'),
        (13, '17925314344.desktop', 'Brave / Web Browser', app_command(['brave-browser','brave'], 'com.brave.Browser', browser), 'web-browser'),
    ]
    for plugin, filename, label, command, icon in launchers:
        path = stage / f'.config/xfce4/panel/launcher-{plugin}' / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        # Retain the application icons when the corresponding application is installed.
        if command.startswith('google-chrome'): icon = 'google-chrome'
        elif command == 'chatgpt': icon = 'chatgpt'
        elif command in ['code','code-oss','codium']: icon = command
        elif 'com.visualstudio.code' in command: icon = 'com.visualstudio.code'
        elif 'brave' in command.lower(): icon = 'com.brave.Browser' if 'flatpak' in command else 'brave-browser'
        path.write_text(f'[Desktop Entry]\nType=Application\nName={label}\nExec={command}\nIcon={icon}\nTerminal=false\nStartupNotify=true\n')
    data = stage / '.local/share/xfce-desktop-setup'
    shutil.copy2(REPO / 'scripts/first-login.py', data / 'first-login.py')
    (data / 'wallpaper-pending').touch()
    autostart = stage / '.config/autostart/xfce-desktop-setup.desktop'
    autostart.parent.mkdir(parents=True, exist_ok=True)
    helper = home / '.local/share/xfce-desktop-setup/first-login.py'
    autostart.write_text('[Desktop Entry]\nType=Application\nName=IndigoMagic wallpaper setup\n'
                         f'Exec=python3 {desktop_quote(helper)}\nOnlyShowIn=XFCE;\nTerminal=false\n')
    fontconfig = stage / '.config/fontconfig/conf.d/99-indigo-screen-font.conf'
    fontconfig.parent.mkdir(parents=True, exist_ok=True)
    fontconfig.write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
        '<fontconfig><selectfont><acceptfont><pattern><patelt name="family">'
        '<string>Screen</string></patelt></pattern></acceptfont></selectfont></fontconfig>\n')


def backup(home, root):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=root))
    present = []
    for relative in TARGETS:
        if exists(home / relative):
            copy(home / relative, directory / 'files' / relative)
            present.append(relative)
    manifest = {'version': 1, 'home': str(home.resolve()), 'targets': TARGETS, 'present': present}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return directory


def restore(home, directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('version') != 1 or manifest.get('targets') != TARGETS or manifest.get('home') != str(home.resolve()):
        raise RuntimeError('This backup does not match this user or setup version.')
    present = manifest['present']
    if not isinstance(present, list) or not set(present).issubset(TARGETS):
        raise RuntimeError('Invalid backup manifest.')
    for relative in present:
        if not exists(directory / 'files' / relative):
            raise RuntimeError(f'Incomplete backup: {relative}')
    validate_parents(home, TARGETS)
    for relative in TARGETS:
        remove(home / relative)
        if relative in present:
            copy(directory / 'files' / relative, home / relative)


def apply(home, stage, backups):
    validate_parents(home, TARGETS)
    for relative in TARGETS:
        if not exists(stage / relative):
            raise RuntimeError(f'Incomplete staged installation: {relative}')
    directory = backup(home, backups)
    print(f'Backup: {directory}', flush=True)
    try:
        for relative in TARGETS:
            remove(home / relative)
            copy(stage / relative, home / relative)
    except BaseException:
        restore(home, directory)
        raise
    return directory


def refresh_caches(home):
    if shutil.which('fc-cache'):
        subprocess.run(['fc-cache', '-f'], check=False)
    if shutil.which('gtk-update-icon-cache'):
        for name in ['sgi-elementary-xfce', 'IndigoMagic-Panel']:
            directory = home / '.icons' / name
            if directory.exists():
                subprocess.run(['gtk-update-icon-cache', '-f', '-t', str(directory)], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true', help='apply from a text console after logging out of XFCE')
    mode.add_argument('--restore', type=Path, metavar='BACKUP', help='restore a backup while logged out of XFCE')
    mode.add_argument('--dry-run', action='store_true', help='preview without writing settings (default)')
    parser.add_argument('--dpi', type=int, help='explicit font DPI; source desktop uses 112')
    args = parser.parse_args()
    if args.dpi is not None and not 48 <= args.dpi <= 384:
        parser.error('--dpi must be between 48 and 384')
    home = Path.home().resolve()
    if not args.apply and not args.restore:
        print('Preview only. No settings or packages changed.\nTargets:')
        for relative in TARGETS: print('  ' + str(home / relative))
        print('\n1. ./install.sh --packages\n2. Log out of XFCE; Ctrl+Alt+F3; sign in.\n3. ./install.sh --apply\nSee README.md for details.')
        return
    require_offline()
    if args.apply and platform.machine().lower() not in ['x86_64','amd64','i386','i486','i586','i686','ia64']:
        raise RuntimeError('The bundled redSGI cursor license limits supported architectures; see licenses/redSGI-MaXX.txt.')
    state = home / '.local/state/xfce-desktop-setup'
    validate_parents(home, TARGETS + ['.local/state/xfce-desktop-setup/lock'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.restore:
            restore(home, args.restore.expanduser().resolve())
            print('Restored the recorded files. Packages remain installed. Log back into XFCE.')
        else:
            with tempfile.TemporaryDirectory(prefix='indigomagic-') as temporary:
                stage = Path(temporary)
                prepare(stage, home, args.dpi)
                directory = apply(home, stage, state / 'backups')
            print('Setup installed. Log into the XFCE / X11 session. Wallpaper applies at first login.')
            print('To undo (while logged out): ./install.sh --restore ' + shlex.quote(str(directory)))
        refresh_caches(home)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError, subprocess.SubprocessError, tarfile.TarError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
