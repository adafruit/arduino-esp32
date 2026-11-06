#!/usr/bin/env python3
"""Build this core's bundled-library and HIL sketches with arduino-cli: the project's build contract (SKILL.md).

  check_build.py (--scope PATH... | --base REF [--worktree] | --diff-file FILE) [--example E]... [-j N]
  check_build.py --board B... [--example E]... [--shared] [--build-property K=V]...
  check_build.py --board B --shared --record FILE --hil-config ROSTER [--experimental --build-property K=V...]
  check_build.py --select-only (--scope ... | --base REF [--worktree] | --diff-file FILE) [--hil-config ROSTER]

stdout ends with one JSON line. Exit 0 pass, 1 a build or test failed, 2 usage or a missing
prerequisite ("error" names the remedy), 3 an uncovered path. 2 outranks 1, 1 outranks 3.

This file is the core's profile for agentrc's arduino_build.py in core mode (the `arduino` skill), loaded from the
agentrc test/hil/agentrc.json pins; the mechanics are there. Sketch eligibility and FQBNs follow upstream CI's
.github/scripts/sketch_utils.sh over each sketch's ci.yml.
"""

import functools
import json
import os
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "hil-contract" / "scripts"))
import agentrc_pin  # noqa: E402

LIBRARY_NAME = "ESP32 Arduino"  # platform.txt name=
PLATFORM = "espressif:esp32"
SKETCH_ROOTS = ("libraries",)
LIBS_DIR = "tools/esp32-arduino-libs"  # tools/get.py's prebuilt ESP-IDF, one dir per build.chip_variant
GET_HINT = "cd tools && python3 get.py"

# CI's targets (socs_config.sh CORE_SOCS) and their default options (sketch_utils.sh default_fqbn_for_target): a
# contract test holds both to the scripts
CI_TARGETS = {
    "esp32": "PSRAM=enabled",
    "esp32c3": "",
    "esp32c5": "PSRAM=enabled",
    "esp32c6": "",
    "esp32h2": "",
    "esp32p4": "PSRAM=enabled,USBMode=hwcdc,ChipVariant=postv3",
    "esp32s2": "PSRAM=enabled",
    "esp32s3": "PSRAM=opi,USBMode=default",
}


def merge_options(*groups):
    """sketch_utils.sh _normalize_fqbn_opts: later groups win per menu key, each key at its first position."""
    out = {}
    for group in groups:
        for option in (o.strip() for o in (group or "").split(",")):
            if option:
                out[option.split("=", 1)[0]] = option
    return ",".join(out.values())


def ci_fqbn(target, options):
    """`options` on CI's target, P4's serial mapping last as CI's apply_cdc_on_boot_opt sets it (CI=true: UART0)."""
    if target == "esp32p4":
        options = merge_options(options, "CDCOnBoot=default")
    return f"{PLATFORM}:{target}:{options}" if options else f"{PLATFORM}:{target}"


BOARDS = {t: {"fqbn": ci_fqbn(t, o), "family": t, "filters": t} for t, o in CI_TARGETS.items()}
CI_BOARDS = tuple(BOARDS)
FIXTURE = "test/hil/esp32_ts3usb30.cpp"


def rig(target, options):
    """A farm board on the USB-OTG (TinyUSB) stack with CDC on boot: `span` is the 4 MB SPI flash esptool writes
    (FlashSize), `chip` esptool's --chip; the fixture routes its OTG port to ci.lan."""
    return {
        "fqbn": f"{PLATFORM}:{target}:{options}",
        "family": target,
        "filters": target,
        "span": (0, 0x400000),
        "chip": target,
        "fixture": FIXTURE,
    }


