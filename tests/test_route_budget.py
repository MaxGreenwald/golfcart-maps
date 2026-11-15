"""Route search stays inside a time and state budget.

The node cases in tests/route_budget.mjs run the same router the map uses.
"""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RouteBudget(unittest.TestCase):
    def test_node_route_budget(self):
        script = os.path.join(ROOT, "tests", "route_budget.mjs")
        r = subprocess.run(["node", "--test", script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + "\n" + r.stderr)


if __name__ == "__main__":
    unittest.main()
