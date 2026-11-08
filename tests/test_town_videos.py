"""Town YouTube videos: content/videos.json maps a region slug to an id.

The region page (/30a) and every question page under it (/30a/seaside and the rest)
get a click-to-load youtube-nocookie embed and a VideoObject. Other pages stay the
same. Titles, thumbnails, descriptions and upload dates come from content/video_meta.json,
which scripts/fetch_video_meta.py fills from YouTube oEmbed and the watch page.
"""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_common as C, seo_pages as P, seo_towns as T, town_videos as V

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WITH = ("30a", "hiltonhead", "myrtlebeach", "portaransas")
SUBS = {
    "30a": "seaside",
    "hiltonhead": "hilton-head-island",
    "myrtlebeach": "myrtle-beach",
    "portaransas": "port-aransas",
}
NEEDED = {"name", "description", "thumbnailUrl", "uploadDate", "embedUrl", "contentUrl"}


def ld(html):
    return json.loads(re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1))


def video_node(html):
    return next(x for x in ld(html) if x["@type"] == "VideoObject")


def csp_allows(policy):
    """True when frame-src allows youtube-nocookie.com and img-src allows i.ytimg.com.

    A missing directive falls through to default-src. If that is missing too, the
    browser default allows the request.
    """
    dirs = {}
    for part in policy.split(";"):
        bits = part.strip().split()
        if bits:
            dirs[bits[0].lower()] = bits[1:]

    def token_ok(token, host):
        t = token.strip("'\"").lower()
        if t in ("*", "https:", "http:"):
            return True
        wild = t.startswith("*.")
        if t.startswith("https://") or t.startswith("http://"):
            t = t.split("://", 1)[1]
        t = t.split("/")[0]
        if wild or t.startswith("*."):
            base = t[2:]
            return host == base or host.endswith("." + base)
        return t == host or host.endswith("." + t) or t.endswith("." + host)

    def allows(directive, host):
        src = dirs.get(directive)
        if src is None:
            src = dirs.get("default-src")
        if src is None:
            return True
        return any(token_ok(token, host) for token in src)

    return allows("frame-src", "youtube-nocookie.com") and allows("img-src", "i.ytimg.com")


