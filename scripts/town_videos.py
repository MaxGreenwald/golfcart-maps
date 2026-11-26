"""Region slug to YouTube video, for the region page and its question pages.

content/videos.json is the map. One line adds a video:

  "portaransas": "VIDEO_ID"

Then run scripts/fetch_video_meta.py so content/video_meta.json picks up the title,
description, thumbnail and upload date from YouTube. A slug with no line renders
the same HTML it does without this module.
"""
import datetime, json, os, re
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MAP_PATH = os.path.join(ROOT, "content", "videos.json")
META_PATH = os.path.join(ROOT, "content", "video_meta.json")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
# Full YouTube publish timestamp: ISO 8601 date-time with a timezone offset.
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Date-only stored values become midnight UTC. The calendar date is known;
# the publish time is not, so Z is used instead of inventing a Pacific offset.
FALLBACK_SUFFIX = "T00:00:00Z"
# Same user-facing bans as seo_common.page, so a video cannot publish a page the builder would reject.
BANNED = re.compile(r"(?i)\bbeta\b|verified|android")
FIELDS = ("title", "description", "thumbnailUrl", "uploadDate")
_cache = None

HEAD = """<style>
.gcm-yt{margin:16px 0;max-width:720px}
.gcm-yt-btn{position:relative;display:block;width:100%;margin:0;padding:0;border:0;background:#12343f;cursor:pointer;aspect-ratio:16/9}
.gcm-yt-btn img{width:100%;height:100%;object-fit:cover;display:block}
.gcm-yt-icon{position:absolute;left:50%;top:50%;width:68px;height:48px;margin:-24px 0 0 -34px;background:#e11;border-radius:12px}
.gcm-yt-icon:before{content:"";position:absolute;left:26px;top:14px;border-style:solid;border-width:10px 0 10px 16px;border-color:transparent transparent transparent #fff}
.gcm-yt iframe{display:block;width:100%;aspect-ratio:16/9;border:0}
</style>
<script>
document.addEventListener("click",function(ev){
var b=ev.target.closest&&ev.target.closest(".gcm-yt-btn");
if(!b)return;
var f=document.createElement("iframe");
f.src="https://www.youtube-nocookie.com/embed/"+encodeURIComponent(b.getAttribute("data-id"))+"?autoplay=1&rel=0";
f.title=b.getAttribute("data-title");
f.allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
f.allowFullscreen=true;
f.referrerPolicy="strict-origin-when-cross-origin";
f.loading="lazy";
b.replaceWith(f);
});
</script>
"""


def _region_slugs():
    rows = json.load(open(os.path.join(ROOT, "public", "data", "regions.json"), encoding="utf-8"))
    return {r["slug"] for r in rows}


def load_map(path=MAP_PATH):
    data = json.load(open(path, encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in data.items()):
        raise SystemExit("content/videos.json must map region slug to YouTube id")
    unknown = sorted(set(data) - _region_slugs())
    if unknown:
        raise SystemExit("content/videos.json unknown region slug: " + ", ".join(unknown))
    bad = [f"{k}={v}" for k, v in data.items() if not ID_RE.match(v)]
    if bad:
        raise SystemExit("content/videos.json needs 11-character YouTube ids: " + ", ".join(bad))
    return data


def load_meta(path=META_PATH):
    if not os.path.exists(path):
        raise SystemExit("content/video_meta.json missing. Run scripts/fetch_video_meta.py")
    data = json.load(open(path, encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("content/video_meta.json must be an object keyed by YouTube id")
    return data


def parse_upload_datetime(value):
    """Return a timezone-aware datetime, or None if the string is not valid."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not DATE_RE.match(text):
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_upload_date(value, vid=""):
    """Keep a full ISO timestamp with offset, or add T00:00:00Z to a date-only value."""
    if isinstance(value, str) and DATE_RE.match(value.strip()) and parse_upload_datetime(value):
        return value.strip()
    if isinstance(value, str) and DATE_ONLY_RE.match(value.strip()):
        return value.strip() + FALLBACK_SUFFIX
    label = f"{vid} " if vid else ""
    raise SystemExit(
        f"{label}uploadDate must be ISO 8601 date-time with timezone, got {value!r}"
    )


def _checked(vid, meta):
    if not isinstance(meta, dict) or any(not isinstance(meta.get(k), str) or not meta[k].strip() for k in FIELDS):
        raise SystemExit(f"content/video_meta.json missing title, description, thumbnailUrl or uploadDate for {vid}")
    if not meta["thumbnailUrl"].startswith("https://i.ytimg.com/"):
        raise SystemExit(f"{vid} thumbnail must be an https://i.ytimg.com URL from YouTube")
    uploaded = normalize_upload_date(meta["uploadDate"], vid)
    if "</" in meta["description"] or BANNED.search(meta["title"]) or BANNED.search(meta["description"]):
        raise SystemExit(f"{vid} title or description is not safe to publish")
    out = {k: meta[k] for k in FIELDS}
    out["uploadDate"] = uploaded
    return {"id": vid, **out}


def video_for(slug):
    """Metadata for this region, or None when the map has no line for it."""
    global _cache
    if _cache is None:
        mapping, meta = load_map(), load_meta()
        missing = sorted({v for v in mapping.values() if v not in meta})
        if missing:
            raise SystemExit("no YouTube metadata for " + ", ".join(missing) + ". Run scripts/fetch_video_meta.py")
        _cache = (mapping, meta)
    mapping, meta = _cache
    vid = mapping.get(slug)
    return _checked(vid, meta[vid]) if vid else None


def embed_html(video):
    """Click-to-load facade. No iframe, so YouTube sets no cookie until the click."""
    if not video:
        return ""
    import html
    e = lambda s: html.escape(s, quote=True)
    title, vid = video["title"], video["id"]
    return (
        '<h2>Video</h2>\n'
        '<figure class="gcm-yt">\n'
        f'<button type="button" class="gcm-yt-btn" data-id="{e(vid)}" data-title="{e(title)}" aria-label="{e("Play video: " + title)}">\n'
        f'<img src="{e(video["thumbnailUrl"])}" alt="" width="480" height="360" loading="lazy" decoding="async">\n'
        '<span class="gcm-yt-icon" aria-hidden="true"></span>\n'
        '</button>\n'
        f'<figcaption class="muted">{e(title)}</figcaption>\n'
        '</figure>\n'
    )


def video_head():
    return HEAD


def video_ld(video):
    vid = video["id"]
    return {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": video["title"],
        "description": video["description"],
        "thumbnailUrl": video["thumbnailUrl"],
        "uploadDate": video["uploadDate"],
        "embedUrl": f"https://www.youtube-nocookie.com/embed/{vid}",
        "contentUrl": f"https://www.youtube.com/watch?v={vid}",
    }
