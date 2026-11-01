# Wi-Fi and Bluetooth on the tablet

How Wi-Fi and Bluetooth work on the Galaxy Tab S7 FE under postmarketOS: the chip and its firmware, the software stack, everyday use by touch and from the terminal, where settings are stored, and what to do when something stops working. The values are from my tablet on kernel r6.

See also [FILESYSTEM.md](FILESYSTEM.md) (where files live) and [HACKING.md](HACKING.md) (how to change things safely).

## The hardware

Wi-Fi and Bluetooth come from one Qualcomm **WCN3990** combo chip, attached to the SM7225 (Snapdragon 750G). The two halves are wired up very differently:

| | Wi-Fi | Bluetooth |
|---|---|---|
| Connected over | The SoC's internal bus (SNOC), not PCIe or SDIO | A serial UART |
| Linux driver | `ath10k_snoc` (+ `ath10k_core`, `mac80211`, `cfg80211`) | `hci_uart` with the Qualcomm protocol (`btqca`) |
| Firmware | **Runs on the modem's processor**, not on the chip: `wlanmdsp.mbn`, loaded with the modem | Downloaded into the chip at start: `qca/crbtfw32.tlv`, `qca/crnv32u.bin` |
| Standards | 802.11ac, 2.4 GHz and 5 GHz (no 6 GHz); can act as an access point | Bluetooth 5 |
| Device | `wlan0` (phy0) | `hci0` |

**Wi-Fi depends on the modem.** The Wi-Fi firmware runs on the modem DSP, so Wi-Fi only works if the modem has started. That needs these helpers, all of which run as services or modules:

| Piece | Job |
|---|---|
| `qcom_q6v5_pas` (remoteproc) | Loads and boots the modem firmware (`qcom/sm7225/Samsung/gts7xllite/modem.mbn`) |
| `qrtr`, `qrtr_smd` | The message bus between Linux and the modem/DSPs |
| `qcom_pd_mapper` | Tells the modem which services exist (replaces the old `pd-mapper` daemon) |
| `rmtfs` | Gives the modem access to its calibration storage. Runs with `rmtfs_avoid_writing="true"` (`/etc/conf.d/rmtfs`) so it **never writes** to the real `efs` partitions |
| `tqftpserv` | Serves files the modem asks for at runtime |

Boot order, from `dmesg`:

```
~7 s   Bluetooth: hci0: setting up wcn399x … QCA Downloading qca/crbtfw32.tlv … setup on UART is completed
~11 s  ath10k_snoc 18800000.wifi: qmi chip_id 0x4320 … fw_build_id WLAN.HL.3.3.1-…   (the modem has started)
~17 s  ath10k_snoc 18800000.wifi: wcn3990 hw1.0 … firmware ver api 5                  (wlan0 is ready)
```

Wi-Fi appears about 10–15 s after boot. That's normal: it waits for the modem.

## The software stack

```
 Waybar tray: nm-applet (Wi-Fi)        blueman-applet (Bluetooth)
 Omarchy menu: Setup → Wi-Fi / Bluetooth, Update → Hardware → restart
          │                                    │
     NetworkManager  ── wpa_supplicant      BlueZ (bluetoothd) ── PipeWire (Bluetooth audio)
          │                                    │
       cfg80211 / mac80211                  bluetooth core (hci0)
          │                                    │
       ath10k_snoc ── modem DSP firmware     hci_uart + btqca ── chip firmware
```

| Program | Role | Service |
|---|---|---|
| **NetworkManager** | Decides which network to join, gets an address (its own DHCP client), stores saved networks | `networkmanager` |
| **wpa_supplicant** | Does the actual Wi-Fi login (WPA2/WPA3) for NetworkManager | `wpa_supplicant` |
| **nm-applet** | The Wi-Fi icon in the bar: network list, password pop-ups | started by Hyprland |
| `nm-connection-editor` | Full settings window for every saved network | Omarchy menu → Setup → Wi-Fi |
| **BlueZ** (`bluetoothd`) | The Bluetooth service: pairing, connecting, profiles | `bluetooth` |
| **blueman** (`blueman-applet`, `blueman-manager`) | The Bluetooth icon in the bar and the device manager window | started by Hyprland / menu |
| `bluetui` | Bluetooth manager in the terminal | — |
| **PipeWire** + `pipewire-spa-bluez` | Bluetooth audio (headphones, speakers) | started with the session |
| `tablet-bt-reconnect` | Reconnects your trusted keyboard and mouse at login | started by Hyprland |
| **avahi** | Makes the tablet reachable as `samsung-gts7xllite.local` on Wi-Fi | `avahi-daemon` |
| **rfkill** | The software on/off switch for both radios | `rfkill` |

