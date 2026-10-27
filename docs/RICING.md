# Ricing the Galaxy Tab S7 FE

How to change the look of the tablet's Omarchy-style desktop — colours, wallpaper, bar, fonts, animations — without breaking the things this hardware is picky about.

Everything here is a plain config file in your home directory on the tablet. The same files live in this repo under `dotfiles/`, so the usual loop is: edit in the repo on your PC, push the files to the tablet, see the result, commit.

## The fast way: switch to an Omarchy theme

Omarchy ships 20 themes (catppuccin, gruvbox, nord, rose-pine, kanagawa, everforest, …). On a PC with Omarchy installed, one command re-colours the whole tablet and copies the theme's wallpapers:

```sh
ls /usr/share/omarchy/themes                       # pick one
tools/omarchy-theme.sh catppuccin --dry-run        # preview: prints the colour changes
tools/omarchy-theme.sh catppuccin vansh@samsung-gts7xllite.local
```

It works because every colour in `dotfiles/` is one of Tokyo Night's palette keys (`background`, `accent`, `red`, …). The script swaps each one for the same key in the new theme's `colors.toml`, then reloads Hyprland, Waybar, mako and the wallpaper. Light themes (`mode = "light"`) also switch GTK apps to light.

Not covered by the script: VSCodium (pick a matching theme in its settings) and Chromium (`chrome://settings/appearance`). To go back, run it with `tokyo-night`.

Without Omarchy on your PC, copy a theme's `colors.toml` from the [Omarchy repo](https://github.com/basecamp/omarchy) to `/usr/share/omarchy/themes/<name>/` or edit the script's `themes=` line.

## Where each part of the look lives

| What | File (on the tablet, under `~`) | Applies |
|---|---|---|
| Window borders, gaps, rounding, blur, shadows, animations | `.config/hypr/hyprland.conf` | on save |
| Top bar: modules, height, icons | `.config/waybar/config.jsonc` | `pkill -SIGUSR2 waybar` |
| Top bar: colours, fonts, spacing | `.config/waybar/style.css` | `pkill -SIGUSR2 waybar` |
| Menus and app launcher (fuzzel) | `.config/fuzzel/fuzzel.ini` | next time it opens |
| Notifications | `.config/mako/config` | `makoctl reload` |
| Terminal | `.config/alacritty/alacritty.toml`, `theme.toml` | live |
| Second terminal | `.config/foot/foot.ini`, `theme.ini` | new windows |
| btop | `.config/btop/themes/tokyo-night.theme` | restart btop |
| Lock screen | `.config/hypr/hyprlock.conf` | next lock |
| GTK apps (dark/light, font) | `.config/gtk-3.0/settings.ini`, `gtk-4.0/settings.ini` | restart the app |
| Wallpaper | `.local/share/wallpapers/current` (a link) | Super + Ctrl + Space |

### Editing

- **On the tablet**: Omarchy menu → Setup → Config opens these in VSCodium. Hyprland reloads its config the moment you save.
- **From your PC** (nicer with a keyboard): edit `dotfiles/` in this repo, then send just the configs:
  ```sh
  tar -C dotfiles -cf - .config | ssh vansh@samsung-gts7xllite.local 'tar -xf - -C ~'
  ```
  Run `./install.sh` only for a fresh tablet: it also installs packages and system files.
- A broken `hyprland.conf` doesn't lock you out: Hyprland keeps running and shows the error at the top of the screen. `hyprctl configerrors` lists them over SSH.

## Wallpapers

Put images in `~/.local/share/wallpapers/` (subfolders are fine; the theme script makes one per theme). Super + Ctrl + Space, or Omarchy menu → Style → Background, picks one. The screen is **2560 × 1600** in landscape; images of that size or larger look sharpest.

## Fonts

The UI uses **JetBrainsMono Nerd Font** (the Nerd Font icons in the bar and menus come from it). To use another font:

