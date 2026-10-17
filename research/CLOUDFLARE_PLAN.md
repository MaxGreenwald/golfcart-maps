# Cloudflare Pages migration plan
1. Max: create Cloudflare account (free plan), add site golfcartmap.com. CF imports GoDaddy DNS; check it matches (apex A 185.199.108-111.153, www CNAME maxgreenwald.github.io).
2. Max: `npx wrangler login` on the box (browser OAuth), or create a scoped API token (Pages:Edit) for the agent.
3. Create Pages project `golfcart-maps`, Direct Upload: `npx wrangler pages deploy public --project-name golfcart-maps --branch main`. Verify on *.pages.dev (sw.js headers, tiles, routing).
4. Pages > Custom domains: add golfcartmap.com and www (only activates once CF is authoritative). Add a Redirect Rule www -> apex.
5. Max at GoDaddy: change nameservers ns45/ns46.domaincontrol.com -> the two CF nameservers. Keep DNS records pointing at GitHub during propagation = zero downtime; then CF flips apex/www to Pages.
6. Verify (curl -I headers, SW update, iPhone home-screen app). Keep gh-pages + CNAME untouched as fallback for ~2 weeks; rollback = repoint DNS records to GitHub IPs.
