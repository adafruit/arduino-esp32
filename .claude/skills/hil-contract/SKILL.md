---
name: hil-contract
description: The Arduino ESP32 core HIL contract, under agentrc's `hil` rules. Use when running the core's HIL battery on rig boards (the ESP32-S3 and ESP32-P4 on the ci.lan farm, a dev PC's ESP32 board), when a HIL run fails, hangs or reports a board locked, when reading its report, or for a manual session (flash, GDB, console, a check, a command) on a rig board from hw-validator or hw-debugger.
---

# HIL contract

Read agentrc's `hil` skill first; this page supplies its contract sections. The mechanics are agentrc's `arduino`
skill (`arduino_hil.py`, `arduino_remote.py`), shared with the Adafruit SAMD core, Adafruit TinyUSB Arduino and
Adafruit SPIFlash, whose HIL contracts have the same commands, budgets, session rules and recovery; this page names
what is this core's. Manual runs only: no CI job runs this battery. Scripts, all in `scripts/`, each with its usage in
its docstring:

- `hil_test.py`: the harness on the host with the boards (this core's profile and tests).
- `hil_remote.py`: drives the harness on ci.lan from the dev PC that built the firmware.
- `agentrc_pin.py`: which agentrc both load their shared scripts from: the installed one
  (`${AGENTRC_DIR:-$HOME/.claude}`) on a dev PC, never fetched; in CI the commit `test/hil/agentrc.json` pins; on the
  rig, the copy `hil_remote.py` staged. It refuses an agentrc without core mode.

```bash
H=.claude/skills/hil-contract/scripts
python3 $H/agentrc_pin.py check            # the agentrc a run would load, validated; its root
```

## Hosts/rosters

| Host     | How to tell                        | Roster                                                     |
|----------|------------------------------------|------------------------------------------------------------|
| ci.lan   | the HIL farm; reached over ssh     | `test/hil/ci.json` (tracked)                               |
| a dev PC | a board on this PC's USB           | `test/hil/local.json` (ignored; copy `local.example.json`) |

ci.lan has no arduino-cli and no checkout of this core: firmware is built on the dev PC and staged by
`hil_remote.py`. On a dev PC without `test/hil/local.json`, ask the user for one; an agent that cannot ask returns
each requested board not-run naming the missing file.

A roster entry is the `arduino` skill's (`name`, the board's name in agentrc's board registry and its lock; `uid`, the
DUT's USB serial under this core's TinyUSB stack; `usb_port`, required for an esptool board; `probe`, its USB-UART
bridge's serial, whose registry entry supplies the esptool flasher, or a dev PC's unregistered board's own `flasher`;
`debug`) plus `arduino.tests`: `["cdc", "timing"]`. A board's name must be a rig board of the build profile
(`espressif_s3_devkitm`, `espressif_p4_function_ev`).

ci.lan's two boards are also on tinyusb's roster, tinyuf2's and Adafruit TinyUSB Arduino's. This contract performs
no rig-wide operation. **Farm check**: tinyusb's launcher,
`ssh ci.lan 'cd ~/code/tinyusb && python3 test/hil/helper/hil_farm_check.py -b <board>...'`.

## Selection

A fixed battery per board, the roster's `arduino.tests`, each over the DUT's USB-OTG CDC (TinyUSB, CDC on boot) with
a reply line carrying its command's random tag (a missing, stale or other reply fails the test at its deadline):

- `cdc` (`test/hil/core_cdc/`, also the restoration check): `INFO` must report `stack=tinyusb` and the board's chip;
  `ECHO` of 1, 63, 64, 65, 511, 512, 513 and 1000 random bytes (either side of a full- and a high-speed bulk packet)
  must return every byte as sent, then a `PASS` line with their length and crc32.
- `timing` (`test/hil/core_timing/`): `millis()` read twice 3 s apart must lie within the host's monotonic bracket of
  the two exchanges widened by 1%, `micros()` must agree with `millis()` within 2 ms, and `delay(1000)` measured by
  `micros()` must take 1000 to 1002 ms, widened by 1%. A coarse functional bound, no clock accuracy claim; `INFO`
  reports `f_cpu` for the record.

`-b` narrows the boards. The PR-scoped selector is the build contract's:

```bash
python3 .claude/skills/build/scripts/check_build.py --select-only --base <A> --hil-config test/hil/ci.json
```

Its `hil.boards` are the roster boards to run, `hil.full` means the harness, a HIL sketch, the fixture or a roster
changed (every board), and `hil.uncovered` names each chip family the change reaches with no board on that roster
(on the farm, `esp32` and `esp32c6`): report those uncovered, never pass.

## Build

Each run board needs a clean HIL record at HEAD (build skill, "A HIL record"):

```bash
python3 .claude/skills/build/scripts/check_build.py --board <board> --shared --record build/hil/<board>.build.json \
  --hil-config <roster>
```

The harness admits a record only as the `arduino` skill's "The HIL build record" entry says. A manual flash or GDB
session also takes an experimental record (`--experimental`). Every sketch of a rig board compiles in the farm's
USB-switch fixture (`test/hil/esp32_ts3usb30.cpp`): it drives GPIO47 high from `initVariant()`, which the TS3USB30
reads as D = D2, the DUT side (datasheet SCDS237F, Table 1, with OE low).

## Execution

Budgets, the remote run and the manual session commands are those of Adafruit TinyUSB Arduino's HIL contract
(adafruit/Adafruit_TinyUSB_Arduino, `.claude/skills/hil-contract/SKILL.md`, Execution), with this core's names: the attempt dir is `~/hil-remote/arduino-esp32/<id>`, local records and collections live under
`build/.hil-remote/` (upstream's `.gitignore` ignores `/build`), `check --test` takes `cdc` (default) or `timing`,
`session close` restores `core_cdc`.

```bash
python3 $H/hil_remote.py run --run-id <id> [-b BOARD]...
python3 $H/hil_remote.py wait <id> --timeout 570    # repeat while it exits 3
python3 $H/hil_test.py report build/.hil-remote/<id>/hil-run
python3 $H/hil_remote.py session open --run-id <id> -b <board>     # then session exec/stage/close, as TinyUSB's
```

On the dev PC with the board: `python3 $H/hil_test.py run [-b BOARD]... test/hil/local.json`.

## Reservation

As the `arduino` skill's Locks: the board lock `/tmp/tinyusb-hil-locks/<name>.lock` and the pending kind
`arduino-hil` are shared with tinyusb, tinyuf2 and Adafruit TinyUSB Arduino. `hil_test.py run` and `commission` lock
each board themselves; a manual session holds it under a reason unique to its attempt,
`arduino-hil session <attempt dir> <token>`. Cleanup state is `core_cdc` flashed and checked, every child proven
ended, and the hold released.

## Results

`hil_test.py run` writes `hil_report.json` (schema `arduino-esp32-core-hil`) with the same rows, exits, verdicts and
delegated output (`hil_test.py report`) as Adafruit TinyUSB Arduino's contract; `firmware.fqbns` names each sketch's
FQBN. The caller retries a fail once under a new run id, per the `hil` Caller rules.

## Recovery

Recovery needs a separate dispatch naming the board. It applies to a report row with `cleanup.holder` (exit 4), a
protected record left by a run that died, a board's `arduino-hil` pending-session record, and a session whose `close`
failed. The dispatch carries the board, the failed report (or session id), the holder token and the receipts. Run
each command on ci.lan in the failed run's attempt dir (`ssh ci.lan 'cd ~/hil-remote/arduino-esp32/<id> && python3
.claude/skills/hil-contract/scripts/hil_test.py ...'`), adding `--staged manifest.json` to `restore`; on a dev PC,
from the checkout. When the failed tree's firmware or harness is the defect, run the restore from a newly staged tree
of the fixed commit (a `hil_remote.py run` of the held board stages one and reports it locked), with `--report`
naming the failed run's report by absolute path; the hold, its token and the receipts stay the failed run's.

1. `hil_test.py lock status`, and `hil_test.py report <run dir> -b <board>` for the row's holder token and receipts.
2. A live cleanup holder (reason `hil_test.py`): restore under it, R = `hil_test.py`. A dead holder or a protected
   record: `hil_test.py lock hold --take-over <board> --reason recovery-<id>` prints token T; R = `recovery-<id>`.
3. `hil_test.py restore -b <board> --build-record build/hil/<board>.build.json --under-hold R --report
   <run dir>/hil_report.json <roster>`. It refuses while a child of the failed run is not proven ended: stop and
   report that receipt.
4. Once the restore passed, `hil_test.py lock release --token <the holder's token, or T>`. On failure, keep the hold
   and report.

A failed `session close` keeps its hold: once its pending children are proven ended, run `hil_remote.py session close
<id>` again; if that fails too, keep the hold and report. esptool writes the build's `flash_args` images (bootloader,
partition table, `boot_app0`, application) within the board's 4 MB span; the battery keeps no state across sketches,
so restoring `core_cdc` is the whole cleanup.

## Debug

A GDB session (`hil_test.py gdb`, or `session exec <id> gdb`) runs Espressif's OpenOCD (`openocd-esp32`) on the board's USB-Serial-JTAG
(`debug`: `tool` `openocd-esp32`, `uid` its MAC with colons, `usb_port`) with Espressif's gdb for the chip
(`riscv32-esp-elf-gdb` for the P4, `xtensa-esp32s3-elf-gdb` for the S3). On the ESP32-P4 the USB-Serial-JTAG runs
beside the high-speed OTG the sketches use (datasheet 4.2.2.11), so any record's sketch can be debugged. On the
ESP32-S3 the OTG and the USB-Serial-JTAG share the one internal PHY (TRM 33.4.1): a TinyUSB sketch leaves no JTAG,
and the roster has no S3 `debug` route (Limits).

## Limits

- **Coverage:** the ESP32-S3 and ESP32-P4 (pre-v3.0 silicon, `ChipVariant=prev3`) under the TinyUSB stack: USB CDC
  enumeration and bulk data integrity, and the core's time base against the host. Not covered on hardware: every
  other chip, USB-Serial-JTAG CDC (`USBMode=hwcdc`), UART, Wi-Fi, BLE, I2C, SPI, ADC, PWM and every other peripheral
  (no fixture wired), PSRAM, the second-stage bootloader beyond booting the image, OTA, cold power-on, and every other
  variant; those build only.
- **S3 debug:** pending. It needs a `USBMode=hwcdc` image, whose USB-Serial-JTAG enumerates with the MAC with colons
  as its serial, while the roster's `uid` is the TinyUSB CDC's MAC without them: a flash of such an image fails the
  harness's DUT identity check.
- **Identity:** this core's TinyUSB stack reports the S3's MAC as its USB serial and `0` on the P4 (`USB.cpp`
  `USB_SERIAL`); each board is also pinned by its `usb_port`.
- **CDC receive queue:** `core_cdc` sizes `Serial`'s receive queue to hold a whole echo. Under the default 256 bytes
  the P4 returned 896 of 1000 echoed bytes (run `esp32core-1`, 2026-11-06): `USBCDC::_onRX` drops input when the
  queue stays full for 10 ticks, presumably while `loop()` waits for TX room that the same USB task must free. The
  battery does not exercise that path.
- **Commissioning:** ci.lan's `espressif_p4_function_ev` (uid `0` at `11-1.1`, `303a:0002`) ran the battery on
  2026-11-06: `cdc` and `timing` passed (`f_cpu` 360 MHz) and `core_cdc` was restored; a GDB session listed the
  FreeRTOS tasks over the USB-Serial-JTAG and the board passed `cdc` after it. `espressif_s3_devkitm` (uid
  `84F703C084E4` at `11-1.3`, `303a:1001`) is not yet run: pending.
