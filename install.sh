#!/bin/bash
# Set up the Omarchy-style desktop on a Galaxy Tab S7 FE running postmarketOS
# (console UI, user from pmbootstrap install). Run from the repo on your PC:
#   ./install.sh vansh@samsung-gts7xllite.local      (or vansh@172.16.42.1 over USB)
# The user needs sudo on the tablet (you will be asked for the password).
set -euo pipefail
target=${1:?usage: $0 user@tablet}
cd "$(dirname "$0")"

packages=(
  # session (same stack as postmarketos-ui-sway)
  bluez bluez-openrc elogind elogind-openrc polkit-elogind seatd-openrc
  postmarketos-base-ui postmarketos-base-ui-audio postmarketos-base-ui-networkmanager
  tinydm tinydm-openrc xdg-desktop-portal-gtk avahi
  # desktop
  hyprland xdg-desktop-portal-hyprland hyprlock hypridle hyprsunset hyprpicker
  waybar fuzzel mako swaybg alacritty foot font-jetbrains-mono-nerd wvkbd
  mesa-dri-gallium mesa-vulkan-freedreno brightnessctl wl-clipboard grim slurp
  # tools
  btop bluetui wiremix fastfetch fzf bash linux-firmware-qca
  # apps
  chromium vscodium python3 py3-pip
)

echo "==> Copying files"
tar -C dotfiles -cf - . | ssh "$target" 'tar -xf - -C ~'
tar -C system -cf - . | ssh "$target" 'cat > /tmp/omarchy-tab-system.tar'

echo "==> Installing packages and system config (sudo)"
ssh -t "$target" "set -e
  sudo apk add ${packages[*]}
  sudo tar -xf /tmp/omarchy-tab-system.tar -C / --no-same-owner
  sudo install -m755 ~/.local/bin/tablet-* /usr/local/bin/
  for g in video audio input; do sudo addgroup \$(id -un) \$g || true; done
  sudo sed -i -E 's/^#FastConnectable = false/FastConnectable = true/; s/^#ReconnectAttempts=7/ReconnectAttempts=7/; s/^#ReconnectIntervals=1,2,4,8,16,32,64/ReconnectIntervals=1,2,4,8,16,32,64/; s/^#AutoEnable=true/AutoEnable=true/' /etc/bluetooth/main.conf
  for s in elogind tinydm bluetooth avahi-daemon; do sudo rc-update add \$s default; done
  sudo tinydm-set-session -f -s /usr/share/wayland-sessions/hyprland-dbus.desktop
  mkdir -p ~/Pictures/Screenshots ~/.local/share/wallpapers ~/.local/share/fonts
  tablet-fix-vscodium-terminal
  codium --install-extension enkia.tokyo-night || true
"
echo "==> Done. Copy Omarchy's wallpapers to ~/.local/share/wallpapers (and link one as 'current')"
echo "    and omarchy.ttf to ~/.local/share/fonts, then reboot the tablet."
