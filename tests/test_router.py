"""Shared router: experience legs follow roads. Node cases run from unittest so CI picks them up."""
import os, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RouterLeg(unittest.TestCase):
    def test_node_router_legs(self):
        script = os.path.join(ROOT, "tests", "router_leg.mjs")
        r = subprocess.run(["node", "--test", script], capture_output=True, text=True, timeout=90)
        self.assertEqual(r.returncode, 0, r.stdout + "\n" + r.stderr)


if __name__ == "__main__":
    unittest.main()
