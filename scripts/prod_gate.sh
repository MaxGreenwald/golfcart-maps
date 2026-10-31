#!/usr/bin/env bash
# Shared production gate for the web app and the partner/analytics Workers.
# Approval is an argument the tool requires, not a comment a bot can skip.
#
#   scripts/prod_gate.sh --max-ok <Max chat or card id> --paths public functions lib \
#       --dirty-msg "uncommitted changes in public/ functions/ lib/; commit first"
#
# Refuses (exit 1) when any of these is true:
#   - --max-ok is missing, empty, or not a single token
#     (exception: --new-region-ok <ref> --live-commit <sha> instead of --max-ok passes only when
#      scripts/check_new_region_only.py finds the diff from the live commit to HEAD just adds
#      new regions. Max, Oct 30 2026, chat ref t390s2042. Anything else still needs --max-ok.)
#   - the branch is not master
#   - the given paths have uncommitted changes
#   - HEAD is not exactly refs/remotes/origin/master (unpushed or local-only commits)
#
# After a production Pages upload, deploy_web.sh records the result with:
#   GCM_BOT_LOG=/path/to/bot-log.md scripts/prod_gate.sh --append-log --max-ok <ref> --status PASS|FAIL
# GCM_BOT_LOG defaults to /workspace/gcm/bot-log.md. That file is not on a cloud-agent
# VM; tests and any other machine set GCM_BOT_LOG to a writable path. One line:
#   YYYY-MM-DD HH:MM PT commit=<12 hex> max-ok=<ref> PASS|FAIL
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

gitc() {
  # Pin the repo that holds this script. GIT_DIR must not point the check at some other tree.
  env -u GIT_DIR -u GIT_WORK_TREE git -C "$ROOT" "$@"
}

refuse() {
  echo "production deploy refused: $*" >&2
  exit 1
}

check_ref() {
  local ref=$1
  if [ -z "$ref" ]; then
    refuse "--max-ok <ref> is required (Max chat or card id)"
  fi
  case "$ref" in
    -*)
      refuse "--max-ok needs a Max chat or card id, not a flag"
      ;;
    *[[:space:]]*)
      refuse "--max-ok ref must be one Max chat or card id, with no whitespace"
      ;;
  esac
  if [ "${#ref}" -gt 200 ]; then
    refuse "--max-ok ref is too long"
  fi
}

prod_gate() {
  local max_ok="" dirty_msg="uncommitted changes; commit first" new_region_ok="" live_commit=""
  local -a paths=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --max-ok)
        if [ $# -lt 2 ]; then
          refuse "--max-ok <ref> is required (Max chat or card id)"
        fi
        max_ok=$2
        shift 2
        ;;
      --new-region-ok)
        new_region_ok=${2:-}
        shift $(( $# < 2 ? 1 : 2 ))
        ;;
      --live-commit)
        live_commit=${2:-}
        shift $(( $# < 2 ? 1 : 2 ))
        ;;
      --dirty-msg)
        if [ $# -lt 2 ]; then
          refuse "--dirty-msg needs a message"
        fi
        dirty_msg=$2
        shift 2
        ;;
      --paths)
        shift
        while [ $# -gt 0 ]; do
          case "$1" in
            --*) break ;;
            *) paths+=("$1"); shift ;;
          esac
        done
        ;;
      *)
        refuse "unknown argument: $1"
        ;;
    esac
  done

  if [ -z "$max_ok" ] && [ -n "$new_region_ok" ]; then
    check_ref "$new_region_ok"
    case "$live_commit" in
      ""|-*|*[!0-9a-f]*) refuse "--new-region-ok needs --live-commit <hex sha of what is live now>; otherwise use --max-ok" ;;
    esac
    NEW_REGION_LIVE=$live_commit
  else
    check_ref "$max_ok"
  fi

  local cur
  cur=$(gitc rev-parse --abbrev-ref HEAD)
  if [ "$cur" != master ]; then
    echo "production deploys only from master (on $cur)" >&2
    exit 1
  fi

  local dirty
  if [ "${#paths[@]}" -eq 0 ]; then
    dirty=$(gitc status --porcelain)
  else
    dirty=$(gitc status --porcelain -- "${paths[@]}")
  fi
  if [ -n "$dirty" ]; then
    echo "$dirty_msg" >&2
    printf '%s\n' "$dirty" >&2
    exit 1
  fi

  if ! gitc rev-parse --verify --quiet refs/remotes/origin/master >/dev/null; then
    refuse "origin/master is not available (fetch origin master); refusing so a local-only commit cannot ship"
  fi
  local head origin
  head=$(gitc rev-parse HEAD)
  origin=$(gitc rev-parse refs/remotes/origin/master)
  if [ "$head" != "$origin" ]; then
    refuse "HEAD $head is not origin/master $origin (no unpushed or local-only commits)"
  fi

  if [ -n "${NEW_REGION_LIVE:-}" ]; then
    if ! python3 "$ROOT/scripts/check_new_region_only.py" "$NEW_REGION_LIVE"; then
      refuse "--new-region-ok only covers a diff that just adds new regions; this deploy needs --max-ok"
    fi
  fi
}

append_bot_log() {
  local max_ok="" status=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --max-ok)
        if [ $# -lt 2 ]; then
          refuse "--max-ok <ref> is required (Max chat or card id)"
        fi
        max_ok=$2
        shift 2
        ;;
      --status)
        if [ $# -lt 2 ]; then
          refuse "--status PASS or FAIL is required"
        fi
        status=$2
        shift 2
        ;;
      *)
        refuse "unknown argument: $1"
        ;;
    esac
  done
  check_ref "$max_ok"
  case "$status" in
    PASS|FAIL) ;;
    *) refuse "--status must be PASS or FAIL" ;;
  esac
  local log when commit
  log=${GCM_BOT_LOG:-/workspace/gcm/bot-log.md}
  when=$(TZ=America/Los_Angeles date +"%Y-%m-%d %H:%M PT")
  commit=$(gitc rev-parse --short=12 HEAD)
  mkdir -p "$(dirname "$log")"
  printf '%s commit=%s max-ok=%s %s\n' "$when" "$commit" "$max_ok" "$status" >> "$log"
}

if [ "${1:-}" = "--append-log" ]; then
  shift
  append_bot_log "$@"
else
  prod_gate "$@"
fi
