<!-- Replace each paragraph below. CI fails if a section is missing or still this placeholder, if Evidence has no command output or URL, if no EVIDENCE stamp or GitHub Actions run URL matches the PR head SHA, or if a command only prints its own result. After a later push, rerun scripts/evidence.sh on HEAD. -->

## Summary

What changes for a driver or shop, in 1 to 3 lines.

## Evidence

Run a real check on this PR's HEAD and paste the stamp block plus the command output:

```
scripts/evidence.sh python -m unittest discover -s tests -v
EVIDENCE sha=0123456789ab exit=0 cmd=python -m unittest discover -s tests -v
<command output>
```

A GitHub Actions run URL that contains this PR's head SHA also counts (the commit checks page for that full SHA).

These do not count, because the command only prints its own result: python -c "print('PASS')", echo PASS, printf PASS.

Screenshots for UI changes, and the source for road data, still belong here.

## Merge danger

What could break, which towns/roads/pages it touches, whether anything could show a road as legal when it is not, and how to roll back.
