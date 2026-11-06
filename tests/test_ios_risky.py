"""Risky mode in the iPhone shell was hidden for App Store review (Oct 18 2026).
It is restored and starts on. The website still starts on Legal only.
CarPlay uses the phone chip so both sides share one choice (AGENTS.md rule 35)."""
import os, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def rd(p):
    return (ROOT / p).read_text(encoding="utf-8")
class IosRisky(unittest.TestCase):
    def test_review_hide_is_gone(self):
        html, app, cp = rd("public/index.html"), rd("public/app.js"), rd("public/carplay.js")
        self.assertNotIn(".ios-app #cRisk", html)
        self.assertNotIn(".ios-app #whatRisky", html)
        self.assertNotIn(".ios-app .risky-only", html)
        self.assertIn(".ios-app #tip,.ios-app #cChg,.ios-app #cityBeta{display:none!important}", html)
        self.assertNotIn("if(window.GCM_IOS)v=false", app)
        self.assertNotIn("allowRisky&&!window.GCM_IOS", cp)
        self.assertIn("Try <b>⚠️ Risky</b>", app)
    def test_iphone_defaults_on_and_carplay_uses_the_chip(self):
        app, cp, swift = rd("public/app.js"), rd("public/carplay.js"), rd("ios/App/App/CarPlaySceneDelegate.swift")
        self.assertIn("localStorage.getItem('gcm-risky')", app)
        self.assertIn("setRisky(s!=='0')", app)
        self.assertIn("let useRisky=!!allowRisky;", cp)
        self.assertIn("if(window.GCM_IOS){const chip=document.getElementById('cRisk');useRisky=!!(chip&&chip.classList.contains('on'))}", cp)
        self.assertNotIn("plan(f,t,m,false", swift)
        self.assertIn("plan(f,t,m,true,null,d)", swift)
        self.assertIn("plan(f,t,m,true,h,d)", swift)
if __name__ == "__main__":
    unittest.main()
