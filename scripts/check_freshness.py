#!/usr/bin/env python3
"""Fail when a recurring Engineer check artifact is missing or too old.

ops/expected_runs.json lists each job, its artifact path pattern,
max_age_hours, and owner. Paths are relative to --base-dir (or the
GCM_FRESHNESS_BASE env, default /workspace/gcm) so tests can point at
fixtures. Dates come from a YYYY-MM-DD token in the filename when the
pattern is dated; from a matching log line when line_pattern is set;
otherwise from the file mtime.

Usage:
  python3 scripts/check_freshness.py
  python3 scripts/check_freshness.py --base-dir /workspace/gcm
  python3 scripts/check_freshness.py --config ops/expected_runs.json --base-dir DIR --now 2026-11-22T12:00:00Z
Exit 0 and print FRESHNESS PASS when every job is fresh.
Exit 1 and print 'STALE <job> last=<date or none>' for each stale job.
Exit 2 on usage errors.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "ops" / "expected_runs.json"
DEFAULT_BASE = Path("/workspace/gcm")
DATE_TOKEN = "YYYY-MM-DD"
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# bot-log lines look like: 2026-11-20 10:25 PT | Emma | analytics limit-trip log | ...
LOG_TIME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?:\s+(?P<time>\d{1,2}:\d{2})(?:\s+(?P<tz>[A-Za-z_/+0-9-]+))?)?"
)
PT_ZONE = ZoneInfo("America/Los_Angeles")


def parse_now(value):
    """Parse an ISO timestamp or YYYY-MM-DD as UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("invalid --now value %r" % (value,)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def default_now():
    env = os.environ.get("GCM_FRESHNESS_NOW")
    if env:
        return parse_now(env)
    return datetime.now(timezone.utc)


def default_base():
    env = os.environ.get("GCM_FRESHNESS_BASE")
    if env:
        return Path(env)
    return DEFAULT_BASE


def load_jobs(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("jobs", raw.get("runs"))
    if not isinstance(raw, list):
        raise ValueError("%s must be a JSON list of jobs" % (path,))
    jobs = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("job %d is not an object" % i)
        job = item.get("job")
        artifact = item.get("artifact")
        max_age = item.get("max_age_hours")
        if not job or not artifact:
            raise ValueError("job %d needs job and artifact" % i)
        if max_age is None:
            raise ValueError("job %s needs max_age_hours" % job)
        jobs.append(
            {
                "job": str(job),
                "artifact": str(artifact),
                "max_age_hours": float(max_age),
                "owner": item.get("owner") or "",
                "line_pattern": item.get("line_pattern") or "",
            }
        )
    return jobs


def resolve(base_dir, artifact):
    path = Path(artifact)
    if path.is_absolute():
        return path
    return Path(base_dir) / path


def filename_date(path):
    """Return midnight UTC for the last YYYY-MM-DD in a filename, or None."""
    match = None
    for match in DATE_RE.finditer(path.name):
        pass
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)


def glob_dated(base_dir, pattern):
    """Return (path, date) pairs for files matching a dated artifact pattern."""
    glob_pat = pattern.replace(DATE_TOKEN, "*")
    path = resolve(base_dir, glob_pat)
    if path.is_absolute() and not path.is_relative_to(base_dir):
        matches = sorted(Path("/").glob(str(path).lstrip("/")))
    else:
        rel = path
        try:
            rel = path.relative_to(base_dir)
        except ValueError:
            rel = Path(glob_pat)
        matches = sorted(Path(base_dir).glob(str(rel)))
    found = []
    for item in matches:
        if not item.is_file():
            continue
        when = filename_date(item)
        if when is not None:
            found.append((item, when))
    return found


def parse_log_time(line):
    """Parse a leading bot-log timestamp into a timezone-aware datetime."""
    match = LOG_TIME_RE.match(line.strip())
    if not match:
        return None
    day = datetime.strptime(match.group("date"), "%Y-%m-%d")
    clock = match.group("time")
    zone_name = match.group("tz")
    if clock:
        hour, minute = clock.split(":")
        day = day.replace(hour=int(hour), minute=int(minute))
    if zone_name in ("PT", "PST", "PDT"):
        return day.replace(tzinfo=PT_ZONE).astimezone(timezone.utc)
    if zone_name in ("UTC", "Z", "GMT"):
        return day.replace(tzinfo=timezone.utc)
    return day.replace(tzinfo=timezone.utc)


def last_from_log(path, line_pattern):
    """Latest timestamp on a line that contains line_pattern, or None."""
    if not path.is_file():
        return None
    latest = None
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line_pattern not in line:
            continue
        when = parse_log_time(line)
        if when is not None and (latest is None or when > latest):
            latest = when
    return latest


def last_from_mtime(path):
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def last_seen(base_dir, job):
    """Return (datetime or None, display date or 'none') for a job."""
    pattern = job["artifact"]
    if job["line_pattern"]:
        when = last_from_log(resolve(base_dir, pattern), job["line_pattern"])
    elif DATE_TOKEN in pattern or "*" in pattern:
        dated = glob_dated(base_dir, pattern)
        if not dated:
            when = None
        else:
            when = max(item[1] for item in dated)
    else:
        path = resolve(base_dir, pattern)
        when = filename_date(path) if path.is_file() else None
        if when is None:
            when = last_from_mtime(path)
    if when is None:
        return None, "none"
    return when, when.date().isoformat()


def is_stale(when, now, max_age_hours):
    if when is None:
        return True
    age = now - when
    return age > timedelta(hours=max_age_hours)


def check(jobs, base_dir, now):
    stale = []
    for job in jobs:
        when, label = last_seen(base_dir, job)
        if is_stale(when, now, job["max_age_hours"]):
            stale.append("STALE %s last=%s" % (job["job"], label))
    return stale


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fail when a recurring Engineer check artifact is stale"
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="expected_runs.json (default: ops/expected_runs.json in this repo)",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="root for relative artifact paths (env GCM_FRESHNESS_BASE, "
        "default /workspace/gcm)",
    )
    parser.add_argument(
        "--now",
        default=None,
        help="evaluate as of this UTC timestamp (env GCM_FRESHNESS_NOW)",
    )
    args = parser.parse_args(argv)

    try:
        now = parse_now(args.now) if args.now else default_now()
        base_dir = Path(args.base_dir) if args.base_dir else default_base()
        jobs = load_jobs(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("check_freshness: %s" % exc, file=sys.stderr)
        return 2

    stale = check(jobs, base_dir, now)
    if stale:
        print("\n".join(stale))
        return 1
    print("FRESHNESS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
