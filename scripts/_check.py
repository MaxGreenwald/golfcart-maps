"""Shared PASS/FAIL accounting for scripts/test_*.py.

ck(name, cond, extra) prints one PASS or FAIL line and records the name on failure.
fail(name) records a failure that already happened (a page error, a caught exception).
finish() prints one RESULT line and exits 1 when any check failed, otherwise 0.

Run the scripts as files (`python scripts/test_vehicle.py` or via scripts/live_notrack.py).
Both put scripts/ on sys.path, so `from _check import ck, finish` works.
"""
from __future__ import annotations

import sys

fails = []
_MISSING = object()


def ck(name, cond, extra=_MISSING):
    """Print PASS or FAIL. Record name when cond is false. Return the condition."""
    ok = bool(cond)
    status = "PASS" if ok else "FAIL"
    if extra is _MISSING:
        print(f"{status} {name}")
    else:
        print(f"{status} {name}", extra)
    if not ok:
        fails.append(str(name))
    return ok


def fail(name, extra=_MISSING):
    """Record a failure that already happened."""
    return ck(name, False, extra)


def finish(*prefix):
    """Print RESULT and exit 1 if any ck/fail was recorded."""
    if fails:
        msg = f"{len(fails)} FAIL: {fails}"
    else:
        msg = "ALL PASS"
    if prefix:
        print("RESULT", *prefix, msg)
    else:
        print("RESULT", msg)
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(1 if fails else 0)
