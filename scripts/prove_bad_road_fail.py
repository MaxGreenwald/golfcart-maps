#!/usr/bin/env python3
"""Prove verify_live catches a road wrongly shown as legal.

Builds dist/, injects a display-only plant into dist/app.js (GCMRule.cls still
returns Avoid; mkLine forces that segment to draw/popup as OK), serves locally,
runs scripts/verify_live --only test_road_labels, expects FAIL, then tears down.
Never touches production.

Usage: python3 scripts/prove_bad_road_fail.py
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PT = ZoneInfo("America/Los_Angeles")
PORT = int(os.environ.get("PROVE_PORT", "8767"))
EVIDENCE = os.path.join(ROOT, "research/verify_live_evidence")


def main() -> int:
    os.makedirs(EVIDENCE, exist_ok=True)
    print("1) build dist/")
    subprocess.check_call([sys.executable, "scripts/build_web.py"], cwd=ROOT)

    app = os.path.join(ROOT, "dist", "app.js")
    src = open(app, encoding="utf-8").read()
    # Plant: after c0=cls(s), if this segment is Avoid, force display class 0 (green/OK).
    # Anchor on the real mkLine opener so we only rewrite the classification used for draw/popup.
    pat = re.compile(
        r"function mkLine\(s\)\{const c0=cls\(s\),c=s\[3\]==='c'\?2:unk\(s\)\?4:c0;"
    )
    if not pat.search(src):
        print("FAIL: mkLine pattern not found in dist/app.js; plant cannot be applied")
        return 2
    planted = pat.sub(
        "function mkLine(s){const c0=cls(s);"
        "const __plant=c0===3;"  # any Avoid segment wrongly shown legal
        "const c=s[3]==='c'?2:unk(s)?4:(__plant?0:c0);",
        src,
        count=1,
    )
    # Also force popup status text path: window._rseg.status uses c===3?'Avoid':...
    # With c forced to 0, status becomes "OK for …" while GCMRule.cls remains 3.
    if planted == src:
        print("FAIL: plant did not change dist/app.js")
        return 2
    open(app, "w", encoding="utf-8").write(planted)
    open(os.path.join(EVIDENCE, "plant_note.txt"), "w").write(
        "Plant: mkLine forces every GCMRule Avoid segment to draw/popup as OK (c=0). "
        "Module cls() unchanged. Local dist only; not deployed.\n"
    )
    print("2) planted display bug in dist/app.js (Avoid -> drawn as OK)")

    print(f"3) serve dist/ on :{PORT}")
    srv = subprocess.Popen(
        [sys.executable, "scripts/serve_dist.py", str(PORT), "dist"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        for _ in range(30):
            try:
                import urllib.request

                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1).read(64)
                break
            except Exception:
                time.sleep(0.3)
        else:
            print("FAIL: server did not start")
            return 2

        print("4) verify_live --only test_road_labels (expect FAIL)")
        env = os.environ.copy()
        env["URL"] = f"http://127.0.0.1:{PORT}/"
        r = subprocess.run(
            [sys.executable, "scripts/verify_live", "--only", "test_road_labels", "--url", env["URL"], "--shots", EVIDENCE],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
        log_path = os.path.join(EVIDENCE, "planted_bad_road_fail.txt")
        open(log_path, "w", encoding="utf-8").write(out)
        print(out)
        when = datetime.now(PT).strftime("%Y-%m-%d %H:%M PT")
        if r.returncode != 0 and "verify_live FAIL" in out and (
            "wrongly legal" in out or "Avoid label" in out or "FAIL test_road_labels" in out
        ):
            summary = (
                f"verify_live FAIL (planted bad road proof) time={when} "
                f"log=research/verify_live_evidence/planted_bad_road_fail.txt "
                f"(local dist plant; not production)"
            )
            open(os.path.join(EVIDENCE, "planted_summary.txt"), "w").write(summary + "\n")
            print("\nPROOF OK: verify_live FAILed on planted wrong-legal road")
            print(summary)
            return 0
        print("\nPROOF FAIL: verify_live did not FAIL as expected (returncode=%s)" % r.returncode)
        return 1
    finally:
        try:
            os.killpg(srv.pid, signal.SIGTERM)
        except Exception:
            srv.kill()
        # Rebuild clean dist so the plant does not linger for later work
        print("5) rebuild clean dist/ (remove plant)")
        subprocess.call([sys.executable, "scripts/build_web.py"], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
