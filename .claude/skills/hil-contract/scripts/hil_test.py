#!/usr/bin/env python3
"""The Arduino ESP32 core HIL harness (SKILL.md beside this directory). Linux only.

  hil_test.py run [-b BOARD]... [-t TEST]... [--record-dir DIR] [--run-dir DIR] [--staged MANIFEST] ROSTER
  hil_test.py commission -b BOARD [--record-dir DIR] ROSTER
  hil_test.py flash -b BOARD --build-record R --sketch S --under-hold REASON [--staged M] ROSTER
  hil_test.py restore -b BOARD --build-record R --under-hold REASON [--report PATH] [--release] [--staged M] ROSTER
  hil_test.py gdb -b BOARD --build-record R --sketch S --under-hold REASON [--ex CMD]... [--timeout S] [--staged M]
                 ROSTER
  hil_test.py exec -b BOARD --under-hold REASON [--timeout S] [--staged M] ROSTER -- ARGV...
  hil_test.py console -b BOARD --under-hold REASON [--seconds S] [--baud N] [--reset] [--staged M] ROSTER
  hil_test.py check -b BOARD --build-record R --under-hold REASON [--test T] [--staged M] ROSTER
  hil_test.py report RUN_DIR [-b BOARD]...
  hil_test.py lock (hold|release|status) ...        agentrc's hil_lock.py

flash, restore, gdb and check take --bundle DIR, a record bundle `hil_remote.py session stage` staged,
--build-record then inside it. restore --release passes only when the hold was released too.

The last stdout line of every command but lock is JSON. Exits: 0 pass, 1 a board failed or did not run (cleaned up
or untouched), 2 refused before any hardware access, 3 a session command (--under-hold) whose hold the lock record
shows no live holder of, 4 a cleanup failed, logged in the board's cleanup log (run and commission release the board, a
session command keeps its hold); restore --release 5 the hold may still stand, 6 the restore failed (the hold
released).

This file is the core's HIL profile for agentrc's arduino_hil.py (the `arduino` skill): its tests are that engine's
shared core battery over the HIL sketches' serial protocol on the DUT's USB-OTG CDC (test/hil/core_cdc/core_cdc.ino,
test/hil/core_timing/core_timing.ino), INFO's chip the board's BUILD.BOARDS `chip`; the mechanics are there, loaded
from the agentrc agentrc_pin.py selects.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "build" / "scripts"))
import agentrc_pin  # noqa: E402
import check_build as BUILD  # noqa: E402

TESTS = {"cdc": "core_cdc", "timing": "core_timing"}
ROLE_TESTS = {"device": tuple(TESTS)}
RESTORE_TEST = {"device": "cdc"}
REPORT_SCHEMA = "arduino-esp32-core-hil"
# hil_remote.py (agentrc arduino_remote.py); its local records go under /build, which upstream's .gitignore ignores
REMOTE_BASE = "~/hil-remote/arduino-esp32"
REMOTE_ROSTER = "test/hil/ci.json"
REMOTE_RUNS = "build/.hil-remote"
HIL = ".claude/skills/hil-contract/scripts/hil_test.py"
# ECHO lengths: one byte, either side of a full-speed (64) and a high-speed (512) bulk packet, and several packets
ECHO_LENGTHS = (1, 63, 64, 65, 511, 512, 513, 1000)
TIMING_SPAN = 3.0  # seconds between the two TIME reads
DELAY_MS = 1000
# a coarse functional bound on the core's time base against the host's monotonic clock, beyond the exchange's own
# round trips: no clock-accuracy claim (that needs the datasheet's oscillator figures)
TIMING_TOLERANCE = 0.01
# arduino_hil's shared core battery, INFO's stack the rig boards' USBMode=default: the USB-OTG under TinyUSB
CORE_TESTS = {"cdc": ("cdc", "tinyusb"), "timing": ("timing", "tinyusb")}
TEST_FUNCS = {}

E = None  # agentrc's arduino_hil, bound to this profile by engine()


def engine():
    """agentrc's arduino_hil bound to this profile (and its build profile)."""
    global E
    if E is None:
        BUILD.engine()
        E = agentrc_pin.load("skills/arduino/scripts/arduino_hil.py").bind(sys.modules[__name__])
    return E


def main(argv=None):
    try:
        eng = engine()
    except agentrc_pin.PinError as e:
        print(json.dumps({"pass": False, "error": str(e), "remedy": e.remedy}), flush=True)
        return 2
    return eng.main(argv)


if __name__ == "__main__":
    sys.modules.setdefault("hil_test", sys.modules[__name__])
    sys.exit(main())
