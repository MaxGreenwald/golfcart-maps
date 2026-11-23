#!/usr/bin/env python3
"""Exit 0 only if Playwright can launch headless Chromium on this machine.

scripts/deploy_web.sh production runs this after the prod gate and before the build or any
wrangler call, because the post-upload scripts/verify_live needs Chromium. On Nov 22 2026
(t596u) the upload finished, then verify_live failed 0/12 only because ~/.cache/ms-playwright
was missing, which left a FAIL line for a live deploy. Checking the package import is not
enough: the browser binary must exist and start, so this launches it and opens a blank page.

Run: python3 scripts/check_playwright_chromium.py
"""
import sys

FIX = "run: python3 -m playwright install chromium"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # package missing or broken
        print("chromium preflight FAIL: Python playwright package not importable (%s); "
              "run: pip install playwright && python3 -m playwright install chromium" % e.__class__.__name__,
              file=sys.stderr)
        return 1
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                browser.new_page().goto("about:blank")
            finally:
                browser.close()
    except Exception as e:
        first = (str(e).strip().splitlines() or [""])[0][:200]
        print("chromium preflight FAIL: Playwright Chromium is not installed or will not start (%s); %s"
              % (first, FIX), file=sys.stderr)
        return 1
    print("chromium preflight OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