## Everyday use by touch

| To | Tap |
|---|---|
| Join a Wi-Fi network | The **Wi-Fi icon** in the bar, then the network. If it needs a password, a pop-up window asks for it, and the on-screen keyboard appears |
| Change a saved network (password, priority, static IP) | Omarchy menu → **Setup → Wi-Fi** (`nm-connection-editor`) |
| Pair a Bluetooth device | Omarchy menu → **Setup → Bluetooth** (blueman), tap **Search**, then the device → **Pair**. Mark keyboards and mice **Trusted** so they reconnect at login |
| Connect a paired device | The Bluetooth icon → the device |
| Restart Wi-Fi when it's stuck | Omarchy menu → **Update → Hardware → Wi-Fi** |
| Restart Bluetooth | Omarchy menu → **Update → Hardware → Bluetooth** |

## From the terminal

### Wi-Fi (`nmcli`)

```sh
nmcli dev                                  # devices and their state
nmcli dev wifi list                        # networks in range (add --rescan yes to rescan now)
nmcli dev wifi connect "Name" password "secret"   # join a new network
nmcli con show                             # saved networks
nmcli con up "Name"                        # switch to a saved network
nmcli con down "Name"                      # disconnect
nmcli con delete "Name"                    # forget a network
nmcli con mod "Name" connection.autoconnect-priority 10   # prefer it over others
nmcli radio wifi off; nmcli radio wifi on  # restart the radio
ip -br addr                                # addresses on wlan0, usb0
nmtui                                      # full-screen text menu, if you have a keyboard
```

**Hotspot from the tablet** (the chip supports access-point mode). Note this disconnects the tablet from its current Wi-Fi:

```sh
nmcli dev wifi hotspot ssid TabS7 password "at-least-8-chars"
nmcli con down Hotspot      # stop
```

### Bluetooth (`bluetoothctl`)

```sh
bluetoothctl show                          # the controller: address, powered, pairable
bluetoothctl devices Paired                # paired devices
bluetoothctl scan on                       # look for devices (Ctrl+C or `scan off` to stop)
bluetoothctl pair AA:BB:CC:DD:EE:FF
bluetoothctl trust AA:BB:CC:DD:EE:FF       # reconnect automatically
bluetoothctl connect AA:BB:CC:DD:EE:FF
bluetoothctl disconnect AA:BB:CC:DD:EE:FF
bluetoothctl remove AA:BB:CC:DD:EE:FF      # forget it
bluetoothctl power off; bluetoothctl power on
bluetui                                    # terminal manager (touch works in the terminal too)
```

### Both radios

```sh
rfkill                     # soft/hard blocked state of bluetooth and wlan
rfkill unblock all
sudo rc-service networkmanager restart
sudo rc-service bluetooth restart
sudo dmesg | grep -iE 'ath10k|bluetooth|hci0'   # driver messages
```

## Where the settings are stored

| Path | What it holds |
|---|---|
| `/etc/NetworkManager/system-connections/*.nmconnection` | **Saved Wi-Fi networks, including passwords** in plain text. Readable by root only. Copy these to move networks to a fresh install |
| `/usr/lib/NetworkManager/conf.d/` | postmarketOS defaults: internal DHCP, nftables firewall, connectivity check, **randomised MAC addresses** |
| `/etc/NetworkManager/conf.d/` | Your overrides (empty). Files here win over `/usr/lib` |
| `/var/lib/NetworkManager/` | Leases and runtime state |
| `/var/lib/bluetooth/<controller>/<device>/` | **Bluetooth pairings and keys.** Without them, devices must be paired again |
| `/etc/bluetooth/main.conf` | BlueZ settings. This port sets `FastConnectable`, `ReconnectAttempts=7` with backoff, and `AutoEnable=true` (Bluetooth on at boot) |
| `/etc/bluetooth/input.conf`, `network.conf` | Keyboards/mice and Bluetooth networking |
| `/etc/conf.d/rmtfs` | `rmtfs_avoid_writing="true"`: protects the factory calibration |
| `/lib/firmware/qcom/sm7225/Samsung/gts7xllite/wlanmdsp.mbn`, `modem.mbn` | Wi-Fi and modem firmware (Samsung-signed, from the stock firmware) |
| `/lib/firmware/ath10k/WCN3990/hw1.0/` | ath10k host files for the WCN3990, including `board-2.bin` (radio calibration per board) |
| `/lib/firmware/qca/crbtfw32.tlv.zst`, `crnv32u.bin.zst` | Bluetooth firmware (package `linux-firmware-qca`) |
| `~/.config/waybar/config.jsonc` | The bar; Wi-Fi and Bluetooth are the nm-applet and blueman tray icons |
| `/usr/local/bin/tablet-bt-reconnect` | Reconnect script for trusted devices |

