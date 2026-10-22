"""ONE place for the status / price wording on the generated web pages (landing, region, compare, footer, llms.txt).
Max, Oct 22: "Drop beta everywhere and say 'Free to use'". tests/test_no_beta.py keeps 'beta' out of everything users see."""
COST_Q = "What does Golf Cart Maps cost?"                      # landing FAQ + FAQPage schema
COST_A = "Free to use."
STATUS_PHRASE = "free to use"                                   # llms.txt tagline, /compare intro
LANDING_DESC_TAIL = " Free to use."                             # landing <meta description>/og:description
FOOTER_STATUS = " is free to use"                               # every SEO page footer
COMPARE_PRICE = "Free to use"                                   # /compare table, our row
