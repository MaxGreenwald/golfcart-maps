"""Safari rejects a Response that has followed redirects when a service worker
answers a navigation (error: "Response served by service worker has redirections").
Every online navigate respondWith path must run clean() before returning, and no
path may put a redirected Response into the cache."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = os.path.join(ROOT, "public", "sw.js")


class SwNavigateRedirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SW, encoding="utf-8") as f: cls.sw = f.read()

    def test_clean_helper_strips_redirected_flag(self):
        self.assertIn("const clean=r=>r.redirected?", self.sw)
        self.assertIn("new Response(b,{status:r.status,statusText:r.statusText,headers:r.headers})", self.sw)

    def test_main_navigate_returns_clean(self):
        # The /map (and other app) navigate handler must return clean(r), not r.
        self.assertIn("return clean(r)", self.sw)
        # Old buggy form that Safari rejects on flight wifi / captive redirects.
        self.assertNotRegex(
            self.sw,
            r"mode==='navigate'[^;]*respondWith\(fetch\(e\.request\)\.then\(r=>\{[^}]*return r\}\)",
        )

    def test_partner_navigate_runs_clean(self):
        self.assertIn("fetch(e.request,{cache:'no-store'}).then(clean).catch(", self.sw)

    def test_no_cache_put_of_redirected_response(self):
        # Online fetch handlers only put when !r.redirected (install goes through clean()).
        self.assertIn("if(r.ok&&app&&!r.redirected)", self.sw)  # map shell
        self.assertIn("if(r.ok&&!r.redirected){const c=r.clone();caches.open(C).then(x=>x.put(e.request.url,c))}", self.sw)
        self.assertIn("if(r.ok&&!r.redirected){const c=r.clone();caches.open(C).then(x=>x.put(e.request,c))}", self.sw)
        # No bare if(r.ok){...put without the redirected check on the online paths
        self.assertNotRegex(self.sw, r"\.then\(r=>\{if\(r\.ok\)\{const c=r\.clone\(\);caches\.open")
        self.assertGreaterEqual(self.sw.count("if(r.ok&&!r.redirected)"), 2)

    def test_install_still_cleans_before_put(self):
        self.assertIn("Promise.resolve(clean(r)).then(x=>c.put(u,x))", self.sw)


if __name__ == "__main__":
    unittest.main()
