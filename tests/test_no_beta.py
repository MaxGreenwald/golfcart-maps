"""Max, Oct 22: "Drop beta everywhere ... with a build check so beta can't come back."
Fails on /\\bbeta\\b/i in everything users or crawlers read: the built pages (incl. JSON-LD schema and meta/og),
llms.txt, app JS/HTML in public/, and the generated-page wording in scripts/positioning.py.
Not scanned: public/data/** (map data; OSM place names) and research/ (internal). regions.json keeps an internal 'beta'
quality flag (v3 bar, never shown); JS is checked on string literals only, so `r.beta` code is fine."""
import json, os, re, sys, subprocess, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
BETA = re.compile(r"(?i)\bbeta\b")
STR = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`")
TEXT = (".html", ".js", ".txt", ".xml", ".webmanifest", ".json")

def hits(top):
    out = []
    for d, dirs, files in os.walk(top):
        rel = os.path.relpath(d, top)
        if rel.split(os.sep)[0] in ("data", "vendor"): dirs[:] = []; continue
        for f in files:
            if f.endswith(TEXT):
                p = os.path.join(d, f)
                src = open(p, encoding="utf-8", errors="ignore").read()
                if f.endswith(".js"): src = "\n".join(STR.findall(re.sub(r"(?m)^\s*//.*$|/\*.*?\*/", "", src)))  # JS: user-visible strings only
                for m in BETA.finditer(src):
                    out.append(f"{os.path.relpath(p, top)}: ...{m.string[max(0, m.start()-40):m.end()+30]!r}...")
    return out

class NoBeta(unittest.TestCase):
    def test_public_source(self):
        self.assertEqual(hits(os.path.join(ROOT, "public")), [])
    def test_built_site(self):
        import build_web
        with tempfile.TemporaryDirectory() as t:
            build_web.build(out=t)
            self.assertTrue(os.path.exists(os.path.join(t, "index.html")))
            self.assertEqual(hits(t), [])
    def test_positioning_strings(self):
        import positioning as P
        for k, v in vars(P).items():
            if k.isupper() and isinstance(v, str): self.assertNotRegex(v, BETA, k)

if __name__ == "__main__":
    unittest.main()
