"""Service worker cache name + single-source guards. Run: python3 -m unittest discover -s tests"""
import os, re, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import build_web as B
import check_single_source as S

PUB = os.path.join(B.ROOT, "public")


def snapshot():
    """Every file in public/ as {relpath: bytes} (data tiles are read lazily to keep this fast)."""
    files = {}
    for d, _, fs in os.walk(PUB):
        for f in fs:
            files[os.path.relpath(os.path.join(d, f), PUB)] = None
    def read(p, over={}):
        if p in over: return over[p]
        f = os.path.join(PUB, p)
        return open(f, "rb").read() if os.path.isfile(f) else None
    return files, read


def precached():
    sw = open(os.path.join(PUB, "sw.js"), encoding="utf-8").read()
    return sorted({B._entry_path(u) for u in re.findall(r"'([^']*)'", B.PRE_RE.search(sw).group(1))})


def has_rev(rev):
    return subprocess.run(["git", "-C", B.ROOT, "cat-file", "-e", rev + "^{commit}"], capture_output=True).returncode == 0


class CacheName(unittest.TestCase):
    def name(self, over=None):
        _, read = snapshot()
        return B.cache_name(lambda p: read(p, over or {}))

    def test_every_precached_file_changes_the_name(self):
        base = self.name()
        _, read = snapshot()
        for p in precached() + ["sw.js"]:
            with self.subTest(file=p):
                self.assertNotEqual(self.name({p: (read(p) or b"") + b"\n// edit"}), base)

    def test_non_precached_files_do_not_change_the_name(self):
        base = self.name()
        for p in ["privacy.html", "robots.txt"]:
            with self.subTest(file=p):
                self.assertEqual(self.name({p: b"changed"}), base)

    def test_name_is_deterministic_and_well_formed(self):
        self.assertEqual(self.name(), self.name())
        self.assertRegex(self.name(), r"^gcm-[0-9a-f]{12}$")

    def test_source_sw_has_placeholder_not_a_manual_version(self):
        sw = open(os.path.join(PUB, "sw.js"), encoding="utf-8").read()
        self.assertIn("const C='%s'" % B.PLACEHOLDER, sw)
        self.assertNotRegex(sw, r"gcm-v\d+", "manual gcm-vNN bumps are gone; build_web.py stamps the name")

    def test_build_stamps_dist(self):
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "dist")
            name = B.build(out=out)
            sw = open(os.path.join(out, "sw.js"), encoding="utf-8").read()
            self.assertIn("const C='%s'" % name, sw)
            self.assertNotIn(B.PLACEHOLDER, sw)
            self.assertEqual(open(os.path.join(out, "app.js"), "rb").read(), open(os.path.join(PUB, "app.js"), "rb").read())

    @unittest.skipUnless(has_rev("7ef87cd") and has_rev("656db2c"), "needs full git history")
    def test_catches_656db2c_missed_bump(self):
        """656db2c (turn lanes, live) changed app.js but kept 'gcm-v40' from 7ef87cd: phones kept the old cache.
        The content-hash name differs between the two."""
        old = lambda rev: B.NAME_RE.search(B.read_rev(rev)("sw.js").decode()).group(1)
        self.assertEqual(old("7ef87cd"), old("656db2c"))  # the manual name did NOT change
        self.assertNotEqual(B.cache_name(B.read_rev("7ef87cd")), B.cache_name(B.read_rev("656db2c")))


class InternalStamp(unittest.TestCase):
    def test_simulator_build_stamps_track_js_only_in_dist(self):
        d = tempfile.mkdtemp()
        os.environ["GCM_ANALYTICS_INTERNAL"] = "sim"
        try:
            B.build(out=d, native=True)
            dist = open(os.path.join(d, "track.js"), encoding="utf-8").read()
            src = open(os.path.join(PUB, "track.js"), encoding="utf-8").read()
            self.assertIn("const BUILD_INTERNAL = 'sim';", dist)
            self.assertNotIn(B.INTERNAL_TOKEN, dist)
            self.assertIn(B.INTERNAL_TOKEN, src)
        finally:
            os.environ.pop("GCM_ANALYTICS_INTERNAL", None)
            shutil.rmtree(d)

    def test_rejects_unknown_channel(self):
        with self.assertRaises(SystemExit):
            B.analytics_internal_channel(["build_web.py", "--internal", "testimonial"])


class SingleSource(unittest.TestCase):
    ROWS = [("public/app.js", "a1"), ("public/sw.js", "b1"), ("public/index.html", "c1"), ("public/data/x.json", "d1"),
            ("lib/pay.js", "e1"), ("package.json", "f1"), ("scripts/test.py", "g1")]

    def test_clean_tree_passes(self):
        self.assertEqual(S.problems(self.ROWS), [])
        self.assertEqual(S.problems(S.tracked(None)), [], "this checkout has a committed copy of public/")

    def test_flags_committed_capacitor_bundle(self):
        bad = S.problems(self.ROWS + [("ios/App/App/public/app.js", "zz"), ("android/app/src/main/assets/public/index.html", "c1")])
        self.assertEqual(len(bad), 2)

    def test_flags_byte_identical_copy_anywhere(self):
        self.assertTrue(S.problems(self.ROWS + [("nav/old-index.html", "c1")]))

    def test_flags_renamed_entry_point_copy(self):
        self.assertTrue(S.problems(self.ROWS + [("carplay/app.js", "q9")]))

    def test_flags_dist(self):
        self.assertTrue(S.problems(self.ROWS + [("dist/sw.js", "b2")]))


if __name__ == "__main__":
    unittest.main()
