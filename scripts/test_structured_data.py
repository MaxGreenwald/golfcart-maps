#!/usr/bin/env python3
"""Check JSON-LD in dist/ against Google's required properties and formats.

Walks every <script type="application/ld+json"> block, including @graph and
arrays, and checks each @type the site emits. VideoObject uploadDate must be
an ISO 8601 date-time with a timezone offset (Search Console, Nov 25 2026).

Usage:
  python scripts/test_structured_data.py
  python scripts/test_structured_data.py path/to/html-root
Exit 0 when every node is clean, 1 on any miss. Each miss prints the page
path, @type, field, and expected format.
"""
from __future__ import annotations

import datetime
import html as htmlmod
import json
import os
import re
import sys

from _check import ck, fail, fails, finish

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.I | re.S)
TYPE_ATTR_RE = re.compile(r"""\btype\s*=\s*["']application/ld\+json["']""", re.I)
DATETIME_TZ_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_OR_DT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$"
)

FMT_TEXT = "non-empty string"
FMT_URL = "http(s) URL, or a list of those"
FMT_DATETIME_TZ = (
    "ISO 8601 date-time with timezone offset "
    "(e.g. 2026-11-08T14:03:00Z or 2026-11-08T14:03:00+00:00)"
)
FMT_DATE_OR_DT = "ISO 8601 date or date-time (YYYY-MM-DD, or date-time with timezone)"
FMT_INT = "integer"
FMT_PRICE = "number or numeric string"
FMT_CURRENCY = "ISO 4217 currency code (e.g. USD)"
FMT_QUESTION = "Question object (name + acceptedAnswer)"
FMT_ANSWER = "Answer object (text)"
FMT_LIST_ITEM = "list of ListItem objects"
FMT_OFFER = "Offer object (price, and priceCurrency)"
FMT_KNOWN_TYPE = "a @type this checker covers"


def is_text(value):
    return isinstance(value, str) and bool(value.strip())


def is_url(value):
    if isinstance(value, list):
        return bool(value) and all(is_url(item) for item in value)
    return isinstance(value, str) and re.match(r"^https?://\S+$", value.strip()) is not None


def is_datetime_tz(value):
    if not isinstance(value, str) or not DATETIME_TZ_RE.match(value.strip()):
        return False
    try:
        datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def is_date_or_datetime(value):
    if not isinstance(value, str) or not DATE_OR_DT_RE.match(value.strip()):
        return False
    text = value.strip()
    if DATE_RE.match(text):
        try:
            datetime.date.fromisoformat(text)
            return True
        except ValueError:
            return False
    return is_datetime_tz(text)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_price(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str) and re.match(r"^\d+(?:\.\d+)?$", value.strip()):
        return True
    return False


def price_is_zero(value):
    try:
        return float(value) == 0
    except (TypeError, ValueError):
        return False


def is_currency(value):
    return isinstance(value, str) and re.match(r"^[A-Z]{3}$", value.strip()) is not None


def type_name(value):
    if isinstance(value, str) and "/" in value:
        return value.rstrip("/").rsplit("/", 1)[-1]
    return value


def types_of(node):
    raw = node.get("@type")
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    return [type_name(item) for item in items if isinstance(item, str) and item]


def iter_nodes(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from iter_nodes(item)
        return
    if not isinstance(obj, dict):
        return
    if "@graph" in obj:
        yield from iter_nodes(obj["@graph"])
    if "@type" in obj:
        yield obj
    for key, value in obj.items():
        if key in {"@graph", "@type", "@context", "@id"}:
            continue
        yield from iter_nodes(value)


def html_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in {".git", "node_modules"})
        for name in sorted(filenames):
            if name.lower().endswith((".html", ".htm")):
                out.append(os.path.join(dirpath, name))
    return out


def ld_blocks(text):
    blocks = []
    for match in SCRIPT_RE.finditer(text):
        if TYPE_ATTR_RE.search(match.group(1) or ""):
            blocks.append(match.group(2))
    return blocks


def parse_block(raw):
    text = raw.strip()
    if not text:
        raise ValueError("empty JSON-LD block")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(htmlmod.unescape(text))


def miss(page, typ, field, expected):
    fail(f"{page} @{typ} {field}", f"expected {expected}")


def check_offer(page, typ, field, value):
    if not isinstance(value, dict) or type_name(value.get("@type") or "Offer") not in {"Offer", None}:
        # Accept an Offer object even if @type is omitted, as long as price is present.
        if not isinstance(value, dict):
            miss(page, typ, field, FMT_OFFER)
            return
    if not is_price(value.get("price")):
        miss(page, typ if typ == "Offer" else typ, "price" if typ == "Offer" else f"{field}.price", FMT_PRICE)
        return
    currency = value.get("priceCurrency")
    if currency is None and price_is_zero(value.get("price")):
        return
    if not is_currency(currency):
        miss(page, typ if typ == "Offer" else typ, "priceCurrency" if typ == "Offer" else f"{field}.priceCurrency", FMT_CURRENCY)


def check_node(page, node):
    kinds = types_of(node)
    if not kinds:
        return
    for typ in kinds:
        checker = TYPE_CHECKS.get(typ)
        if checker is None:
            miss(page, typ, "@type", FMT_KNOWN_TYPE)
            continue
        checker(page, typ, node)


def check_video_object(page, typ, node):
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    if not is_text(node.get("description")):
        miss(page, typ, "description", FMT_TEXT)
    if not is_url(node.get("thumbnailUrl")):
        miss(page, typ, "thumbnailUrl", FMT_URL)
    if not is_datetime_tz(node.get("uploadDate")):
        miss(page, typ, "uploadDate", FMT_DATETIME_TZ)


