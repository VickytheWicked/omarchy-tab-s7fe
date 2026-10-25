#!/usr/bin/env python3
"""Generate the tablet's Omarchy-style menu (tablet-menu) from the laptop's
/usr/share/omarchy/default/omarchy/omarchy-menu.jsonc.

Icons and labels come from Omarchy's file; actions are the tablet's own
(Alpine apk, fuzzel, nmtui, bluetui, ...). Entries that make no sense on the
tablet (AUR, Plymouth, drive encryption, ...) are simply not listed here.
"""
import re
import shlex
import sys

OMARCHY_MENU = "/usr/share/omarchy/default/omarchy/omarchy-menu.jsonc"


def load_omarchy(path):
    entries = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r'\s*"([a-z0-9.\-]+)":\s*\{(.*)\},?\s*$', line)
        if not m:
            continue
        body = m.group(2)
        icon = re.search(r'"icon":"([^"]*)"', body)
        label = re.search(r'"label":"([^"]*)"', body)
        entries[m.group(1)] = (icon.group(1) if icon else "", label.group(1) if label else m.group(1))
    return entries


def term(cmd):
    """Run cmd in Alacritty and wait for a key, like Omarchy's presentation terminal."""
    inner = f'{cmd}; echo; read -n 1 -s -r -p "Done! Press any key to close..."'
    return "alacritty -e bash -c " + shlex.quote(inner)


def apk_install(*pkgs):
    return term("sudo apk add " + " ".join(pkgs))


def webapp(url):
    return f"chromium --app={shlex.quote(url)}"


EDIT_HYPR = "codium ~/.config/hypr/hyprland.conf"

