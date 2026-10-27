#!/usr/bin/env bash
# The one way to deploy the partner and analytics Workers.
#
#   scripts/deploy_worker.sh preview partner|analytics
#       -> wrangler deploy --env preview (gcm-partner-preview / gcm-analytics-preview)
#   scripts/deploy_worker.sh production partner|analytics --max-ok <Max chat or card id>
#       -> wrangler deploy (gcm-partner / gcm-analytics)
#
# Production uses the same gate as the web deploy (scripts/prod_gate.sh), before any
# wrangler call. It exits 1 when --max-ok is missing, the branch is not master,
# that worker directory is dirty, or HEAD is not origin/master.
#
# WRANGLER overrides the wrangler binary (same default as scripts/deploy_web.sh).
# Needs CLOUDFLARE_API_TOKEN in the environment.
set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
  echo "usage: scripts/deploy_worker.sh preview partner|analytics" >&2
  echo "       scripts/deploy_worker.sh production partner|analytics --max-ok <Max chat or card id>" >&2
}

mode=""
which=""
max_ok=""
while [ $# -gt 0 ]; do
  case "$1" in
    production|preview)
      mode=$1
      shift
      ;;
    partner|analytics)
      which=$1
      shift
      ;;
    --max-ok)
      if [ $# -lt 2 ]; then
        max_ok=""
        shift
      else
        max_ok=$2
        shift 2
      fi
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$which" in
  partner) dir=workers/partner ;;
  analytics) dir=workers/analytics ;;
  *) usage; exit 1 ;;
esac

case "$mode" in
  production)
    bash scripts/prod_gate.sh --max-ok "$max_ok" --paths "$dir" \
      --dirty-msg "uncommitted changes in $dir; commit first"
    ;;
  preview)
    ;;
  *)
    usage
    exit 1
    ;;
esac

W=${WRANGLER:-}
if [ -z "$W" ]; then
  if [ -x /workspace/.wr3/node_modules/.bin/wrangler ]; then W=/workspace/.wr3/node_modules/.bin/wrangler; else W="npx --yes wrangler@3"; fi
fi

if [ "$mode" = production ]; then
  ( cd "$dir" && $W deploy )
else
  ( cd "$dir" && $W deploy --env preview )
fi