# named as in agentrc's board registry; ChipVariant prev3 ("Before v3.00") covers the farm P4's revision
BOARDS["espressif_s3_devkitm"] = rig("esp32s3", "USBMode=default,CDCOnBoot=cdc,FlashSize=4M,PSRAM=disabled")
BOARDS["espressif_p4_function_ev"] = rig("esp32p4", "USBMode=default,CDCOnBoot=cdc,FlashSize=4M,ChipVariant=prev3")
RIG_BOARDS = tuple(b for b, e in BOARDS.items() if "span" in e)
# menu keys a rig board keeps over a sketch's fqbn_append: its flash, chip revision and USB wiring are the hardware's
RIG_KEYS = ("FlashSize", "ChipVariant", "USBMode", "CDCOnBoot")
# Xtensa and RISC-V, each through a rig board and one CI target: what a shared change builds. S2, C3, C5 and H2 build
# only for their own variants, a sketch change or the recipes (SKILL.md, Limits)
REPRESENTATIVES = {
    "esp32s3": ["espressif_s3_devkitm"],
    "esp32": ["esp32"],
    "esp32p4": ["espressif_p4_function_ev"],
    "esp32c6": ["esp32c6"],
}
# the sketches a HIL record carries, the first also the restoration image: it writes no flash
HIL_SKETCHES = {"device": ("test/hil/core_cdc", "test/hil/core_timing")}
CONTRACT_TESTS = {
    "build": ".claude/test/test_build.py",
    "hil": ".claude/test/test_hil.py",
    "hil_remote": ".claude/test/test_hil_remote.py",
    "agentrc_pin": ".claude/test/test_agentrc_pin.py",
}
SMOKE_BOARDS = ("espressif_s3_devkitm",)
NOTHING = (
    ".claude/",
    ".github/",
    ".agents",
    "docs/",
    ".gitlab",
    ".readthedocs.yaml",
    ".vale",
    ".codespellrc",
    ".editorconfig",
    ".flake8",
    ".clang-format",
    ".gitignore",
    ".gitmodules",
    ".prettierignore",
    ".shellcheckrc",
    ".pre-commit-config.yaml",
    ".pre-commit-agent.yaml",
    "package.json",
)
# outside both contracts: no arduino-cli build here makes or runs them
UNCOVERED = {
    "tests/": "upstream's pytest-embedded validation and performance tests: run on Espressif's runners, not here",
    "idf_component_examples/": "ESP-IDF component examples: built by idf.py, not arduino-cli",
    "CMakeLists.txt": "the ESP-IDF component build",
    "idf_component.yml": "the ESP-IDF component manifest",
    "Kconfig.projbuild": "the ESP-IDF component's Kconfig",
    "programmers.txt": "upload programmers: no build or HIL run uses them",
    "tools/get.py": "the tool installer: rerun it (`cd tools && python3 get.py`) and build",
    "tools/ide-debug/": "IDE debug configurations",
    "tools/pre-commit/": "pre-commit helpers",
}
CI_SCRIPTS = (".github/scripts/socs_config.sh", ".github/scripts/sketch_utils.sh")
EXTRA_DEPENDENCIES = ()  # no sketch's ci.yml names `libs`
CONTRACT_FILES = (
    ".claude/skills/build/scripts/check_build.py",
    ".claude/skills/hil-contract/scripts/hil_test.py",
    ".claude/skills/hil-contract/scripts/hil_remote.py",
    ".claude/skills/hil-contract/scripts/agentrc_pin.py",
    "test/hil/agentrc.json",
)
AGENTRC = None  # set by engine(): agentrc_pin.identity()


class ProfileError(Exception):
    """A missing or unreadable input this profile refuses to guess past."""


@functools.lru_cache(maxsize=None)
def boards_txt():
    """{boards.txt id: {property: value}}, or {} where boards.txt is absent (a tree staged on a rig)."""
    path = ROOT / "boards.txt"
    if not path.is_file():
        return {}
    out = {}
    for m in re.finditer(r"^(\w+)\.([\w.]+)=(.*)$", path.read_text(), re.M):
        out.setdefault(m.group(1), {})[m.group(2)] = m.group(3).strip()
    return out


def fqbn_parts(fqbn):
    """(boards.txt id, {menu: option}) of an FQBN."""
    parts = fqbn.split(":", 3)
    options = dict(o.split("=", 1) for o in parts[3].split(",")) if len(parts) > 3 and parts[3] else {}
    return parts[2], options


