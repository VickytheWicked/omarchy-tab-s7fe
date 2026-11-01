# The tablet's storage and filesystem

What's stored where on the Galaxy Tab S7 FE running postmarketOS: the flash chip and its partitions, how Linux lives inside Android's data partition, and the important folders and files from `/` down to your home directory. The numbers are from my tablet (128 GB model) on kernel r6.

For changing things, see [HACKING.md](HACKING.md). For the look, see [RICING.md](RICING.md).

## The big picture

```
UFS flash chip (128 GB)
├── sda (118.8 GB): Samsung/Qualcomm partitions
│   ├── boot      sda25   Android's kernel (left alone; Android still boots from it)
│   ├── recovery  sda26   ← Linux's boot.img (kernel + initramfs + device tree)
│   ├── super     sda27   Android system/vendor (7.8 GB, unused by Linux)
│   ├── dtbo      sda33   Android device tree overlays (unused by Linux)
│   ├── modem, dsp, efs, persist, … (firmware and calibration; never touched)
│   └── userdata  sda34   ← the whole Linux install (109.4 GB)
│         └── a disk image with its own partition table, mounted as loop0
│               ├── loop0p1  480 MB  ext2  → /boot
│               └── loop0p2  108.9 GB ext4 → /
└── sde (384 MB): more boot-chain partitions (vbmeta, bluetooth, …)
```

**How it boots:**
1. The Samsung bootloader loads the kernel and initramfs from **RECOVERY**. That's why Linux starts when the tablet boots "into recovery", and why kernel updates are written there.
2. The initramfs finds the disk image inside **USERDATA**, sets it up as `/dev/loop0`, and mounts `loop0p2` as `/` and `loop0p1` as `/boot`.
3. OpenRC starts the services, and tinydm starts Hyprland.

Android is still installed: BOOT and SUPER are untouched. It just has no data partition any more.

## The partitions on the flash chip

Named partitions live in `/dev/disk/by-partlabel/` (75 of them). The ones worth knowing:

