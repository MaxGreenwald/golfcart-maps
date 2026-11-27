#!/usr/bin/env python3
"""Read-only Cloudflare free-tier headroom check for Golf Cart Maps.

Usage:
  python3 scripts/cf_headroom.py
  python3 scripts/cf_headroom.py --out /path/to/out.txt
  python3 scripts/cf_headroom.py --fixture tests/fixtures/cf_headroom_nov19_fail.json
  python3 scripts/cf_headroom.py --recovery
  python3 scripts/cf_headroom.py --recovery --day 2026-11-20
  python3 scripts/cf_headroom.py --recovery --fixture path.json

Reads today's usage (the current UTC day) from Cloudflare's GraphQL Analytics
API (read-only) and projects a full UTC day from hours elapsed. Compares each
counter to Workers Free plan limits from Cloudflare's official pricing pages
(cited on FREE_LIMITS). Prints one line per counter: worker, counter, used,
projected, limit, percent. WARN at 50 percent projected or higher, exit 1 at
80 percent projected or higher, and ends with a RESULT line.

An incident counts as fixed only with --recovery: every counter was under
50 percent of its limit for a complete UTC day, AND the gcm-analytics daily
volume for that day is near the 7-day baseline from before 19 Nov 2026.
"Near" means at least 75 percent of that baseline (a shortfall of at most
25 percent). A day above the baseline also counts as near. /stats daily and
daily.csv have no per-day events total, so the volume metric is daily
sessions from those endpoints (or an events field if a future response adds
one). The stats key is read the same way as scripts/dashboard.py
($GCM_STATS_KEY, else /home/box/.secrets/gcm_stats_key).

This script never deploys, never changes a Cloudflare plan or setting, never
creates a token, and never prints secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Official Workers Free plan limits. Daily counters reset at 00:00 UTC.
# Durable Objects (SQLite) rows read / written:
#   https://developers.cloudflare.com/durable-objects/platform/pricing/
# Workers KV keys read / written:
#   https://developers.cloudflare.com/kv/platform/pricing/
# Worker requests:
#   https://developers.cloudflare.com/workers/platform/pricing/
# These caps are account-wide on the Free plan. Per-worker lines show that
# worker's usage against the shared account cap. ACCOUNT lines sum every
# namespace or script the API returns, so preview or other Workers on the
# same account are not invisible.
FREE_LIMITS = {
    "do_rows_read": 5_000_000,
    "do_rows_written": 100_000,
    "kv_reads": 100_000,
    "kv_writes": 1_000,
    "worker_requests": 100_000,
}

# GraphQL datasets (official analytics docs):
#   durableObjectsPeriodicGroups.sum.rowsRead / rowsWritten
#     https://developers.cloudflare.com/durable-objects/observability/metrics-and-analytics/
#   kvOperationsAdaptiveGroups (sum.requests, dimensions.actionType)
#     https://developers.cloudflare.com/kv/observability/metrics-analytics/
#   workersInvocationsAdaptive.sum.requests
#     https://developers.cloudflare.com/analytics/graphql-api/

WARN_PCT = 50.0
FAIL_PCT = 80.0

# Recovery: 7 UTC days immediately before 19 Nov 2026.
BASELINE_FIRST = date(2026, 11, 12)
BASELINE_LAST = date(2026, 11, 18)
# "Near" the baseline: observed >= baseline * NEAR_MIN_FRACTION.
# That is a shortfall of at most 25 percent. Above baseline is also near.
NEAR_MIN_FRACTION = 0.75
NEAR_SHORTFALL_PCT = 25.0

ANALYTICS_STATS_URL = "https://gcm-analytics.maxgreenwald-assistant.workers.dev"
GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
CF_API = "https://api.cloudflare.com/client/v4"
DEFAULT_OUT_DIR = Path("/workspace/gcm/cf-headroom")
PT = ZoneInfo("America/Los_Angeles")

# Production Workers this check covers. gcm-analytics and gcm-partner names
# are also read from workers/*/wrangler.toml (top-level name, not preview).
# gcm-sdr-chat is a standalone Worker, not in this repo; the KV binding name
# is SDR_CHAT. The namespace id is resolved at runtime via the API, not stored
# in this repo.
SDR_WORKER = "gcm-sdr-chat"
SDR_KV_BINDING = "SDR_CHAT"
REPO_WORKERS = ("gcm-analytics", "gcm-partner")
ALL_WORKERS = ("gcm-analytics", "gcm-partner", "gcm-sdr-chat")

# Counters printed per worker (the free-tier counters we depend on).
WORKER_COUNTERS = {
    "gcm-analytics": ("do_rows_read", "do_rows_written", "worker_requests"),
    "gcm-partner": ("do_rows_read", "do_rows_written", "worker_requests"),
    "gcm-sdr-chat": ("kv_reads", "kv_writes", "worker_requests"),
}
ACCOUNT_COUNTERS = (
    "do_rows_read",
    "do_rows_written",
    "kv_reads",
    "kv_writes",
    "worker_requests",
)

# Permissions this read-only check may need. Named when the API refuses.
NEEDED_PERMISSIONS = (
    "Account Analytics: Read",
    "Account Settings: Read",
    "Workers Scripts: Read",
    "Workers KV Storage: Read",
)


def repo_root():
    return Path(__file__).resolve().parent.parent


def utc_now():
    return datetime.now(timezone.utc)


def parse_iso_utc(value):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_day_start(day):
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def hours_elapsed(now):
    """Hours from 00:00 UTC to now, on now's UTC day."""
    start = utc_day_start(now.date())
    return max((now - start).total_seconds() / 3600.0, 0.0)


