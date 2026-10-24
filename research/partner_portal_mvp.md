# Partner portal MVP (Oct 24 2026)

Design-partner admin for golf cart rental shops: Max invites a shop, the owner brands `/p/<slug>`, picks a city (San Diego default), adds ordered experience stops and affiliate offers (larger map pins + optional coupons), and hands renters an access code after charging $5–10 in the shop’s own checkout. No Stripe / consumer paid plan.

## URLs

| Who | Path |
|-----|------|
| Super / shop admin | `/partner` |
| Brand teaser | `/p/<slug>` |
| Renter unlock | `/p/<slug>/go?code=CODE` |
| Full city map with overlays | `/map/<cityslug>?partner=<slug>&code=CODE` |
| API (same origin) | `/api/partner/*` → `gcm-partner[-preview]` Worker |

Brand pages use `/p/<slug>` on purpose: bare `/<slug>` is already the SEO city page.

## Stack

- Cloudflare Pages static UI under `public/partner/` and `public/p.html + public/p.js `
- Pages Function proxy: `functions/api/partner/[[path]].js`
- Worker + SQLite Durable Object: `workers/partner/` (same pattern as `gcm-analytics`)
- Shared helpers: `lib/partner.js` (slug rules, codes)

## Auth

1. **Google OAuth** when `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` are set on the Worker. Redirect URI: `{PUBLIC_ORIGIN}/api/partner/auth/callback`.
2. **Mock / preview login** when those secrets are absent and `DEV_AUTH_EMAIL` is set (default on preview: `maxgreenwald.assistant@gmail.com`). `POST /api/partner/auth/dev` with `{ "email": "…" }`. Invite accept: also pass `"expect": "<invited email>"` or `"invite": "<token>"`.

Super-admin allowlist (`SUPER_ADMINS` var): `max@golfcartmap.com`, `maxgreenwald.assistant@gmail.com`.

**Invite email:** MVP returns a one-time invite link from the super-admin UI; outbound email is not wired. Copy the link to the shop owner.

Session cookie: `gcm_partner` (HttpOnly, Secure, SameSite=Lax), HMAC with `PARTNER_SESSION_SECRET`.

## Env / secrets

Worker (`wrangler secret put NAME [--env preview]`):

| Name | Required | Purpose |
|------|----------|---------|
| `PARTNER_SESSION_SECRET` | yes (use any long random for preview) | Session HMAC |
| `GOOGLE_CLIENT_ID` | for real Google login | OAuth |
| `GOOGLE_CLIENT_SECRET` | for real Google login | OAuth |

Vars in `workers/partner/wrangler.toml`: `SUPER_ADMINS`, `DEV_AUTH_EMAIL`, optional `PUBLIC_ORIGIN`.

Pages may set `PARTNER_URL` to override the Worker base (default: `gcm-partner` on production host, `gcm-partner-preview` on `*.pages.dev`).

## Deploy (preview only — never production without Max)

```bash
# 1) Partner worker (preview)
cd workers/partner
# once: wrangler secret put PARTNER_SESSION_SECRET --env preview
npx wrangler@3 deploy --env preview

# 2) Pages preview from repo root
scripts/deploy_web.sh preview partner-portal-mvp
# → https://partner-portal-mvp.golfcart-maps.pages.dev/partner
```

Local UI (API still needs the Worker, or will 502):

```bash
python3 scripts/build_web.py
python3 scripts/serve_dist.py   # or any static server on dist/
```

## Click-through script (mock auth)

1. Open `/partner` → mock-login as `maxgreenwald.assistant@gmail.com`
2. Create shop (e.g. name “La Jolla Cart Co”, slug `lajollacartco`, city San Diego)
3. Invite `shopowner@gmail.com` → copy invite link
4. Sign out → open invite link → mock-login as that email with expect= → accept
5. Set brand, keep city `sd`, add experience (seals → cove), add affiliate with coupon
6. Generate access code → open renter link `/p/lajollacartco/go?code=…`
7. Confirm larger ★ affiliate pins + numbered stops; “Full city map” opens `/map/sandiego?partner=…&code=…`

## Tests

```bash
python3 -m unittest tests.test_partner_portal tests.test_region_urls tests.test_no_beta -q
```

## Honest status

| Piece | Status |
|-------|--------|
| Super admin create/list/disable shop | Works (mock or Google) |
| Invite link | Works; **email send stubbed** (copy link) |
| Shop brand + city select | Works |
| Experiences CRUD | Works (lat/lon form; no drag-map editor yet) |
| Affiliates + coupon | Works; larger ★ pins on renter + full map |
| Renter code unlock | Works (multi-use, optional expiry) |
| Full map city lock + overlays | Works via `?partner=&code=` |
| Google OAuth | Wired; needs secrets |
| Production deploy | **Not done** — Max approval required |
| Shop checkout / $5–10 charge | Out of scope (shop’s app) |
