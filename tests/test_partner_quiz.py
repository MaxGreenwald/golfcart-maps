"""Rules quiz end to end on the real partner Worker: the shop turns the quiz on and sees the
questions; a renter's map stays closed until every answer is right; the pass shows in the
shop's list with the code and time."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_dev_server import PartnerDev, node_ok, sign_in

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
SEED = {"slug": "beachmode", "name": "Beach Mode Rentals", "owner": "owner@example.com", "region_id": "gulfshores",
        "shop": {"color": "#14b8c4", "vehicle": "golf_cart", "rental": {"rules": "Drivers 16 and up. Seat belts on."}},
        "codes": [{"code": "CART7", "multi_use": True}]}


def shot(target, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        target.screenshot(path=os.path.join(SHOTS, name))


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class RulesQuiz(unittest.TestCase):
    def test_quiz_gates_the_map_and_records_the_pass(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            ap = b.new_page(viewport={"width": 1000, "height": 1200}, timezone_id="America/Los_Angeles")
            ap.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
            sign_in(ap, dev.url, "owner@example.com")
            ap.wait_for_selector("#quizOn")
            ap.wait_for_selector("#quizPreview li b")
            self.assertIn("25 mph", ap.inner_text("#quizPreview"))
            self.assertIn("Drivers 16 and up", ap.inner_text("#quizPreview"))
            ap.check("#quizOn")
            ap.wait_for_function("() => document.body.innerText.includes('Rules quiz on')")

            ctx = b.new_context(viewport={"width": 390, "height": 1400}, timezone_id="America/Los_Angeles")
            rp = ctx.new_page()
            rp.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
            rp.goto(dev.url + "/p/beachmode/go?code=CART7", wait_until="domcontentloaded")
            rp.wait_for_selector("#quizForm")
            self.assertEqual(rp.locator(".xcard, .yay").count(), 0, "map stays closed")
            shot(rp, "quiz-renter.png")
            # Wrong on purpose: pick the first option everywhere it is not the answer.
            for fs in rp.locator(".qz").all():
                fs.locator("input").last.check()
            rp.click("#quizSend")
            rp.wait_for_selector(".qz.bad")
            self.assertRegex(rp.inner_text("#quizMsg"), r"need(s)? another look")
            notice = rp.inner_text("#quizNotice")
            self.assertIn("reminder of the local cart rules, not legal advice", notice)
            self.assertIn("follow posted signs and the law", notice)
            self.assertNotIn("waiver", rp.inner_text("#quizForm").lower())
            shot(rp, "quiz-renter-wrong.png")
            # Pick the right answers by text, as a renter would.
            right = {"speed": "25 mph", "red": "Off limits for this cart", "signs": "The posted sign",
                     "shop": "I read the shop\u2019s rules and will follow them"}
            for fs in rp.locator(".qz").all():
                qid = fs.get_attribute("data-q")
                if qid in right:
                    fs.locator("label.qz-opt", has_text=right[qid]).locator("input").check()
                else:
                    self.fail("unexpected question " + qid)
            rp.click("#quizSend")
            rp.wait_for_selector(".yay", timeout=20000)
            self.assertIn("CART7", rp.inner_text(".yay"))
            # Same device, same day: no second quiz.
            rp.reload(wait_until="domcontentloaded")
            rp.wait_for_selector(".yay", timeout=20000)
            self.assertEqual(rp.locator("#quizForm").count(), 0)
            ctx.close()

            ap.reload()
            ap.wait_for_selector("#quizPasses code")
            self.assertIn("CART7", ap.inner_text("#quizPasses"))
            self.assertNotIn("\u2014", ap.inner_text("#quizCard"))
            self.assertIn("not legal advice", ap.inner_text("#quizNoticeAdmin"))
            shot(ap.locator("#quizCard"), "quiz-admin.png")
            b.close()


if __name__ == "__main__":
    unittest.main()
