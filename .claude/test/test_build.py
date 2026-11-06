#!/usr/bin/env python3
"""The build contract's profile: the board table against upstream CI's targets and FQBN rules (socs_config.sh and
sketch_utils.sh, run here without yq), ci.yml eligibility and FQBNs, source classification and selection through
agentrc's arduino_build.py in core mode, and the VID:PID adapter. arduino-cli is not run; a real build is evidence
only from a run of the script itself."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "build" / "scripts"))
import check_build as cb  # noqa: E402

E = cb.engine()
SKETCH_UTILS = ROOT / ".github/scripts/sketch_utils.sh"


def ci_function(call, ci="true"):
    """`call` under sketch_utils.sh's FQBN functions (sourcing the script runs its command dispatch)."""
    lines, keep = [], False
    for line in SKETCH_UTILS.read_text().splitlines():
        if line.startswith(("function _normalize_fqbn_opts ", "function apply_cdc_on_boot_opt ")) or line.startswith(
            "function default_fqbn_for_target "
        ):
            keep = True
        if keep:
            lines.append(line)
            keep = line != "}"
    env = {**os.environ, "CI": ci}
    return subprocess.run(
        ["bash", "-c", "\n".join(lines + [call])], capture_output=True, text=True, check=True, env=env
    ).stdout.strip()


def with_ci_yml(text):
    """A patch making every sketch's ci.yml `text`."""
    import yaml

    return mock.patch.object(cb, "ci_yml", lambda example: yaml.safe_load(text) or {})


