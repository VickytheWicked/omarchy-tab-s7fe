# Hacking on the Galaxy Tab S7 FE

How to change the tablet yourself: its apps and settings, its desktop, and its kernel and drivers. It's the day-to-day workflow behind [PORTING.md](PORTING.md) (how it got here) and [RICING.md](RICING.md) (how it looks).

The paths below are the ones on my PC (`~/Work/android-debug`, `~/Work/omarchy-tab-s7fe`) and tablet (user `vansh`). Adjust them for yours.

## The mental model

The tablet has four layers. The lower the layer, the bigger the payoff and the worse a mistake:

| Layer | What's in it | Where it lives | If you break it |
|---|---|---|---|
| **4. Your desktop** | Hyprland, Waybar, menus, themes, `tablet-*` scripts | `~/.config`, `/usr/local/bin` | Fix it over SSH |
| **3. The OS** | Alpine packages (`apk`), services (OpenRC), system config | `/etc`, `/usr` | Fix it over SSH, as long as SSH still starts |
| **2. Kernel and drivers** | `vmlinuz`, modules (`.ko`), device tree (`.dtb`), initramfs | `/boot`, `/lib/modules`, packed into `boot.img` on the **RECOVERY** partition | Download mode + heimdall to put the old `boot.img` back |
| **1. Boot chain** | Samsung bootloader, VBMETA, partitions | eMMC/UFS partitions | Download mode; in the worst case, stock firmware |

Do as much as you can at the highest layer that works. Go down a layer only when you have to.

## Before you change anything: your safety net

Learn these before experimenting. Each step is the fallback for the one above it:

1. **Undo the file.** Before editing a config or script, copy it (`cp file file.bak`). Changes in this repo are under git, so `git diff` and `git checkout -- file` work too.
2. **Forced restart:** hold **Volume Down + Power** for about 10 s. Nothing can be damaged by it, but don't use it while the tablet is writing a kernel or doing its first-boot resize.
3. **Old kernel module:** keep the previous `.ko.zst` next to the new one (for example, `~/sm5714_fuelgauge.ko.zst.r6`) and copy it back if the new one misbehaves.
4. **Old boot image:** `/boot/boot.img.*` on the tablet, and `~/Work/android-debug/flash/r5-rollback` and `flash/r6-rescue` on the PC. To put one back without Linux running:
   - Power off, hold **Volume Up + Volume Down** while plugging in the USB cable, then short-press **Volume Up** on the warning screen (Download mode only accepts commands after that).
   - `heimdall flash --RECOVERY boot.img` on the PC.
5. **Back to Android:** `~/Work/android-debug/flash/restore-stock` has the stock recovery and vbmeta, and `~/Work/android-debug/firmware` has the full stock firmware.

**Rules I follow:**
- Change **one thing at a time**, and check it works before the next.
- Write down the old value before you change it. For a chip register, read it first.
- If something fails twice, stop and work out why instead of trying variations.
- Never flash an image you haven't verified. Compare the sha256 after writing, as `tablet-update` does.

## Connecting

```sh
ssh vansh@samsung-gts7xllite.local   # over Wi-Fi (avahi; the IP changes, the name doesn't)
ssh vansh@172.16.42.1                # over the USB cable (USB port in device mode)
```

- SSH accepts keys only, and only from the USB cable or the local network (`/etc/ssh/sshd_config.d/10-key-only.conf`, `/etc/nftables.d/49_ssh_local.nft`).
- `sudo` doesn't ask for a password on the tablet.
- `scp file vansh@samsung-gts7xllite.local:/tmp/` copies files over.

The tablet is **Alpine Linux** (postmarketOS edge), not Arch like Omarchy:

| On Arch / Omarchy | On the tablet |
|---|---|
| `pacman -S x` | `sudo apk add x` |
| `pacman -Rs x` | `sudo apk del x` |
| `pacman -Ss x` | `apk search x` |
| `pacman -Syu` | `tablet-update` (also rewrites RECOVERY if the kernel changed) |
| `systemctl restart x` | `sudo rc-service x restart` |
| `systemctl enable x` | `sudo rc-update add x default` |
| `journalctl -b` | `sudo dmesg` (kernel) and `/var/log/messages` (services) |

The shell is BusyBox `ash`, so some GNU flags don't exist (`ls --time-style`, `grep -P`), and scripts should be plain `sh`. `sudo apk add bash coreutils grep` if you need the GNU versions.

## Layer 4: the desktop

Edit the copy in the repo, then copy it to the tablet:

