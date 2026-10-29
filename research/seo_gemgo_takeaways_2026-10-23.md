# Why GEM Go (and 4 cart apps) show up in Google's AI Overview for "lsv map app", and we don't

Checked 2026-10-23 ~12:05 PM PT. Max searched "lsv map app"; the AI Overview listed GEM Go, CartPath, Cruze Cart,
Waddle Nav and SlowGo. Sources: rendered HTML of each page fetched with headless Chromium today, plus the GEM press release.

## GEM Go — https://www.gemcar.com/gem-go/

| Element | What it has |
|---|---|
| `<title>` | `Low-Speed Road Web App \| GEM Go` |
| meta description | "Explore U.S. roadways 35 mph or less with GEM Go. Enter your city, address or drop a pin to see where you can go in your low-speed vehicle." |
| **robots** | **`noindex, nofollow`** — the page itself asks Google not to index it |
| H1s | "Gem Go is currently under maintenance" (tool is down today), "Low-Speed Road Interactive Map" |
| Body | ~3 sentences: "More than half of U.S. roadways are 35 mph or less… GEM Low-speed vehicles (LSVs) are street legal on most U.S. roads 35 mph or less, travel at a top speed of 25 mph… Speed limit data provided by TomTom." |
| Schema | Yoast default only: WebPage, BreadcrumbList, WebSite, Organization ("GEM Electric Vehicles"). **No SoftwareApplication, no FAQPage.** |
| FAQ | None on the page |
| Tool | lives at go.gemcar.com (cert error today) |

**Takeaway: GEM Go is not in the AI Overview because of its page.** The page is noindex, has almost no copy, no app schema,
no FAQ, and the tool is in maintenance. It ranks on **off-page entity signals**:

1. **A syndicated press release that defines the thing in one sentence.** PR Newswire, Aug 15 2023: "GEM Go identifies nearby
   roads with posted speed limits of 35 mph or lower, which are legal for low-speed vehicle (LSV) operation in most communities…
   GEM Go is a free web-based, mobile-friendly, interactive mapping app." Copied verbatim by waevinc.com, dealer blogs
   (Briggs Equipment), Instagram, and a Russian GEM distributor. LLMs quote that sentence back almost word for word.
2. **"First-ever low-speed road app" framing** — a category-defining claim that gets repeated.
3. **Brand authority**: GEM (Polaris heritage, 65,000+ LSVs sold) is a known entity for "LSV"; the AI trusts a manufacturer on LSV rules.
4. **The exact query words**: "low-speed", "LSV", "app", "map", "35 mph or less", "street legal" — all in one short definitional sentence.
5. **Hedged accuracy**: "street legal on **most** U.S. roads 35 mph or less" — true, quotable, not overclaimed.

## The other four (brief skim)

| App | Title / H1 | Meta / lead | Schema | FAQ | Distribution |
|---|---|---|---|---|---|
| CartPath (cartpath.me) | "CartPath - Golf Cart & LSV Navigation App" / "Golf cart and LSV navigation that keeps you on legal roads." | "finds routes on roads with speed limits of 35 mph or less… golf cart, LSV, or NEV" | SoftwareApplication (description, installUrl = App Store, screenshots, offers) + Organization + WebSite | 9 Qs (golf cart vs LSV, accuracy, coverage…) | Live App Store listing "Turn-by-Turn GPS for LSVs"; /compare page "CartPath vs Google Maps for Golf Carts" |
| SlowGo (slowgoapp.com) | "SlowGo — Golf Cart GPS · Life's better at 15 mph." | "Free golf cart and LSV navigation for iPhone. Routes on roads posted 35 mph and under in Florida, Georgia and Arizona." | Organization, WebSite, SoftwareApplication, **FAQPage with 17 Qs** | 17 | App Store, CarPlay; a "short version" definitional paragraph ("SlowGo is a golf cart GPS — a navigation app for golf carts, LSVs, and NEVs…") |
| Waddle Nav (waddlenav.com) | title just "Waddle Nav" / "Golf cart and LSV navigation that sticks to roads you can legally drive." | no meta description | none found | 5 Qs, incl. "What's the difference between a golf cart and an LSV?" | Not shipped yet (says "in beta", App Store "in the next 30 days"); LinkedIn: "the first navigation app designed for LSVs and golf carts" |
| Cruze Cart (cruzecart.com) | "Cruze Cart — Free Golf Cart Navigation App \| GPS Map & Turn-by-Turn Directions" | "only low-speed streets (35 mph or less) are used" | (site blocked our headless fetch; content via search index) | yes | Live App Store + Google Play, city page /peachtree-city |

## Patterns that get an app into the AI Overview for "LSV map app"

1. **One definitional sentence** with the query words: "<Name> is a <golf cart / LSV> <map / navigation> app that shows/routes
   on roads posted 35 mph or less." Every one of the five has it in the title, meta, H1 or first paragraph.
2. **"Golf cart *and LSV*" in the title.** CartPath and Cruze Cart put the category in `<title>`; we said "Golf Cart Maps" + "LSV Roads".
3. **App entity signals**: live App Store / Play listings (CartPath, Cruze Cart, SlowGo), SoftwareApplication schema with
   description + installUrl. We can't claim an App Store listing until build 18 is approved.
4. **FAQPage schema answering "golf cart vs LSV" and "where can I drive"** (SlowGo 17, CartPath 9).
5. **Third-party mentions**: GEM's press release and dealer reposts; LinkedIn for Waddle. We have almost none.
6. **Hedged accuracy**: "most U.S. roads", "local rules win". AI Overviews prefer pages that don't overclaim.

## What we already beat them on (say it plainly)

Town-by-town rules, separate golf cart vs LSV rules, local bans with citations, 64 regions, a web map with no install. None of the five cite the law.

## What this branch (seo-map-maps) changes

- Home title "Golf Cart Map & LSV Map of Legal Roads by Town | Golf Cart Maps"; description "The golf cart map and LSV map app for N beach and golf towns…".
- New home section **"LSV map: roads posted 35 mph or less"** with the accurate limit (35 mph in 59 of 64 regions; 25 mph in NJ, Catalina, Gulf Shores; local bans win), computed from roadrule.js.
- FAQ + FAQPage: "Is there an LSV map app?", "Where can I drive my LSV?"; region and town pages: "Where can I drive my LSV in <place>?".
- SoftwareApplication schema: a definitional description ("Golf cart map and LSV map app: shows which roads golf carts and street-legal low speed vehicles (LSVs) may use in each town…") + keywords.
- llms.txt: intro "a golf cart map, LSV map and route planner…", plus an "LSV map (low speed vehicle map)" line.

## Not done here (needs Max / outside this branch)

- **A press release / launch post** with GEM's pattern (one definitional sentence, "35 mph or less", 64 towns, law cited), sent to cart/LSV trade press and dealers. This is likely the biggest lever, and it means sending things out, so Max decides.
- **App Store listing** subtitle with "Golf Cart & LSV Map" once build 18 is approved (and then installUrl in schema).
- A **/compare-style "Golf Cart Maps vs Google Maps for LSVs"** page, like CartPath's.
- Optional dedicated `/lsv-map` landing page targeting "LSV map app" / "low speed vehicle map" / "street legal golf cart map".
