# EC / ACPI map: Casper Excalibur G900 (board NLCB 001)

**English** | [Türkçe](EC-MAP.tr.md)

Source: this laptop's DSDT (Insyde, `CML`), decoded with `casper-ctl discover` and `casper-ctl ec-fields`.
"Observed" means seen on the running machine. "Inferred" means read from DSDT code and not yet confirmed by a test.

## EC region

`OperationRegion (ERAM, EmbeddedControl, Zero, 0xFF)`, accessed through the Linux `ec_sys` debugfs file
(`/sys/kernel/debug/ec/ec0/io`). Writes need `ec_sys write_support=1`.

## Fields used

Offsets are `byte.bit`. Names come from the DSDT.

| Field | Offset | Width | Meaning |
|---|---|---|---|
| `LKBR` `LKBG` `LKBB` | 0x89 0x8A 0x8B | 8 | Keyboard R, G, B. Observed: writing them with the handshake changed the color |
| `LKBL` | 0xC1.0 | 4 | Keyboard level. DSDT uses 0, 1, 2 (inferred brightness levels) |
| `LKBM` | 0xC1.4 | 4 | Keyboard mode (meaning not mapped) |
| `LKBA` | 0xAA.4 | 4 | Keyboard effect/animation value (meaning not mapped) |
| `LKCC` `LKBE` `LKBC` `LKBS` | 0xAA.0 .1 .2 .3 | 1 | Commit, acknowledge, change flag, save |
| `RGBK` | 0xC0.7 | 1 | Read 0 on this machine; meaning unknown |
| `BLIS` | 0xC3.2 | 1 | Backlight state, used by the Fn backlight key handler (inferred) |
| `FN1R` `FN2R` | 0xCA 0xCC | 16 | Fan 1 / fan 2 RPM, **high byte first** (observed: 2650-4200 RPM range) |
| `RPM1` `RPM2` | 0xB2 0xB3 | 8 | Low byte of the tach values; not useful alone |
| `RTMP` | 0x58 | 8 | Temperature in degrees C (observed: matches coretemp) |
| `FANM` | 0xC3.0 | 1 | Fan-max state reported to the Fn fan key handler (inferred); observed 0 |
| `FANE` `FAND` | 0xD2.2 .3 | 1 | One-shot fan command bits written by WMI function 0xFB00/0x0200 selector 1 |
| `SFAN` | 0xF4 | 8 | Declared, never referenced in the DSDT |
| `CBSC` | 0xA3 | 8 | Last Fn-key event code: 0x10 backlight, 0x11 fan, 0x12 other (from `_Qxx` code) |
| `DWNK` | 0x50.0 | 1 | Windows-key lock (written by WMI selector 0) |

## Keyboard protocol

From `\_SB.GWMI.WSAA`, function `0xFB00`, subfunction `0x0100` (DSDT line 60797 onward):

1. `LKBC` = 0
2. `LKBA`, `LKBB`, `LKBG`, `LKBR` = values
3. `LKBL` from the input level (the DSDT maps input 0, 1, 2 to `LKBL` 2, 0, 1)
4. `LKBM` = mode
5. `LKCC` = 1; wait until `LKBE` = 1
6. `LKBE` = 0; `LKBS` = 1; wait until `LKBE` = 1

`casper-ctl` implements this as `kbd_ec_set` (one handshake per call). Observed: green (`00FF00`) applied and the EC
acknowledged both waits.

## Fans

- Two fans. RPM reads work (`fan-status`).
- Observed: writing `FAND` = 1 once did not change RPM at the same temperature within the first sample. `FAND` stayed
  latched at 1 until cleared. Inconclusive; do not rely on it.
- No DSDT code writes a fan speed. If the Windows software sets fan curves, it likely goes through the `WMIA.WMCB`
  method and the EC command interface (`ECMD`, `ECXC`). Not yet analysed.

## WMI blocks (from `casper-ctl discover`)

| GUID | ACPI scope | Object | Type |
|---|---|---|---|
| `86CCFD48-205E-4A77-9C48-2021CBEDE341` | `_SB.WMTF` | `WMTF` | method |
| `2BC49DEF-7B15-4F05-8BB7-EE37B9547C0B` | `_SB.WFDE` | `WMDE` | method |
| `A6FEA33E-DABF-46F5-BFC8-460D961BEC9F` | `_SB.WFDE` | | event 0xD0 |
| `1F13AB7F-6220-4210-8F8E-8BB5E71EE969` | `_SB.WFTE` | `WMDE` | method |
| `ABBC0F20-8EA1-11D1-00A0-C90629100000` | `_SB.WMIA` | | event 0x80 |
| `ABBC0F40` to `ABBC0F48` (same suffix) | `_SB.WMIA` | `BV B1 B2 BL BC BW II GS CT` | data blocks |
| `101F83BB-30B7-DF11-8D81-0800200C9A66` | `_SB.WMIA` | `WMCB` | method, 255 instances |
| `644C5791-B7B0-4123-A90B-E93876E0DAAD` | `_SB.GWMI` | `AA` | data block (written by `WSAA`) |
| `74286D6E-429C-427A-B34B-B5D15D032B05` | `_SB.GWMI` | | event 0x80 |
| `05901221-D566-11D1-B2F0-00A0C9062910` | several | `CC AE AB` | BMOF (method schemas) |

## Open questions

- What `LKBL`, `LKBM`, `LKBA` values do (brightness steps, effects).
- What `RGBK` = 0 means on a keyboard that accepts colors.
- Fan control: `WMIA.WMCB`, `ECMD`/`ECXC`, and whether `FAND`/`FANE` need a companion write.
- Whether power limits written through RAPL persist or are reset by the EC.
