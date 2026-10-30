#!/usr/bin/env bash
# Set a partner shop's rental vehicle after the partner Worker with the `vehicle` field is deployed.
# Usage: GCM_PARTNER_SESSION='<gcm_partner cookie of a super-admin>' scripts/set_shop_vehicle.sh beachmode lsv [origin]
# Same change as: /partner as super-admin -> open the shop -> "Your rental vehicles" -> Save brand.
set -euo pipefail
slug="${1:?slug}"; veh="${2:?golf_cart|lsv}"; origin="${3:-https://golfcartmap.com}"
case "$veh" in golf_cart|lsv) ;; *) echo "vehicle must be golf_cart or lsv" >&2; exit 2;; esac
: "${GCM_PARTNER_SESSION:?set GCM_PARTNER_SESSION to a super-admin gcm_partner cookie}"
ck="Cookie: gcm_partner=$GCM_PARTNER_SESSION"
sid=$(curl -fsS -H "$ck" "$origin/api/partner/admin/shops" | python3 -c "import json,sys;print(next(s['id'] for s in json.load(sys.stdin)['shops'] if s['slug']=='$slug'))")
curl -fsS -X PATCH -H "$ck" -H 'content-type: application/json' -d "{\"vehicle\":\"$veh\"}" "$origin/api/partner/admin/shops/$sid" >/dev/null
got=$(curl -fsS "$origin/api/partner/public/$slug" | python3 -c "import json,sys;print(json.load(sys.stdin)['shop'].get('vehicle'))")
echo "$slug vehicle=$got"
[ "$got" = "$veh" ]
