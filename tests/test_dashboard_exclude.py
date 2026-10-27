"""Scorecard headline: filtered WAI, plus the unfiltered comparison once /stats sends it."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import dashboard as D


class ExcludeLine(unittest.TestCase):
    def test_old_worker_has_no_excluded_line(self):
        md = D.render({"weekly_active": 274, "weekly_active_route_users": 36, "days": 7, "totals": {"installs": 274}, "daily": []},
                      "production", "https://gcm-analytics.example/stats", "2026-10-25")
        self.assertIn("Weekly active installs: **274** (route users: 36)", md)
        self.assertNotIn("Unfiltered was", md)

    def test_filtered_worker_shows_what_was_removed(self):
        md = D.render({"weekly_active": 40, "weekly_active_route_users": 12,
                       "weekly_active_unfiltered": 274, "weekly_active_route_users_unfiltered": 36,
                       "days": 7, "totals": {}, "daily": []},
                      "production", "https://gcm-analytics.example/stats", "2026-10-25")
        self.assertIn("Weekly active installs: **40** (route users: 12)", md)
        self.assertIn("Excluded internal/test installs: 234 (route users: 24). Unfiltered was 274 / 36.", md)


if __name__ == "__main__":
    unittest.main()
