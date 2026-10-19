#!/usr/bin/env python3
"""Block the word "verified" (any case, including "unverified") in user-facing copy.

Only coastal San Diego segments with two agreeing sources may be called verified, and that badge lives
between `sd-verified-badge:start` and `sd-verified-badge:end` markers in public/app.js (the code there
must be gated to the SD region and to ways listed in public/data/sd/verified.json). Everything else fails.

Scanned: every text file in public/ except the generated map data, the displayed strings in
public/data/regions.json (name, short, cover, rule.cite) and rules.json (cite/label/note text shown in the
app), functions/ and lib/. Allowed exceptions: the Stripe /api/verify endpoint name.
Run: python3 scripts/check_verified_wording.py   (exit 1 on any hit)"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORD = re.compile(r"verified", re.I)
ALLOW = [re.compile(r"""['"/]verify\?session_id""")]          # endpoint name, never shown
TEXT_EXT = {".html", ".js", ".txt", ".xml", ".webmanifest", ".json", ".css", ".svg", ".md"}
START, END = "sd-verified-badge:start", "sd-verified-badge:end"
hits = []


def strip_badge(src, path):
    out, i = [], 0
    while True:
        a = src.find(START, i)
        if a < 0: out.append(src[i:]); break
        b = src.find(END, a)
        if b < 0: hits.append(f"{path}: '{START}' without '{END}'"); out.append(src[i:]); break
        block = src[a:b]
        if "'sd'" not in block and '"sd"' not in block:
            hits.append(f"{path}: the sd-verified-badge block must be gated to the 'sd' region")
        out.append(src[i:a]); i = b + len(END)
    return "".join(out)


def scan(path, text):
    for m in WORD.finditer(text):
        ctx = text[max(0, m.start() - 60): m.end() + 60]
        if any(a.search(ctx) for a in ALLOW): continue
        line = text.count("\n", 0, m.start()) + 1
        hits.append(f"{os.path.relpath(path, ROOT)}:{line}: …{ctx.strip()}…")


for base in ("public", "functions", "lib"):
    for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
        if os.path.relpath(dp, ROOT).startswith(os.path.join("public", "data")): dn[:] = []; continue
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.splitext(f)[1] not in TEXT_EXT: continue
            t = open(p, encoding="utf-8", errors="replace").read()
            if f == "app.js": t = strip_badge(t, p)
            scan(p, t)

regions = json.load(open(os.path.join(ROOT, "public/data/regions.json")))
for r in regions:
    shown = " | ".join(str(x) for x in (r.get("name"), r.get("short"), r.get("cover"), (r.get("rule") or {}).get("cite")) if x)
    scan(f"public/data/regions.json[{r.get('id')}]", shown)


def shown_strings(o, k=None):
    if isinstance(o, dict):
        for kk, v in o.items():
            if not kk.startswith("_"): yield from shown_strings(v, kk)   # "_note" keys are developer notes
    elif isinstance(o, list):
        for v in o: yield from shown_strings(v, k)
    elif isinstance(o, str): yield o


# road source labels shown in popups ("Source: ..."), one list per region index
DATA = os.path.join(ROOT, "public", "data")
for rid in sorted(os.listdir(DATA)):
    ip = os.path.join(DATA, rid, "index.json")
    if os.path.isfile(ip):
        src = json.load(open(ip)).get("sources") or []
        scan(f"public/data/{rid}/index.json[sources]", " | ".join(json.dumps(x, ensure_ascii=False) for x in src))

scan("public/data/rules.json", " | ".join(shown_strings(json.load(open(os.path.join(ROOT, "public/data/rules.json"))))))

if hits:
    print("FAIL: 'verified' outside the coastal-SD verified badge path:"); print("\n".join("  " + h for h in hits)); sys.exit(1)
print("RESULT ALL PASS (no 'verified' claims outside the SD badge path)")
