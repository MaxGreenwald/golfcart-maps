#!/usr/bin/env python3
"""Guards for the iOS (Capacitor) build. Run by .github/workflows/ios-testflight.yml after it merges origin/master.

1. In sync: HEAD must contain origin/master (so the app can never ship a stale web app again; build 7 was 42 commits behind).
2. App-only overrides must be present in public/ (they are what makes the web app work inside the native shell):
   - no service worker in the native app (index.html unregisters it when Capacitor.isNativePlatform())
   - paywall API calls go to absolute https://golfcartmap.com in native (pay.js)
   - privacy link is absolute https://golfcartmap.com/privacy (index.html)
   - carplay.js exists and is loaded; app.js exposes window._lastDetail (used by carplay.js)
   - livedata.js loads in the native shell and reads region JSON from https://golfcartmap.com (data only)
3. The app bundles the built web app: capacitor webDir is dist/ (public/ + stamped sw.js from scripts/build_web.py),
   and every workflow runs build_web.py before `cap sync` (checked only where those files exist, i.e. on ios-release).
4. Divergence budget: public/, functions/, lib/ may differ from origin/master only in the allowlisted files below.
   Since branch ios-unify the overrides live in master itself, so the list is empty: ios-release = master's web app.
Usage: check_native_overrides.py [--ref origin/master] [--no-git]"""
import glob, json, os, re, subprocess, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ALLOW = set()   # overrides now live in master (runtime-guarded by Capacitor.isNativePlatform()); ios-release must not diverge
def rd(p):
    f = os.path.join(ROOT, p)
    return open(f, encoding="utf-8").read() if os.path.exists(f) else ""
WORKFLOWS = [os.path.relpath(f, ROOT) for f in glob.glob(os.path.join(ROOT, ".github/workflows/*.yml"))]
def git(*a): return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)
CHECKS = [
    ("native app unregisters the service worker", lambda: re.search(r"isNativePlatform\(\)\)\{navigator\.serviceWorker\.getRegistrations\(\)\.then\(rs=>rs\.forEach\(r=>r\.unregister\(\)\)\)", rd("public/index.html"))),
    ("service worker is NOT registered in native (register only in the else branch)", lambda: re.search(r"unregister\(\)\)\)[^<]*\}\s*else\s+navigator\.serviceWorker\.register\(", rd("public/index.html")) and rd("public/index.html").count("serviceWorker.register(") == 1),
    ("paywall API uses absolute https://golfcartmap.com in native", lambda: re.search(r"isNativePlatform\(\)\?'https://golfcartmap\.com':''\)\+'/api/'", rd("public/pay.js"))),
    ("privacy link is absolute", lambda: "https://golfcartmap.com/privacy" in rd("public/index.html")),
    ("carplay.js exists and defines GCMCarPlay", lambda: os.path.exists(os.path.join(ROOT, "public/carplay.js")) and "window.GCMCarPlay" in rd("public/carplay.js")),
    ("carplay.js is loaded after app.js", lambda: re.search(r'src="app\.js"></script>\s*<script src="carplay\.js">', rd("public/index.html"))),
    ("livedata.js loads after native.js and before app.js", lambda: re.search(r'src="native\.js"></script><script src="livedata\.js"></script>', rd("public/index.html")) and rd("public/index.html").index("livedata.js") < rd("public/index.html").index('src="app.js"')),
    ("livedata.js reads JSON only from https://golfcartmap.com in the native app", lambda: "https://golfcartmap.com" in rd("public/livedata.js") and "GCM_NATIVE" in rd("public/livedata.js") and "SCHEMA" in rd("public/livedata.js") and "eval(" not in rd("public/livedata.js") and "new Function" not in rd("public/livedata.js")),
    ("region JSON publishes a schema and allows the native WebView to read it", lambda: re.search(r'"schema"\s*:\s*\d+', rd("public/data/schema.json")) and "/data/*" in rd("public/_headers") and "Access-Control-Allow-Origin: *" in rd("public/_headers")),
    ("app.js exposes window._lastDetail", lambda: "window._lastDetail=" in rd("public/app.js")),
    ("capacitor webDir is dist (built from public/, never a committed copy)", lambda: not rd("capacitor.config.json") or json.loads(rd("capacitor.config.json")).get("webDir") == "dist"),
    ("every workflow builds dist/ before cap sync", lambda: all(
        all("build_web.py" in step for step in re.findall(r"^.*cap sync.*$", rd(w), re.M))
        for w in WORKFLOWS)),
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