```sh
cd ~/Work/omarchy-tab-s7fe
$EDITOR dotfiles/.config/hypr/hyprland.conf
scp dotfiles/.config/hypr/hyprland.conf vansh@samsung-gts7xllite.local:.config/hypr/
ssh vansh@samsung-gts7xllite.local 'hyprctl reload'
```

- **Hyprland** applies most changes on `hyprctl reload`. A broken config shows an error bar at the top instead of crashing.
- **Try settings live first:** `hyprctl keyword general:gaps_out 4` changes a setting until the next reload. Once it looks right, put it in the file.
- **Waybar:** `tablet-waybar` keeps it running. Kill it and it restarts with the new config.
- **Menus:** `tablet-menu` is generated from Omarchy's menu definition by `tools/gen-tablet-menu.py`. Edit the generator, not the output.
- **Scripts:** `dotfiles/.local/bin/tablet-*` are installed to `/usr/local/bin` (`sudo install -m755 tablet-x /usr/local/bin/`).
- **Everything at once:** `./install.sh vansh@samsung-gts7xllite.local` copies all dotfiles and system files and reinstalls the packages.

Running a command from SSH inside the desktop session:

```sh
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-1
export HYPRLAND_INSTANCE_SIGNATURE=$(ls $XDG_RUNTIME_DIR/hypr | head -1)
hyprctl clients
```