```sh
sudo apk add font-cascadia            # or font-noto, nerd-fonts-all, font-awesome …
# or drop .ttf/.otf files into ~/.local/share/fonts, then:
fc-cache -f
```

Then change the font name in `waybar/style.css`, `fuzzel/fuzzel.ini`, `mako/config` and the terminal configs. Keep a Nerd Font for Waybar and fuzzel, or the icons turn into boxes.

## Icons, GTK and Qt themes

Available in Alpine: `papirus-icon-theme`, `adw-gtk3` (Adwaita restyled for GTK3 apps), `nwg-look` (GUI to pick GTK theme/icons/cursor), `qt6ct` and `kvantum` (Qt apps).

```sh
sudo apk add papirus-icon-theme adw-gtk3 nwg-look
nwg-look        # choose theme and icons; it writes the gtk-3.0/gtk-4.0 settings
```

## Animations, blur and shadows

Animations use Omarchy's curves and are on. Blur and shadows are **off** (`decoration` in `hyprland.conf`). The GPU is an Adreno 619 driving 1600 × 2560 at 60 Hz; blur samples the screen behind every transparent window, so try it before keeping it:

```ini
decoration {
    rounding = 8
    blur {
        enabled = true
        size = 4
        passes = 1        # each extra pass costs a lot at this resolution
    }
    shadow {
        enabled = true
        range = 8
    }
}
debug {
    overlay = true        # FPS and frame times on screen while you tune; remove afterwards
}
```

If dragging windows drops below 60 FPS, lower `passes`/`size` or turn blur off again. Transparent terminals (`window.opacity` in Alacritty) only look different with blur on.

## Designing for touch

There is often no keyboard or mouse, so size things for a finger:

- At the display scale of 1.6, **1 logical pixel ≈ 0.11 mm**. A comfortable touch target is about 7–9 mm, so **~44 px or more**. The bar is 44 px high and fuzzel rows are 44 px (`line-height`), with 15 px text. Going smaller makes them hard to hit; going bigger is fine.
- Every menu needs its **Close** row: while fuzzel is open, taps outside it never reach the bar, so there is no other way to dismiss it by touch. If you add your own fuzzel menus, copy the pattern from `tablet-menu`/`tablet-apps`.
- Bar buttons are the touch shortcuts (Omarchy logo = menu, ✕ = close window, keyboard = on-screen keyboard, ⏻ = system menu). Wi-Fi and Bluetooth are tray icons (nm-applet, blueman): tap them for networks and devices. Add your own buttons in `waybar/config.jsonc` with `"on-click"`.
- The on-screen keyboard (squeekboard) pops up by itself in text fields of GTK apps, terminals and Chromium, and hides when focus leaves every window. Its look follows GTK's light/dark setting.
- `scale` in the `monitor =` line makes the whole UI bigger or smaller (1.6 now; try 1.5 or 1.75). Keep the `transform` numbers as they are; the touchscreen depends on them.

## Don't touch these (hardware workarounds)

These settings look odd but keep the tablet working. Change the look around them:

| Setting | Why |
|---|---|
| `monitor = DSI-1, …, transform, 3` and `touchdevice { transform = 3 }` | Panel is portrait; both must match or touches land in the wrong place |
| `cursor { no_hardware_cursors = true }` | The hardware cursor plane is misplaced on the rotated panel |
| No `dpms` anywhere (idle, power button) | Switching the panel off can leave it black until a reboot; only the backlight goes off |
| No brightness animations, brightness keys without repeat | Each brightness change is a command on the display link; bursts of them glitch the picture or freeze the tablet (fixed in kernel r6, still best avoided) |
| hypridle timeout 15 min | Same reason: fewer brightness changes |

## Sharing your rice

Commit your changes to `dotfiles/` and they're a pull request away. Add a screenshot (Print key, saved to `~/Pictures/Screenshots`) to `docs/screenshots/`.
