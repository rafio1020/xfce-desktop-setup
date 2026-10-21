An SGI workstation theme for Xfce, Gnome, MATE, Cinnamon, LXDE, etc. Introducing IndigoMagic GTK+ 2/3 widgets and icon theme pack!

To install, extract into /usr/share/themes and copy or link to ~/.themes then enable as user AND root in Xfce:

Settings>Appearance>Style>>Icons>>Fonts>>Settings
Settings>Mouse and Touchpad>Theme
Settings>Window Manager>Style
Settings>Desktop>Background
Settings>Session and Startup>Add>Sound
Panel Preferences>Appearance>Background
Applications Menu>Properties>Icon

To enabe bitmap fonts: sudo rm /etc/fonts/conf.d/70-no-bitmaps.conf
then extract into /usr/share/fonts and run: sudo fc-cache -fv

To enabe QT5 theme: sudo apt install qt5-style-plugins
then add to ~/.profile: export QT_QPA_PLATFORMTHEME=gtk2

To install Plank theme: extract into ~/.local/share/plank/themes/folder
plank --preferences to select it, then drop in your desktop shortcuts.

To install system monitor with tray icon:
1. sudo apt install xosview kdocker
2. Settings>Session and Startup>Add>xosview
and enter: kdocker -i iconfile.png -n gr_osview xosview
3. Then copy included template to ~/.Xdefaults

To install Plymouth theme:
1. mv sgi /usr/share/plymouth/themes
2. sudo plymouth-set-default-theme -R sgi
3. cd /usr/share/plymouth/themes/sgi
4. mv sgi.script startup.script
5. mv shutdown.script sgi.script

* Icons are in size 48px only (50 in Plank) which excludes the vector set but includes elementary-xfce as a base. Check back later for updates.