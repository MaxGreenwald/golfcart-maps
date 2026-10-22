# Town pages (Gary's copy goes here)
One JSON file per town: `content/towns/<region-slug>/<town-slug>.json`, rendered at build time to `/<region-slug>/<town-slug>`
by `scripts/seo_towns.py` (called from build_web.py). Schema (all strings plain text):

    { "slug", "region" (region slug), "name", "state", "question_title" (the H1, a question),
      "answer_short" (<=60 words), "golf_cart": {"allowed", "roads", "speed_line", "notes"}, "lsv": {...same},
      "rules": [{"topic","rule","citation","source_url"}], "banned_roads": [{"name","rule","crossings_ok"}],
      "faq": [{"q","a"}], "rental_shops": [{"name","url"}], "nearby": [town slugs in the same region],
      "map_center": [lat, lng], "zoom", "published" (YYYY-MM-DD), "last_checked" (YYYY-MM-DD), "checked_by" }

The build fails on the words free / verified / CarPlay / Android, on an answer over 60 words, or a missing field.
The page says "Rules last checked {date}", never "verified". See content/towns/_example.json (rendered only to /_preview/).