# (id, omarchy id for icon/label or None, label override, icon override, action)
# A row without action is a submenu; its children are the rows whose id starts with "id.".
MENU = [
    ("apps", "apps", None, None, "tablet-apps"),
    ("learn", "learn", None, None, None),
    ("learn.keybindings", "learn.keybindings", None, None, "tablet-keybindings"),
    ("learn.omarchy", "learn.omarchy", None, None, webapp("https://omarchy.org/manual/")),
    ("learn.hyprland", "learn.hyprland", None, None, webapp("https://wiki.hypr.land/")),
    ("learn.alpine", "learn.arch", "Alpine", "\uf300", webapp("https://wiki.alpinelinux.org/")),
    ("learn.postmarketos", "learn.community", "postmarketOS", None, webapp("https://wiki.postmarketos.org/")),
    ("learn.neovim", "learn.neovim", None, None, webapp("https://www.lazyvim.org/keymaps")),
    ("learn.bash", "learn.bash", None, None, webapp("https://devhints.io/bash")),
    ("trigger", "trigger", None, None, None),
    ("trigger.capture", "trigger.capture", None, None, None),
    ("trigger.capture.screenshot", "trigger.capture.screenshot", "Screenshot (region)", None, "tablet-screenshot region"),
    ("trigger.capture.full", "trigger.capture.screenshot", "Screenshot (full screen)", None, "tablet-screenshot full"),
    ("trigger.capture.color", "trigger.capture.color", None, None, "pkill hyprpicker || hyprpicker -a"),
    ("trigger.toggle", "trigger.toggle", None, None, None),
    ("trigger.toggle.idle-lock", "trigger.toggle.idle-lock", None, None, "tablet-toggle idle"),
    ("trigger.toggle.notifications", "trigger.toggle.notifications", None, None, "tablet-toggle notifications"),
    ("trigger.toggle.nightlight", "trigger.toggle.nightlight", None, None, "tablet-nightlight-toggle"),
    ("trigger.toggle.top-bar", "trigger.toggle.top-bar", None, None, "pkill -SIGUSR1 waybar"),
    ("trigger.toggle.window-gaps", "trigger.toggle.window-gaps", None, None, "tablet-toggle gaps"),
    ("trigger.hardware", "trigger.hardware", None, None, None),
    ("trigger.hardware.usb-host", "trigger.hardware.touchscreen", "USB: host mode (keyboard/mouse)", None, "tablet-usb-mode host"),
    ("trigger.hardware.usb-device", "trigger.hardware.laptop-display", "USB: device mode (laptop cable)", None, "tablet-usb-mode device"),
    ("style", "style", None, None, None),
    ("style.theme", "style.theme", "Theme (Tokyo Night)", None, "notify-send 'Theme' 'Tokyo Night is the theme on the tablet'"),
    ("style.background", "style.background", None, None, "tablet-background"),
    ("style.hyprland", "style.hyprland", None, None, EDIT_HYPR),
    ("setup", "setup", None, None, None),
    ("setup.wifi", "update.hardware.wifi", None, None, "alacritty -e nmtui"),
    ("setup.bluetooth", "update.hardware.bluetooth", None, None, "alacritty -e bluetui"),
    ("setup.audio", "update.hardware.audio", None, None, "alacritty -e wiremix"),
    ("setup.monitors", "setup.monitors", None, None, EDIT_HYPR),
    ("setup.keybindings", "setup.keybindings", None, None, EDIT_HYPR),
    ("setup.input", "setup.input", None, None, EDIT_HYPR),
    ("setup.config", "setup.config", None, None, None),
    ("setup.config.hyprland", "setup.config.hyprland", None, None, EDIT_HYPR),
    ("setup.config.hypridle", "setup.config.hyprsunset", "Hypridle", None, "codium ~/.config/hypr/hypridle.conf"),
    ("setup.config.waybar", "update.process.shell", "Waybar", None, "codium ~/.config/waybar"),
    ("setup.config.alacritty", "install.terminal.alacritty", "Alacritty", None, "codium ~/.config/alacritty/alacritty.toml"),
    ("install", "install", None, None, None),
    ("install.package", "install.package", None, "\uf300", "alacritty -e tablet-pkg-install"),
    ("install.editor", "install.editor", None, None, None),
    ("install.editor.vscodium", "install.editor.vscode", "VSCodium", None, apk_install("vscodium")),
    ("install.editor.neovim", "learn.neovim", "Neovim", None, apk_install("neovim")),
    ("install.editor.helix", "install.editor.helix", None, None, apk_install("helix")),
    ("install.editor.vim", "install.editor.vim", None, None, apk_install("gvim")),
    ("install.browser", "install.browser", None, None, None),
    ("install.browser.firefox", "install.browser.firefox", None, None, apk_install("firefox")),
    ("install.browser.chromium", "setup.default.browser.chromium", "Chromium", None, apk_install("chromium")),
    ("install.development", "install.development", None, None, None),
    ("install.development.node", "install.development.javascript.node", None, None, apk_install("nodejs", "npm")),
    ("install.development.deno", "install.development.javascript.deno", None, None, apk_install("deno")),
    ("install.development.python", "install.development.python", None, None, apk_install("python3", "py3-pip")),
    ("install.development.go", "install.development.go", None, None, apk_install("go")),
    ("install.development.rust", "install.development.rust", None, None, apk_install("rust", "cargo")),
    ("install.development.zig", "install.development.zig", None, None, apk_install("zig")),
    ("install.development.java", "install.development.java", None, None, apk_install("openjdk21")),
    ("install.development.dotnet", "install.development.dotnet", None, None, apk_install("dotnet9-sdk")),
    ("install.development.php", "install.development.php", None, None, apk_install("php83")),
    ("install.development.ruby", "install.development.rails", "Ruby", None, apk_install("ruby")),
    ("install.development.elixir", "install.development.elixir", None, None, apk_install("elixir")),
    ("install.font", "install.style.font", None, None, None),
    ("install.font.cascadia", "install.style.font.cascadia", None, None, apk_install("font-cascadia")),
    ("install.font.meslo", "install.style.font.meslo", None, None, apk_install("font-meslo-nerd")),
    ("install.font.fira", "install.style.font.fira", None, None, apk_install("font-fira-code-nerd")),
    ("remove", "remove", None, None, None),
    ("remove.package", "remove.package", None, "\uf300", "alacritty -e tablet-pkg-remove"),
    ("update", "update", None, None, None),
    ("update.system", "update.firmware", "System", None, term("tablet-update")),
    ("update.process", "update.process", None, None, None),
    ("update.process.bar", "update.process.shell", "Bar", None, "pkill -x waybar; setsid -f waybar >/dev/null 2>&1"),
    ("update.process.hyprsunset", "update.process.hyprsunset", None, None, "tablet-toggle restart-nightlight"),
    ("update.hardware", "update.hardware", None, None, None),
    ("update.hardware.audio", "update.hardware.audio", None, None, "pkill -x wireplumber; pkill -x pipewire-pulse; pkill -x pipewire; setsid -f /usr/libexec/pipewire-launcher"),
    ("update.hardware.wifi", "update.hardware.wifi", None, None, "nmcli radio wifi off; sleep 2; nmcli radio wifi on; notify-send 'Wi-Fi' 'Restarted'"),
    ("update.hardware.bluetooth", "update.hardware.bluetooth", None, None, "sudo -n rc-service bluetooth restart && notify-send 'Bluetooth' 'Restarted'"),
    ("update.time", "update.time", None, None, "sudo -n chronyc -a makestep && notify-send 'Time' \"$(date '+%A %H:%M')\""),
    ("about", "about", None, None, term("fastfetch")),
    ("system", "system", None, None, None),
    ("system.lock", "system.lock", "Lock (needs a keyboard)", None, "pidof hyprlock || hyprlock"),
    ("system.logout", "system.logout", None, None, "hyprctl dispatch exit"),
    ("system.reboot", "system.reboot", None, None, "sudo -n reboot"),
    ("system.shutdown", "system.shutdown", "Shutdown (unplug USB first)", None, "sudo -n poweroff"),
]

