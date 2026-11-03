#!/usr/bin/env bash
# Run a real check in the current tree and stamp the output with HEAD.
#
#   scripts/evidence.sh python -m unittest tests.test_pr_body -v
#
# Prints one line, then the command's stdout and stderr:
#   EVIDENCE sha=<HEAD 12 chars> exit=<code> cmd=<command>
# Exits with the command's exit code. Paste that block into the PR Evidence
# section. After a later push, run it again on the new HEAD.
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/evidence.sh <command> [args...]" >&2
  exit 2
fi

if ! full=$(git rev-parse HEAD 2>/dev/null); then
  echo "scripts/evidence.sh: not a git checkout (no HEAD)" >&2
  exit 2
fi
if [ "${#full}" -lt 12 ]; then
  echo "scripts/evidence.sh: HEAD is shorter than 12 characters" >&2
  exit 2
fi
sha=${full:0:12}
cmd="$*"

out=$(mktemp)
trap 'rm -f "$out"' EXIT
set +e
"$@" >"$out" 2>&1
code=$?
set -e
printf 'EVIDENCE sha=%s exit=%s cmd=%s\n' "$sha" "$code" "$cmd"
cat "$out"
exit "$code"
