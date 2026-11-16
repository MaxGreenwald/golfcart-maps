#!/usr/bin/env python3
"""Check a production --max-ok ref against Max's deploy allowlist.

The allowlist is not in this repo. Another process owns it.
Default path: /workspace/gcm/approvals/deploy_refs.json
Override: GCM_DEPLOY_REFS

Shape (one object per approval; do not invent refs):

  {"refs":[{"ref":"<Max chat or card id>","source":"<where Max's own words are>","scope":"<what this approval covers>","one_time":true}]}

  ref       single token Max approved (chat or card id)
  source    where those words are (message id or other pointer)
  scope     what the approval covers
  one_time  true means the ref may ship one production deploy, then it is used

A ref that contains "relay" in any case (the pattern *relay*, which includes
gary-relay-*) is refused even when a row lists it.

one_time use is recorded only by `mark`, which deploy logging (--append-log)
and a finished worker deploy (--mark-used) call. `check` does not write.
A one_time ref is already used when either record cites it:

  - deploy_refs_used.json next to the allowlist: {"refs":["<ref>", ...]}
  - a $GCM_BOT_LOG line (default /workspace/gcm/bot-log.md) with the exact
    token max-ok=<ref> and PASS or FAIL

usage: scripts/check_deploy_ref.py check|mark --ref <ref>
Exit 0 when the ref may be used (check) or the mark is recorded (mark).
Exit 1 with "production deploy refused: ..." on stderr otherwise.
"""
import json
import os
import sys
import tempfile

DEFAULT_ALLOWLIST = "/workspace/gcm/approvals/deploy_refs.json"
DEFAULT_BOT_LOG = "/workspace/gcm/bot-log.md"
USED_NAME = "deploy_refs_used.json"


def fail(reason):
    print("production deploy refused: %s" % reason, file=sys.stderr)
    raise SystemExit(1)


def allowlist_path():
    return os.environ.get("GCM_DEPLOY_REFS") or DEFAULT_ALLOWLIST


def bot_log_path():
    return os.environ.get("GCM_BOT_LOG") or DEFAULT_BOT_LOG


def used_path(allow_path):
    directory = os.path.dirname(os.path.abspath(allow_path)) or "."
    return os.path.join(directory, USED_NAME)


def looks_relayed(ref):
    # *relay* covers gary-relay-* and any other relayed token.
    return "relay" in ref.casefold()


def load_allowlist(path):
    if not os.path.exists(path):
        fail("approval allowlist is missing: %s" % path)
    if not os.path.isfile(path):
        fail("approval allowlist is not a file: %s" % path)
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        fail("approval allowlist is unreadable: %s (%s)" % (path, exc.strerror or exc))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail("approval allowlist is invalid: %s (%s)" % (path, exc.msg))
    refs = data.get("refs") if isinstance(data, dict) else None
    if not isinstance(refs, list):
        fail(
            'approval allowlist is invalid: %s (want {"refs":[{"ref","source","scope","one_time"}]})'
            % path
        )
    rows = {}
    for index, row in enumerate(refs):
        if not isinstance(row, dict):
            fail("approval allowlist is invalid: %s (refs[%d] must be an object)" % (path, index))
        ref = require_text(row, "ref", index, path)
        if any(ch.isspace() for ch in ref) or ref.startswith("-") or len(ref) > 200:
            fail("approval allowlist is invalid: %s (refs[%d].ref must be one token)" % (path, index))
        require_text(row, "source", index, path)
        require_text(row, "scope", index, path)
        one_time = row.get("one_time")
        if not isinstance(one_time, bool):
            fail(
                "approval allowlist is invalid: %s (refs[%d].one_time must be true or false)"
                % (path, index)
            )
        if ref in rows:
            fail("approval allowlist is invalid: %s (duplicate ref %s)" % (path, json.dumps(ref)))
        rows[ref] = {"source": row["source"], "scope": row["scope"], "one_time": one_time}
    return rows


def require_text(row, key, index, path):
    value = row.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        fail(
            "approval allowlist is invalid: %s (refs[%d].%s must be a non-empty string)"
            % (path, index, key)
        )
    return value


def load_used(path):
    if not os.path.exists(path):
        return []
    if not os.path.isfile(path):
        fail("used-ref record is not a file: %s" % path)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        fail("used-ref record is unreadable: %s (%s)" % (path, exc.strerror or exc))
    except json.JSONDecodeError as exc:
        fail("used-ref record is invalid: %s (%s)" % (path, exc.msg))
    refs = data.get("refs") if isinstance(data, dict) else None
    if not isinstance(refs, list) or not all(isinstance(item, str) and item for item in refs):
        fail('used-ref record is invalid: %s (want {"refs":["<ref>", ...]})' % path)
    return refs


def log_cites(ref):
    path = bot_log_path()
    if not os.path.exists(path):
        return False
    if not os.path.isfile(path):
        fail("deploy log is not a file: %s" % path)
    token = "max-ok=" + ref
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as exc:
        fail("deploy log is unreadable: %s (%s)" % (path, exc.strerror or exc))
    for line in lines:
        parts = line.split()
        if token in parts and ("PASS" in parts or "FAIL" in parts):
            return True
    return False


def already_used(ref, allow_path):
    if ref in load_used(used_path(allow_path)):
        return True
    return log_cites(ref)


def ensure_recordable(path):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    if os.path.exists(path):
        if not os.path.isfile(path) or not os.access(path, os.W_OK):
            fail("used-ref record is not writable: %s" % path)
        return
    if not os.path.isdir(directory) or not os.access(directory, os.W_OK):
        fail("used-ref record directory is not writable: %s" % directory)


def save_used(path, refs):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp = tempfile.mkstemp(prefix="deploy_refs_used.", suffix=".tmp", dir=directory)
    except OSError as exc:
        fail("used-ref record directory is not writable: %s (%s)" % (directory, exc.strerror or exc))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"refs": refs}, handle)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        fail("used-ref record is not writable: %s (%s)" % (path, exc.strerror or exc))


def record(path, ref):
    refs = load_used(path)
    if ref in refs:
        return
    refs.append(ref)
    save_used(path, refs)


def run(cmd, ref):
    if looks_relayed(ref):
        fail(
            "--max-ok ref %s looks relayed (matches *relay* or gary-relay-*); "
            "a relayed ref is not Max's own approval"
            % json.dumps(ref)
        )
    path = allowlist_path()
    rows = load_allowlist(path)
    row = rows.get(ref)
    if row is None:
        fail("--max-ok ref %s is not in the approval allowlist (%s)" % (json.dumps(ref), path))
    used = used_path(path)
    if cmd == "check":
        # check never writes. A dry run can call it twice and still pass.
        if row["one_time"] and already_used(ref, path):
            fail("--max-ok ref %s is one_time and was already used" % json.dumps(ref))
        if row["one_time"]:
            ensure_recordable(used)
        return
    if cmd == "mark":
        # Idempotent. Safe after the deploy log line is written: a log citation
        # makes the next check fail, and a second mark does not add a duplicate.
        if row["one_time"]:
            record(used, ref)
        return
    fail("unknown allowlist command")


def main(argv):
    if len(argv) != 4 or argv[1] not in ("check", "mark") or argv[2] != "--ref":
        print("usage: scripts/check_deploy_ref.py check|mark --ref <ref>", file=sys.stderr)
        return 2
    run(argv[1], argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
