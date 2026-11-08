"""Scorecard headline: filtered WAI only (no Unfiltered caveat)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import dashboard as D


class ExcludeLine(unittest.TestCase):
    def test_headline_is_filtered_without_unfiltered_caveat(self):
        md = D.render({"weekly_active": 40, "weekly_active_route_users": 12,
                       "weekly_active_unfiltered": 274, "weekly_active_route_users_unfiltered": 36,
                       "days": 7, "totals": {}, "daily": []},
                      "production", "https://gcm-analytics.example/stats", "2026-10-25")
        self.assertIn("Weekly active installs: **40** (route users: 12)", md)
        self.assertNotIn("Unfiltered", md)
        self.assertNotIn("unfiltered", md)
        self.assertNotIn("Excluded internal/test installs", md)

    def test_old_worker_still_renders(self):
        md = D.render({"weekly_active": 274, "weekly_active_route_users": 36, "days": 7, "totals": {"installs": 274}, "daily": []},
                      "production", "https://gcm-analytics.example/stats", "2026-10-25")
        self.assertIn("Weekly active installs: **274** (route users: 36)", md)
        self.assertNotIn("Unfiltered", md)


if __name__ == "__main__":
    unittest.main()
