#!/usr/bin/env bash
# Work-safety check: finished work must never exist only on this box.
# Fails if: any branch has commits not on origin; any worktree has uncommitted
# changes older than MAX_AGE_H hours (default 24); any /workspace/gcm-* folder
# has no .git (a folder whose subfolders are all git worktrees counts as OK).
# Prints a one-line summary. Usage: scripts/check_work_safety.sh [-v]
REPO=${REPO:-/workspace/golfcart-maps}; WS=${WS:-/workspace}; MAX_AGE_H=${MAX_AGE_H:-24}
V=0; [ "$1" = -v ] && V=1
cd "$REPO" || { echo "work-safety: FAIL repo $REPO missing"; exit 2; }
git fetch -q origin 2>/dev/null
lb=(); while read -r b; do n=$(git rev-list --count "refs/heads/$b" --not --remotes=origin); [ "$n" -gt 0 ] && lb+=("$b($n)"); done < <(git for-each-ref --format='%(refname:short)' refs/heads)
now=$(date +%s); cutoff=$((now - MAX_AGE_H*3600)); od=()
while read -r w; do [ -d "$w" ] || continue
  while IFS= read -r line; do f="$w/${line:3}"; f="${f%/}"; [ -e "$f" ] || { od+=("$w"); break; }
    m=$(find "$f" -type f -printf '%T@\n' 2>/dev/null | sort -n | head -1); m=${m%.*}; [ -z "$m" ] && m=$(stat -c %Y "$f")
    [ "$m" -lt "$cutoff" ] && { od+=("$w"); break; }
  done < <(git -C "$w" status --porcelain)
done < <(git worktree list --porcelain | awk '/^worktree /{print substr($0,10)}')
ng=(); for d in "$WS"/gcm-*/; do d=${d%/}; [ -e "$d/.git" ] && continue
  sub=$(find "$d" -mindepth 1 -maxdepth 1 -type d); ok=1; [ -z "$sub" ] && ok=0
  for s in $sub; do [ -e "$s/.git" ] || ok=0; done; [ $ok = 1 ] || ng+=("$(basename "$d")"); done
if [ $V = 1 ]; then printf 'local-only: %s\n' "${lb[@]}"; printf 'stale-dirty: %s\n' "${od[@]}"; printf 'no-git: %s\n' "${ng[@]}"; fi
s="work-safety: local-only branches=${#lb[@]} stale-dirty worktrees=${#od[@]} gcm folders without .git=${#ng[@]}"
if [ $((${#lb[@]}+${#od[@]}+${#ng[@]})) -eq 0 ]; then echo "$s -> PASS"; else echo "$s -> FAIL [${lb[*]}] [${od[*]##*/}] [${ng[*]}]"; exit 1; fi
