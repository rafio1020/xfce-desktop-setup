# Third-party assets and changes

The asset archive is a snapshot of the theme files used by the source Fedora desktop on 2026-10-21. It contains source CSS, SVG/PNG icons, XFWM4 images, bitmap fonts, cursor files, and wallpaper rather than proprietary application binaries. Asset paths below are relative to the archive root.

| Component | Origin / terms | Local changes |
| --- | --- | --- |
| `.themes/IndigoMagic/gtk-3.0` | [IndigoMagic theme pack](https://www.xfce-look.org/p/1371886/), listed as GPLv3; CSS credits Dave Maldonado and OneStepBack | Captured installed CSS, including local desktop-selection styling; old backup files omitted |
| `.themes/IndigoMagic/xfwm4` | SGI (4Dwm) XFCE theme by John Tsiombikas, 2006 | Original README and redistribution notice retained in the theme and [licenses/xfwm4-SGI.txt](licenses/xfwm4-SGI.txt) |
| `.icons/sgi-elementary-xfce` | SGI variant from the IndigoMagic pack, based on [elementary-xfce](https://github.com/shimmerproject/elementary-xfce) | Captured installed theme; icon cache omitted; original README retained |
| `.icons/IndigoMagic-Panel` | Local custom panel/status icon overlay inheriting `sgi-elementary-xfce` | Captured SVGs and relative symlinks; generated cache omitted |
| `.icons/redSGI` | Cursor set from the IndigoMagic pack with MaXX license | [Original license](licenses/redSGI-MaXX.txt) retained intact, also inside the archive; permitted deployment architectures are limited by that license |
| `.local/share/fonts/indigomagic` | SGI bitmap fonts distributed with the IndigoMagic pack | Captured PCF fonts; generated font directory/cache files omitted |
| `.local/share/xfce-desktop-setup/wallpapers/Sprinkle.png` | Wallpaper distributed with the IndigoMagic pack | Original image copied without editing |

The pack's original installation notes are preserved in [assets/UPSTREAM-README.txt](assets/UPSTREAM-README.txt) for attribution and provenance. They are historical upstream notes, **not this repository's installation procedure**; follow the main README and installer here.

[GPL-3.0 text](licenses/GPL-3.0.txt) is provided for the GPL-licensed portions. Component-specific notices take precedence over the repository's license. The GPL label on the upstream pack does not replace the separately included MaXX and XFWM4 notices.

Portable configuration changes made on 2026-10-21:

- Removed tray history, recent menu entries, inactive paths into Downloads, and source-monitor wallpaper bindings.
- Kept a single bottom panel and regenerated launchers for applications detected on the destination PC.
- Kept the current GTK CSS overrides and visual settings; excluded unrelated app state, sessions, and hardware configuration.
- Made font DPI optional, retained destination DPI by default, and applied wallpaper at first login using destination monitor names.
- Changed Alt+F1 from the built-in Applications Menu command to the installed Whisker Menu command.

Screenshots show the real source desktop. Brand names, icons, and trademarks remain the property of their respective owners. No third-party application is bundled or represented as authored by this project.
