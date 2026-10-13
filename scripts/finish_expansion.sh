#!/bin/bash
# Waits for the background data build, then verifies routing and redeploys to GitHub Pages.
cd /workspace/golfcart-maps
while pgrep -f "scripts/build_data.py" >/dev/null; do sleep 30; done
if ! grep -q '"tileSize"' /tmp/build.log; then echo "build failed" >> /tmp/finish.log; exit 1; fi
pgrep -f "http.server 8765" >/dev/null || (cd public && nohup python3 -m http.server 8765 >/dev/null 2>&1 &); sleep 2
/workspace/.venv/bin/python scripts/test_trips.py >> /tmp/finish.log 2>&1
/workspace/.venv/bin/python scripts/test_regress.py 7 | tail -1 >> /tmp/finish.log 2>&1
git add -A && git -c user.name="Max Greenwald" -c user.email=max@users.noreply.github.com commit -qm "Expand coverage: Oceanside to the border incl. Coronado & Imperial Beach" && \
git branch -f gh-pages $(git subtree split --prefix public HEAD) && git push -f origin gh-pages >> /tmp/finish.log 2>&1 && git push origin HEAD:master >> /tmp/finish.log 2>&1
tail -1 /tmp/build.log >> /tmp/finish.log; echo "DEPLOYED $(date)" >> /tmp/finish.log
