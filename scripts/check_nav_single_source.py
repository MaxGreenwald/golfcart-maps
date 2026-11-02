"""One nav engine for phone and CarPlay (AGENTS.md rule 35, Max t459u).

Off-route, reroute, turn advance, heading, and arrival decisions live in public/navfollow.js (GCMFollow.engine)
on public/nav.js. The phone controller and the CarPlay adapter (carplay.js navFix, called by native CarPlay)
must both go through it. Native Swift may only render what navFix returns.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
errs = []

def need(path, pat, why):
    p = ROOT / path
    if not p.exists() or not re.search(pat, p.read_text()):
        errs.append(f"{path}: missing {pat!r} ({why})")

need("public/navfollow.js", r"const e = E\(\)", "phone controller must use the shared engine")
need("public/carplay.js", r"GCMFollow\.engine\(", "CarPlay adapter must use the shared engine")
need("public/carplay.js", r"navStepsFor\(", "CarPlay maneuvers must come from the phone's steps")

# Nav decisions re-implemented in native code (the build 42 bug: CarPlay had its own off-route logic).
BANNED = [r"\b(struct|enum) CarPlay(OffRoute|WrongWay|Advance|Course|Heading|Guard|Match|VoicePlan)\b", r"\bfunc routeBearing\b",
          r"distance\(from:[^)]*toLine", r"\boffRouteM\b", r"\bwrongWay\w*\s*[:=]"]
for f in sorted((ROOT / "ios").rglob("*.swift")) if (ROOT / "ios").exists() else []:
    if "/tests/" in str(f):
        continue
    for n, line in enumerate(f.read_text().splitlines(), 1):
        for b in BANNED:
            if re.search(b, line):
                errs.append(f"{f.relative_to(ROOT)}:{n}: nav decision in native code ({b}); call GCMBridge navFix instead")

if errs:
    print("FAIL nav single source:\n  " + "\n  ".join(errs)); sys.exit(1)
print("PASS nav single source: phone and CarPlay share GCMFollow.engine; no native nav decisions")
