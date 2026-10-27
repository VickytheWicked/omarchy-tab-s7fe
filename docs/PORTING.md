# How the Galaxy Tab S7 FE was converted to Linux

The full story of turning a Samsung Galaxy Tab S7 FE (SM-T735) from Android into a mainline Linux tablet with an Omarchy-style Hyprland desktop: the decisions, the dead ends, and how each problem was tracked down. For just the steps, see [Installing](../README.md#installing) in the README.

## The starting point

| | |
|---|---|
| Device | Galaxy Tab S7 FE with mobile data, SM-T735, codename `gts7xllite`, Indian model (`INU`, international `XX` firmware) |
| SoC | Qualcomm SM7225 (Snapdragon 750G), platform `lito`; a close relative of the SM6350 in the Fairphone 4 |
| Software | Android 14 / One UI 6.1, Samsung's Linux 4.19 kernel |
| Memory / storage | 5.3 GB RAM / 128 GB UFS |
| Screen | 12.4" 2560 × 1600 LCD, FocalTech FT8203 panel + touch controller, Display Stream Compression |

**The goal**: the same desktop as on the laptop, which runs [Omarchy](https://omarchy.org) (Arch Linux + Hyprland).

Omarchy itself can't run here. It's an installer for x86-64 PCs with UEFI, and this is an ARM tablet with Samsung's own bootloader. The realistic options were:

1. **Termux + a Linux userland under Android.** No risk, but no real Hyprland: Android stays in charge of the screen, input and power.
2. **Native Linux.** Unlock the bootloader and boot a real Linux kernel. Permanent cost: Samsung's Knox warranty fuse burns.

We went native.

## Step 1: Finding a kernel that knows the hardware

There is no official postmarketOS port for this tablet. What exists is **community work outside the official trees**:

- [**vishalbala-nps/linux**](https://github.com/vishalbala-nps/linux): a fork of [sm6350-mainline](https://github.com/sm6350-mainline/linux) with the SM-T735 **device tree** (the file that tells the kernel what hardware sits where) and a driver for the **FT8203 display panel**. A separate `sm5714` branch has a work-in-progress battery fuel-gauge driver.
- [**Marker284/samsung-gts7xllite-display-touch**](https://github.com/Marker284/samsung-gts7xllite-display-touch): the **touchscreen driver**, panel stability fixes, GPU bring-up, and porting notes.

That's why this is a **mainline** port. It runs the current upstream Linux (7.2) plus a few patches, not Samsung's old 4.19 Android kernel. Display, touch and the GPU were reported working; **charging was not**, and audio, camera, S Pen and sensors were not done.

One hardware caveat: Samsung shipped this tablet with two different panels. Only the FocalTech FT8203 works; the Himax HX83121A has no driver. You only find out which one you have when Linux boots. (This tablet turned out to have the FT8203.)

## Step 2: Packaging it for postmarketOS

[postmarketOS](https://postmarketos.org) (now also called Nura) is an Alpine Linux-based distribution for phones and tablets. Its tool `pmbootstrap` builds a whole system image from three per-device packages, which are in [`pmaports/`](../pmaports/device/testing/):

| Package | What it holds |
|---|---|
| `linux-samsung-gts7xllite` | The kernel: vishalbala's `panel` branch at a fixed commit, our patches, and a config based on the Fairphone 4's |
| `firmware-samsung-gts7xllite` | Closed-source firmware the chips need: modem, DSPs, Wi-Fi, GPU, touchscreen |
| `device-samsung-gts7xllite` | `deviceinfo`: how to build the boot image (Samsung header format, 4096-byte sectors, the `SEANDROIDENFORCE` trailer the bootloader expects), the kernel command line, and which partitions to use |

### Where Linux lives on the tablet

Android's partitions are reused rather than repartitioning the disk:

```
BOOT      Android's kernel        untouched: a normal power-on still starts Android's kernel
RECOVERY  Linux kernel + initramfs   started with Volume Up + Power
VBMETA    empty, verification off    so the bootloader accepts a non-Samsung image
USERDATA  Linux root filesystem      (Android's data is erased)
```

So Android's kernel is still there, but without its data partition it no longer gets far. Going back means flashing stock RECOVERY and VBMETA and wiping USERDATA (see the README).

## Step 3: Unlocking the bootloader

1. Settings → Developer options → **OEM unlocking**. On Samsung this only appears once the device has been online and signed in for about a week, and **Knox Guard** (Samsung's remote-lock service for financed devices) has released it (`knox.kg.state = Completed`).
2. Download mode (power off, hold Volume Up + Volume Down, plug in USB), **long-press Volume Up**, confirm. The tablet wipes itself.
3. After the wipe, Knox Guard re-checks online (`KG STATUS: CHECKING`). It's best to let Android boot once, online, until that settles.

The **Knox warranty fuse** (`WARRANTY VOID`) is a one-time hardware fuse. It burns the first time the tablet starts non-Samsung software, and it never goes back to 0. Secure Folder, Samsung Pass, Wallet and Health stop working for good. On this tablet it now reads `warranty_bit=1`.

## Step 4: Flashing, in two stages

Samsung tablets have no `fastboot`. Images go in through **Download mode**, using Samsung's protocol:

- **odin4** (Samsung's Linux tool) never completed its USB handshake with this tablet.
- **heimdall** (open-source) worked, including the 1.45 GB root filesystem.

Two Download-mode quirks cost time. The USB handshake only works on the real *Downloading…* screen, after a **short** press of Volume Up on the warning screen (a long press offers to *re-lock* the bootloader). And a failed odin4 attempt left the session broken, so heimdall needed a fresh Download-mode start.

To keep risk low, flashing was split:

- **Stage 1: RECOVERY + VBMETA only.** Android and its data stayed intact. Booting recovery started our kernel, which found no root filesystem and stopped in postmarketOS's **debug shell**, reachable over USB networking at `172.16.42.1`. That proved the kernel, device tree and USB worked, and the screen showed the boot log: the FT8203 panel worked.
- **Stage 2: USERDATA**, the full system. This wiped Android's data.

## Step 5: The first boot panic

The first full boot ended in a **kernel panic: no `/sbin/init`**. The root filesystem on the tablet held only 6,488 files instead of about 8,600.

The first theory was wrong: a forced restart during the first-boot filesystem resize. Re-flashing gave a panic with *identical* numbers, which pointed at the image, not the tablet. Unpacking the image on the laptop showed it really was incomplete.

**Root cause:** the laptop's desktop (Omarchy) runs `udiskie --automount`. While `pmbootstrap install` was writing the image, udiskie spotted the image's partitions as new drives and mounted them. pmbootstrap's writes went into udiskie's mounts instead of the image file.

**Fix:** pause udiskie during `pmbootstrap install`, and always check the image before flashing (does `/sbin/init` exist, is the file count right).

## Step 6: Bringing up the hardware

With a booting system, each piece of hardware became its own small investigation. Each fix is a patch in [`pmaports/device/testing/linux-samsung-gts7xllite/`](../pmaports/device/testing/linux-samsung-gts7xllite/).

### Display: vertical streaks and broken glyphs (patch 0004)

The picture had streaks and garbled letters. The panel uses **Display Stream Compression (DSC)**: the SoC compresses each frame and the panel decompresses it. The driver enabled DSC *block prediction*, which this panel decodes differently. Turning it off fixed the picture (vishalbala later made the same change upstream).

The image was also **upside down**. Hyprland rotates the output (`transform 3`), and the touchscreen gets the same transform so taps land in the right place.

### Power-off that wouldn't (patch 0005)

The tablet couldn't power off: it hung or came straight back. The mainline device tree placed the **PMK8350** power-management chip at SPMI address (SID) 0, on top of the **PM6350**, which really lives there. Samsung's stock device tree, extracted from the firmware, shows the PMK8350 at **SID 6**. Changing that one number fixed power-off, removed a duplicate power-key device, and made the real-time clock readable.

### Touchscreen (patches 0001 and 0003)

The FT8203 is one chip for both display and touch, and touch is read over **SPI**. Marker284's touch driver went in as patch 0001. The device tree lacked the SPI controller (`spi6`) the touch chip hangs off, which patch 0003 adds along with the touch node.

### Battery level (patch 0006)

Battery percentage, voltage, current and temperature come from the **SM5714** fuel gauge on I2C. vishalbala's work-in-progress driver had leftover merge-conflict markers and no charging status. Patch 0006 is that driver, cleaned up.

### Wi-Fi and Bluetooth

Wi-Fi (WCN3990) worked with the firmware package. Bluetooth needed Qualcomm's `crbtfw32.tlv`/`crnv32u.bin` from `linux-firmware-qca`, now a dependency of the device package. `tablet-bt-reconnect` reconnects paired keyboards and mice at login.

### USB host mode (patch 0007)

USB defaults to *device* mode, for SSH over the cable. Patch 0007 makes the USB controller switchable (`tablet-usb-mode host|device`). Host mode works, but the 5 V the port must supply to a keyboard comes from the **SM5714's boost converter**, which nothing drives yet. Use a powered OTG hub for now.

### Charging (patch 0008)

"Plugged in, still discharging": the bootloader leaves the SM5714 charger at **500 mA**, while the screen alone draws about 1.5 A. **Samsung's GPL kernel source** (their charger driver) gave the register map and register encodings. Samsung's device tree gave the stock limits: 1.8 A input, 2.1 A charge, 4.38 V full. Patch 0008 polls the charger every 10 s, applies those limits, follows Samsung's temperature rules (reduce above 41 °C, stop above 50 °C or below 0 °C), keeps the charger's safety watchdog fed, and reports charging from the charger's own status bits. No fast charging: the SM5440 direct charger and USB-PD negotiation aren't driven.

### Black screen with the backlight on

After the screen was switched off and on, it sometimes stayed black with the backlight lit. Switching the display off (DPMS) runs the panel's power-down path, where the **touch driver pulses the reset line it shares with the panel**. Because the panel driver keeps the panel powered (`keep_powered`, a stability fix from Marker284), the panel is never re-initialised afterwards. The power button and idle now **only turn the backlight off** (`tablet-display-toggle`). DPMS is never used.

### White grain and freezes on brightness changes (kernel r6)

Every brightness change briefly garbled the picture with white grain, logged as `dsi_err_worker: status=5` (DSI timeout + FIFO error). Several in a row could freeze the tablet.

Brightness is a command sent to the panel over the same **DSI link** that streams the pixels. The display driver waits for the end of a frame and then **sleeps another 2–4 ms** before sending a command, which assumes a long gap between frames. This panel's gap (vertical blanking) is 37 lines, about **0.24 ms**. So every brightness command landed in the middle of the next frame, as a slow low-power transfer, and collided with the pixel stream. The r6 kernel sends the command right at the end of the frame when the blanking is that short.

### Charging that flip-flopped (kernel r6)

The charger switched between full and reduced charging every 10 seconds, 669 times in one boot. Raising the charge current from 1.0 to 1.7 A raised the "battery temperature" by 2.7 °C within 6 seconds, faster than any battery can heat. The reading came from the **SM5714 package itself, which is also the charger**, so the temperature limit was reacting to the charger's own heat. Samsung's device tree showed where stock Android really reads battery temperature: a **thermistor on the PM6150L PMIC's ADC** (channel `0x53`). The r6 kernel describes that channel and uses it, falling back to the old reading if it's ever implausible.

## Step 7: The desktop

With hardware working, the console system became an Omarchy look-alike:

- **Hyprland** started at boot through tinydm autologin, inside `dbus-run-session` (`system/usr/share/wayland-sessions/hyprland-dbus.desktop`).
- **Omarchy's config, translated.** Omarchy's Lua-based Hyprland defaults on the laptop were translated into Hyprland's own config syntax: same keybindings, gaps, animation curves and Tokyo Night colours.
- **Menu.** Omarchy's menu is defined in `omarchy-menu.jsonc`. `tools/gen-tablet-menu.py` turns that definition into `tablet-menu`, a fuzzel-based menu with tablet-appropriate actions (Alpine's `apk` instead of `pacman`, for example).
- **Waybar** replaces omarchy-shell, which isn't packaged for Alpine. It has the same modules plus touch buttons: menu, close window, on-screen keyboard, system menu.
- **Touch, not mouse.** Taps outside fuzzel never reach the bar while fuzzel is open (verified by logging), so every menu level got **Close** and **Back** rows. The on-screen keyboard is **squeekboard**, which pops up by itself in text fields (Wayland text-input-v3; Chromium needs `--enable-wayland-ime`), and Wi-Fi/Bluetooth are the touch-friendly nm-applet and blueman tray icons instead of terminal tools. The bar and menu rows are 44 px, about 7.5 mm, a comfortable finger target.
- **Mouse limited to the top half of the screen**: the display hardware's cursor plane is misplaced on a rotated panel, so Hyprland draws the cursor in software (`cursor:no_hardware_cursors`).
- **Developer tools**: Chromium, VSCodium and Claude Code. Alpine's VSCodium ships the terminal component (`node-pty`) without a Linux binary, so `tablet-fix-vscodium-terminal` builds one, and `tablet-update` rebuilds it after upgrades.
- **Updates**: `tablet-update` runs `apk upgrade`. A kernel update only rewrites `/boot/boot.img`, but the tablet boots from the RECOVERY partition, so the script also copies the new image to RECOVERY and verifies it.

## Step 8: Updating the kernel over Wi-Fi

Later kernel updates don't need Download mode at all:

1. Build the kernel on the PC (`make ARCH=arm64 LLVM=1` with the package's config and patches).
2. Copy the kernel, modules and device tree over SSH.
3. On the tablet, rebuild `boot.img` and write it to RECOVERY, keeping the previous image as a fallback.
4. Reboot. If the new kernel doesn't boot, Download mode + heimdall can always put the previous `boot.img` back.

## What's still missing

| | Why |
|---|---|
| Sound | Speakers use two Cirrus Logic CS35L45 smart amps fed over TDM from the Qualcomm DSP; needs device-tree, machine-driver and tuning-firmware work, and untuned smart amps can damage speakers |
| Fast charging | SM5440 direct charger and USB-PD negotiation |
| USB power for accessories | SM5714 boost (OTG) control |
| Camera, S Pen, sensors | No drivers yet |
| Himax panel variant | No panel driver |

## Lessons

- **Read the stock device tree.** Samsung's DTB and DTBO, extracted from the firmware, answered the hardest questions: the PMK8350 address, charger limits, the battery thermistor channel, panel timings.
- **Samsung's GPL source is a register manual.** The charger patch comes from reading their driver, not guessing.
- **Verify before you flash.** One unverified image cost hours.
- **Measure before you fix.** The display-off black screen, the brightness grain and the charging flip-flop all looked like "the display/charger is flaky". Each one turned out to have a specific, provable cause.

## Credits

The port stands on [vishalbala-nps](https://github.com/vishalbala-nps/linux) (device tree, panel driver, fuel gauge, firmware), [Marker284](https://github.com/Marker284/samsung-gts7xllite-display-touch) (touchscreen driver, panel fixes, notes), [sm6350-mainline](https://github.com/sm6350-mainline/linux), the Fairphone 4 postmarketOS port, [postmarketOS](https://postmarketos.org), [Alpine](https://alpinelinux.org) and [Omarchy](https://omarchy.org).