def chip_variant(fqbn):
    """The FQBN's build.chip_variant, the prebuilt ESP-IDF dir it compiles against: the selected menu option's, else
    the board's, else build.mcu (platform.txt)."""
    board_id, options = fqbn_parts(fqbn)
    props = boards_txt().get(board_id)
    if not props:
        raise ProfileError(f"{board_id} is not in boards.txt")
    for menu, option in options.items():
        value = props.get(f"menu.{menu}.{option}.build.chip_variant")
        if value:
            return value
    return props.get("build.chip_variant") or props["build.mcu"]


@functools.lru_cache(maxsize=None)
def sdkconfig(variant):
    path = ROOT / LIBS_DIR / variant / "sdkconfig"
    if not path.is_file():
        raise ProfileError(f"{path.relative_to(ROOT)} missing: install the tools ({GET_HINT})")
    return path.read_text()


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


# the shape sketch_utils.sh reads each key in
CI_YML_SHAPES = {
    "requires": _strings,
    "requires_any": _strings,
    "targets": lambda v: isinstance(v, dict) and all(isinstance(x, bool) for x in v.values()),
    "fqbn": lambda v: isinstance(v, dict) and all(_strings(x) for x in v.values()),
    "fqbn_append": lambda v: isinstance(v, str)
    or (isinstance(v, dict) and all(isinstance(x, str) for x in v.values())),
}


