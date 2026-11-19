"""CI browser-test hook: don't let third-party assets hang Page.goto(load).

map.html loads Nunito from fonts.googleapis.com as a render-blocking stylesheet.
Playwright's default goto wait_until is "load", which waits for that stylesheet
(and any other document resources). When the font CSS hangs, tests fail with
TimeoutError: Page.goto: Timeout 30000ms exceeded before they reach the
window.ready checks. That flake hit every in-flight web-ci run on 2026-11-19,
including a rerun of master 8fb7a3d, while the same tests passed locally.

This module is imported automatically when PYTHONPATH includes this directory
(the browser job in .github/workflows/web-ci.yml sets that). It:

1. Defaults Page.goto to wait_until="domcontentloaded" unless the caller set one.
   Tests already wait for window.ready afterwards.
2. Stubs fonts.googleapis.com and fonts.gstatic.com so even an explicit
   wait_until="load" cannot block on Google Fonts.

It does not change the site, routing, or production assets.
"""
from __future__ import annotations

try:
    from playwright.sync_api import Browser, Page
except ImportError:
    Browser = None  # type: ignore
    Page = None  # type: ignore

EMPTY_CSS = b"/* ci stub: do not block load on Google Fonts */"


def stub_fonts(context):
    def fulfill_css(route):
        route.fulfill(status=200, content_type="text/css; charset=utf-8", body=EMPTY_CSS)

    def fulfill_font(route):
        route.fulfill(status=200, content_type="font/woff2", body=b"")

    context.route("https://fonts.googleapis.com/**", fulfill_css)
    context.route("https://fonts.gstatic.com/**", fulfill_font)


def install():
    if Page is None or getattr(Page.goto, "_gcm_harness", False):
        return
    orig_goto = Page.goto

    def goto(self, url, **kwargs):
        kwargs.setdefault("wait_until", "domcontentloaded")
        return orig_goto(self, url, **kwargs)

    goto._gcm_harness = True
    goto._gcm_orig = orig_goto
    Page.goto = goto

    orig_new_context = Browser.new_context

    def new_context(self, **kwargs):
        ctx = orig_new_context(self, **kwargs)
        stub_fonts(ctx)
        return ctx

    new_context._gcm_harness = True
    Browser.new_context = new_context

    orig_new_page = Browser.new_page

    def new_page(self, **kwargs):
        page = orig_new_page(self, **kwargs)
        stub_fonts(page.context)
        return page

    new_page._gcm_harness = True
    Browser.new_page = new_page


install()
