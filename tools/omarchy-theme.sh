#!/bin/bash
# Re-colour the tablet with one of Omarchy's themes. Run on the laptop (it reads
# /usr/share/omarchy/themes):
#   tools/omarchy-theme.sh catppuccin vansh@samsung-gts7xllite.local
#   tools/omarchy-theme.sh catppuccin --dry-run      (write to a temp dir, show the diff)
# The configs in dotfiles/ use Tokyo Night, and every colour in them is one of
# its colors.toml keys, so each key's hex is swapped for the same key's hex in
# the new theme. Wallpapers from the theme go to ~/.local/share/wallpapers.
set -euo pipefail
theme=${1:?usage: $0 <omarchy theme> user@tablet|--dry-run}
target=${2:?usage: $0 <omarchy theme> user@tablet|--dry-run}
themes=/usr/share/omarchy/themes
[ -f "$themes/$theme/colors.toml" ] || { echo "no theme $themes/$theme (try: ls $themes)" >&2; exit 1; }
cd "$(dirname "$0")/.."

files=(
  .config/hypr/hyprland.conf .config/hypr/hyprlock.conf
  .config/waybar/style.css .config/fuzzel/fuzzel.ini .config/mako/config
  .config/alacritty/theme.toml .config/foot/theme.ini
  .config/btop/themes/tokyo-night.theme
)

# key -> hex (no '#', lower case) from a colors.toml
palette() { sed -nE 's/^([a-z_]+) *= *"#([0-9a-fA-F]{6})".*/\1 \2/p' "$1" | tr 'A-F' 'a-f'; }

# Two passes through placeholders so a new colour is never replaced again by a
# later key. Keys in file order: when Tokyo Night uses one hex for two keys
# (accent and blue), the first key wins.
to_tags=() from_tags=() seen=" "
while read -r key hex; do
  [[ $seen == *" $hex "* ]] && continue
  seen+="$hex "
  new=$(palette "$themes/$theme/colors.toml" | awk -v k="$key" '$1 == k { print $2 }')
  [ -n "$new" ] || continue
  to_tags+=(-e "s/$hex/@@$key@@/gI")
  from_tags+=(-e "s/@@$key@@/$new/g")
done < <(palette "$themes/tokyo-night/colors.toml")

out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
for f in "${files[@]}"; do
  mkdir -p "$out/$(dirname "$f")"
  sed "${to_tags[@]}" "dotfiles/$f" | sed "${from_tags[@]}" > "$out/$f"
done
mode=$(sed -nE 's/^mode *= *"(.*)"/\1/p' "$themes/$theme/colors.toml")
mkdir -p "$out/.config/gtk-3.0" "$out/.config/gtk-4.0"
for g in gtk-3.0 gtk-4.0; do
  sed -E "s/^(gtk-application-prefer-dark-theme)=.*/\1=$([ "$mode" = light ] && echo 0 || echo 1)/" \
    "dotfiles/.config/$g/settings.ini" > "$out/.config/$g/settings.ini"
done

if [ "$target" = --dry-run ]; then
  for f in "${files[@]}"; do diff -u "dotfiles/$f" "$out/$f" || true; done
  exit 0
fi

echo "==> $theme ($mode) -> $target"
tar -C "$out" -cf - .config | ssh "$target" 'tar -xf - -C ~'
if [ -d "$themes/$theme/backgrounds" ]; then
  ssh "$target" "mkdir -p ~/.local/share/wallpapers/$theme"
  tar -C "$themes/$theme/backgrounds" -cf - . | ssh "$target" "tar -xf - -C ~/.local/share/wallpapers/$theme"
  first=$(ls "$themes/$theme/backgrounds" | head -1)
  [ -n "$first" ] && ssh "$target" "ln -sfn $theme/$first ~/.local/share/wallpapers/current"
fi
# reload everything that does not pick the change up by itself
ssh "$target" 'export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-1
  export HYPRLAND_INSTANCE_SIGNATURE=$(ls "$XDG_RUNTIME_DIR/hypr" | head -1)
  hyprctl reload >/dev/null; makoctl reload; pkill -SIGUSR2 -x waybar
  hyprctl dispatch exec "pkill -x swaybg; swaybg -i ~/.local/share/wallpapers/current -m fill" >/dev/null'
echo "==> Done. Fuzzel and new terminals use it at once; restart btop and running terminals."
