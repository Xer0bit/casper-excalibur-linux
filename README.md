# casper-excalibur-linux

Linux control for the **Casper Excalibur G900** (board `NLCB 001`, Insyde BIOS, i7-10750H, RTX 2060 Mobile).
Casper only ships Windows software for keyboard lighting and fan/performance settings. This project talks to the
same embedded controller (EC) and kernel interfaces from Linux:

- `casper-ctl`: a single bash CLI (`bin/casper-ctl`)
- `casper-gui`: a small GTK3 front end that uses the CLI through one authenticated helper

The EC register map was reverse-engineered from this laptop's own ACPI DSDT. Nothing here is endorsed by Casper.

## Status

| Feature | State |
|---|---|
| Keyboard color (`kbd-color`) | Works on hardware (the firmware's own EC handshake) |
| Keyboard level / mode / effect | Commands run and are acknowledged by the EC; what each value does is not mapped yet |
| Keep keyboard state across boot and resume | Implemented (`install-service`); not yet confirmed on hardware |
| Fan RPM, temperature | Works on hardware (`fan-status`) |
| Fan speed control | **Not available.** The DSDT has no fan-speed write; `FANE`/`FAND` effect unclear (see `docs/EC-MAP.md`) |
| CPU power limits, turbo, EPP, governor, presets | Implemented through standard sysfs; not yet confirmed on hardware |
| GPU clock lock / power limit | Implemented through `nvidia-smi`; the power limit is `N/A` on this vBIOS |
| GTK GUI | Implemented; compile-checked and its helper protocol tested, but not yet run on a display |
| Offline test suite | `tests/run.sh` (fake EC image, no hardware needed) |

## Install

```
git clone <your repo url> casper-excalibur-linux
cd casper-excalibur-linux
sudo ./install.sh
```

The installer puts `casper-ctl` and `casper-gui` in `/usr/local/bin`, creates `/etc/casper-ctl`, and decodes the EC
field map from your DSDT (`sudo casper-ctl ec-fields`; needs `acpica-tools`, installed automatically on apt systems).

Step-by-step guide, requirements and troubleshooting: [docs/INSTALL.md](docs/INSTALL.md).
Check for missing drivers any time: `sudo casper-ctl doctor` (`--fix` installs them).

Keep the keyboard color across reboots and suspend:

```
sudo casper-ctl kbd-color 00FF00
sudo casper-ctl install-service none     # 'none' = restore keyboard only; or quiet|balanced|performance|max
```

Uninstall: `sudo ./uninstall.sh` (`--purge` also removes `/etc/casper-ctl`).

## CLI

```
sudo casper-ctl status                    # everything readable
sudo casper-ctl kbd-color FF8040
sudo casper-ctl kbd-level 2 | kbd-mode 5 | kbd-effect 3     # raw EC values
sudo casper-ctl fan-status [watch]        # both fan RPMs, temperature
sudo casper-ctl preset balanced           # quiet | balanced | performance | max
sudo casper-ctl rapl 45 65                # CPU PL1 / PL2 in watts
sudo casper-ctl turbo off | cpu-epp power | cpu-gov powersave
sudo casper-ctl gpu-lock 300 1500 | gpu-unlock
sudo casper-ctl help                      # all commands
```

Environment: `DRY=1` prints writes instead of doing them; `FORCE=1` lifts the CPU/fan safety limits.

## GUI

```
casper-gui
```

Asks for your password once (polkit). Tabs: Keyboard, Fans (monitor), CPU / Power, GPU. A log pane shows each command
and its output.

## Safety

- EC writes are refused unless the DMI board name is `NLCB 001`. EC maps differ between models. Override with
  `CASPER_SKIP_BOARD_CHECK=1` only if you know what you are doing.
- EC writes go through named DSDT fields with read-modify-write, so neighbouring bits in a byte are preserved.
- Every EC byte written is logged; `sudo casper-ctl ec-undo` restores them.
- The keyboard handshake includes the EC's own save step. Do not call it in a tight loop.
- Limits: CPU PL1 above 120 W, PL2 above 135 W, and fan duty below 30% are refused unless `FORCE=1`.

## How it works

- `casper-ctl discover` decodes WMI GUIDs and the EC `OperationRegion` from the DSDT.
- `casper-ctl ec-fields` lists every EC field name with its byte and bit offset.
- `ec-snap` / `ec-diff` find which bytes change when you press an Fn key or change a setting in Windows.
- The keyboard color protocol is copied from the DSDT method `\_SB.GWMI.WSAA` (function `0xFB00`/`0x0100`).

Details, field table and open questions: [docs/EC-MAP.md](docs/EC-MAP.md).

## Other Casper or Tongfang-style laptops

Run `sudo casper-ctl discover` and `sudo casper-ctl ec-fields`, compare with `docs/EC-MAP.md`, and use
`ec-snap`/`ec-diff` while changing one setting at a time. Reads work on any board. Sending a pull request with a
verified map for another board is welcome.

## Tests

```
./tests/run.sh
```

## Put this on GitHub

```
cd casper-excalibur-linux
git status                      # history is already committed
gh repo create casper-excalibur-linux --private --source=. --push
# or: create an empty repo on github.com, then
git remote add origin git@github.com:<you>/casper-excalibur-linux.git
git push -u origin main
```

Do not commit ACPI dumps (`*.dat`, `*.dsl`); they are in `.gitignore` because they can contain machine-specific data.

## License

MIT. See [LICENSE](LICENSE).