def header_policies(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("/"):
            continue
        if s.lower().startswith("content-security-policy:"):
            out.append(s.split(":", 1)[1].strip())
    return out


class TownVideos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = V.load_map()
        cls.meta = V.load_meta()
        cls.regs = {g["slug"]: g for g in C.regions()}
        cls.rules = C.effective_rules()
        cls.region_html = {slug: P.region_page(cls.regs[slug], cls.rules[cls.regs[slug]["id"]]) for slug in list(WITH) + ["sandiego", "villages"]}
        cls.town_html = {}
        for slug, town in SUBS.items():
            path = os.path.join(T.TOWNS, slug, town + ".json")
            tw = json.load(open(path, encoding="utf-8"))
            cls.town_html[(slug, town)] = T.town_page(tw, cls.regs[slug], path)
        path = os.path.join(T.TOWNS, "sandiego", "la-jolla.json")
        tw = json.load(open(path, encoding="utf-8"))
        cls.town_html[("sandiego", "la-jolla")] = T.town_page(tw, cls.regs["sandiego"], path)

    def test_map_is_region_slug_to_id(self):
        self.assertEqual(set(self.map), set(WITH))
        for slug, vid in self.map.items():
            self.assertIn(slug, self.regs)
            self.assertRegex(vid, r"^[A-Za-z0-9_-]{11}$")
            self.assertIn(vid, self.meta)

    def test_region_page_has_facade_and_video_object(self):
        for slug in WITH:
            h = self.region_html[slug]
            vid = self.map[slug]
            meta = self.meta[vid]
            self.assertIn('class="gcm-yt-btn"', h)
            self.assertIn(f'data-id="{vid}"', h)
            self.assertIn('loading="lazy"', h)
            self.assertIn("aspect-ratio:16/9", h)
            self.assertIn("https://www.youtube-nocookie.com/embed/", h)
            self.assertIn(meta["thumbnailUrl"], h)
            self.assertIn("https://i.ytimg.com/", h)
            self.assertIn(f'aria-label="Play video: {C.e(meta["title"])}"', h)
            self.assertNotIn("<iframe", h.lower())
            node = video_node(h)
            self.assertEqual(node["@context"], "https://schema.org")
            self.assertTrue(NEEDED <= set(node))
            self.assertEqual(node["name"], meta["title"])
            self.assertEqual(node["description"], meta["description"])
            self.assertEqual(node["thumbnailUrl"], meta["thumbnailUrl"])
            self.assertEqual(node["uploadDate"], meta["uploadDate"])
            self.assertRegex(node["uploadDate"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertEqual(node["embedUrl"], f"https://www.youtube-nocookie.com/embed/{vid}")
            self.assertEqual(node["contentUrl"], f"https://www.youtube.com/watch?v={vid}")
            types = {x["@type"] for x in ld(h)}
            self.assertTrue({"Organization", "WebSite", "SoftwareApplication", "FAQPage", "BreadcrumbList", "VideoObject"} <= types)

    def test_question_subpage_30a_seaside(self):
        h = self.town_html[("30a", "seaside")]
        vid = self.map["30a"]
        self.assertIn(f'data-id="{vid}"', h)
        self.assertIn('loading="lazy"', h)
        self.assertNotIn("<iframe", h.lower())
        node = video_node(h)
        self.assertEqual(node["name"], self.meta[vid]["title"])
        self.assertEqual(node["uploadDate"], "2026-11-06")
        self.assertEqual(node["embedUrl"], f"https://www.youtube-nocookie.com/embed/{vid}")
        types = {x["@type"] for x in ld(h)}
        self.assertTrue({"WebPage", "BreadcrumbList", "FAQPage", "VideoObject"} <= types)
        webpage = next(x for x in ld(h) if x["@type"] == "WebPage")
        self.assertEqual(webpage["@type"], "WebPage")
        self.assertIn("dateModified", webpage)

    def test_other_question_pages_for_these_towns(self):
        for slug, town in SUBS.items():
            if slug == "30a":
                continue
            h = self.town_html[(slug, town)]
            self.assertIn(f'data-id="{self.map[slug]}"', h, town)
            self.assertEqual(video_node(h)["uploadDate"], self.meta[self.map[slug]]["uploadDate"])
        for slug in WITH:
            for name in os.listdir(os.path.join(T.TOWNS, slug)):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(T.TOWNS, slug, name)
                tw = json.load(open(path, encoding="utf-8"))
                h = T.town_page(tw, self.regs[slug], path)
                self.assertIn(self.map[slug], h, f"{slug}/{tw['slug']}")
                self.assertEqual(video_node(h)["contentUrl"], f"https://www.youtube.com/watch?v={self.map[slug]}")

    def test_pages_without_a_video_stay_plain(self):
        for slug in ("sandiego", "villages"):
            h = self.region_html[slug]
            self.assertNotIn("gcm-yt", h)
            self.assertNotIn("youtube", h.lower())
            self.assertNotIn("VideoObject", h)
        h = self.town_html[("sandiego", "la-jolla")]
        self.assertNotIn("gcm-yt", h)
        self.assertNotIn("VideoObject", h)
        real = V.video_for
        V.video_for = lambda slug: None
        try:
            plain_region = P.region_page(self.regs["sandiego"], self.rules[self.regs["sandiego"]["id"]])
            plain_30a = P.region_page(self.regs["30a"], self.rules[self.regs["30a"]["id"]])
            path = os.path.join(T.TOWNS, "30a", "seaside.json")
            tw = json.load(open(path, encoding="utf-8"))
            plain_town = T.town_page(tw, self.regs["30a"], path)
        finally:
            V.video_for = real
        self.assertEqual(plain_region, self.region_html["sandiego"])
        self.assertNotIn("gcm-yt", plain_30a)
        self.assertEqual(ld(plain_30a), ld(self.region_html["30a"])[:-1])
        self.assertNotIn("gcm-yt", plain_town)
        self.assertEqual(ld(plain_town), ld(self.town_html[("30a", "seaside")])[:-1])

    def test_csp_helper_and_headers(self):
        self.assertTrue(csp_allows("default-src 'self' https://www.youtube-nocookie.com https://i.ytimg.com"))
        self.assertTrue(csp_allows("frame-src https://www.youtube-nocookie.com; img-src https://i.ytimg.com"))
        self.assertTrue(csp_allows("frame-src https://*.youtube-nocookie.com; img-src https://*.ytimg.com"))
        self.assertTrue(csp_allows("script-src 'self'"))
        self.assertFalse(csp_allows("default-src 'self'"))
        self.assertFalse(csp_allows("frame-src https://www.youtube.com; img-src https://i.ytimg.com"))
        self.assertFalse(csp_allows("frame-src https://www.youtube-nocookie.com; img-src 'self'"))
        headers = open(os.path.join(ROOT, "public", "_headers"), encoding="utf-8").read()
        self.assertIn("youtube-nocookie.com", headers)
        self.assertIn("i.ytimg.com", headers)
        found = [("_headers", p) for p in header_policies(headers)]
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "functions")):
            for name in filenames:
                if name.endswith((".js", ".html", ".json")):
                    text = open(os.path.join(dirpath, name), encoding="utf-8", errors="ignore").read()
                    for m in re.finditer(r"(?i)content-security-policy[\"']?\s*[:=]\s*[\"']([^\"']+)", text):
                        found.append((os.path.join(dirpath, name), m.group(1)))
        for src, policy in found:
            self.assertTrue(csp_allows(policy), src)


if __name__ == "__main__":
    unittest.main()
