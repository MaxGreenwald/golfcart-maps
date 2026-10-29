"""75 ft faster-road stretches are legal; longer stretches and explicit bans stay risky.

Node cases live in tests/short_legal.mjs so they run the same router the map uses.
"""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ShortLegal(unittest.TestCase):
    def test_node_short_legal(self):
        script = os.path.join(ROOT, "tests", "short_legal.mjs")
        r = subprocess.run(["node", "--test", script], capture_output=True, text=True, timeout=90)
        self.assertEqual(r.returncode, 0, r.stdout + "\n" + r.stderr)


if __name__ == "__main__":
    unittest.main()
