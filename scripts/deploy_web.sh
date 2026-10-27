#!/usr/bin/env bash
# The one way to deploy the web app. Builds dist/ from public/ (stamps the service worker cache
# name from a content hash), runs the fast checks, then uploads dist/ + functions/ to Cloudflare Pages.
#
#   scripts/deploy_web.sh preview <branch>
#       -> https://<branch>.golfcart-maps.pages.dev
#   scripts/deploy_web.sh production --max-ok <Max chat or card id>
#       -> https://golfcartmap.com
#
# Production calls the shared gate (scripts/prod_gate.sh) before any build or wrangler
# call. The gate exits 1 when --max-ok is missing, the branch is not master,
# public/ functions/ lib/ are dirty, or HEAD is not origin/master
# (an unpushed or local-only commit).
#
# After a production Pages upload, this runs scripts/verify_live against
# https://golfcartmap.com and appends one line to $GCM_BOT_LOG
# (default /workspace/gcm/bot-log.md). That path is not present on a cloud-agent VM;
# set GCM_BOT_LOG to a writable file there. Line format:
#   YYYY-MM-DD HH:MM PT commit=<12 hex> max-ok=<ref> PASS|FAIL
# verify_live FAIL still appends the line, then this script exits non-zero.
#
# Needs CLOUDFLARE_API_TOKEN in the environment. WRANGLER overrides the wrangler binary
# (default: /workspace/.wr3/node_modules/.bin/wrangler, else npx wrangler@3).
set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
  echo "usage: scripts/deploy_web.sh preview <branch-name other than master>" >&2
  echo "       scripts/deploy_web.sh production --max-ok <Max chat or card id>" >&2
}

mode=""
branch=""
max_ok=""
while [ $# -gt 0 ]; do
  case "$1" in
    production|preview)
      mode=$1
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
      if [ "$mode" = preview ] && [ -z "$branch" ]; then
        branch=$1
        shift
      else
        echo "unknown argument: $1" >&2
        usage
        exit 1
      fi
      ;;
  esac
done

case "$mode" in
  production)
    # Before build, unit tests, or wrangler. Same gate the worker deploy uses.
    bash scripts/prod_gate.sh --max-ok "$max_ok" --paths public functions lib \
      --dirty-msg "uncommitted changes in public/ functions/ lib/; commit first"
    branch=master
    ;;
  preview)
    [ -n "$branch" ] && [ "$branch" != master ] || { usage; exit 1; }
    ;;
  *)
    usage
    exit 1
    ;;
esac

python3 scripts/check_single_source.py
python3 -m unittest tests.test_web_build -q
python3 scripts/build_web.py
W=${WRANGLER:-}
if [ -z "$W" ]; then
  if [ -x /workspace/.wr3/node_modules/.bin/wrangler ]; then W=/workspace/.wr3/node_modules/.bin/wrangler; else W="npx --yes wrangler@3"; fi
fi
# run from the repo root so wrangler also bundles ./functions (the /api/ paywall endpoints);
# wrangler keeps its cache in the nearest node_modules/ (gitignored), so make sure there is one here
mkdir -p node_modules
commit=$(env -u GIT_DIR -u GIT_WORK_TREE git rev-parse HEAD)
msg=$(env -u GIT_DIR -u GIT_WORK_TREE git log -1 --format=%s | cut -c1-200)
$W pages deploy dist --project-name golfcart-maps --branch "$branch" --commit-hash "$commit" --commit-message "$msg" --commit-dirty=true

if [ "$mode" = production ]; then
  set +e
  python3 scripts/verify_live --url https://golfcartmap.com
  rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then status=PASS; else status=FAIL; fi
  bash scripts/prod_gate.sh --append-log --max-ok "$max_ok" --status "$status"
  exit "$rc"
fi
