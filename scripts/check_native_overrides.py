#!/usr/bin/env python3
"""Guards for the iOS (Capacitor) build. Run by .github/workflows/ios-testflight.yml after it merges origin/master.

1. In sync: HEAD must contain origin/master (so the app can never ship a stale web app again; build 7 was 42 commits behind).
2. App-only overrides must be present in public/ (they are what makes the web app work inside the native shell):
   - no service worker in the native app (index.html unregisters it when Capacitor.isNativePlatform())
   - paywall API calls go to absolute https://golfcartmap.com in native (pay.js)
   - privacy link is absolute https://golfcartmap.com/privacy (index.html)
   - carplay.js exists and is loaded; app.js exposes window._lastDetail (used by carplay.js)
3. Divergence budget: public/, functions/, lib/ may differ from origin/master only in the allowlisted files below.
   Once the overrides live in master itself (branch ios-unify), this list should shrink to nothing.
Usage: check_native_overrides.py [--ref origin/master] [--no-git]"""
import os, re, subprocess, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ALLOW = {"public/app.js", "public/index.html", "public/pay.js", "public/sw.js", "public/carplay.js"}
def rd(p):
    f = os.path.join(ROOT, p)
    return open(f, encoding="utf-8").read() if os.path.exists(f) else ""
def git(*a): return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)
CHECKS = [
    ("native app unregisters the service worker", lambda: re.search(r"isNativePlatform\(\)\)\{navigator\.serviceWorker\.getRegistrations\(\)\.then\(rs=>rs\.forEach\(r=>r\.unregister\(\)\)\)", rd("public/index.html"))),
    ("service worker is NOT registered in native (register only in the else branch)", lambda: re.search(r"unregister\(\)\)\)[^<]*\}\s*else\s+navigator\.serviceWorker\.register\(", rd("public/index.html")) and rd("public/index.html").count("serviceWorker.register(") == 1),
    ("paywall API uses absolute https://golfcartmap.com in native", lambda: re.search(r"isNativePlatform\(\)\?'https://golfcartmap\.com':''\)\+'/api/'", rd("public/pay.js"))),
    ("privacy link is absolute", lambda: "https://golfcartmap.com/privacy" in rd("public/index.html")),
    ("carplay.js exists and defines GCMCarPlay", lambda: os.path.exists(os.path.join(ROOT, "public/carplay.js")) and "window.GCMCarPlay" in rd("public/carplay.js")),
    ("carplay.js is loaded after app.js", lambda: re.search(r'src="app\.js"></script>\s*<script src="carplay\.js">', rd("public/index.html"))),
    ("app.js exposes window._lastDetail", lambda: "window._lastDetail=" in rd("public/app.js")),
]
def main(a):
    ref = a[a.index("--ref") + 1] if "--ref" in a else "origin/master"; bad = 0
    for name, f in CHECKS:
        ok = bool(f()); bad += not ok; print("PASS" if ok else "FAIL", name)
    if "--no-git" not in a:
        r = git("merge-base", "--is-ancestor", ref, "HEAD")
        if r.returncode: bad += 1; print("FAIL HEAD does not contain", ref, "- run: git merge", ref, "(behind by", git("rev-list", "--count", "HEAD.." + ref).stdout.strip(), "commits)")
        else: print("PASS HEAD contains", ref)
        diff = [x for x in git("diff", "--name-only", ref, "HEAD", "--", "public", "functions", "lib").stdout.split() if x]
        extra = [x for x in diff if x not in ALLOW]
        if extra: bad += 1; print("FAIL app differs from", ref, "outside the override allowlist:", extra)
        else: print("PASS divergence limited to overrides:", diff or "none")
    print("RESULT", "ALL PASS" if not bad else f"{bad} FAIL"); return 1 if bad else 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
