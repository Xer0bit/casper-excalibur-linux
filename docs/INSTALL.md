# Installing on Ubuntu

Supported: Ubuntu 22.04, 24.04 and newer (also Debian-based derivatives), stock `linux-generic` kernel.
Tested on a Casper Excalibur G900 (board `NLCB 001`) running Ubuntu 26.04, kernel 7.0.

## 1. Requirements

| Need | Why | Provided by |
|---|---|---|
| Casper Excalibur G900 (`NLCB 001`) | EC writes (keyboard color) are enabled only for this board | hardware |
| `ec_sys` kernel module | embedded controller access | stock Ubuntu kernel |
| Secure Boot **off** | kernel lockdown blocks EC writes and unsigned DKMS modules | BIOS setting |
| NVIDIA proprietary driver | GPU status, clock lock | `ubuntu-drivers` |
| `acpica-tools` | decodes this laptop's EC map from its own ACPI tables | apt |
| `python3-gi`, `gir1.2-gtk-3.0`, `pkexec` | the GUI and its password prompt | apt |

You do not need to install these by hand. `doctor` finds what is missing and installs it.

## 2. Install (three commands)

```
git clone https://github.com/Xer0bit/casper-excalibur-linux.git casper-excalibur-linux
cd casper-excalibur-linux
sudo ./install.sh
```

The installer installs the apt packages, copies `casper-ctl` and `casper-gui` to `/usr/local/bin`, decodes the EC map, and
finishes by running the driver check below.

## 3. Detect and fix missing drivers

```
sudo casper-ctl doctor          # read-only report
sudo casper-ctl doctor --fix    # install what is missing, then re-check
```

Example output:

```
ok       board          Casper Excalibur G900 (NLCB 001): all features
ok       ec_sys         embedded controller interface present
MISSING  gtk3           python3-gi / GTK3 typelib (needed by casper-gui)
MISSING  nvidia         NVIDIA GPU found, no working driver (reboot first if you just installed one)
```

| Status | Meaning |
|---|---|
| `ok` | present and working |
| `MISSING` | a feature will not work; `--fix` installs it where apt can |
| `warn` | works with limits (for example another board, so EC writes stay disabled) |
| `info` | nothing to do |

`--fix` installs apt packages, loads `intel_rapl_msr`, builds the EC map, and **asks before** installing the NVIDIA driver
(`ubuntu-drivers install`) because that needs a reboot. It never changes Secure Boot or the kernel.

Check Secure Boot yourself with `mokutil --sb-state`. If it is on, `doctor` shows `warn lockdown`. Turn it off in the BIOS,
or the keyboard color will not change.

## 4. First run

```
sudo casper-ctl status
sudo casper-ctl kbd-color 8000FF       # keyboard turns purple
casper-gui                             # or search "Casper" in the app menu
```

Keep the keyboard color across reboots and suspend:

```
sudo casper-ctl install-service none
```

## 5. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `EC interface unavailable` | `ec_sys` missing or debugfs not mounted. Run `doctor`; use the stock kernel |
| Color command succeeds but nothing changes | Secure Boot lockdown. Disable it, reboot |
| `nvidia-smi` fails right after the driver install | Reboot once |
| GUI does not open | `doctor` shows `gtk3` missing: `sudo casper-ctl doctor --fix` |
| `WARN: no platform_profile`, `no EC fan map` on `preset` | Expected on this laptop: no vendor platform driver, fan registers not mapped. Fan speed is monitoring only |
| Different Casper model | EC writes stay off. CPU and GPU controls still work. See [EC-MAP.md](EC-MAP.md) |

## 6. Casper's online services

Casper publishes no documented public API for its laptop hardware controls that this project could verify. Its
Windows utilities talk to the same embedded controller, and so does `casper-ctl`. For that reason `doctor` finds
drivers from your own machine (DMI, kernel, apt) and does not call any Casper server. If Casper publishes an API or
driver feed, open an issue with the link and it can be added.

## 7. Uninstall

```
sudo ./uninstall.sh            # --purge also removes /etc/casper-ctl
```
