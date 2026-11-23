#!/usr/bin/env python3
"""The HIL profile: its tables run agentrc arduino_hil's shared core battery against a simulated DUT on a fake host
clock, the rosters, and the profile bound to arduino_hil.py. The simulation proves the host's parsing and verdicts under
this profile's stack, chip and constants only; what the firmware does is a farm run's evidence."""
import json
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "hil-contract" / "scripts"))
import hil_test as ht  # noqa: E402

E = ht.engine()
BOARD = {"name": "espressif_s3_devkitm"}


class FakeClock:
    """arduino_hil's `time`: the host clock moves only on sleep() and on the FakeDut's port I/O, so every exchange takes
    the same host time whatever the machine's load."""

    def __init__(self):
        self.us = 0

    def monotonic(self):
        return self.us / 1e6

    def sleep(self, seconds):
        self.us += round(seconds * 1e6)


class FakeDut:
    """core_cdc's and core_timing's protocol (test/hil/core_cdc/core_cdc.ino, test/hil/core_timing/core_timing.ino)
    over a byte stream, each write and read taking IO_US of the host's clock, with the DUT's clock running `rate` times
    the host's and delay(ms) measuring `delay_us` (default ms + 0.4 ms)."""

    IO_US = 1000

    def __init__(self, clock, stack="tinyusb", chip="esp32s3", rate=1.0, delay_us=None):
        self.clock, self.stack, self.chip, self.rate, self.delay_us = clock, stack, chip, rate, delay_us
        self.out, self.pending = b"", b""
        self.echo = None  # (nonce, bytes left, bytes so far)
        self.closed = False

    def reset_input_buffer(self):
        pass

    def close(self):
        self.closed = True

    @property
    def in_waiting(self):
        return min(len(self.out), 17)  # replies arrive in fragments

    def read(self, n):
        self.clock.us += self.IO_US
        chunk, self.out = self.out[:n], self.out[n:]
        return chunk

    def write(self, data):
        self.clock.us += self.IO_US
        self.pending += data
        while self.pending:
            if self.echo:
                nonce, left, seen = self.echo
                take, self.pending = self.pending[:left], self.pending[left:]
                seen += take
                self.out += take
                left -= len(take)
                self.echo = (nonce, left, seen) if left else None
                if not left:
                    self.out += (
                        f"\r\nHIL_RESULT {nonce} echo PASS len={len(seen)} crc={zlib.crc32(seen):08x}\r\n".encode()
                    )
                continue
            if b"\n" not in self.pending:
                return
            line, self.pending = self.pending.split(b"\n", 1)
            self.command(line.decode())

    def command(self, line):
        w = line.split()
        cmd, nonce = w[0], w[1]
        if cmd == "INFO":
            reply = f"HIL_INFO {nonce} stack={self.stack} chip={self.chip} f_cpu=240000000"
        elif cmd == "ECHO":
            self.echo = (nonce, int(w[2]), b"")
            return
        elif cmd == "TIME":
            us = int(self.clock.us * self.rate)
            reply = f"HIL_RESULT {nonce} time PASS ms={us // 1000} us={us}"
        elif cmd == "DELAY":
            us = self.delay_us if self.delay_us is not None else int(w[2]) * 1000 + 400
            reply = f"HIL_RESULT {nonce} delay PASS ms={w[2]} us={us}"
        else:
            reply = f"HIL_RESULT {nonce} ? REJECT why=unknown"
        self.out += (reply + "\r\n").encode()