@functools.lru_cache(maxsize=None)
def ci_yml(example):
    """The sketch's ci.yml as a dict ({} without one); ProfileError on YAML, a key or a shape sketch_utils.sh does not
    read."""
    path = ROOT / example / "ci.yml"
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        raise ProfileError("PyYAML is required to read the sketches' ci.yml: python3 -m pip install PyYAML")
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ProfileError(f"{example}/ci.yml: {e}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ProfileError(f"{example}/ci.yml: a {type(data).__name__}, not a mapping")
    if set(data) - set(CI_YML_SHAPES):
        raise ProfileError(
            f"{example}/ci.yml: keys {sorted(set(data) - set(CI_YML_SHAPES))} this profile does not read"
        )
    bad = [k for k, v in data.items() if v is not None and not CI_YML_SHAPES[k](v)]
    if bad:
        raise ProfileError(f"{example}/ci.yml: {bad} not in the shape sketch_utils.sh reads")
    return data


@functools.lru_cache(maxsize=None)
def meets(requirement, config):
    """sketch_utils.sh check_requirements: `grep -E "^<requirement>"` over the sdkconfig."""
    return bool(re.search("^" + requirement, config, re.M))


def full_fqbn(ci, target):
    """The sketch's first sorted full `fqbn` for `target`, the one CI builds; None without one."""
    return min((ci.get("fqbn") or {}).get(target) or (), default=None)


def requested(ci, target):
    """The options the sketch asks of `target`: its full `fqbn`'s, else its fqbn_append."""
    full = full_fqbn(ci, target)
    return merge_options(*full.split(":", 3)[3:]) if full else fqbn_append(ci, target)


def exclude(board, example):
    """sketch_utils.sh's skips: `targets: {<chip>: false}`, then `requires` (all; Matter over Thread passes on C5,
    whose one sdkconfig is Wi-Fi's) and `requires_any` (one) against the sdkconfig of the build's chip variant; on a
    rig board also a sketch whose options set one of the rig's hardware keys (RIG_KEYS) otherwise."""
    ci = ci_yml(example)
    if not ci:
        return False
    fqbn_ = BOARDS[board]["fqbn"]
    target, options = fqbn_parts(fqbn_)
    if (ci.get("targets") or {}).get(target) is False:
        return True
    variant = chip_variant(fqbn_)
    config = sdkconfig(variant)
    for r in ci.get("requires") or ():
        if not meets(r, config) and not (r == "CONFIG_ENABLE_MATTER_OVER_THREAD=y" and target == "esp32c5"):
            return True
    anyof = ci.get("requires_any") or ()
    if anyof and not any(meets(r, config) for r in anyof):
        return True
    if board in CI_BOARDS:
        return False
    asked = dict(o.split("=", 1) for o in requested(ci, target).split(",") if o)
    return any(k in asked and asked[k] != v for k, v in options.items() if k in RIG_KEYS)


def fqbn_append(ci, target):
    """sketch_utils.sh fqbn_append_for_target: a string for every target, or a map whose `default` the target's
    entry overrides."""
    value = ci.get("fqbn_append") or ""
    if isinstance(value, dict):
        return merge_options(value.get("default"), value.get(target))
    return merge_options(value)


def fqbn(board, example):
    """The FQBN CI builds the sketch with: on a CI target its ci.yml `fqbn` (the first, sorted, of that target's list:
    the others are not built here) or the target's options under its fqbn_append, P4's CDCOnBoot last
    (apply_cdc_on_boot_opt, CI=true); on a rig board the board's own under what the sketch asks (exclude() drops a
    sketch asking other hardware keys)."""
    base = BOARDS[board]["fqbn"]
    ci = ci_yml(example) if example.startswith(SKETCH_ROOTS) else {}
    if not ci:
        return base
    target = fqbn_parts(base)[0]
    asked = requested(ci, target)
    if board not in CI_BOARDS:
        return f"{PLATFORM}:{target}:" + merge_options(base.split(":", 3)[3], asked)
    full = full_fqbn(ci, target)
    if full:
        return ci_fqbn(fqbn_parts(full)[0], asked)
    return ci_fqbn(target, merge_options(CI_TARGETS[target], asked))


def variant_boards(variant):
    """The board names whose FQBN's boards.txt id builds `variant`."""
    return [
        b for b, e in BOARDS.items() if boards_txt().get(fqbn_parts(e["fqbn"])[0], {}).get("build.variant") == variant
    ]


INCLUDE = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
SOURCE_SUFFIXES = (".ino", ".c", ".cpp", ".h", ".hpp")


@functools.lru_cache(maxsize=None)
def library_headers():
    """{header file name: libraries whose src/ has it}."""
    out = {}
    for f in (ROOT / "libraries").glob("*/src/**/*"):
        if f.suffix in (".h", ".hpp"):
            out.setdefault(f.name, set()).add(f.relative_to(ROOT / "libraries").parts[0])
    return out


def included_libraries(files, own=None):
    """The bundled libraries other than `own` whose headers `files` include."""
    out = set()
    for f in files:
        for inc in INCLUDE.findall(f.read_text(errors="replace")):
            out |= library_headers().get(os.path.basename(inc), set())
    return out - {own}


@functools.lru_cache(maxsize=None)
def library_users():
    """{library: libraries whose src/ includes one of its headers}."""
    users = {}
    for src in (ROOT / "libraries").glob("*/src"):
        lib = src.parent.name
        for owner in included_libraries((f for f in src.rglob("*") if f.suffix in SOURCE_SUFFIXES), lib):
            users.setdefault(owner, set()).add(lib)
    return users


@functools.lru_cache(maxsize=None)
def sketch_libraries():
    """{sketch: the bundled libraries its own sources include}."""
    return {e: included_libraries(f for f in (ROOT / e).iterdir() if f.suffix in SOURCE_SUFFIXES) for e in E.examples()}


def dependents(lib):
    """`lib` and every bundled library that includes it, transitively."""
    seen, todo = set(), [lib]
    while todo:
        cur = todo.pop()
        if cur not in seen:
            seen.add(cur)
            todo += library_users().get(cur, ())
    return seen


def library_sketches(lib):
    """The sketches of `lib` and of its dependents, and every sketch including one of them."""
    libs = dependents(lib)
    return sorted(e for e, used in sketch_libraries().items() if e.split("/")[1] in libs or used & libs)


def classify_source(path):
    """The core's own source rules (arduino_build.classify falls through to the common ones on None; a changed file
    of an example sketch is classified before this)."""
    for prefix, why in UNCOVERED.items():
        if path.startswith(prefix):
            return "uncovered", None, why
    if path in CI_SCRIPTS:
        return "tests", "build", "CI's targets, options and sketch rules: the contract tests check parity"
    if path.startswith("cores/"):
        return "shared", None, "core runtime"
    if path.startswith("variants/"):
        variant = path.split("/")[1]
        boards = variant_boards(variant)
        return (
            ("boards", tuple(boards), f"variant {variant}")
            if boards
            else ("uncovered", None, f"variant {variant} is built by no board this contract builds")
        )
    if path in ("boards.txt", "platform.txt"):
        return "boards", CI_BOARDS + RIG_BOARDS, "board and build recipes: CI's targets and the rig boards"
    if path.startswith(LIBS_DIR + "/"):
        variant = path.split("/")[2]
        boards = tuple(b for b, e in BOARDS.items() if chip_variant(e["fqbn"]) == variant)
        return (
            ("boards", boards, f"the prebuilt ESP-IDF of {variant}")
            if boards
            else ("uncovered", None, f"{LIBS_DIR}/{variant} is the chip variant of no board this contract builds")
        )
    if path == "package/package_esp32_index.template.json" or path.startswith("tools/"):
        return "shared", None, "the toolchain and ESP-IDF libraries pin, partitions or build helpers"
    if path.startswith("libraries/"):
        lib = path.split("/")[1]
        sketches = library_sketches(lib)
        return (
            ("sketches", sketches, f"bundled {lib}, the libraries including it and the sketches including either")
            if sketches
            else ("uncovered", None, f"bundled {lib} has no sketch to build, nor does any library including it")
        )
    return None


def vid_pid(build_dir, board=None, roster_entry=None):
    """VID:PID a TinyUSB sketch enumerates with: USB.cpp's USB_VID/USB_PID from the compile's -D flags, else the
    variant's pins_arduino.h, else USB.cpp's fallback (Espressif's 303a:0002); None when unresolved."""
    try:
        commands = json.loads((Path(build_dir) / "compile_commands.json").read_text())
    except (OSError, ValueError):
        return None
    entry = next((c for c in commands if c.get("file", "").endswith("/cores/esp32/USB.cpp")), None)
    if entry is None:
        return None
    try:
        argv = entry.get("arguments") or shlex.split(entry.get("command", ""))
    except ValueError:
        return None
    variant = ""
    for arg in argv:
        # the compile's variant dir is under the build's own sketchbook, gone once it ends: this checkout's by name
        m = re.match(r"-I.*/variants/([^/]+)$", arg)
        header = ROOT / "variants" / m.group(1) / "pins_arduino.h" if m else None
        if header and header.is_file():
            variant += header.read_text(errors="replace")
    # USB.cpp's fallbacks: USB_ESPRESSIF_VID (esp32-hal-tinyusb.h) and its own USB_PID
    source = (ROOT / "cores/esp32/USB.cpp").read_text() + (ROOT / "cores/esp32/esp32-hal-tinyusb.h").read_text()
    fallbacks = {
        "USB_VID": re.search(r"#define\s+USB_ESPRESSIF_VID\s+(0x[0-9a-fA-F]+)", source),
        "USB_PID": re.search(r"#define\s+USB_PID\s+(0x[0-9a-fA-F]+)", source),
    }
    ids = []
    for name, fallback in fallbacks.items():
        values = [a.split("=", 1)[1] for a in argv if a.startswith(f"-D{name}=")]
        values = values or re.findall(rf"#define\s+{name}\s+(0x[0-9a-fA-F]+)", variant)
        values = values or ([fallback.group(1)] if fallback else [])
        if not values:
            return None
        ids.append(int(values[-1], 0))
    return f"{ids[0]:04x}:{ids[1]:04x}"


E = None  # agentrc's arduino_build, bound to this profile by engine()


def engine():
    """agentrc's arduino_build bound to this profile."""
    global AGENTRC, E
    if E is None:
        AGENTRC = agentrc_pin.identity()
        E = agentrc_pin.load("skills/arduino/scripts/arduino_build.py").bind(sys.modules[__name__])
    return E


def main(argv=None):
    try:
        eng = engine()
        if not (ROOT / LIBS_DIR).is_dir():
            raise ProfileError(f"{LIBS_DIR} missing: install the tools ({GET_HINT})")
        return eng.main(argv)
    except agentrc_pin.PinError as e:
        print(json.dumps({"version": 2, "pass": False, "error": str(e), "remedy": e.remedy}))
        return 2
    except ProfileError as e:
        print(json.dumps({"version": 2, "pass": False, "error": str(e)}))
        return 2


if __name__ == "__main__":
    sys.modules.setdefault("check_build", sys.modules[__name__])
    sys.exit(main())
