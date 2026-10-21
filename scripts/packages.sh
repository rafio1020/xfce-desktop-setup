#!/usr/bin/env bash
set -euo pipefail
preview=false
case "${1:-}" in
  --dry-run) preview=true ;;
  '') ;;
  *) echo 'Usage: ./install.sh --packages [--dry-run]' >&2; exit 2 ;;
esac
# Read identifiers, never execute os-release as shell code.
os_id="$(sed -n 's/^ID=//p' /etc/os-release | tr -d '\"')"
os_like="$(sed -n 's/^ID_LIKE=//p' /etc/os-release | tr -d '\"')"
case " $os_id $os_like " in
  *' fedora '*)
    if [[ -e /run/ostree-booted ]]; then
      echo 'Fedora Atomic is not supported by the package installer. Use an XFCE installation with dnf.' >&2; exit 1
    fi
    commands=('sudo dnf install')
    packages=(python3 git xorg-x11-server-Xorg xorg-x11-xinit xrandr xfce4-session xfce4-panel xfce4-settings xfconf xfwm4 xfdesktop Thunar exo xfce4-terminal xfce4-appfinder xfce4-whiskermenu-plugin xfce4-screenshooter xfce4-taskmanager xfce4-power-manager xfce4-notifyd xfce4-screensaver fontconfig procps-ng)
    ;;
  *' ubuntu '*|*' debian '*)
    commands=('sudo apt-get update' 'sudo apt-get install')
    packages=(python3 git xorg x11-xserver-utils xfce4 xfce4-terminal xfce4-whiskermenu-plugin xfce4-screenshooter xfce4-taskmanager xfce4-power-manager xfce4-notifyd xfce4-screensaver fontconfig procps)
    ;;
  *' cachyos '*|*' arch '*)
    commands=('sudo pacman -Syu --needed')
    packages=(python git xorg-server xorg-xinit xorg-xrandr xfce4-session xfce4-panel xfce4-settings xfconf xfwm4 xfdesktop thunar exo xfce4-terminal xfce4-appfinder xfce4-whiskermenu-plugin xfce4-screenshooter xfce4-taskmanager xfce4-power-manager xfce4-notifyd xfce4-screensaver fontconfig procps-ng)
    ;;
  *) echo "Unsupported distribution: $os_id. Install XFCE, Whisker Menu, Python 3 and fontconfig manually; see README." >&2; exit 1 ;;
esac
for ((i=0;i<${#commands[@]};i++)); do
  read -r -a command_args <<< "${commands[$i]}"
  if ((i==${#commands[@]}-1)); then command_args+=("${packages[@]}"); fi
  printf '%q ' "${command_args[@]}"; printf '\n'
  if [[ "$preview" == false ]]; then "${command_args[@]}"; fi
done
if [[ "$preview" == false ]]; then
  echo 'Packages installed. Log into XFCE once, then log out before running ./install.sh --apply from a text console.'
fi
