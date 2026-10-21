#!/usr/bin/env bash
# full suite for one branch in its own worktree + port: run_full.sh <branch> <port>
b=$1; port=$2; w=/workspace/gcm-feat/$b; log=/workspace/gcm-feat/$b.log
cd /workspace/golfcart-maps; [ -d $w ] || git worktree add -q -f $w $b
cd $w/public && (python3 -m http.server $port >/dev/null 2>&1 & echo $! > /workspace/gcm-feat/$b.pid); sleep 1; cd $w
export URL=http://localhost:$port/
: > $log
for f in scripts/test*.js; do r=$(timeout 300 node $f 2>&1 | tail -1); echo "$f :: $r" >> $log; done
for f in tests/*.mjs; do r=$(node --test $f 2>&1 | grep -E '^# fail'); echo "$f :: $r" >> $log; done
for f in tests/test_*.py; do m=tests.$(basename $f .py); r=$(timeout 600 python3 -m unittest $m -q 2>&1 | tail -1); echo "$f :: $r" >> $log; done
for f in scripts/test*.py; do r=$(timeout 600 python3 $f 2>&1 | grep -v '^\s*$' | tail -1 | cut -c1-160); echo "$f :: $r" >> $log; done
kill $(cat /workspace/gcm-feat/$b.pid); echo DONE >> $log
