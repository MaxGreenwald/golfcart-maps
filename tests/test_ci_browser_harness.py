"""The CI sitecustomize hook defaults goto to domcontentloaded and stubs Google Fonts."""
import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "ci_harness" / "sitecustomize.py"
WORKFLOW = ROOT / ".github" / "workflows" / "web-ci.yml"


class CiBrowserHarness(unittest.TestCase):
    def test_workflow_puts_the_harness_on_pythonpath(self):
        text = WORKFLOW.read_text()
        self.assertIn("scripts/ci_harness", text)
        self.assertIn("PYTHONPATH", text)

    def test_hook_file_exists_and_mentions_fonts(self):
        text = HOOK.read_text()
        self.assertIn("domcontentloaded", text)
        self.assertIn("go_back", text)
        self.assertIn("fonts.googleapis.com", text)
        self.assertIn("fonts.gstatic.com", text)

    def test_hook_defaults_goto_wait_until(self):
        try:
            from playwright.sync_api import Page
        except ImportError:
            self.skipTest("playwright not installed")
        spec = importlib.util.spec_from_file_location("gcm_ci_sitecustomize", HOOK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(getattr(Page.goto, "_gcm_harness", False))
        self.assertTrue(getattr(Page.go_back, "_gcm_harness", False))
        self.assertTrue(getattr(Page.go_forward, "_gcm_harness", False))
        self.assertTrue(getattr(Page.reload, "_gcm_harness", False))


if __name__ == "__main__":
    unittest.main()
