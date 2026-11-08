#!/usr/bin/env python3
"""Fill content/video_meta.json from YouTube for every id in content/videos.json.

Add a video later: one line in content/videos.json ("region-slug": "VIDEO_ID"), then run
this script. Title and thumbnail come from YouTube oEmbed. Upload date and description
come from the public watch page. publishDate and dateText must agree. Nothing is filled in
by hand.

  python scripts/fetch_video_meta.py
  python scripts/fetch_video_meta.py --check
"""
import datetime, json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_videos as V

UA = "Mozilla/5.0 (compatible; GolfCartMaps/1.0; +https://golfcartmap.com)"
DATE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{1,2}), (\d{4})$")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as res:
        return res.read()


def _iso(text):
    m = DATE.match(text)
    if not m:
        raise SystemExit(f"YouTube date {text!r} is not Mon D, YYYY")
    return datetime.date(int(m.group(3)), datetime.datetime.strptime(m.group(1), "%b").month, int(m.group(2))).isoformat()


def parse_watch(html, title):
    """Upload date and description from a YouTube watch page. Both date fields must agree."""
    published = re.findall(r'"publishDate":\{"simpleText":"([^"]+)"\}', html)
    shown = re.findall(r'"dateText":\{"simpleText":"([^"]+)"\}', html)
    if len(published) != 1 or published != shown:
        raise SystemExit(f"watch page dates disagree for {title!r}: publish={published} shown={shown}")
    if title not in html and title.replace("&", "\\u0026") not in html:
        raise SystemExit(f"watch page does not contain the oEmbed title {title!r}")
    marker = 'attributedDescriptionBodyText":{"content":'
    i = html.find(marker)
    if i < 0:
        raise SystemExit(f"YouTube description missing for {title!r}")
    desc, _ = json.JSONDecoder().raw_decode(html[i + len(marker):])
    if not isinstance(desc, str) or not desc.strip():
        raise SystemExit(f"YouTube description empty for {title!r}")
    return _iso(published[0]), desc


def fetch_one(vid):
    if not V.ID_RE.match(vid):
        raise SystemExit(f"not a YouTube id: {vid}")
    raw = json.loads(_get(f"https://www.youtube.com/oembed?format=json&url=https://youtu.be/{vid}"))
    title, thumb = raw.get("title"), raw.get("thumbnail_url")
    if not title or not thumb or not thumb.startswith("https://i.ytimg.com/"):
        raise SystemExit(f"oEmbed missing title or i.ytimg.com thumbnail for {vid}")
    html = _get(f"https://www.youtube.com/watch?v={vid}&hl=en&gl=US&bpctr=9999999999").decode("utf-8", "replace")
    uploaded, desc = parse_watch(html, title)
    return {"title": title, "description": desc, "thumbnailUrl": thumb, "uploadDate": uploaded}


def fetch_all(mapping=None):
    mapping = V.load_map() if mapping is None else mapping
    out = {}
    for vid in sorted(set(mapping.values())):
        out[vid] = fetch_one(vid)
    return out


def main(argv):
    check = "--check" in argv
    got = fetch_all()
    if check:
        have = V.load_meta()
        if got != have:
            for vid in sorted(set(got) | set(have)):
                if got.get(vid) != have.get(vid):
                    print(f"DIFF {vid}")
            raise SystemExit("content/video_meta.json does not match YouTube")
        print("video metadata matches YouTube")
        return 0
    text = json.dumps(got, ensure_ascii=False, indent=2) + "\n"
    open(V.META_PATH, "w", encoding="utf-8").write(text)
    print(f"wrote {len(got)} videos to content/video_meta.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
