#!/usr/bin/env bash
# The one way to deploy the web app. Builds dist/ from public/ (stamps the service worker cache
# name from a content hash), runs the fast checks, then uploads dist/ + functions/ to Cloudflare Pages.
#
#   scripts/deploy_web.sh preview <branch>   -> https://<branch>.golfcart-maps.pages.dev
#   scripts/deploy_web.sh production         -> https://golfcartmap.com  (only with Max's OK; must be on master)
#
# Needs CLOUDFLARE_API_TOKEN in the environment. WRANGLER overrides the wrangler binary
# (default: /workspace/.wr3/node_modules/.bin/wrangler, else npx wrangler@3).
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:-}; branch=${2:-}
case "$mode" in
  production)
    cur=$(git rev-parse --abbrev-ref HEAD)
    [ "$cur" = master ] || { echo "production deploys only from master (on $cur)"; exit 1; }
    [ -z "$(git status --porcelain -- public functions lib)" ] || { echo "uncommitted changes in public/ functions/ lib/; commit first"; exit 1; }
    branch=master ;;
  preview)
    [ -n "$branch" ] && [ "$branch" != master ] || { echo "usage: $0 preview <branch-name other than master>"; exit 1; } ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
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
$W pages deploy dist --project-name golfcart-maps --branch "$branch" --commit-hash "$(git rev-parse HEAD)" --commit-message "$(git log -1 --format=%s | cut -c1-200)" --commit-dirty=true
