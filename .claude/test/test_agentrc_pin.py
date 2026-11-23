#!/usr/bin/env python3
"""agentrc_pin.py, agentrc's canonical bootstrap: this core's test/hil/agentrc.json and the agentrc this checkout
really selects. agentrc's tests own the bootstrap's common behavior; nothing here fetches or reaches a rig."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "hil-contract" / "scripts"))
import agentrc_pin  # noqa: E402
import hil_test  # noqa: E402

hil_test.engine()  # the selected agentrc: a missing one fails here, naming the remedy

CONSUMER = ".claude/skills/hil-contract/scripts/agentrc_pin.py"
CONFIG = "test/hil/agentrc.json"
CLEAN_ENV = {
    k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k not in ("AGENTRC_DIR", "CI", "GITHUB_ACTIONS")
}


class Config(unittest.TestCase):
    def test_the_repository_configuration(self):
        data = agentrc_pin.config()
        self.assertEqual(data["url"], "https://github.com/hathach/agentrc.git")
        self.assertEqual(data["cache_namespace"], "arduino-esp32")
        self.assertEqual(data["extra_engines"], [])  # no hil_ci.py wrapper or shared report commenter here

    def test_features_are_the_ones_this_profile_uses(self):
        # core mode (check_build.PLATFORM) and the shared battery (hil_test.CORE_TESTS); no base image, no named build
        self.assertTrue(hil_test.BUILD.PLATFORM and hil_test.CORE_TESTS)
        self.assertFalse(any("base" in b for b in hil_test.BUILD.BOARDS.values()))
        self.assertTrue(all(isinstance(s, str) for v in hil_test.BUILD.HIL_SKETCHES.values() for s in v))
        self.assertEqual(agentrc_pin.config()["features"], ["core", "battery"])

    def test_staged_trees_carry_the_bootstrap_and_its_configuration(self):
        self.assertLessEqual({CONSUMER, CONFIG}, set(hil_test.BUILD.CONTRACT_FILES))


class Selected(unittest.TestCase):
    """The agentrc this checkout really selects: the installed one on a dev PC, the pin in CI."""

    def test_the_copy_is_the_selected_canonical(self):
        canonical = Path(agentrc_pin.identity()["root"]) / "skills/arduino/scripts/agentrc_pin.py"
        self.assertEqual((ROOT / CONSUMER).read_bytes(), canonical.read_bytes())

    def test_hil_test_binds_the_selected_identity(self):
        ident = agentrc_pin.identity()
        self.assertLessEqual(
            {*agentrc_pin.ENGINES, *agentrc_pin.FILES, agentrc_pin.SELF, "skills/hil/scripts/hil_remote_core.py"},
            set(ident["files"]),
        )
        self.assertEqual(ident["source"], "pin" if agentrc_pin.ci() else "installed")
        self.assertEqual(hil_test.BUILD.AGENTRC, ident)

    def test_a_staged_tree_loads_every_script_from_its_own_copy(self):
        # a fresh interpreter: the staged modules must never replace the engines the other tests load
        helper = agentrc_pin._selection()[0]
        ident = agentrc_pin.identity()
        code = """if True:
            import json, os, sys, sysconfig
            sys.path.insert(0, sys.argv[1])
            import agentrc_pin as pin
            before = set(sys.modules)
            ident = pin.identity()
            engines = [pin.load(e).__file__ for e in (*pin.ENGINES, *pin.config()['extra_engines'])]
            paths = {k: os.path.join(v, '') for k, v in sysconfig.get_paths().items()}
            lib = (paths['stdlib'], paths['platstdlib'])
            site = (paths['purelib'], paths['platlib'])  # may sit inside stdlib
            modules = sorted(f for n in set(sys.modules) - before
                             if (f := getattr(sys.modules[n], '__file__', None))
                             and (f.startswith(site) or not f.startswith(lib)))
            print(json.dumps({'source': ident['source'], 'commit': ident['commit'], 'files': ident['files'],
                              'sha256': ident['sha256'], 'engines': engines, 'modules': modules}))
        """
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d)
            for rel in (CONSUMER, CONFIG):
                (tree / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, tree / rel)
            helper.stage(ident, tree, name="agentrc")
            (tree / "manifest.json").write_text(
                json.dumps({"agentrc": {"commit": ident["commit"], "dirty": ident["dirty"]}}) + "\n"
            )
            p = subprocess.run(
                [sys.executable, "-I", "-B", "-c", code, str((tree / CONSUMER).parent)],
                capture_output=True,
                text=True,
                env={**CLEAN_ENV, "CI": "true", "AGENTRC_DIR": str(tree / "absent")},
            )
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            got = json.loads(p.stdout)
            self.assertEqual(
                (got["source"], got["commit"], got["files"], got["sha256"]),
                ("staged", ident["commit"], ident["files"], ident["sha256"]),
            )
            staged = (tree / "agentrc").resolve()
            for f in (*got["engines"], *got["modules"]):
                self.assertTrue(Path(f).resolve().is_relative_to(staged), f)


if __name__ == "__main__":
    unittest.main()
