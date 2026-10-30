#!/usr/bin/env python3
"""Exit 0 only when the diff from the live commit to HEAD just ADDS new regions.

Max, Oct 30 2026 (chat ref t390s2042): brand-new towns may ship to production
without a per-deploy --max-ok. Everything else still needs --max-ok.

Allowed:
  - public/data/regions.json: every live entry unchanged and in the same order;
    only new entries with new ids appended.
  - Added files under public/data/<id>/ where <id> is one of those new ids and
    public/data/<id>/ did not exist at the live commit.
Anything else (a modified, deleted or renamed file, a change to an existing
region, code, scripts, other data) fails.

usage: scripts/check_new_region_only.py <live-commit> [<head>=HEAD]
"""
import json
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REGIONS = "public/data/regions.json"


def git(*args):
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    return subprocess.run(["git", "-C", ROOT, *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def regions_at(ref):
    return json.loads(git("show", "%s:%s" % (ref, REGIONS)))


def check(live, head="HEAD"):
    problems = []
    rows = [l for l in git("diff", "--name-status", "--no-renames", live, head).splitlines() if l]
    if not rows:
        return ["no changes vs live commit %s" % live]
    old, new = regions_at(live), regions_at(head)
    old_ids = [r.get("id") for r in old]
    new_ids = []
    if new[:len(old)] != old:
        problems.append("%s: an existing region entry was changed, removed or reordered" % REGIONS)
    else:
        for r in new[len(old):]:
            rid = r.get("id")
            if not rid or rid in old_ids or rid in new_ids or "/" in rid:
                problems.append("%s: bad or duplicate new region id %r" % (REGIONS, rid))
            else:
                new_ids.append(rid)
    live_dirs = {l.split("/")[2] for l in git("ls-tree", "-r", "--name-only", live, "public/data/").splitlines()
                 if l.count("/") >= 3}
    for row in rows:
        status, path = row.split("\t", 1)
        if path == REGIONS and status == "M":
            continue
        parts = path.split("/")
        if (status == "A" and len(parts) >= 4 and parts[:2] == ["public", "data"]
                and parts[2] in new_ids and parts[2] not in live_dirs):
            continue
        problems.append("%s %s: not a new-region-only addition" % (status, path))
    if not new_ids:
        problems.append("no new region added to %s" % REGIONS)
    return problems


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        problems = check(*argv[1:3])
    except (subprocess.CalledProcessError, ValueError) as e:
        problems = ["could not read the diff: %s" % getattr(e, "stderr", e)]
    if problems:
        for p in problems:
            print("new-region check FAIL: %s" % p, file=sys.stderr)
        return 1
    print("new-region check PASS: only new regions added vs %s" % argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
