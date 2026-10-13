#!/bin/bash
# After finish_expansion.sh deploys, rebuild once more so the expanded data picks up the latest overrides.py, then redeploy.
cd /workspace/golfcart-maps
until grep -q "DEPLOYED" /tmp/finish.log 2>/dev/null || grep -q "build failed" /tmp/finish.log 2>/dev/null; do sleep 60; done
grep -q "build failed" /tmp/finish.log && exit 1
python3 scripts/build_data.py > /tmp/rebuild2.log 2>&1 || exit 1
/workspace/.venv/bin/python scripts/test_trips.py >> /tmp/rebuild2.log 2>&1
git add -A && git -c user.name="Max Greenwald" -c user.email=max@users.noreply.github.com commit -qm "Rebuild expanded coverage with latest speed overrides" && \
git branch -f gh-pages $(git subtree split --prefix public HEAD) && git push -f origin gh-pages >> /tmp/rebuild2.log 2>&1 && git push origin HEAD:master >> /tmp/rebuild2.log 2>&1 && echo "REDEPLOYED $(date)" >> /tmp/rebuild2.log