def check_organization(page, typ, node):
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    if not is_url(node.get("url")):
        miss(page, typ, "url", FMT_URL)
    if "logo" in node and not is_url(node.get("logo")):
        miss(page, typ, "logo", FMT_URL)


def check_website(page, typ, node):
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    if not is_url(node.get("url")):
        miss(page, typ, "url", FMT_URL)


def check_software_application(page, typ, node):
    # Google's Software App rich result also wants offers, aggregateRating, or
    # review. seo_common.software() deliberately has no offers block, so this
    # check requires name plus the fields that generator always emits.
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    if typ == "SoftwareApplication":
        if not is_text(node.get("description")):
            miss(page, typ, "description", FMT_TEXT)
        if not is_text(node.get("applicationCategory")):
            miss(page, typ, "applicationCategory", FMT_TEXT)
        if not is_text(node.get("operatingSystem")):
            miss(page, typ, "operatingSystem", FMT_TEXT)
        return
    # MobileApplication and WebApplication on this site include offers.
    if not is_text(node.get("applicationCategory")):
        miss(page, typ, "applicationCategory", FMT_TEXT)
    if not is_text(node.get("operatingSystem")):
        miss(page, typ, "operatingSystem", FMT_TEXT)
    if "offers" not in node:
        miss(page, typ, "offers", FMT_OFFER)
    else:
        check_offer(page, typ, "offers", node.get("offers"))


def check_faq_page(page, typ, node):
    entity = node.get("mainEntity")
    if not isinstance(entity, list) or not entity:
        miss(page, typ, "mainEntity", FMT_QUESTION + " list")
        return
    for item in entity:
        if not isinstance(item, dict) or "Question" not in types_of(item):
            miss(page, typ, "mainEntity", FMT_QUESTION)


def check_question(page, typ, node):
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    answer = node.get("acceptedAnswer")
    if not isinstance(answer, dict) or ("Answer" not in types_of(answer) and "text" not in answer):
        miss(page, typ, "acceptedAnswer", FMT_ANSWER)


def check_answer(page, typ, node):
    if not is_text(node.get("text")):
        miss(page, typ, "text", FMT_TEXT)


def check_item_list(page, typ, node):
    items = node.get("itemListElement")
    if not isinstance(items, list) or not items:
        miss(page, typ, "itemListElement", FMT_LIST_ITEM)
        return
    for item in items:
        if not isinstance(item, dict) or "ListItem" not in types_of(item):
            miss(page, typ, "itemListElement", FMT_LIST_ITEM)


def check_list_item(page, typ, node):
    if not is_int(node.get("position")):
        miss(page, typ, "position", FMT_INT)
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    if "item" not in node and "url" not in node:
        miss(page, typ, "item or url", FMT_URL)
    else:
        target = node.get("item", node.get("url"))
        if isinstance(target, dict):
            if not (is_url(target.get("@id")) or is_url(target.get("url")) or is_text(target.get("name"))):
                miss(page, typ, "item", FMT_URL)
        elif not is_url(target):
            miss(page, typ, "item" if "item" in node else "url", FMT_URL)


def check_web_page(page, typ, node):
    if not is_text(node.get("name")):
        miss(page, typ, "name", FMT_TEXT)
    if not is_url(node.get("url")):
        miss(page, typ, "url", FMT_URL)
    for field in ("datePublished", "dateModified"):
        if field in node and not is_date_or_datetime(node.get(field)):
            miss(page, typ, field, FMT_DATE_OR_DT)


def check_contact_point(page, typ, node):
    if not is_text(node.get("contactType")):
        miss(page, typ, "contactType", FMT_TEXT)


def check_offer_type(page, typ, node):
    check_offer(page, typ, "price", node)


TYPE_CHECKS = {
    "VideoObject": check_video_object,
    "Organization": check_organization,
    "WebSite": check_website,
    "SoftwareApplication": check_software_application,
    "MobileApplication": check_software_application,
    "WebApplication": check_software_application,
    "FAQPage": check_faq_page,
    "Question": check_question,
    "Answer": check_answer,
    "BreadcrumbList": check_item_list,
    "ItemList": check_item_list,
    "ListItem": check_list_item,
    "WebPage": check_web_page,
    "CollectionPage": check_web_page,
    "ContactPoint": check_contact_point,
    "Offer": check_offer_type,
}


def check_tree(root):
    rel_root = os.path.relpath(root, ROOT) if os.path.abspath(root).startswith(ROOT + os.sep) else root
    if not os.path.isdir(root):
        fail(rel_root, "directory missing; build dist/ first")
        return
    files = html_files(root)
    if not files:
        fail(rel_root, "no HTML files")
        return
    pages = 0
    nodes = 0
    kinds = set()
    before = len(fails)
    for path in files:
        rel = os.path.relpath(path, root)
        try:
            text = open(path, encoding="utf-8").read()
        except OSError as exc:
            fail(rel, str(exc))
            continue
        blocks = ld_blocks(text)
        if not blocks:
            continue
        pages += 1
        for raw in blocks:
            try:
                data = parse_block(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                fail(rel, f"invalid JSON-LD: {exc}")
                continue
            for node in iter_nodes(data):
                nodes += 1
                kinds.update(types_of(node))
                check_node(rel, node)
    if len(fails) == before:
        ck(
            f"structured data in {rel_root}",
            True,
            f"{pages} pages, {nodes} nodes, {len(kinds)} types",
        )


check_tree(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist"))
finish()