HEADER = r'''#!/bin/bash
# Omarchy-style menu for the tablet, generated by gen-tablet-menu.py from the
# laptop's omarchy-menu.jsonc (icons and labels) with tablet actions.
# usage: tablet-menu [route]   e.g. tablet-menu system, tablet-menu trigger.capture
# Escape goes back to the parent menu; at the top it closes.

declare -A ICON LABEL ACTION
declare -a ORDER
add() { ORDER+=("$1"); ICON[$1]=$2; LABEL[$1]=$3; ACTION[$1]=$4; }
'''

FOOTER = r'''
children() {
  local parent=$1 id rest
  for id in "${ORDER[@]}"; do
    if [[ -z $parent ]]; then
      [[ $id != *.* ]] && echo "$id"
    else
      rest=${id#"$parent."}
      [[ $id == "$parent."* && $rest != *.* ]] && echo "$id"
    fi
  done
}

title_of() { [[ -z $1 ]] && echo "Go" || echo "${LABEL[$1]}"; }

run() {
  setsid -f bash -c "$1" >/dev/null 2>&1
}

# Toggle like Omarchy: invoking the menu while it is open closes it (any level).
pidfile=${XDG_RUNTIME_DIR:-/tmp}/tablet-menu.pid
if [[ -f $pidfile ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
  kill "$(cat "$pidfile")" 2>/dev/null
  pkill -x fuzzel
  rm -f "$pidfile"
  exit 0
fi
pkill -x fuzzel
echo $$ > "$pidfile"
trap 'rm -f "$pidfile"' EXIT

back_icon=$'\U000f004d'
close_icon=$'\U000f0156'
route=${1:-}

while true; do
  if [[ -n $route && -n ${ACTION[$route]:-} ]]; then
    run "${ACTION[$route]}"
    exit 0
  fi
  mapfile -t ids < <(children "$route")
  [[ ${#ids[@]} -eq 0 ]] && exit 1
  # Touch has no Escape key, and taps outside fuzzel do not reach the bar while
  # it is open: every menu gets Close on top, submenus also get Back.
  if [[ -n $route ]]; then ids=(__close__ __back__ "${ids[@]}"); else ids=(__close__ "${ids[@]}"); fi
  idx=$(for id in "${ids[@]}"; do
          case $id in
            __close__) printf '%s  Close\n' "$close_icon" ;;
            __back__) printf '%s  Back\n' "$back_icon" ;;
            *) printf '%s  %s\n' "${ICON[$id]}" "${LABEL[$id]}" ;;
          esac
        done | fuzzel --dmenu --index --prompt "$(title_of "$route")  " --lines "${#ids[@]}" --width 42)
  [[ -n $idx && ${ids[$idx]} == __close__ ]] && exit 0
  if [[ -z $idx || ${ids[$idx]} == __back__ ]]; then
    [[ -z $route ]] && exit 0
    [[ $route == *.* ]] && route=${route%.*} || route=""
    continue
  fi
  route=${ids[$idx]}
done
'''


def main():
    om = load_omarchy(OMARCHY_MENU)
    out = [HEADER]
    for mid, oid, label, icon, action in MENU:
        if oid and oid not in om:
            sys.exit(f"Omarchy menu has no entry {oid}")
        o_icon, o_label = om.get(oid, ("", mid))
        out.append("add {} {} {} {}".format(
            shlex.quote(mid), shlex.quote(icon or o_icon),
            shlex.quote(label or o_label), shlex.quote(action or "")))
    out.append(FOOTER)
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
