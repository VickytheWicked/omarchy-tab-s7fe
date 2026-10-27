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
  waybar fuzzel mako swaybg alacritty foot font-jetbrains-mono-nerd squeekboard
  network-manager-applet blueman
  mesa-dri-gallium mesa-vulkan-freedreno brightnessctl wl-clipboard grim slurp
  # tools
  btop bluetui wiremix fastfetch fzf bash linux-firmware-qca
  # apps
  chromium vscodium python3 py3-pip
)

echo "==> Copying files"
tar -C dotfiles -cf - . | ssh "$target" 'tar -xf - -C ~'
# private temp file: its contents are extracted as root
sys_tar=$(ssh "$target" mktemp)
tar -C system -cf - . | ssh "$target" "cat > $sys_tar"

echo "==> Installing packages and system config (sudo)"
ssh -t "$target" "set -e
  sudo apk add ${packages[*]}
  sudo tar -xf $sys_tar -C / --no-same-owner
  rm -f $sys_tar
  sudo nft -f /etc/nftables.nft   # 49_ssh_local.nft: SSH only from USB and the local network
  sudo install -m755 ~/.local/bin/tablet-* /usr/local/bin/
  # menu, bar and USB-mode actions run sudo -n (no terminal to ask for a password)
  printf '%s\n' \"\$(id -un) ALL=(root) NOPASSWD: /usr/sbin/reboot, /usr/sbin/poweroff, /usr/sbin/rc-service bluetooth restart, /usr/sbin/chronyc -a makestep, /usr/sbin/tee /sys/class/usb_role/a600000.usb-role-switch/role\" | sudo tee /etc/sudoers.d/80-tablet-actions >/dev/null
  sudo chmod 440 /etc/sudoers.d/80-tablet-actions
  sudo visudo -cf /etc/sudoers.d/80-tablet-actions
  for g in video audio input; do sudo addgroup \$(id -un) \$g || true; done
  sudo sed -i -E 's/^#FastConnectable = false/FastConnectable = true/; s/^#ReconnectAttempts=7/ReconnectAttempts=7/; s/^#ReconnectIntervals=1,2,4,8,16,32,64/ReconnectIntervals=1,2,4,8,16,32,64/; s/^#AutoEnable=true/AutoEnable=true/' /etc/bluetooth/main.conf
  for s in elogind tinydm bluetooth avahi-daemon; do sudo rc-update add \$s default; done
  sudo tinydm-set-session -f -s /usr/share/wayland-sessions/hyprland-dbus.desktop
  # key-only SSH, but only once a key is installed (ssh-copy-id), or you would be locked out
  if [ -s ~/.ssh/authorized_keys ]; then
    printf '%s\\n' 'PasswordAuthentication no' 'KbdInteractiveAuthentication no' | sudo tee /etc/ssh/sshd_config.d/10-key-only.conf >/dev/null
    sudo rc-service sshd reload
  else
    echo '!!! No SSH key in ~/.ssh/authorized_keys: password logins stay on (run ssh-copy-id, then install.sh again)'
  fi
  mkdir -p ~/Pictures/Screenshots ~/.local/share/wallpapers ~/.local/share/fonts
  tablet-fix-vscodium-terminal
  codium --install-extension enkia.tokyo-night || true
"
echo "==> Done. Copy Omarchy's wallpapers to ~/.local/share/wallpapers (and link one as 'current')"
echo "    and omarchy.ttf to ~/.local/share/fonts, then reboot the tablet."
