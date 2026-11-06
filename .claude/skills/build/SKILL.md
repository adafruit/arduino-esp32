---
name: build
description: The Arduino ESP32 core build contract. Use when a change must be verified by building, when an agent needs the boards and sketches a diff affects, when a HIL run or debug session needs firmware and its build record, or when a workflow asks for "the project's build". Resolves scope to boards, compiles the bundled libraries' sketches and the HIL sketches with arduino-cli against this checkout as the Espressif ESP32 platform, reports pass/fail with the first error.
---

# Build contract

`scripts/check_build.py` is the entry point for verifying a change; agents and workflows call it rather than composing
`arduino-cli compile` lines. It is this core's profile for agentrc's `arduino` skill (`arduino_build.py`) in core
mode, loaded from the installed agentrc (`${AGENTRC_DIR:-$HOME/.claude}`), never fetched; CI fetches the commit
`test/hil/agentrc.json` pins. `.claude/skills/hil-contract/scripts/agentrc_pin.py check` names the one in use. That
skill's page ("A core") is the shared behavior: the isolated arduino-cli environment that makes this checkout the
`espressif:esp32` platform whatever is installed or linked under `~/Arduino/hardware`, bundled libraries as the
core's own and the record. This page is what is this core's.

```bash
B=.claude/skills/build/scripts/check_build.py
python3 $B --scope <changed paths or dirs> -j 16      # boards and sketches a change affects
python3 $B --base <A> -j 16                           # same, from the topic's diff over the agent tip
python3 $B --base <A> --worktree -j 16                # same, plus uncommitted and untracked changes
python3 $B --select-only (--scope ... | --base REF [--worktree] | --diff-file FILE) [--hil-config ROSTER]
python3 $B --board espressif_s3_devkitm [--board ...] [--example libraries/Wire/examples/WireScan ...]
python3 $B --board espressif_s3_devkitm --shared --record build/hil/espressif_s3_devkitm.build.json \
  --hil-config test/hil/ci.json
```

Prerequisites: the toolchains and prebuilt ESP-IDF libraries in this checkout (`cd tools && python3 get.py`), and
PyYAML for the sketches' `ci.yml`; a missing one is exit 2 naming it. No sketch needs a library outside the core.

The last stdout line is JSON: `pass`; `firstError`, and `error` on exit 2 naming the cause or remedy; `boards[]` (one
row per board and sketch: `status` `ok`, `failed` or `error`, `fqbn`, `log`, `artifacts`, `platform`,
`foreignHeaders`, `libraries`, `removed`); `tests[]`; `paths[]` (each changed path's `rule` and `reason`);
`uncovered`; `dependencies`; `nothingToBuild`; `warnings`; `input` (HEAD, dirty, submodules); `narrowed`; `record`
when one was written. Exit 0 pass, 1 a build, test or record check failed, 2 usage or a missing prerequisite, 3 an
uncovered path; 2 outranks 1, and 1 outranks 3. Each build's log is `<buildDir>/check_build.log`.

## Reporting

An agent that reports `buildOk` and `notes` (agentrc's `code-writer`) maps the JSON this way: `buildOk` is `pass`. A
pass with no build or test run is "nothing to build": say so in `notes`. Exit 3 is `buildOk` false with each
`uncovered` reason quoted verbatim. Exit 1 or 2 quotes `firstError` (and `error`). Each `warnings` entry is quoted in
`notes`.

## Judgment

- **Selection is the script's**, first match per path; `paths[].reason` says why:
  - a changed file of a bundled library's sketch builds that sketch wherever it is eligible;
  - `cores/`, `tools/` (partitions, `gen_esp32part.py`, the prebuilt libraries) and
    `package/package_esp32_index.template.json` (the toolchain and ESP-IDF pin: rerun `get.py` first) build every
    representative;
  - `variants/<v>/` the boards in the table on that variant (only the CI targets' and the rig boards'; any other
    variant is uncovered); `boards.txt` and `platform.txt` every CI target and both rig boards;
  - a bundled library's source builds its sketches and those of every bundled library that includes its headers,
    transitively, on the representatives;
  - `.github/scripts/socs_config.sh` and `sketch_utils.sh` run the contract tests, which hold the board table and the
    FQBN rules to them; the rest of `.github/`, `docs/` and repo metadata build nothing;
  - `tests/` (upstream's pytest-embedded validation), `idf_component_examples/`, the ESP-IDF component files,
    `programmers.txt`, `tools/get.py` and anything unmatched are uncovered.
- **Boards** (`BOARDS`): CI's targets (`socs_config.sh` `CORE_SOCS`: `esp32`, `esp32c3`, `esp32c5`, `esp32c6`,
  `esp32h2`, `esp32p4`, `esp32s2`, `esp32s3`) with `sketch_utils.sh`'s default options as CI runs them (`CI=true`, so
  P4 builds `CDCOnBoot=default`), and the rig boards `espressif_s3_devkitm` and `espressif_p4_function_ev`: USB-OTG
  (TinyUSB) with CDC on boot, `FlashSize=4M`, the P4 `ChipVariant=prev3`, each with the farm's USB-switch fixture
  `test/hil/esp32_ts3usb30.cpp`. Representatives: both rig boards, `esp32` and `esp32c6` (Xtensa and RISC-V twice).
- **Sketches** are every `.ino` dir under `libraries/`, as CI scans them, filtered and configured by their `ci.yml` as
  `sketch_utils.sh` reads it: `targets: {<chip>: false}` skips that target; `requires` (all) and `requires_any` (one)
  are anchored regular expressions over the build's `tools/esp32-arduino-libs/<chip variant>/sdkconfig` (the rig P4's
  is `esp32p4_es`); `fqbn_append` (a string, or a map with `default`) adds menu options over the target's; a full
  `fqbn` list replaces them. A rig board keeps its `FlashSize`, `ChipVariant`, `USBMode` and `CDCOnBoot` over a
  sketch's `fqbn_append`. A `ci.yml` key this profile does not read refuses the build. The contract tests pin the
  sketches no board builds (`unbuildable_examples()`).
- **Cost**: each compile takes about 30 CPU seconds. A `cores/` change selects about 1100 compiles, `boards.txt`
  about 2800: pass `-j` near the host's core count. While iterating, narrow with `--board`/`--example`
  (`narrowed: true`, the change's selection unverified), then run the full selection before a PR.
- **A HIL record** (`--board B --shared --record FILE --hil-config ROSTER`, by convention
  `build/hil/<board>.build.json`) is the HIL contract's build receipt; each sketch's VID:PID is `USB.cpp`'s
  `USB_VID`/`USB_PID` (a `-D` flag, the variant's `pins_arduino.h`, else `USB.cpp`'s 303a:0002).
- **Private dirs for parallel agents.** Each build uses `build/agent-<pid>/<board>/<sketch path>`, removed when it
  passes; `--shared` builds into `build/hil/<board>/<sketch>` under `build/hil/.lock` and keeps it for flashing.
- **Printing a command is not verification.** A verdict is the JSON of a run that happened; an agent that cannot run
  the script reports the build as not run.

## Limits

- S2, C3, C5 and H2 are no representative: a `cores/` or library change compiles nothing for them; their own sketch,
  variant or recipe changes do.
- `CameraWebServer` lists several FQBNs for `esp32`, `esp32s2` and `esp32s3`; CI builds each, this contract only the
  first, sorted (four configurations omitted, pinned by a contract test).
- The FQBN parity tests run `sketch_utils.sh`'s own option functions; its `ci.yml` reading (yq) is reimplemented and
  tested against its documented semantics, not run.