Keep the hardware workarounds listed in [RICING.md](RICING.md#dont-touch-these-hardware-workarounds): no DPMS, no brightness animations, a software cursor, and matching rotation for the monitor and touchscreen.

**Design for touch:** there's no keyboard. Anything you add needs a way to reach it and a way to close it by tapping. A fuzzel menu blocks touches everywhere else on the screen, so every menu needs its own Close row.

## Layer 3: the OS

```sh
sudo apk add i2c-tools                 # install a package
rc-status                              # what's running
sudo rc-service bluetooth restart      # restart a service
sudo rc-update add avahi-daemon default  # start at boot
```

- **System files go in `system/`** in the repo, mirroring `/` (for example, `system/etc/local.d/dsi-clk-fix.start`), so a fresh install gets them too.
- **Boot-time scripts:** `/etc/local.d/*.start` runs at the end of boot (the `local` service).
- **Firewall:** nftables. Drop rules into `/etc/nftables.d/`, then `sudo nft -f /etc/nftables.nft`. If SSH goes wrong, test the rule over the USB cable first.
- **Kernel parameters at runtime:** `/sys/module/<module>/parameters/` (for example, `msm/parameters/xfer_skip_clk_rate`).

## Looking at the hardware (read-only, always safe)

Before changing anything at a lower layer, look at what's actually there:

```sh
sudo dmesg | tail -50                       # recent kernel messages
sudo dmesg | grep -iE 'error|fail|sm5714'   # problems, or one driver
lsmod                                       # loaded modules
cat /sys/class/power_supply/sm5714-fuelgauge/uevent   # battery: level, current, voltage, status, health
cat /sys/class/backlight/*/brightness
cat /sys/bus/iio/devices/iio:device0/in_*_input       # PMIC ADC: battery thermistor, system voltage
ls /sys/bus/i2c/devices/                    # chips on the I2C buses
```

Reading a chip's registers over I2C (`i2c-tools`):

```sh
sudo i2cget -f -y 0 0x49 0x0d     # bus 0, chip 0x49 (SM5714 charger), register 0x0d (STATUS1)
for r in $(seq 0 80); do printf "%02x:%s " $r $(sudo i2cget -f -y 0 0x49 $r | cut -c3-); done
```

- `-f` is needed because a driver owns the chip. Reading is safe, with one exception: **interrupt registers (0x00–0x05 on the charger) clear when read**, so read them once and save the result.
- **Save dumps of a working state and a broken state, then `diff` them.** That's how the charger bug was narrowed down (see [the charger example](#worked-example-the-stuck-charger)).

## Layer 2a: changing a driver module (no reboot)

When the change is inside one module (`=m` in the config), you can rebuild just that module and swap it in live. This is how the charger fix was tested.

**Requirement:** the build tree must be **exactly the build that's running** (same config, same `vmlinux`). Otherwise the tablet rejects the module (BTF/version mismatch). The tree at `~/Work/android-debug/build/linux-bc46d64b…` is the running `#12` build.

```sh
cd ~/Work/android-debug/build/linux-bc46d64b51988485fbaafdb24a80e3148bf1f0a3
$EDITOR drivers/power/supply/sm5714_fuelgauge.c

# build only this module (.git moved aside, or the kernel version gets a -g suffix)
mv .git ../.git-aside
make ARCH=arm64 LLVM=1 -j$(nproc) drivers/power/supply/sm5714_fuelgauge.ko
mv ../.git-aside .git

zstd -19 -f drivers/power/supply/sm5714_fuelgauge.ko -o /tmp/sm5714_fuelgauge.ko.zst
scp /tmp/sm5714_fuelgauge.ko.zst vansh@samsung-gts7xllite.local:/tmp/
```

On the tablet:

```sh
m=/lib/modules/$(uname -r)/kernel/drivers/power/supply/sm5714_fuelgauge.ko.zst
cp $m ~/sm5714_fuelgauge.ko.zst.bak          # backup first
sudo install -m644 /tmp/sm5714_fuelgauge.ko.zst $m
sudo depmod
sudo rmmod sm5714_fuelgauge && sudo modprobe sm5714_fuelgauge
sudo dmesg | tail                            # did it load? any warnings?
```

- **Check the module isn't also in the initramfs** (`zstd -dc /boot/initramfs | cpio -t | grep name`). If it is, run `sudo mkinitfs` and rewrite RECOVERY (Layer 2b), or the old copy loads at boot.
- **Some modules can't be unloaded safely:** the display (`msm`), the panel and touch drivers, and the USB controller if you're connected over USB. For those, install the module and reboot instead.

## Layer 2b: a new kernel or device tree

Needed for built-in code (`=y`), device tree changes, or kernel config changes.

**On the PC:**

```sh
cd ~/Work/android-debug/build/linux-bc46d64b51988485fbaafdb24a80e3148bf1f0a3
mv .git ../.git-aside
make ARCH=arm64 LLVM=1 -j$(nproc)            # Image, dtbs and modules
make ARCH=arm64 LLVM=1 INSTALL_MOD_PATH=../stage-new modules_install
mv ../.git-aside .git
```

Copy these to the tablet: `arch/arm64/boot/vmlinuz`, `arch/arm64/boot/dts/qcom/sm7225-samsung-gts7xllite.dtb` and the **whole** `../stage-new/lib/modules/<version>` directory. **The modules must come from the same build.** Older ones are rejected, and you lose touch, battery, Wi-Fi and the firewall.

**On the tablet:**

```sh
sudo cp /boot/boot.img /boot/boot.img.prev          # fallback
sudo install -m644 /tmp/vmlinuz /boot/vmlinuz
sudo install -m644 /tmp/new.dtb /boot/dtbs/qcom/sm7225-samsung-gts7xllite.dtb
sudo cp -a /tmp/modules/<version> /lib/modules/      # the modules from the same build
sudo mkinitfs                                        # rebuilds /boot/boot.img

# Linux boots from RECOVERY: write the image there and verify it
sudo dd if=/boot/boot.img of=/dev/disk/by-partlabel/recovery bs=4M conv=fsync
sync
size=$(stat -c %s /boot/boot.img)
[ "$(sudo head -c $size /dev/disk/by-partlabel/recovery | sha256sum)" = "$(sha256sum < /boot/boot.img)" ] && echo OK || echo MISMATCH
```

Reboot only on `OK`. On `MISMATCH`, write it again. If the new kernel doesn't come back, use Download mode and `heimdall flash --RECOVERY boot.img` with the previous image (see [the safety net](#before-you-change-anything-your-safety-net)).

**Also keep in mind:**
- **Keep a copy of every image that booted** (`flash/r5-rollback`, `flash/r6-rescue`, …).
- **Patch 0011 must stay off at boot:** `/etc/local.d/dsi-clk-fix.start` turns it on 60 s after boot. Turning it on at boot froze the tablet.
- **Never hold a volume key while Linux starts:** it drops into the initramfs debug shell. If you end up there, don't run `pmos_continue_boot` remotely.

## Saving kernel changes as patches

The build tree is a git repo with **one commit per patch** (0001–0012). After a change works:

```sh
cd ~/Work/android-debug/build/linux-bc46d64b51988485fbaafdb24a80e3148bf1f0a3
git add -p && git commit                     # explain what and why: future you will need it
git format-patch -1 --stdout > ~/Work/omarchy-tab-s7fe/pmaports/device/testing/linux-samsung-gts7xllite/0013-short-name.patch
```

Then, in `pmaports/device/testing/linux-samsung-gts7xllite/APKBUILD`:
1. Add the patch to `source=`.
2. Bump `pkgrel`.
3. Add its checksum: `sha512sum 0013-short-name.patch`, or run `pmbootstrap checksum linux-samsung-gts7xllite`.

A fresh `pmbootstrap install` then builds the same kernel you're running.

## Writing a driver without a datasheet

Samsung doesn't publish datasheets for these chips. What worked here:

1. **Read the stock Android kernel source.** It's GPL, so Samsung publishes it. For this tablet: [daviddean-x/android_kernel-gts7xllite](https://github.com/daviddean-x/android_kernel-gts7xllite). Register maps are in `include/linux/mfd/...`, and the behaviour you need to copy is in the driver `.c` files. Copies of the SM5714 files are in `~/Work/android-debug/ports/compare/sm5714/stock/`.
2. **Read the stock device tree overlays** (dtbo from the firmware) for which chip sits on which bus and at which address, plus Samsung's limits (currents, voltages, temperatures).
3. **Check the community ports:** vishalbala-nps/linux and Marker284/samsung-gts7xllite-display-touch. Someone may already have done part of it.
4. **Test by hand before writing code.** Read a register, change one bit with `i2cset`, and watch what happens. Our driver rewrites most charger settings every 10 s, which undoes any experiment within seconds.
5. **Copy stock's order of operations.** For example, stock turns charging on at a 500 mA input limit and then raises it. Chips often have reasons for that you can't see.

**Don't write** to registers you can't name from the stock source. Above all, never write the hidden option and OTP registers (charger 0x49/0x4A/0x51 indirect access): they can permanently change the chip.

### Worked example: the stuck charger

1. **Symptom:** plugged in, "Not charging", battery at 11%.
2. **Look:** `uevent` showed about 8 mA flowing into the battery. STATUS1 said power was present, and STATUS2 said not charging. The ADC showed the system rail at 4.41 V against a 3.69 V battery, so the charger was running the tablet but not charging the battery.
3. **Rule out the gauge:** with the charger suspended for 2 s, the battery read −199 mA, so the gauge was right.
4. **Compare with stock:** stock's charge enable is `ENQ4FET` (CNTL1 bit 3), which our driver never touched. The interrupt flags showed the fast-charge timer had expired.
5. **Try by hand:** setting the bit, toggling it and suspending the charger all failed. A full power cycle fixed it.
6. **Diff the dumps:** the control registers were identical when stuck and when charging, so the stuck state is internal to the chip.
7. **Fix in the driver (patch 0012):** set the enable bit ourselves, stop charging at full like stock does, and restart the charge cycle every 3 hours so the timer never expires. Hot-swapped as in [Layer 2a](#layer-2a-changing-a-driver-module-no-reboot), then the failure was reproduced by clearing the bit by hand, and the driver recovered from it.

## Don't do these

| Don't | Why |
|---|---|
| Use DPMS (`hyprctl dispatch dpms off`, idle daemons that call it) | The panel can stay black until a reboot. Turn the backlight off instead. |
| Animate brightness or send bursts of brightness changes | Each change is a command over the display link. Bursts used to corrupt the picture or freeze the tablet. |
| Enable the PM7250B VBUS / OTG regulator | Two power sources on the USB port. OTG belongs to the SM5714, which isn't driven yet. |
| Install modules from a different build | They're rejected: no touch, battery, Wi-Fi or firewall. |
| Flash anything without checking its sha256 | A half-written RECOVERY doesn't boot. |
| `pkill -f` with a pattern that appears in your own SSH command | It kills your own shell. |
| Leave `udiskie --automount` running during `pmbootstrap install` (PC) | It mounts the image halfway through and you get a rootfs without `/sbin/init`. |
| Write I2C registers you can't name | Some are one-time-programmable. |
| Change the charger's current or voltage limits without watching the temperature | That's the battery. The driver already cuts charging to 1 A above 41 °C and stops it above 50 °C. Keep those limits. |

## Working with Claude Code on this

Claude Code does all of the above over SSH, with the same safety net. What makes it go well:
- **Say what you see, not what you think is wrong:** "Not charging with both chargers" is better than "the driver is broken".
- **Say how the tablet is connected** (USB cable or Wi-Fi) and **whether you're near it**. Some fixes need a button press.
- **State your limits up front:** no keyboard, which changes are OK without asking, and which you want to confirm first (anything that flashes, reboots or burns a fuse).
- Ask it to **write findings into these docs** and to **save kernel changes as numbered patches**, so the repo stays the single record.
