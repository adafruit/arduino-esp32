#!/usr/bin/env python3
"""agentrc_pin.py, agentrc's canonical bootstrap: this core's test/hil/agentrc.json and the agentrc this checkout
really selects. agentrc's tests own the bootstrap's common behavior, and `agentrc_pin.py test` its conformance check
(the copy, the staged round trip, the closure); nothing here fetches or reaches a rig."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "hil-contract" / "scripts"))
import agentrc_pin  # noqa: E402
import hil_test  # noqa: E402

hil_test.engine()  # the selected agentrc: a missing one fails here, naming the remedy


class Config(unittest.TestCase):
    def test_the_repository_configuration(self):
        data = agentrc_pin.config()
        self.assertEqual(data["url"], "https://github.com/hathach/agentrc.git")
        self.assertEqual(data["cache_namespace"], "arduino-esp32")
        self.assertEqual(data["extra_engines"], [])  # no hil_ci.py wrapper or shared report commenter here

    def test_features_are_the_ones_this_profile_uses(self):
        # core mode (check_build.PLATFORM), the shared battery (hil_test.CORE_TESTS) and the hwcdc named build; no base
        # image
        self.assertTrue(hil_test.BUILD.PLATFORM and hil_test.CORE_TESTS)
        self.assertFalse(any("base" in b for b in hil_test.BUILD.BOARDS.values()))
        self.assertTrue(any(isinstance(s, dict) for v in hil_test.BUILD.HIL_SKETCHES.values() for s in v))
        self.assertEqual(agentrc_pin.config()["features"], ["core", "battery", "named"])


class Selected(unittest.TestCase):
    """The agentrc this checkout really selects: the installed one on a dev PC, the pin in CI."""

    def test_hil_test_binds_the_selected_identity(self):
        ident = agentrc_pin.identity()
        self.assertEqual(ident["source"], "pin" if agentrc_pin.ci() else "installed")
        self.assertEqual(hil_test.BUILD.AGENTRC, ident)


if __name__ == "__main__":
    unittest.main()