def project_used(used, hours):
    """Project a full 24-hour UTC day from hours already elapsed."""
    if hours <= 0:
        return float(used)
    return float(used) * 24.0 / hours


def percent_of_limit(value, limit):
    if limit <= 0:
        return 0.0
    return 100.0 * float(value) / float(limit)


def classify(projected, limit):
    pct = percent_of_limit(projected, limit)
    if pct >= FAIL_PCT:
        return "FAIL", pct
    if pct >= WARN_PCT:
        return "WARN", pct
    return "OK", pct


def format_line(worker, counter, used, projected, limit, status, pct):
    return (
        f"{worker}  {counter}  used={int(round(used))}  "
        f"projected={int(round(projected))}  limit={int(limit)}  "
        f"{pct:.1f}%  {status}"
    )


def load_wrangler_production_names(root=None):
    """Top-level wrangler name values (production), not [env.preview]."""
    root = Path(root or repo_root())
    names = []
    workers_dir = root / "workers"
    if not workers_dir.is_dir():
        return names
    for path in sorted(workers_dir.glob("*/wrangler.toml")):
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        name = data.get("name")
        if name:
            names.append(str(name))
    return names


def load_targets(root=None):
    """Worker names from repo wrangler configs, plus the standalone SDR Worker."""
    names = load_wrangler_production_names(root)
    missing = [name for name in REPO_WORKERS if name not in names]
    if missing:
        raise RuntimeError(
            "wrangler.toml production names missing expected workers: "
            + ", ".join(missing)
            + " (found: "
            + (", ".join(names) if names else "none")
            + ")"
        )
    extra = [name for name in names if name not in REPO_WORKERS]
    if extra:
        # New production Workers in this repo should be added to WORKER_COUNTERS.
        names = list(REPO_WORKERS)
    return list(ALL_WORKERS)


def default_out_path(day):
    return DEFAULT_OUT_DIR / f"{day.isoformat()}.txt"


