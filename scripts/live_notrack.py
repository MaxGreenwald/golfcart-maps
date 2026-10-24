"""Run a Playwright test script against a site without polluting production analytics:
every browser context gets window.NO_TRACK=1 before any page script runs.

  URL=https://golfcartmap.com/map/ python3 scripts/live_notrack.py scripts/test_ui.py
"""
import runpy, sys
from playwright.sync_api._generated import Browser, BrowserContext

_nc = Browser.new_context


def new_context(self, *a, **k):
    c = _nc(self, *a, **k)
    c.add_init_script("window.NO_TRACK=1")
    return c


Browser.new_context = new_context
_np = Browser.new_page


def new_page(self, *a, **k):
    p = _np(self, *a, **k)
    p.context.add_init_script("window.NO_TRACK=1")
    return p


Browser.new_page = new_page
sys.argv = sys.argv[1:]
if not sys.argv:
    raise SystemExit("usage: live_notrack.py <script.py> [args...]")
runpy.run_path(sys.argv[0], run_name="__main__")