class Tables(unittest.TestCase):
    def test_ci_targets_are_socs_config_core_socs(self):
        out = subprocess.run(
            ["bash", "-c", 'source .github/scripts/socs_config.sh && echo "${CORE_SOCS[@]}"'],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        self.assertEqual(sorted(out), sorted(cb.CI_TARGETS))

    def test_ci_board_fqbns_are_sketch_utils_defaults(self):
        for target in cb.CI_TARGETS:
            want = ci_function(f"default_fqbn_for_target {target} '' '' '' espressif:esp32 ''")
            self.assertEqual(cb.BOARDS[target]["fqbn"], want, target)

    def test_library_name_is_the_platforms(self):
        self.assertIn(f"name={cb.LIBRARY_NAME}\n", (ROOT / "platform.txt").read_text())

    def test_every_fqbn_option_is_a_boards_txt_menu(self):
        props = cb.boards_txt()
        for name, entry in cb.BOARDS.items():
            board_id, options = cb.fqbn_parts(entry["fqbn"])
            for menu, option in options.items():
                self.assertIn(f"menu.{menu}.{option}", props[board_id], f"{name}: {menu}={option}")

    def test_representatives_and_rig_boards(self):
        for family, boards in cb.REPRESENTATIVES.items():
            for b in boards:
                self.assertEqual(cb.BOARDS[b]["family"], family)
        self.assertEqual({b for b, v in cb.BOARDS.items() if "span" in v}, set(cb.RIG_BOARDS))
        for b in cb.RIG_BOARDS:
            self.assertEqual(cb.BOARDS[b]["fixture"], cb.FIXTURE)
            self.assertEqual(cb.BOARDS[b]["chip"], cb.fqbn_parts(cb.BOARDS[b]["fqbn"])[0])

    def test_chip_variants(self):
        self.assertEqual(cb.chip_variant(cb.BOARDS["espressif_p4_function_ev"]["fqbn"]), "esp32p4_es")
        self.assertEqual(cb.chip_variant(cb.BOARDS["esp32p4"]["fqbn"]), "esp32p4")
        self.assertEqual(cb.chip_variant(cb.BOARDS["espressif_s3_devkitm"]["fqbn"]), "esp32s3")
        for entry in cb.BOARDS.values():
            self.assertTrue((ROOT / cb.LIBS_DIR / cb.chip_variant(entry["fqbn"]) / "sdkconfig").is_file())

    def test_unbuildable_examples_are_pinned(self):
        # their ci.yml requires Bluedroid, which no prebuilt sdkconfig enables: CI skips them on every target too
        self.assertEqual(
            E.unbuildable_examples(),
            [
                "libraries/BLE/examples/BLE5_extended_scan",
                "libraries/BLE/examples/BLE5_multi_advertising",
                "libraries/BLE/examples/BLE5_periodic_advertising",
                "libraries/BLE/examples/BLE5_periodic_sync",
            ],
        )

    def test_every_ci_yml_parses(self):
        for example in E.examples():
            cb.ci_yml(example)

    def test_contract_files_exist(self):
        for f in cb.CONTRACT_FILES:
            self.assertTrue((ROOT / f).is_file(), f)


class CiYml(unittest.TestCase):
    """sketch_utils.sh's ci.yml semantics."""

    S = "libraries/ESP32/examples/ChipID/GetChipID"

    def test_targets_false_skips_that_target_only(self):
        with with_ci_yml("targets:\n  esp32s2: false\n"):
            self.assertTrue(cb.exclude("esp32s2", self.S))
            self.assertFalse(cb.exclude("esp32s3", self.S))

    def test_requires_all_and_requires_any_one(self):
        with with_ci_yml("requires:\n  - CONFIG_SOC_WIFI_SUPPORTED=y\n"):
            self.assertFalse(cb.exclude("esp32", self.S))
            self.assertTrue(cb.exclude("esp32h2", self.S))
        with with_ci_yml("requires_any:\n  - CONFIG_SOC_WIFI_SUPPORTED=y\n  - CONFIG_SOC_IEEE802154_SUPPORTED=y\n"):
            self.assertFalse(cb.exclude("esp32h2", self.S))
            self.assertFalse(cb.exclude("esp32s2", self.S))
            self.assertTrue(cb.exclude("esp32p4", self.S))

    def test_requirements_are_anchored_regexes(self):
        with with_ci_yml("requires:\n  - CONFIG_SOC_WIFI_SUPPORTED=[yn]\n"):
            self.assertFalse(cb.exclude("esp32", self.S))
        with with_ci_yml("requires:\n  - SOC_WIFI_SUPPORTED=y\n"):
            self.assertTrue(cb.exclude("esp32", self.S))

    def test_c5_matter_over_thread_exception_is_requires_only(self):
        with with_ci_yml("requires:\n  - CONFIG_ENABLE_MATTER_OVER_THREAD=y\n"):
            self.assertFalse(cb.exclude("esp32c5", self.S))
            self.assertTrue(cb.exclude("esp32s3", self.S))
        with with_ci_yml("requires_any:\n  - CONFIG_ENABLE_MATTER_OVER_THREAD=y\n"):
            self.assertTrue(cb.exclude("esp32c5", self.S))

    def test_rig_p4_reads_its_own_chip_variants_sdkconfig(self):
        seen = []
        real = cb.sdkconfig.__wrapped__
        with with_ci_yml("requires:\n  - CONFIG_IDF_TARGET_ESP32P4=y\n"), mock.patch.object(
            cb, "sdkconfig", lambda v: seen.append(v) or real(v)
        ):
            cb.exclude("espressif_p4_function_ev", self.S)
        self.assertEqual(seen, ["esp32p4_es"])

    def test_missing_sdkconfig_refuses(self):
        with with_ci_yml("requires:\n  - CONFIG_X=y\n"), mock.patch.object(cb, "LIBS_DIR", "nowhere"):
            cb.sdkconfig.cache_clear()
            try:
                with self.assertRaises(cb.ProfileError):
                    cb.exclude("esp32", self.S)
            finally:
                cb.sdkconfig.cache_clear()

    def test_unknown_keys_shapes_and_yaml_errors_refuse(self):
        for text in (
            "platforms:\n  qemu: false\n",
            "requires: CONFIG_SOC_WIFI_SUPPORTED=y\n",
            "targets:\n  esp32: no-thanks\n",
            "fqbn:\n  esp32: espressif:esp32:esp32\n",
            "fqbn_append: [PSRAM=enabled]\n",
            "requires: [unclosed\n",
            "false\n",
            "[]\n",
            "true\n",
            "- requires: []\n",
        ):
            with tempfile.TemporaryDirectory() as tmp, mock.patch.object(cb, "ROOT", Path(tmp)):
                (Path(tmp) / "s").mkdir()
                (Path(tmp) / "s/ci.yml").write_text(text)
                with self.assertRaises(cb.ProfileError, msg=text):
                    cb.ci_yml.__wrapped__("s")

    def test_fqbn_append_matches_sketch_utils(self):
        cases = {
            "fqbn_append: PartitionScheme=huge_app": "PartitionScheme=huge_app",
            "fqbn_append:\n  default: PartitionScheme=huge_app\n  esp32: PartitionScheme=min_spiffs,PSRAM=disabled": {
                "esp32": "PartitionScheme=min_spiffs,PSRAM=disabled",
                "esp32s3": "PartitionScheme=huge_app",
            },
        }
        for text, appends in cases.items():
            for target in cb.CI_TARGETS:
                append = appends if isinstance(appends, str) else appends.get(target, appends["esp32s3"])
                want = ci_function(f"default_fqbn_for_target {target} '' '' '' espressif:esp32 '{append}'")
                with with_ci_yml(text):
                    self.assertEqual(cb.fqbn(target, self.S), want, (text, target))

    def test_full_fqbn_takes_the_first_sorted_and_p4_cdc_rule(self):
        text = "fqbn:\n  esp32p4:\n    - espressif:esp32:esp32p4:PSRAM=enabled,USBMode=default,ChipVariant=postv3\n"
        with with_ci_yml(text):
            self.assertEqual(
                cb.fqbn("esp32p4", self.S),
                ci_function(
                    "apply_cdc_on_boot_opt espressif:esp32:esp32p4:PSRAM=enabled,USBMode=default,ChipVariant=postv3"
                ),
            )
            self.assertEqual(cb.fqbn("esp32s3", self.S), cb.BOARDS["esp32s3"]["fqbn"])
        with with_ci_yml("fqbn:\n  esp32:\n    - espressif:esp32:esp32:b=2\n    - espressif:esp32:esp32:a=1\n"):
            self.assertEqual(cb.fqbn("esp32", self.S), "espressif:esp32:esp32:a=1")

    def test_omitted_multi_fqbn_configurations_are_pinned(self):
        # CI builds every FQBN a ci.yml lists for a target; this contract builds the first (Limits)
        omitted = {}
        for example in E.examples():
            for target, fqbns in (cb.ci_yml(example).get("fqbn") or {}).items():
                if len(fqbns) > 1:
                    omitted[f"{example} {target}"] = sorted(fqbns)[1:]
        cam = "libraries/ESP32/examples/Camera/CameraWebServer"
        self.assertEqual(
            omitted,
            {
                f"{cam} esp32": ["espressif:esp32:esp32:PSRAM=enabled,PartitionScheme=custom,FlashMode=dio"],
                f"{cam} esp32s2": ["espressif:esp32:esp32s2:PSRAM=enabled,PartitionScheme=custom,FlashMode=dio"],
                f"{cam} esp32s3": [
                    "espressif:esp32:esp32s3:PSRAM=enabled,USBMode=default,PartitionScheme=custom,FlashMode=qio",
                    "espressif:esp32:esp32s3:PSRAM=opi,USBMode=default,PartitionScheme=custom,FlashMode=qio",
                ],
            },
        )

    def test_rig_boards_take_what_a_sketch_asks_but_never_other_hardware(self):
        with with_ci_yml("fqbn_append: PartitionScheme=huge_app,FlashSize=4M,PSRAM=enabled"):
            self.assertFalse(cb.exclude("espressif_s3_devkitm", self.S))
            self.assertEqual(
                cb.fqbn("espressif_s3_devkitm", self.S),
                "espressif:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=4M,PSRAM=enabled,"
                "PartitionScheme=huge_app",
            )
        for asks in ("FlashSize=16M", "USBMode=hwcdc", "CDCOnBoot=default"):
            with with_ci_yml(f"fqbn_append: PartitionScheme=huge_app,{asks}"):
                self.assertTrue(cb.exclude("espressif_s3_devkitm", self.S), asks)
                self.assertFalse(cb.exclude("esp32s3", self.S), asks)

    def test_rig_boards_take_a_full_fqbns_options(self):
        sr = "libraries/ESP_SR/examples/Basic"  # its full FQBNs ask 16 MB flash: no rig board builds it
        self.assertTrue(cb.exclude("espressif_s3_devkitm", sr))
        self.assertTrue(cb.exclude("espressif_p4_function_ev", sr))
        text = (
            "fqbn:\n  esp32p4:\n    - espressif:esp32:esp32p4:USBMode=default,PartitionScheme=huge_app,FlashMode=qio\n"
        )
        with with_ci_yml(text):
            self.assertFalse(cb.exclude("espressif_p4_function_ev", self.S))
            self.assertEqual(
                cb.fqbn("espressif_p4_function_ev", self.S),
                "espressif:esp32:esp32p4:USBMode=default,CDCOnBoot=cdc,FlashSize=4M,ChipVariant=prev3,"
                "PartitionScheme=huge_app,FlashMode=qio",
            )

    def test_hil_sketches_take_the_rig_fqbn(self):
        self.assertEqual(cb.fqbn("espressif_s3_devkitm", "test/hil/x"), cb.BOARDS["espressif_s3_devkitm"]["fqbn"])


class Selection(unittest.TestCase):
    def test_rules(self):
        wire = sorted(
            [e for e in E.examples() if e.startswith("libraries/Wire/")]
            + ["libraries/ESP32/examples/CI/CIBoardsTest", "libraries/ESP_I2S/examples/ES8388_loopback"]
        )
        cases = {
            "cores/esp32/HardwareSerial.cpp": ("shared", None),
            "tools/partitions/default.csv": ("shared", None),
            "tools/gen_esp32part.py": ("shared", None),
            "tools/esp32-arduino-libs/esp32c5/sdkconfig": ("boards", ("esp32c5",)),
            "tools/esp32-arduino-libs/esp32p4_es/lib/libx.a": ("boards", ("espressif_p4_function_ev",)),
            "tools/esp32-arduino-libs/hosted/x.bin": ("uncovered", None),
            "package/package_esp32_index.template.json": ("shared", None),
            "libraries/Wire/src/Wire.cpp": ("sketches", wire),
            "libraries/ESP32/examples/ChipID/GetChipID/GetChipID.ino": (
                "example",
                "libraries/ESP32/examples/ChipID/GetChipID",
            ),
            ".github/scripts/socs_config.sh": ("tests", "build"),
            ".github/scripts/sketch_utils.sh": ("tests", "build"),
            ".claude/skills/build/scripts/check_build.py": ("tests", "build"),
            ".github/workflows/push.yml": ("nothing", None),
            "docs/en/index.rst": ("nothing", None),
            "CLAUDE.md": ("nothing", None),
            "README.md": ("nothing", None),
            "tests/validation/uart/uart.ino": ("uncovered", None),
            "idf_component_examples/hello_world/main/main.cpp": ("uncovered", None),
            "CMakeLists.txt": ("uncovered", None),
            "tools/get.py": ("uncovered", None),
            "programmers.txt": ("uncovered", None),
            "weird/file": ("uncovered", None),
        }
        for path, want in cases.items():
            self.assertEqual(E.classify(path)[:2], want, path)

    def test_a_library_builds_the_sketches_of_libraries_including_it(self):
        effect, sketches, _ = E.classify("libraries/FS/src/FS.cpp")
        self.assertEqual(effect, "sketches")
        libs = {s.split("/")[1] for s in sketches}
        self.assertTrue({"SD", "SD_MMC", "LittleFS", "SPIFFS", "WebServer"} <= libs, libs)
        self.assertNotIn("Wire", libs)
        self.assertEqual(E.classify("libraries/NoSuchLib/src/x.h")[0], "uncovered")

    def test_a_variant_builds_the_boards_on_it(self):
        effect, boards, _ = E.classify("variants/esp32s3/pins_arduino.h")
        self.assertEqual((effect, sorted(boards)), ("boards", ["esp32s3", "espressif_s3_devkitm"]))
        effect, boards, _ = E.classify("variants/esp32p4/pins_arduino.h")
        self.assertEqual((effect, sorted(boards)), ("boards", ["esp32p4", "espressif_p4_function_ev"]))
        self.assertEqual(E.classify("variants/adafruit_feather_esp32s3/pins_arduino.h")[0], "uncovered")

    def test_recipes_build_ci_and_the_rig_boards(self):
        for path in ("boards.txt", "platform.txt"):
            effect, boards, _ = E.classify(path)
            self.assertEqual((effect, sorted(boards)), ("boards", sorted(cb.CI_BOARDS + cb.RIG_BOARDS)))

    def test_core_change_builds_every_representative(self):
        sel = E.select(["cores/esp32/esp32-hal-gpio.c"])
        self.assertEqual(sorted(sel["builds"]), sorted(b for f in cb.REPRESENTATIVES.values() for b in f))


class Identity(unittest.TestCase):
    def commands(self, variant, *flags):
        d = Path(self.tmp.name)
        argv = ["g++", f"-I{ROOT}/variants/{variant}", *flags]
        (d / "compile_commands.json").write_text(
            json.dumps([{"file": f"{ROOT}/cores/esp32/USB.cpp", "arguments": argv}])
        )
        return cb.vid_pid(d)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_variant_header_then_usb_cpp_fallback(self):
        self.assertEqual(self.commands("esp32s3"), "303a:1001")
        self.assertEqual(self.commands("esp32p4"), "303a:0002")

    def test_variant_read_from_this_checkout_once_the_builds_sketchbook_is_gone(self):
        d = Path(self.tmp.name)
        argv = ["g++", "-I/gone/build/.arduino-cli-1/sketchbook/hardware/espressif/esp32/variants/esp32s3"]
        (d / "compile_commands.json").write_text(json.dumps([{"file": "/gone/cores/esp32/USB.cpp", "arguments": argv}]))
        self.assertEqual(cb.vid_pid(d), "303a:1001")

    def test_compile_flags_win(self):
        self.assertEqual(self.commands("esp32s3", "-DUSB_VID=0x239A", "-DUSB_PID=0x8113"), "239a:8113")

    def test_unresolved_is_none(self):
        self.assertIsNone(cb.vid_pid(Path(self.tmp.name) / "missing"))
        (Path(self.tmp.name) / "compile_commands.json").write_text("[]")
        self.assertIsNone(cb.vid_pid(Path(self.tmp.name)))


if __name__ == "__main__":
    unittest.main()