def load_fixture(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("fixture must be a JSON object")
    return data


def counters_from_fixture(data):
    rows = data.get("counters")
    if not isinstance(rows, list) or not rows:
        raise ValueError("fixture.counters must be a non-empty list")
    out = []
    for row in rows:
        out.append(
            {
                "worker": str(row["worker"]),
                "counter": str(row["counter"]),
                "used": float(row["used"]),
            }
        )
    return out


def evaluate_counters(rows, hours, complete_day=False):
    """Return (lines, statuses). complete_day compares used, not a projection."""
    lines = []
    statuses = []
    for row in rows:
        used = float(row["used"])
        limit = int(FREE_LIMITS[row["counter"]])
        projected = used if complete_day else project_used(used, hours)
        status, pct = classify(projected, limit)
        lines.append(
            format_line(
                row["worker"],
                row["counter"],
                used,
                projected,
                limit,
                status,
                pct,
            )
        )
        statuses.append(status)
    return lines, statuses


def result_line(statuses):
    fails = sum(1 for status in statuses if status == "FAIL")
    warns = sum(1 for status in statuses if status == "WARN")
    if fails:
        return f"RESULT {fails} FAIL", 1
    if warns:
        return f"RESULT {warns} WARN", 0
    return "RESULT ALL PASS", 0


def stats_key():
    """Same lookup as scripts/dashboard.py. Never print the value."""
    key = os.environ.get("GCM_STATS_KEY")
    if key:
        return key.strip()
    try:
        return Path("/home/box/.secrets/gcm_stats_key").read_text().strip()
    except OSError:
        raise RuntimeError(
            "no stats key: set GCM_STATS_KEY or create /home/box/.secrets/gcm_stats_key"
        ) from None


def cf_token():
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if token:
        return token.strip()
    raise RuntimeError("CLOUDFLARE_API_TOKEN is not set")


def redact_secrets(text, secrets):
    out = text or ""
    for secret in secrets:
        if secret:
            out = out.replace(secret, "[redacted]")
    return out


def http_json(url, token=None, payload=None, method=None, timeout=60):
    headers = {"user-agent": "gcm-cf-headroom", "accept": "application/json"}
    data = None
    if payload is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(payload).encode()
        method = method or "POST"
    if token:
        headers["authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace") if err.fp else ""
        raise ApiError(err.code, url, body, token) from None
    except urllib.error.URLError as err:
        raise ApiError(0, url, str(err.reason), token) from None
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise ApiError(status, url, body, token) from None
    return status, parsed


class ApiError(Exception):
    def __init__(self, status, url, body, token=None):
        self.status = status
        self.url = url.split("?")[0]
        self.body = redact_secrets(body, [token] if token else [])
        msg = f"HTTP {status} {self.url}: {self.body[:2000]}"
        super().__init__(msg)


def permission_report(exc):
    """Human-readable permission note plus the redacted API error."""
    text = str(exc)
    lower = text.lower()
    named = []
    # Only name a permission when the error text points at it.
    mapping = {
        "analytics": "Account Analytics: Read",
        "account settings": "Account Settings: Read",
        "workers scripts": "Workers Scripts: Read",
        "workers kv": "Workers KV Storage: Read",
        "kv storage": "Workers KV Storage: Read",
    }
    for needle, label in mapping.items():
        if needle in lower and label not in named:
            named.append(label)
    auth = any(
        word in lower
        for word in (
            "auth",
            "unauthorized",
            "forbidden",
            "permission",
            "not allowed",
            "access denied",
            "authentication error",
        )
    ) or (isinstance(exc, ApiError) and exc.status in (401, 403))
    lines = ["API error: " + text]
    if named:
        lines.append("Missing permission: " + ", ".join(named))
    elif auth:
        lines.append(
            "The token was refused. This read-only check needs: "
            + ", ".join(NEEDED_PERMISSIONS)
            + ". The GraphQL usage query specifically needs Account Analytics: Read. "
            "Do not create a new token from this script."
        )
    return "\n".join(lines)


def fetch_account_id(token):
    env_id = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if env_id:
        return env_id
    status, data = http_json(CF_API + "/accounts?per_page=50", token=token, method="GET")
    if not data.get("success", True) and data.get("errors"):
        raise ApiError(status, CF_API + "/accounts", json.dumps(data), token)
    rows = data.get("result") or []
    if not rows:
        raise RuntimeError("Cloudflare API returned no accounts for this token")
    if len(rows) == 1:
        return rows[0]["id"]
    # Prefer the account that hosts a known production Worker.
    for row in rows:
        aid = row.get("id")
        if not aid:
            continue
        try:
            _, scripts = http_json(
                f"{CF_API}/accounts/{aid}/workers/scripts", token=token, method="GET"
            )
        except ApiError:
            continue
        names = {item.get("id") for item in (scripts.get("result") or [])}
        if "gcm-analytics" in names:
            return aid
    raise RuntimeError(
        "multiple Cloudflare accounts on this token; set CLOUDFLARE_ACCOUNT_ID"
    )


def list_do_namespaces(token, account_id):
    url = f"{CF_API}/accounts/{account_id}/workers/durable_objects/namespaces"
    _, data = http_json(url, token=token, method="GET")
    if data.get("success") is False:
        raise ApiError(200, url, json.dumps(data), token)
    out = []
    for row in data.get("result") or []:
        out.append(
            {
                "id": row.get("id") or row.get("namespace_id"),
                "script": row.get("script") or row.get("script_name") or "",
                "class": row.get("class") or row.get("class_name") or "",
                "name": row.get("name") or "",
            }
        )
    return out


def list_kv_namespaces(token, account_id):
    url = f"{CF_API}/accounts/{account_id}/storage/kv/namespaces?per_page=100"
    _, data = http_json(url, token=token, method="GET")
    if data.get("success") is False:
        raise ApiError(200, url, json.dumps(data), token)
    return data.get("result") or []


def sdr_kv_namespace_id(token, account_id, kv_namespaces):
    """Resolve the SDR_CHAT namespace id from Worker bindings, then titles."""
    settings_urls = [
        f"{CF_API}/accounts/{account_id}/workers/scripts/{SDR_WORKER}/settings",
        f"{CF_API}/accounts/{account_id}/workers/services/{SDR_WORKER}/environments/production/bindings",
    ]
    for url in settings_urls:
        try:
            _, data = http_json(url, token=token, method="GET")
        except ApiError:
            continue
        result = data.get("result") or data
        bindings = []
        if isinstance(result, dict):
            bindings = result.get("bindings") or result.get("kv_namespaces") or []
        elif isinstance(result, list):
            bindings = result
        for bind in bindings:
            name = bind.get("name") or bind.get("binding")
            nstype = (bind.get("type") or "").lower()
            nid = bind.get("namespace_id") or bind.get("id")
            if name == SDR_KV_BINDING and nid:
                return nid
            if "kv" in nstype and nid:
                return nid
    # Fall back to a namespace title that names the SDR chat Worker.
    for row in kv_namespaces:
        title = (row.get("title") or "").lower()
        if "sdr" in title and "chat" in title:
            return row.get("id")
        if title in {"sdr_chat", "sdr-chat", "gcm-sdr-chat"}:
            return row.get("id")
    if len(kv_namespaces) == 1:
        return kv_namespaces[0].get("id")
    return None


HEADROOM_QUERY = """
query Headroom($accountTag: string!, $start: Time!, $end: Time!, $date: Date!) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      workersInvocationsAdaptive(
        limit: 10000
        filter: { datetime_geq: $start, datetime_lt: $end }
      ) {
        sum { requests }
        dimensions { scriptName }
      }
      durableObjectsPeriodicGroups(
        limit: 10000
        filter: { datetime_geq: $start, datetime_lt: $end }
      ) {
        sum { rowsRead rowsWritten }
        dimensions { namespaceId }
      }
      kvOperationsAdaptiveGroups(
        limit: 10000
        filter: { date: $date }
      ) {
        sum { requests }
        dimensions { actionType namespaceId }
      }
    }
  }
}
"""


def graphql(token, query, variables):
    status, data = http_json(
        GRAPHQL_URL, token=token, payload={"query": query, "variables": variables}
    )
    errors = data.get("errors") or []
    if errors:
        raise ApiError(status, GRAPHQL_URL, json.dumps(data), token)
    return data


def _sum_field(row, *keys):
    node = row.get("sum") or {}
    for key in keys:
        if node.get(key) is not None:
            return float(node[key])
    return 0.0


def usage_from_graphql(data, do_namespaces, sdr_kv_id):
    accounts = (((data.get("data") or {}).get("viewer") or {}).get("accounts")) or []
    account = accounts[0] if accounts else {}
    ns_script = {}
    for row in do_namespaces:
        if row.get("id"):
            ns_script[row["id"]] = row.get("script") or ""

    used = {}

    def add(worker, counter, amount):
        key = (worker, counter)
        used[key] = used.get(key, 0.0) + float(amount or 0)

    for row in account.get("workersInvocationsAdaptive") or []:
        script = ((row.get("dimensions") or {}).get("scriptName")) or ""
        add(script, "worker_requests", _sum_field(row, "requests"))
        add("ACCOUNT", "worker_requests", _sum_field(row, "requests"))

    for row in account.get("durableObjectsPeriodicGroups") or []:
        ns = ((row.get("dimensions") or {}).get("namespaceId")) or ""
        script = ns_script.get(ns, "")
        reads = _sum_field(row, "rowsRead", "rows_read")
        writes = _sum_field(row, "rowsWritten", "rows_written")
        if script:
            add(script, "do_rows_read", reads)
            add(script, "do_rows_written", writes)
        else:
            add("UNKNOWN_DO:" + (ns[:8] if ns else "none"), "do_rows_read", reads)
            add("UNKNOWN_DO:" + (ns[:8] if ns else "none"), "do_rows_written", writes)
        add("ACCOUNT", "do_rows_read", reads)
        add("ACCOUNT", "do_rows_written", writes)

    for row in account.get("kvOperationsAdaptiveGroups") or []:
        dims = row.get("dimensions") or {}
        action = (dims.get("actionType") or "").lower()
        ns = dims.get("namespaceId") or ""
        requests = _sum_field(row, "requests")
        if action == "read":
            counter = "kv_reads"
        elif action == "write":
            counter = "kv_writes"
        else:
            continue
        worker = "gcm-sdr-chat" if (sdr_kv_id and ns == sdr_kv_id) else ("KV:" + (ns[:8] if ns else "none"))
        if sdr_kv_id and ns == sdr_kv_id:
            add("gcm-sdr-chat", counter, requests)
        add("ACCOUNT", counter, requests)
        if not sdr_kv_id or ns != sdr_kv_id:
            # Keep non-SDR namespaces visible only in ACCOUNT, plus a named
            # line if we could not map the SDR namespace at all.
            if not sdr_kv_id:
                add(worker, counter, requests)

    return used


def rows_from_used(used, workers=ALL_WORKERS, include_account=True):
    rows = []
    for worker in workers:
        for counter in WORKER_COUNTERS[worker]:
            rows.append(
                {
                    "worker": worker,
                    "counter": counter,
                    "used": used.get((worker, counter), 0.0),
                }
            )
    if include_account:
        for counter in ACCOUNT_COUNTERS:
            rows.append(
                {
                    "worker": "ACCOUNT",
                    "counter": counter,
                    "used": used.get(("ACCOUNT", counter), 0.0),
                }
            )
    return rows


def fetch_live_usage(token, day, start, end):
    account_id = fetch_account_id(token)
    do_namespaces = []
    kv_namespaces = []
    sdr_kv_id = None
    notes = []
    try:
        do_namespaces = list_do_namespaces(token, account_id)
    except ApiError as err:
        notes.append("Durable Object namespace list failed: " + permission_report(err))
    try:
        kv_namespaces = list_kv_namespaces(token, account_id)
        sdr_kv_id = sdr_kv_namespace_id(token, account_id, kv_namespaces)
        if not sdr_kv_id:
            notes.append(
                "Could not resolve the gcm-sdr-chat KV namespace id; "
                "SDR lines may be zero while ACCOUNT kv_* still includes all namespaces."
            )
    except ApiError as err:
        notes.append("KV namespace list failed: " + permission_report(err))
    data = graphql(
        token,
        HEADROOM_QUERY,
        {
            "accountTag": account_id,
            "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date": day.isoformat(),
        },
    )
    used = usage_from_graphql(data, do_namespaces, sdr_kv_id)
    return used, notes


def fetch_stats(days=30, base=ANALYTICS_STATS_URL):
    key = stats_key()
    url = f"{base}/stats?days={days}"
    req = urllib.request.Request(
        url,
        headers={"x-stats-key": key, "user-agent": "gcm-cf-headroom"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace") if err.fp else ""
        raise ApiError(err.code, url, redact_secrets(body, [key]), None) from None


def daily_volume(row):
    """Per-day volume used for the recovery baseline comparison.

    /stats daily and daily.csv do not include a total events column. If a
    future response adds events, that field is preferred. Otherwise this
    uses sessions, the daily count those endpoints do expose.
    """
    if not row:
        return None, "missing"
    if row.get("events") is not None:
        return float(row["events"]), "events"
    if row.get("sessions") is not None:
        return float(row["sessions"]), "sessions"
    return None, "missing"


def stats_daily_map(stats):
    out = {}
    for row in stats.get("daily") or []:
        day = row.get("day")
        if day:
            out[str(day)] = row
    return out


def baseline_mean(daily_map, metric):
    days = []
    values = []
    cursor = BASELINE_FIRST
    while cursor <= BASELINE_LAST:
        key = cursor.isoformat()
        days.append(key)
        row = daily_map.get(key) or {}
        if metric == "events" and row.get("events") is not None:
            values.append(float(row["events"]))
        elif metric == "sessions":
            values.append(float(row.get("sessions") or 0))
        else:
            values.append(float(row.get(metric) or 0))
        cursor += timedelta(days=1)
    if len(values) != 7:
        raise RuntimeError("baseline window is not 7 days")
    return days, sum(values) / 7.0


def is_near_baseline(observed, baseline):
    """True when observed is at least 75 percent of the pre-Nov-19 mean."""
    if baseline <= 0:
        return observed >= 0
    return observed >= baseline * NEAR_MIN_FRACTION


def recovery_from_parts(day, counter_rows, daily_map):
    lines = []
    statuses = []
    # Headroom on a complete UTC day uses used, not a same-day projection.
    head_lines, head_statuses = evaluate_counters(
        counter_rows, hours=24.0, complete_day=True
    )
    under = all(
        percent_of_limit(row["used"], FREE_LIMITS[row["counter"]]) < WARN_PCT
        for row in counter_rows
    )
    lines.append(f"recovery_day: {day.isoformat()} (UTC, complete)")
    lines.append(
        "headroom_rule: every counter under 50% of its free-plan limit for the full UTC day"
    )
    lines.extend(head_lines)
    if under:
        lines.append("headroom: under 50% on all counters")
    else:
        lines.append("headroom: not under 50% on all counters")
        statuses.append("FAIL")
    # Any FAIL/WARN from evaluate_counters also counts.
    statuses.extend(head_statuses)

    row = daily_map.get(day.isoformat()) or {}
    observed, metric = daily_volume(row)
    base_days, base_mean = baseline_mean(
        daily_map, "events" if metric == "events" else "sessions"
    )
    lines.append(
        "volume_metric: "
        + metric
        + (
            " (/stats daily and daily.csv have no per-day events total; sessions is the daily volume those endpoints expose)"
            if metric == "sessions"
            else ""
        )
    )
    lines.append(
        "baseline: arithmetic mean of UTC days "
        + base_days[0]
        + " through "
        + base_days[-1]
        + " (7 days immediately before 19 Nov 2026)"
    )
    lines.append(
        f"near_definition: observed is near the baseline when it is at least "
        f"{NEAR_MIN_FRACTION * 100:.0f}% of the baseline mean "
        f"(a shortfall of at most {NEAR_SHORTFALL_PCT:.0f}%). "
        "A day above the baseline also counts as near."
    )
    if observed is None:
        lines.append("observed: missing")
        lines.append(f"baseline_mean: {base_mean:.4f}")
        lines.append("near: no (missing observed volume)")
        statuses.append("FAIL")
        near = False
    else:
        share = (100.0 * observed / base_mean) if base_mean else 0.0
        near = is_near_baseline(observed, base_mean)
        lines.append(f"observed: {int(round(observed))}")
        lines.append(f"baseline_mean: {base_mean:.4f}")
        lines.append(
            f"near: {'yes' if near else 'no'} ({share:.1f}% of baseline; need at least {NEAR_MIN_FRACTION * 100:.0f}%)"
        )
        if not near:
            statuses.append("FAIL")
    if under and near:
        lines.append("incident_fixed: yes")
    else:
        lines.append("incident_fixed: no")
        if "FAIL" not in statuses:
            statuses.append("FAIL")
    return lines, statuses


def write_output(text, path):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path), None
    except OSError as err:
        return None, f"could not write {path}: {err}"


def header_lines(kind, day, now, hours, complete_day, source):
    pt = now.astimezone(PT).strftime("%Y-%m-%d %H:%M PT")
    lines = [
        f"# Cloudflare free-tier headroom ({kind})",
        f"# UTC day: {day.isoformat()}",
        f"# as of: {now.strftime('%Y-%m-%dT%H:%M:%SZ')} ({pt})",
        f"# source: {source}",
    ]
    if complete_day:
        lines.append("# complete UTC day: used is compared to the limit (no same-day projection)")
    else:
        lines.append(f"# hours elapsed in this UTC day: {hours:.4f}")
        lines.append("# projected = used * 24 / hours elapsed")
    lines.append(
        "# Limits are account-wide on the Workers Free plan. Per-worker lines "
        "are that worker's usage against the shared cap. ACCOUNT sums every "
        "script or namespace the API returned."
    )
    lines.append(
        "# WARN at >=50% projected (or used, on a complete day). FAIL and exit 1 at >=80%."
    )
    return lines


def run_headroom(args):
    notes = []
    if args.fixture:
        data = load_fixture(args.fixture)
        now = parse_iso_utc(data["now"]) if data.get("now") else utc_now()
        if args.now:
            now = parse_iso_utc(args.now)
        day = now.date()
        hours = hours_elapsed(now)
        rows = counters_from_fixture(data)
        source = "fixture " + str(args.fixture)
    else:
        now = parse_iso_utc(args.now) if args.now else utc_now()
        day = now.date()
        hours = hours_elapsed(now)
        token = cf_token()
        start = utc_day_start(day)
        used, notes = fetch_live_usage(token, day, start, now)
        rows = rows_from_used(used)
        source = "Cloudflare GraphQL Analytics API (read-only)"
    lines, statuses = evaluate_counters(rows, hours, complete_day=False)
    header = header_lines("headroom", day, now, hours, False, source)
    result, code = result_line(statuses)
    body = "\n".join(header + notes + lines + [result]) + "\n"
    return body, code, day


def run_recovery(args):
    notes = []
    if args.fixture:
        data = load_fixture(args.fixture)
        rec = data.get("recovery") or data
        day = date.fromisoformat(str(rec.get("day") or args.day or data.get("day")))
        rows = counters_from_fixture(rec if rec.get("counters") else data)
        daily_map = rec.get("daily") or data.get("daily") or {}
        # Allow {day: {sessions, events}} or {day: number}.
        normalized = {}
        for key, val in daily_map.items():
            if isinstance(val, dict):
                normalized[str(key)] = val
            else:
                normalized[str(key)] = {"sessions": val}
        daily_map = normalized
        now = utc_day_start(day) + timedelta(days=1)
        source = "fixture " + str(args.fixture)
    else:
        if args.day:
            day = date.fromisoformat(args.day)
        else:
            day = (utc_now() - timedelta(days=1)).date()
        today = utc_now().date()
        if day >= today:
            raise RuntimeError(
                "recovery requires a complete UTC day; pass --day YYYY-MM-DD before today"
            )
        token = cf_token()
        start = utc_day_start(day)
        end = start + timedelta(days=1)
        used, notes = fetch_live_usage(token, day, start, end)
        rows = rows_from_used(used)
        # 30 days covers the pre-Nov-19 baseline and the recovery day.
        stats = fetch_stats(days=30)
        daily_map = stats_daily_map(stats)
        now = end
        source = "Cloudflare GraphQL Analytics API (read-only) plus gcm-analytics /stats"
    lines, statuses = recovery_from_parts(day, rows, daily_map)
    # Recovery itself is a yes/no gate: any FAIL means the incident is not fixed.
    # WARN on a complete-day counter still means it was not under 50 percent.
    header = header_lines("recovery", day, now, 24.0, True, source)
    result, code = result_line(statuses)
    # If headroom had only WARN (50-80%) the incident is still not fixed; force FAIL.
    if any(line.startswith("incident_fixed: no") for line in lines) and code == 0:
        result, code = "RESULT 1 FAIL", 1
    body = "\n".join(header + notes + lines + [result]) + "\n"
    return body, code, day


def build_parser():
    parser = argparse.ArgumentParser(description="Cloudflare free-tier headroom check (read-only)")
    parser.add_argument(
        "--fixture",
        metavar="JSON",
        help="skip the API and evaluate this fixture (for offline tests)",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help=f"write dated output (default {DEFAULT_OUT_DIR}/YYYY-MM-DD.txt)",
    )
    parser.add_argument(
        "--recovery",
        action="store_true",
        help="check whether an incident is fixed for a complete UTC day",
    )
    parser.add_argument(
        "--day",
        metavar="YYYY-MM-DD",
        help="UTC day for --recovery (default: yesterday)",
    )
    parser.add_argument(
        "--now",
        metavar="ISO",
        help="override the current UTC timestamp (tests and fixtures)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.recovery:
            body, code, day = run_recovery(args)
        else:
            body, code, day = run_headroom(args)
    except ApiError as err:
        msg = permission_report(err)
        print(msg, file=sys.stderr)
        print("RESULT 1 FAIL")
        return 1
    except (RuntimeError, ValueError, KeyError, OSError) as err:
        print(str(err), file=sys.stderr)
        print("RESULT 1 FAIL")
        return 1
    out_path = Path(args.out) if args.out else default_out_path(day)
    written, write_err = write_output(body, out_path)
    sys.stdout.write(body)
    if written:
        print(f"wrote {written}", file=sys.stderr)
    elif write_err:
        # Still succeed or fail on the counters. The box output path may not
        # exist in CI; tests pass --out to a temp file.
        print(write_err, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
