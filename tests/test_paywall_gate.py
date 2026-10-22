"""Driver plan (StoreKit) paywall: what is and isn't gated. The core legal-roads map must NEVER be gated."""
import json, os, re, subprocess, unittest
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: open(os.path.join(R, p), encoding='utf-8').read()
IDS = {'com.matchimus.golfcartmaps.driver.monthly': ('1.00', 'P1M'), 'com.matchimus.golfcartmaps.driver.yearly': ('10.00', 'P1Y')}

class PaywallGate(unittest.TestCase):
    def test_behaviour_in_node(self):
        out = subprocess.run(['node', os.path.join(R, 'tests', 'paywall_gate.mjs')], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_storekit_config(self):
        sk = json.loads(rd('ios/App/App/GCMDriver.storekit'))
        self.assertEqual(len(sk['subscriptionGroups']), 1, 'one subscription group')
        subs = {s['productID']: (s['displayPrice'], s['recurringSubscriptionPeriod'], s['type']) for s in sk['subscriptionGroups'][0]['subscriptions']}
        self.assertEqual({k: v[:2] for k, v in subs.items()}, IDS)
        self.assertTrue(all(v[2] == 'RecurringSubscription' for v in subs.values()))

    def test_ids_match_everywhere(self):
        sw, js = rd('ios/App/App/GCMPurchases.swift'), rd('public/entitlements.js')
        for i in IDS:
            self.assertIn('"%s"' % i, sw); self.assertIn("'%s'" % i, js)
        self.assertIn('GCMPurchases.swift in Sources', rd('ios/App/App.xcodeproj/project.pbxproj'))
        self.assertIn('GCMBridgeViewController', rd('ios/App/App/Base.lproj/Main.storyboard'))

    def test_wording(self):
        js = rd('public/entitlements.js')
        text = ' '.join(re.findall(r'`[^`]*`', js, re.S))
        self.assertNotRegex(text.lower(), r'\bfree\b')
        self.assertIn('Restore purchases', js); self.assertIn('Terms of Use', js); self.assertIn('Privacy Policy', js)
        self.assertTrue(os.path.exists(os.path.join(R, 'public', 'privacy.html')))

    def test_loaded_and_cached(self):
        self.assertIn('<script src="entitlements.js"></script>', rd('public/index.html'))
        self.assertIn("'entitlements.js'", rd('public/sw.js'))

if __name__ == '__main__':
    unittest.main()
