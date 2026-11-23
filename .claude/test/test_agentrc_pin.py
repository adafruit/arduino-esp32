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

    def test_profile_api_and_features_are_the_selected_engines(self):
        engine = hil_test.BUILD.E
        self.assertEqual(agentrc_pin.config()["profile_api"], engine.PROFILE_API)
        self.assertLessEqual(set(agentrc_pin.config()["features"]), set(engine.PROFILE_FEATURES))

    def test_staged_trees_carry_the_bootstrap_and_its_configuration(self):
        self.assertLessEqual({CONSUMER, CONFIG}, set(hil_test.BUILD.CONTRACT_FILES))


class Selected(unittest.TestCase):
    """The agentrc this checkout really selects: the installed one on a dev PC, the pin in CI."""

    def test_the_copy_is_the_selected_canonical(self):
        canonical = Path(agentrc_pin.identity()["root"]) / agentrc_pin.SELF
        self.assertEqual((ROOT / CONSUMER).read_bytes(), canonical.read_bytes())

    def test_hil_test_binds_the_selected_identity(self):
        ident = agentrc_pin.identity()
        self.assertLessEqual(
            {*agentrc_pin.ENGINES, agentrc_pin.SELF, agentrc_pin.LOADER, "skills/hil/scripts/hil_remote_core.py"},
            set(ident["files"]),
        )
        self.assertEqual(ident["source"], "pin" if agentrc_pin.ci() else "installed")
        self.assertEqual(hil_test.BUILD.AGENTRC, ident)

    def test_the_real_engines_load_from_their_staged_closure_alone(self):
        helper, _, ident = agentrc_pin._selection()
        # a fresh interpreter in a staged copy, so its engines never replace the ones the other tests load
        code = """if True:
            import json, sys, sysconfig
            sys.path.insert(0, sys.argv[1])
            import agentrc_pin
            before = set(sys.modules)
            staged = agentrc_pin.identity()
            engines = [agentrc_pin.load(e).__file__ for e in agentrc_pin.ENGINES]
            lib = tuple(sysconfig.get_paths()[k] for k in ('stdlib', 'platstdlib', 'purelib', 'platlib'))
            new = sorted(f for n in set(sys.modules) - before
                         if (f := getattr(sys.modules[n], '__file__', None)) and not f.startswith(lib))
            print(json.dumps({'engines': engines, 'modules': new, 'source': staged['source'],
                              'commit': staged['commit'], 'files': staged['files'], 'sha256': staged['sha256']}))
        """
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d).resolve()
            for f in (CONSUMER, CONFIG):
                (tree / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / f, tree / f)
            helper.stage(ident, tree, name="agentrc")
            (tree / "manifest.json").write_text(
                json.dumps({"agentrc": {"commit": ident["commit"], "dirty": ident["dirty"]}})
            )
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            env.update(CI="true", AGENTRC_DIR=str(tree / "absent"))  # neither the pin nor an install is reached
            p = subprocess.run(
                [sys.executable, "-I", "-B", "-c", code, str((tree / CONSUMER).parent)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            got = json.loads(p.stdout)
            self.assertEqual(got["engines"], [str(tree / "agentrc" / e) for e in agentrc_pin.ENGINES])
            self.assertEqual(
                (got["source"], got["commit"], got["files"], got["sha256"]),
                ("staged", ident["commit"], ident["files"], ident["sha256"]),
            )
            for f in got["modules"]:
                self.assertTrue(Path(f).resolve().is_relative_to(tree / "agentrc"), f)


if __name__ == "__main__":
    unittest.main()