class Battery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = FakeClock()
        for patch in (
            mock.patch.object(E, "time", self.clock),
            mock.patch.object(E, "node", return_value="/dev/ttyACM0"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def dut(self, **kw):
        return FakeDut(self.clock, **kw)

    def run_test(self, test, dut):
        with mock.patch("serial.Serial", return_value=dut):
            result = E.test_func(test)(
                {"dir": "/x"}, "abcd1234", self.clock.monotonic() + 5, None, self.tmp.name, BOARD
            )
        self.assertTrue(dut.closed)
        self.assertTrue((Path(self.tmp.name) / "core-abcd1234.log").is_file())
        return result

    def replying(self, dut, cmd, reply):
        """`dut` answering `cmd` with reply(nonce) instead of its own reply."""
        command = dut.command

        def answer(line):
            if line.startswith(cmd + " "):
                dut.out += (reply(line.split()[1]) + "\r\n").encode()
            else:
                command(line)

        dut.command = answer
        return dut

    def test_cdc_passes_with_this_profiles_echo_lengths(self):
        ok, detail = self.run_test("cdc", self.dut())
        self.assertTrue(ok, detail)
        self.assertIn(f"tinyusb stack, f_cpu=240000000: echoed {list(ht.ECHO_LENGTHS)} bytes", detail)

    def test_cdc_fails_on_the_other_stack_or_chip(self):
        ok, detail = self.run_test("cdc", self.dut(stack="hwcdc"))
        self.assertFalse(ok)
        self.assertIn("'stack': 'hwcdc'", detail)
        ok, detail = self.run_test("cdc", self.dut(chip="esp32p4"))
        self.assertFalse(ok)
        self.assertIn("'chip': 'esp32p4'", detail)

    def test_a_reply_with_another_nonce_times_out(self):
        dut = self.replying(self.dut(), "INFO", lambda nonce: "HIL_INFO other stack=tinyusb chip=esp32s3")
        with self.assertRaisesRegex(TimeoutError, "no reply for nonce abcd1234i"):
            self.run_test("cdc", dut)

    def test_info_answered_by_a_result_fails(self):
        for test in ("cdc", "timing"):
            with self.subTest(test=test):
                dut = self.replying(self.dut(), "INFO", lambda nonce: f"HIL_RESULT {nonce} ? REJECT why=unknown")
                ok, detail = self.run_test(test, dut)
                self.assertFalse(ok)
                self.assertIn("INFO answered HIL_RESULT abcd1234i ? REJECT why=unknown", detail)

    def test_timing_fails_on_a_reply_other_than_pass(self):
        for cmd, op, nonce in (("TIME", "time", "abcd1234a"), ("DELAY", "delay", "abcd1234d")):
            with self.subTest(cmd=cmd):
                dut = self.replying(self.dut(), cmd, lambda n, op=op: f"HIL_RESULT {n} {op} REJECT why=busy")
                ok, detail = self.run_test("timing", dut)
                self.assertFalse(ok)
                self.assertIn(f"{op}: HIL_RESULT {nonce} {op} REJECT why=busy", detail)

    def test_timing_passes_at_the_hosts_rate_and_fails_on_a_short_delay(self):
        ok, detail = self.run_test("timing", self.dut())
        self.assertTrue(ok, detail)
        self.assertIn(f"delay({ht.DELAY_MS}) {ht.DELAY_MS * 1000 + 400} us", detail)
        ok, detail = self.run_test("timing", self.dut(delay_us=ht.DELAY_MS * 900))
        self.assertFalse(ok)
        self.assertIn(f"delay({ht.DELAY_MS}) {ht.DELAY_MS * 0.9:.1f} ms outside the host bracket", detail)

    def test_millis_must_lie_in_the_hosts_bracket_widened_by_the_tolerance(self):
        for rate, ok_ in ((0.95, False), (0.995, True), (1.005, True), (1.05, False)):
            with self.subTest(rate=rate):
                ok, detail = self.run_test("timing", self.dut(rate=rate))
                self.assertEqual(ok, ok_, detail)
                if not ok_:
                    self.assertIn("millis() ", detail)
                    self.assertIn("outside the host bracket", detail)

    def test_timing_bracket_uses_this_profiles_tolerance(self):
        # [1000, 1000] ms widened by TIMING_TOLERANCE (1%) and one millis() tick: [989, 1011]
        for dev_ms in (989.1, 1000, 1010.9):
            self.assertEqual(E.core_timing_problem(dev_ms, 1000, 1000), "", dev_ms)
        for dev_ms in (988.9, 1011.1):
            self.assertEqual(
                E.core_timing_problem(dev_ms, 1000, 1000),
                f"{dev_ms:.1f} ms outside the host bracket [989.0, 1011.0] ms",
            )


class Rosters(unittest.TestCase):
    def test_checked_in_roster_loads(self):
        roster = E.load_roster(ROOT / "test/hil/ci.json")
        self.assertEqual(sorted(roster), sorted(ht.BUILD.RIG_BOARDS))
        for name, board in roster.items():
            self.assertEqual(board["arduino"]["tests"], list(ht.ROLE_TESTS["device"]), name)
            self.assertIn("usb_port", board, name)

    def test_example_roster_names_a_profile_board(self):
        boards = json.loads((ROOT / "test/hil/local.example.json").read_text())["boards"]
        for b in boards:
            self.assertIn("span", ht.BUILD.BOARDS[b["name"]])
            self.assertEqual(b["arduino"]["tests"], list(ht.ROLE_TESTS["device"]))


class Profile(unittest.TestCase):
    def test_tests_and_sketches_agree(self):
        sketches = {Path(s).name for s in ht.BUILD.HIL_SKETCHES["device"]}
        self.assertEqual(set(ht.TESTS.values()), sketches)  # the engine's bind() checks the restore and the roles

    def test_remote_records_stay_under_the_ignored_build_dir(self):
        self.assertTrue(ht.REMOTE_RUNS.startswith("build/"))
        self.assertIn("\n/build\n", (ROOT / ".gitignore").read_text())

    def test_each_rig_boards_chip_comes_from_the_build_profile(self):
        self.assertEqual(
            {b: E.core_chip({"name": b}) for b in ht.BUILD.RIG_BOARDS},
            {"espressif_s3_devkitm": "esp32s3", "espressif_p4_function_ev": "esp32p4"},
        )

    def test_engine_is_bound_to_this_profile(self):
        self.assertIs(E.P, ht)
        self.assertIs(E.B.P, ht.BUILD)


if __name__ == "__main__":
    unittest.main()
