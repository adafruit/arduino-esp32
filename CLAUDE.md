# Arduino ESP32 Core Agent Instructions

## Working Rules

- Espressif's Arduino core (the `espressif:esp32` board package), maintained upstream at espressif/arduino-esp32.
  Agent support lives only on branch `hathach/agent` of adafruit/arduino-esp32, as commits touching only paths
  upstream lacks: this file, `AGENTS.md`, `.agents`, `.claude/`, `test/hil/` and `.pre-commit-agent.yaml`. None of
  them goes upstream (PRs and Follow-ups).
- No standalone build: sketches compile against this checkout as the `espressif:esp32` platform through the build
  contract's isolated arduino-cli environment, never the installed board package or the `~/Arduino/hardware` link.
  Each checkout or worktree needs its toolchains and prebuilt ESP-IDF libraries first: `cd tools && python3 get.py`
  (a worktree may link `tools/dist` to another checkout's download cache).
- Development boards: the ci.lan farm's `espressif_s3_devkitm` (ESP32-S3) and `espressif_p4_function_ev`
  (ESP32-P4).
- Code references - runtime: `cores/esp32/` (`esp32-hal-*.c` over ESP-IDF, `USB.cpp`/`USBCDC.cpp` on TinyUSB,
  `HWCDC.cpp` on the USB-Serial-JTAG, `HardwareSerial`); boards: `variants/<variant>/`, `boards.txt`,
  `platform.txt`; bundled libraries: `libraries/`; prebuilt ESP-IDF: `tools/esp32-arduino-libs/<chip>/` (its
  `sdkconfig` per chip), pinned by `package/package_esp32_index.template.json`; CI's matrix and sketch rules:
  `.github/scripts/socs_config.sh`, `.github/scripts/sketch_utils.sh` and each sketch's `ci.yml`; upstream's own
  pytest-embedded validation: `tests/`, outside both contracts.

## Code Rules

- Upstream files keep upstream's conventions; `.pre-commit-config.yaml` (upstream's) applies to every file, agent
  files included: black and flake8 at 120 columns, clang-format v18 with `.clang-format`, prettier on YAML,
  codespell, vale on Markdown.
- Check chip, peripheral and USB behavior against the chip's datasheet, technical reference manual and errata
  (agentrc's `read-doc`) before changing or reviewing code that depends on it.
- Keep each file's line endings.

## Skills

- Agents, skills and workflows beyond this repo's `.claude/` come from [agentrc](https://github.com/hathach/agentrc);
  install it before agent work on this core. Its `arduino` skill's core mode holds the mechanics both contracts run,
  shared with the Adafruit SAMD core, Adafruit TinyUSB Arduino and Adafruit SPIFlash.
- Skill script tests live in `.claude/test/test_*.py`; `.pre-commit-agent.yaml` runs them against the installed
  agentrc (`${AGENTRC_DIR:-$HOME/.claude}`); CI fetches the commit `test/hil/agentrc.json` pins instead.
- Hardware diagnosis and repair use agentrc's `hw-debugger`; independent hardware claims and committed-fix validation
  use `hw-validator`; routine HIL runs use `hil-operator` - all orchestrated by `chief`.

## Build and Validate

- Build contract: `.claude/skills/build/SKILL.md`. It resolves a change to boards and sketches and builds them with
  arduino-cli against this checkout; `--shared --record` writes the HIL build record and keeps the images HIL flashes.
- HIL contract: `.claude/skills/hil-contract/SKILL.md`. It owns taking and releasing a rig board, names the roster for
  the host you are on, runs the battery on a dev PC's board or the ci.lan farm, and gives hw-validator and
  hw-debugger their manual sessions. Manual runs only: no CI job runs it. Hardware validation comes from its report,
  never from a build.
- For code changes: `python3 .claude/skills/build/scripts/check_build.py --base <A> --worktree -j 16`.
- Before submitting, and again after a rebase: `pre-commit run --all-files` and
  `pre-commit run --config .pre-commit-agent.yaml --all-files`.

## PRs and Follow-ups

- Topic work branches from `hathach/agent` at a recorded tip `A` over upstream commit `U`, keeping a ref on the
  tested commit `X`. An upstream PR head is `git rebase --onto U A` of a copy of the topic: its full tree must equal
  `X`'s outside the agent paths above (modes and gitlinks included), and its evidence says "HIL-tested at `X`;
  firmware sources identical to `Y`". Publishing over a newer upstream than `U` rebuilds and reruns HIL.
- Before rebasing `hathach/agent` onto a new upstream commit, check upstream still lacks every agent path.
