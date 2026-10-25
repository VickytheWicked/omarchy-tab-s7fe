# Omarchy on the Galaxy Tab S7 FE

Mainline Linux ([postmarketOS](https://postmarketos.org)) on the **Samsung Galaxy Tab S7 FE LTE (SM-T735, `gts7xllite`, Snapdragon 750G / SM7225)**, with an [Omarchy](https://omarchy.org)-style Hyprland desktop: Omarchy's keybindings, menu, Waybar layout and Tokyo Night theme, adapted for a touch tablet.

> ⚠️ **Unlocking the bootloader wipes the tablet and trips Samsung Knox permanently** (Secure Folder, Samsung Pass/Wallet/Health stop working for good). Linux **does not charge the battery** yet. Read [Known limitations](#known-limitations) before you start.

## What works

| Hardware | Status | Notes |
|---|---|---|
| Display (FocalTech FT8203 panel, DSC) | ✅ | Himax HX83121A panel variant is **not** supported |
| Touchscreen | ✅ | FocalTech FT8203 over SPI |
| GPU (Adreno 619) | ✅ | freedreno / Turnip, Hyprland runs accelerated |
| Wi-Fi (WCN3990) | ✅ | |
| Bluetooth | ✅ | needs `linux-firmware-qca` |
| Battery level | ✅ | SM5714 fuel gauge (level, status, voltage, current) |
| Power off | ✅ | stays off **with the USB cable unplugged** |
| USB networking / SSH over USB | ✅ | USB port defaults to device mode |
| USB host (OTG) | ⚠️ | controller works, but **no 5 V VBUS** (SM5714 charger has no driver): use a powered OTG hub |
| Charging | ❌ | no SM5714 charger driver yet — charge in Download mode |
| Audio, camera, S Pen, sensors | ❌ | not working yet |

## What is in this repo

```
pmaports/device/testing/
  linux-samsung-gts7xllite/     mainline 7.2 kernel + 7 patches (see below)
  device-samsung-gts7xllite/    deviceinfo (boots from RECOVERY, rootfs in USERDATA)
  firmware-samsung-gts7xllite/  ADSP/CDSP/modem/Wi-Fi/GPU/touch firmware
dotfiles/                       Hyprland, Waybar, fuzzel, Alacritty, mako, VSCodium... + tablet-* scripts
system/                         Hyprland tinydm session, power-key and Chromium settings
tools/gen-tablet-menu.py        generates tablet-menu from Omarchy's omarchy-menu.jsonc
install.sh                      sets up the desktop on a freshly flashed tablet over SSH
```

### Kernel patches

Base: [vishalbala-nps/linux](https://github.com/vishalbala-nps/linux) `panel` branch (fork of [sm6350-mainline](https://github.com/sm6350-mainline/linux)), which carries the device tree and the FT8203 panel driver.

| Patch | What it does |
|---|---|
| 0001 | FocalTech FT8203 SPI touchscreen driver (from Marker284) |
| 0002 | Panel driver stability fixes: keep panel powered, brightness in LP mode (Marker284) |
| 0003 | DTS: SPI6 controller, touchscreen node, USB peripheral mode |
| 0004 | Panel: DSC block prediction off — fixes vertical streaks and broken glyphs |
| 0005 | DTS: PMK8350 is SID 6 (stock layout) — fixes power-off hang, duplicate PON, RTC |
| 0006 | SM5714 fuel gauge driver (vishalbala's, merge-conflict leftovers removed, STATUS added) |
| 0007 | DTS: USB OTG with a manual role switch (`tablet-usb-mode`) |

## Installing

You need a Linux PC with [pmbootstrap](https://docs.postmarketos.org/pmbootstrap/) and `heimdall` (odin4 never completed its handshake with this tablet; heimdall works).

1. **Unlock the bootloader.** Developer options → *OEM unlocking*, then in Download mode (power off, hold **Vol Up + Vol Down**, plug in USB) **long-press Vol Up** and confirm. This wipes the tablet. Let it boot Android once, online, until `KG STATUS` is not blocking.
2. **Add the packages** to your pmaports checkout:
   ```sh
   cp -r pmaports/device/testing/* "$(pmbootstrap config aports)"/device/testing/
   pmbootstrap init        # vendor samsung, device gts7xllite, UI console, init openrc
   ```
3. **Build the image.** If your desktop auto-mounts drives (Omarchy runs `udiskie --automount`), **pause it first** — it mounts the image partitions mid-build and you get an empty rootfs:
   ```sh
   pkill -f 'udiskie --automount'
   pmbootstrap install --no-sparse
   ```
   Check the image before flashing (the root partition must contain `/sbin/init`), then make the sparse image yourself:
   ```sh
   img2simg samsung-gts7xllite.img userdata.img
   avbtool make_vbmeta_image --flags 2 --padding_size 4096 --output vbmeta.img
   ```
4. **Flash** in Download mode. On the warning screen **short-press Vol Up** first — the USB handshake only works on the actual *Downloading…* screen:
   ```sh
   heimdall flash --RECOVERY boot.img --VBMETA vbmeta.img --USERDATA userdata.img
   ```
   Android keeps the BOOT partition, Linux boots from RECOVERY.
5. **Boot Linux**: hold **Vol Down + Power** ~7 s, then **Vol Up + Power** and **let go at the Samsung logo** (a volume key held while Linux starts drops into the initramfs debug shell). Leave the first boot alone for a few minutes while it grows the filesystem.
6. **Install the desktop** from this repo (Wi-Fi or USB):
   ```sh
   ./install.sh user@samsung-gts7xllite.local     # or user@172.16.42.1 over USB
   ```
   Copy Omarchy's wallpapers into `~/.local/share/wallpapers` (link one as `current`) and `omarchy.ttf` into `~/.local/share/fonts` — they are Omarchy's artwork, so they are not included here.

## Using it

The desktop starts at boot (tinydm autologin into Hyprland).

| Keys | Action |
|---|---|
| Super + Space | Omarchy menu (also: tap the logo in the bar) |
| Super + Alt + Space | Apps |
| Super + Escape | System menu (also: ⏻ in the bar) |
| Power button | screen (and touch) off / on |
| Super + Return | Terminal (Alacritty) |
| Super + Shift + Return / B | Chromium |
| Super + Shift + N | VSCodium |
| Super + W | Close window (also: ✕ in the bar) |
| Super + 1…0 | Workspaces (+ Shift: move window) |
| Super + Ctrl + C / O / H | Capture / Toggle / Hardware menus |
| Super + Ctrl + B | Bluetooth (bluetui) |
| Super + Ctrl + U | USB host ↔ device |
| Super + Ctrl + K | On-screen keyboard (also: keyboard icon in the bar) |
| Print / Super + Print | Screenshot / colour picker |
| Super + K | All keybindings |

Commands on the tablet:

| Command | |
|---|---|
| `tablet-update` | `apk upgrade`, then copies a changed `/boot/boot.img` to RECOVERY and verifies it |
| `tablet-pkg-install` / `tablet-pkg-remove` | Omarchy-style fuzzy package installer for `apk` |
| `tablet-usb-mode host\|device` | switch the USB-C port role |
| `tablet-fix-vscodium-terminal` | Alpine's VSCodium ships no Linux `node-pty`; this builds it |

SSH: `ssh user@samsung-gts7xllite.local` (avahi) or `ssh user@172.16.42.1` over the USB cable.

## Known limitations

- **No charging in Linux.** Linux reads the battery but cannot charge it. Charge in **Download mode** (the bootloader charges). With a cable plugged in, *power off* powers straight back on into Linux, so unplug first.
- **Power button** turns only the screen off; the tablet keeps running.
- Only the **FocalTech FT8203** panel variant works.
- Suspend is untested; the lock screen cannot be used with the on-screen keyboard, so idle only turns the screen off.
- `hyprland-guiutils` and Omarchy's walker/omarchy-shell are not packaged for Alpine; the menu uses fuzzel, the bar uses Waybar.
- Packages come from Alpine (musl): software built for glibc distributions usually does not run.

## Recovering / going back to Android

Keep Samsung's firmware for your build (e.g. from [Bifrost](https://github.com/zacharee/Bifrost)). Flash the stock `recovery.img` and `vbmeta.img` back with heimdall and wipe USERDATA, or flash the full firmware. Knox stays tripped.

## Credits

- [vishalbala-nps](https://github.com/vishalbala-nps/linux) — SM-T735 device tree, panel driver, SM5714 fuel gauge, [firmware](https://github.com/vishalbala-nps/firmware-samsung-gts7xllite)
- [Marker284](https://github.com/Marker284/samsung-gts7xllite-display-touch) — touchscreen driver, panel fixes, GPU bring-up, porting notes
- [sm6350-mainline](https://github.com/sm6350-mainline/linux) and the Fairphone 4 postmarketOS port
- [postmarketOS](https://postmarketos.org) / Nura and [Alpine Linux](https://alpinelinux.org)
- [Omarchy](https://omarchy.org) by DHH — keybindings, menu structure, look and Tokyo Night theme

## License

Scripts and configs in this repo: MIT (see `LICENSE`). Kernel patches are GPL-2.0, like the kernel. Firmware is proprietary and is downloaded from its upstream, not included.