| Partition | Device | What it holds | Touch it? |
|---|---|---|---|
| `recovery` | sda26 | **Linux's boot image** (`/boot/boot.img` copied here) | Yes, only by writing a verified `boot.img` (`tablet-update` does this) |
| `userdata` | sda34 | **The Linux root and boot filesystems** (as a disk image) | Only through the mounted `/` and `/boot` |
| `boot` | sda25 | Android's kernel | No: it's your way back to Android |
| `super` | sda27 | Android system, vendor and product (dynamic partitions) | No |
| `dtbo` | sda33 | Android device tree overlays, a reference for hardware facts | Read only (it's how the charger chip addresses were found) |
| `vbmeta` | sde21 | Android Verified Boot data, flashed to allow an unsigned RECOVERY | No |
| `modem`, `dsp`, `apnhlos` | sda24, sda17, sda19 | Qualcomm firmware (Linux uses its own copies in `/lib/firmware`) | No |
| `efs`, `sec_efs` | sda6, sda9 | **IMEI, Wi-Fi/Bluetooth MAC addresses, calibration.** Unique to this tablet and can't be recreated | **Never.** Back up with `dd` before any experiment near it |
| `persist` | sda5 | Sensor and radio calibration | Never |
| `param` | sda7 | Bootloader settings and boot logo | No |
| `bluetooth` | sde5 | Bluetooth firmware for Android | No |
| `cache`, `misc` | sda30, sda10 | Android recovery and update scratch space | No |

Rule of thumb: **only `recovery` and `userdata` belong to Linux.** Everything else belongs to the bootloader or Android, and some of it is irreplaceable.

## `/boot`: the boot partition (480 MB, ext2)

Mounted `nodev,nosuid,noexec`. About 265 MB is used, mostly by saved images.

| File | What it is |
|---|---|
| `vmlinuz` | The kernel |
| `initramfs` | The early-boot filesystem: finds and mounts the root filesystem, handles the volume-key debug shell |
| `sm7225-samsung-gts7xllite.dtb` | **The device tree:** describes the tablet's hardware (panel, touch, charger, buses) for the kernel |
| `dtbs/qcom/*.dtb` | Device trees for every Qualcomm board the kernel supports. Only the gts7xllite one is used |
| `boot.img` | `vmlinuz` + `initramfs` + `dtb` packed together in Android boot-image format by `mkinitfs`. **This is what goes on RECOVERY** |
| `boot.img.r5`, `.r6`, `.r1-good`, `.pre-otg`, `.prev-update` | **Saved earlier images.** Your rollback points. `tablet-update` refreshes `.prev-update` |
| `vmlinuz.r5`, `*.dtb.r1-good` | Saved earlier kernels and device trees |

Each saved image is about 24 MB. Delete old ones only when `/boot` gets full, and keep at least the last one that booted.

## `/`: the root filesystem (109 GB, ext4)

The tablet runs **Alpine Linux** (postmarketOS edge) with BusyBox and OpenRC. On this tablet about 6 GB is used and 94 GB is free.

The tree follows the usual Linux layout. `/bin`, `/sbin` and `/lib` are links into `/usr`.

| Folder | What's in it |
|---|---|
| `/usr` | Installed software (2.9 GB). Managed by `apk`; don't edit by hand |
| `/usr/local` | Your own system-wide additions: the `tablet-*` scripts are in `/usr/local/bin` |
| `/etc` | System configuration (details below) |
| `/home/vansh` | Your files and per-user configuration (details below) |
| `/root` | Root's home |
| `/boot` | The boot partition (above) |
| `/lib/modules/<version>` | Kernel modules (`.ko.zst`) for the running kernel |
| `/lib/firmware` | Firmware loaded into chips at runtime (details below) |
| `/var` | Data that changes: package cache, logs, service state |
| `/tmp` | Temporary files, **in RAM** (up to 2.6 GB). Emptied on every boot |
| `/run` | Runtime state in RAM: PID files, sockets, your session directory `/run/user/10000` |
| `/media`, `/mnt` | Mount points for USB drives and manual mounts |
| `/opt`, `/srv` | Empty; for software installed outside `apk` |
| `/lost+found` | Pieces of files rescued by `fsck` after a crash. Normally empty |
| `/proc`, `/sys`, `/dev` | Virtual: the kernel's view of processes, hardware and devices (details below) |

### `/etc`: system configuration

| Path | What it controls |
|---|---|
| `fstab` | Which filesystems mount where (`/` and `/boot` by UUID) |
| `deviceinfo` | Local overrides of the device settings, here the **kernel command line**: panel parameters, log level |
| `/usr/share/deviceinfo/device-samsung-gts7xllite` | The device package's settings: device tree name, boot-image offsets, `flash_method=heimdall-bootimg`, `drm=true` |
| `mkinitfs/` | What goes into the initramfs |
| `apk/world` | **The packages you asked for** (85). `apk` installs these and their dependencies |
| `apk/repositories` | Where packages come from: postmarketOS main and Alpine edge main/community/testing |
| `runlevels/boot`, `runlevels/default` | **Which services start at boot** (links to `init.d` scripts). Change with `rc-update` |
| `init.d/` | Service scripts (`rc-service <name> start/stop/restart/status`) |
| `conf.d/` | Settings for those services |
| `local.d/*.start` | Your scripts run at the end of boot: `dsi-clk-fix.start` turns on the display clock fix 60 s after boot |
| `modprobe.d/` | Module options and blacklists |
| `modules-load.d/` | Extra modules to load at boot (empty) |
| `sysctl.conf`, `sysctl.d/` | Kernel runtime settings |
| `ssh/sshd_config.d/10-key-only.conf` | SSH accepts keys only, no passwords |
| `nftables.nft`, `nftables.d/49_ssh_local.nft` | Firewall: SSH only from USB and the local network |
| `sudoers.d/90-vansh-nopasswd` | `sudo` without a password for `vansh` |
| `elogind/logind.conf.d/10-power-key.conf` | The power button doesn't shut down; the desktop handles it |
| `NetworkManager/` | Wi-Fi settings; saved networks are in `system-connections/` (root only, contains passwords) |
| `bluetooth/main.conf` | Bluetooth auto-enable and reconnect settings |
| `chromium/chromium.conf` | Chromium flags for Wayland and touch |
| `hostname`, `hosts` | `samsung-gts7xllite` |
| `passwd`, `group`, `shadow` | Users, groups, password hashes |
| `os-release`, `alpine-release` | Which OS and version |

The repo's `system/` folder mirrors the files in `/etc` and `/usr` that were changed for this port, so `install.sh` can recreate them.

### `/lib/firmware`: firmware for the chips

The kernel loads these into the chips' own processors when their drivers start:

| Path | For |
|---|---|
| `qcom/sm7225/Samsung/gts7xllite/adsp.mbn`, `adsp*.jsn` | Audio DSP |
| `…/cdsp.mbn`, `cdspr.jsn` | Compute DSP |
| `…/modem.mbn`, `modem_pr/`, `modemr.jsn` | Modem (LTE) and the **Wi-Fi firmware** (`wlanmdsp.mbn`), which runs on the modem processor |
| `…/a615_zap.mbn`, `qcom/a619_gmu.bin`, `qcom/a630_sqe.fw` | GPU (Adreno 619) |
| `…/lagoon_ipa_fws.mbn` | Network packet accelerator (IPA) |
| `qca/crbtfw32.tlv.zst`, `crnv32u.bin.zst` | Bluetooth (from `linux-firmware-qca`) |

The `gts7xllite` files are Samsung-signed and come from the stock firmware. Without them, Wi-Fi, GPU and DSPs don't start.

### `/var`: changing data

| Path | What it is |
|---|---|
| `cache/apk` | Downloaded packages (about 920 MB). Safe to clear: `sudo apk cache clean` |
| `log/dmesg` | Kernel log saved at boot |
| `log/logbookd.db` | The system log database (read with `logread`; see the note below) |
| `log/apk.log` | Package install and remove history |
| `lib/` | Service state: NetworkManager leases, Bluetooth pairings (`lib/bluetooth/`), chrony time data |
| `backups-modules-r5.tar` | Modules saved before the r6 kernel update; can go once r6 has proven itself |

> **Note (2026-11-01):** the log service `logbookd` is currently crashed (`rc-service logbookd status`), and the database hasn't been written since 25 October. Until it's fixed, use `dmesg` for kernel messages. Services that log to the system log aren't being recorded.

### Swap

There's no swap partition. `postmarketos-zram-swap` makes an **8 GB compressed swap in RAM** (`/dev/zram0`). This is fast and spares the flash from wear.

## Your home directory: `/home/vansh` (about 2.5 GB)

| Path | What it is |
|---|---|
| `.config/hypr/hyprland.conf` | **The desktop:** monitor and touch rotation, keybindings, window rules, autostart (`exec-once`) |
| `.config/hypr/hypridle.conf` | Idle: backlight off after 15 min (backlight only, never DPMS) |
| `.config/hypr/hyprlock.conf` | The lock screen |
| `.config/waybar/config.jsonc`, `style.css` | The top bar: modules, tap actions, colours |
| `.config/fuzzel/fuzzel.ini` | The launcher and menus (row size for touch) |
| `.config/mako/config` | Notifications |
| `.config/alacritty/`, `.config/foot/` | Terminals; `theme.toml`/`theme.ini` hold the colours |
| `.config/gtk-3.0/`, `.config/gtk-4.0/settings.ini` | Theme, icons, font and dark mode for GTK apps |
| `.config/btop/` | The system monitor and its themes |
| `.config/mimeapps.list` | Which app opens which file type |
| `.config/VSCodium/`, `.config/chromium/` | App settings and profiles (large; not in the repo) |
| `.config/rc/runlevels` | Per-user OpenRC services (currently unused) |
| `.local/bin/` | Your scripts (`tablet-*` originals; installed copies are in `/usr/local/bin`) |
| `.local/share/wallpapers/` | Wallpapers. **`current`** is a link to the active one; the picker changes it |
| `.local/share/applications/` | Your app launcher entries (`.desktop` files), such as the USB mode toggles |
| `.local/share/fonts/` | Extra fonts (run `fc-cache -f` after adding) |
| `.local/share/keyrings/` | Saved passwords and secrets (GNOME keyring) |
| `.ssh/authorized_keys` | Keys allowed to log in. **If you empty this, you lose SSH** (passwords are off) |
| `.claude/`, `.claude.json` | Claude Code on the tablet: settings, history, login (`.credentials.json`: keep private) |
| `.ash_history` | Your shell history |
| `.cache/` | Thumbnails and app caches; safe to delete |

Hidden files (starting with `.`) only show with `ls -a`.

## The virtual filesystems: `/proc`, `/sys`, `/dev`

These aren't on the flash at all. The kernel generates them, so they show the live state of the hardware. Most of what you'd inspect while debugging is here:

| Path | What it shows or controls |
|---|---|
| `/proc/cpuinfo`, `/proc/meminfo` | CPU and memory |
| `/proc/mounts` | What's mounted right now |
| `/proc/swaps` | The zram swap |
| `/sys/class/power_supply/sm5714-fuelgauge/` | **Battery:** `capacity`, `status`, `health`, `current_now` (µA; + is charging), `voltage_now` (µV), `temp` (0.1 °C) |
| `/sys/class/backlight/*/brightness` | Screen brightness |
| `/sys/bus/iio/devices/iio:device0/` | PMIC ADC: battery thermistor, die temperature, system voltage |
| `/sys/class/thermal/thermal_zone*/temp` | CPU, GPU and other temperatures (m°C) |
| `/sys/bus/i2c/devices/` | Chips on I2C: `0-0071` fuel gauge, `0-0049` charger |
| `/sys/class/usb_role/a600000.usb-role-switch/role` | USB port mode: `device` or `host` (`tablet-usb-mode`) |
| `/sys/module/<name>/parameters/` | Live module settings (for example `msm/parameters/xfer_skip_clk_rate`) |
| `/sys/block/loop0/loop/backing_file` | Confirms `/` comes from `/dev/sda34` (USERDATA) |
| `/dev/disk/by-partlabel/` | Partitions by name (`recovery`, `userdata`, …) |
| `/dev/dri/` | The GPU and display (used by Hyprland) |
| `/dev/input/` | Touchscreen, buttons, keyboards |
| `/dev/i2c-*` | Raw I2C buses (for `i2cget`) |

Writing to `/sys` changes hardware immediately and is gone after a reboot. That makes it the safe place to experiment before making something permanent.

## On the PC

| Path | What it is |
|---|---|
| `~/Work/omarchy-tab-s7fe/` | **This repo:** the source of truth for everything installed on the tablet |
| `…/dotfiles/` | The home-directory configs (mirrors `/home/vansh`) |
| `…/system/` | Changed system files (mirrors `/etc` and `/usr`) |
| `…/pmaports/device/testing/` | The kernel, device and firmware packages with all kernel patches |
| `…/tools/` | Menu generator and theme switcher |
| `~/Work/android-debug/build/linux-bc46d64b…/` | The kernel build tree (git, one commit per patch); matches the running kernel |
| `~/Work/android-debug/flash/` | Flashable images: `r5-rollback`, `r6-rescue` and `restore-stock` (back to Android) |
| `~/Work/android-debug/firmware/` | The stock Samsung firmware and its extracted images |
| `~/Work/android-debug/ports/compare/sm5714/stock/` | Samsung's charger driver source, used as a reference |
| `~/.local/var/pmbootstrap/` | pmbootstrap's work directory (build chroots, package cache) |

## Space and cleanup

```sh
df -h / /boot                 # free space
du -sh ~/.cache /var/cache/apk  # the usual space hogs
sudo apk cache clean          # remove old downloaded packages
rm -rf ~/.cache/*             # app caches (apps recreate them)
```

On `/boot`, remove old `boot.img.*` copies only when it gets full. Keep the last image that booted.