## Addresses

- **Wi-Fi uses a different made-up MAC address per network** (`wifi.cloned-mac-address=stable` in `50-random-mac.conf`). It's stable for each network, so routers still recognise the tablet, but it isn't the factory address. Scans use random addresses too. If a router filters by MAC, use the address `ip link show wlan0` shows while connected to that network.
- **Bluetooth uses `02:00:B2:F8:C6:45`.** The `02:` prefix marks a locally assigned address: Linux doesn't read Samsung's factory address from the `efs` partition. Pairings work normally. If the address ever changes (for example after a kernel or device-tree change), paired devices need pairing again.

## Using the tablet over Wi-Fi

- **SSH:** `ssh vansh@samsung-gts7xllite.local`. avahi announces the name, so it works even when the hotspot hands out a new IP. The firewall allows SSH only from private addresses (`/etc/nftables.d/49_ssh_local.nft`).
- **Connectivity check:** NetworkManager fetches `http://networkcheck.postmarketos.org` to detect captive portals (hotel or airport logins). To turn it off, create `/etc/NetworkManager/conf.d/90-no-connectivity.conf` containing `[connectivity]` and `enabled=false`, then restart NetworkManager.
- **Bluetooth audio** goes through PipeWire with `pipewire-spa-bluez`. Volume is `wpctl` (the bar's volume module). The tablet's own speakers and microphone don't work on Linux yet, so Bluetooth is the only sound output.

## When something's wrong

Work down the list. Each step is more drastic than the one before.

**Wi-Fi**

| Symptom | Try |
|---|---|
| No Wi-Fi icon, or `nmcli dev` has no `wlan0` | Wait 20 s after boot (it waits for the modem). Then check `sudo dmesg | grep -iE 'ath10k|remoteproc|modem'` for firmware errors, and `rc-status` for `rmtfs` started |
| `wlan0` is there but finds no networks | `rfkill` (blocked?), then `nmcli radio wifi off; nmcli radio wifi on` |
| Joins, but no internet | `ip -br addr` (got an address?), `ping -c3 1.1.1.1` (routing), `ping -c3 example.com` (DNS). If only DNS fails, check `/etc/resolv.conf` |
| Wrong password saved | `nmcli con delete "Name"`, then join again |
| Slow or drops | Move closer or prefer 5 GHz (`nmcli dev wifi list` shows `CHAN`/`FREQ`). Check `nmcli -f 802-11-wireless.powersave con show "Name"` |
| Still broken | `sudo rc-service networkmanager restart`, then reboot |

**Bluetooth**

| Symptom | Try |
|---|---|
| No Bluetooth icon or `bluetoothctl show` says no controller | `sudo dmesg | grep -i hci0`: "setup on UART is completed" must appear. If firmware is missing: `sudo apk add linux-firmware-qca` |
| Controller there but devices won't connect | `bluetoothctl power off; bluetoothctl power on`, then put the device back in pairing mode |
| Keyboard or mouse doesn't reconnect at login | Mark it trusted (`bluetoothctl trust …`), or run `tablet-bt-reconnect` |
| Pairing fails repeatedly | `bluetoothctl remove …`, forget the tablet on the device too, pair again |
| Still broken | Omarchy menu → Update → Hardware → Bluetooth, then reboot |

**Gathering details before asking for help:**

```sh
nmcli dev; nmcli con show; ip -br addr; rfkill
bluetoothctl show; bluetoothctl devices Paired
sudo dmesg | grep -iE 'ath10k|qcom_q6v5|remoteproc|bluetooth|hci0' | tail -40
rc-status | grep -iE 'network|wpa|blue|rmtfs|rfkill'
```

## Don't do these

| Don't | Why |
|---|---|
| Set `rmtfs_avoid_writing` to false, or write to `efs`, `sec_efs` or `persist` | They hold this tablet's factory calibration and addresses. They can't be recreated |
| Delete or replace the files in `qcom/sm7225/Samsung/gts7xllite/` | Without the Samsung-signed modem and Wi-Fi firmware, Wi-Fi doesn't start |
| Let NetworkManager manage `usb0` | It's deliberately unmanaged: the USB link to your PC uses a fixed address (`172.16.42.1`) |
| Stop `rmtfs`, `tqftpserv` or the modem to save power | Wi-Fi goes with them |
| Share the `.nmconnection` files or `/var/lib/bluetooth` | They contain your Wi-Fi passwords and Bluetooth keys |
| Rely on Wi-Fi alone while changing network or firewall settings | You can lock yourself out. Keep a USB SSH session open (`vansh@172.16.42.1`) as a fallback |
