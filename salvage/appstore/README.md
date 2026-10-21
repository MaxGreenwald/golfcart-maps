# Golf Cart Maps: App Store 1.0 prep (Oct 18, 2026)
ASC app 6823958385, version 1.0 (5eff07f6-…), PREPARE_FOR_SUBMISSION. Nothing submitted, no build attached.

## Set in ASC via API
- Subtitle, description, keywords, promo text, support + marketing URL (https://golfcartmap.com/), privacy URL (https://golfcartmap.com/privacy), copyright "2026 Matchimus LLC" (listing.json, description.txt)
- Category: Navigation, secondary Travel
- Age rating: every answer None/No -> 4+
- Content rights: uses third-party content with rights (OpenStreetMap ODbL, DOE AFDC)
- Review contact Max Greenwald / max@golfcartmap.com / +1 303 887 7689, no demo account, notes = review_notes.txt
- Price $0 (USA base), availability: United States only, new territories off
- Screenshots: 5 x iPhone 6.9" (1320x2868) and 5 x iPad 13" (2064x2752), all COMPLETE
- Export compliance: Info.plist already has ITSAppUsesNonExemptEncryption=false; build 12 reports usesNonExemptEncryption=false

## App Privacy (web UI only): answers
Assumes the iOS build includes branch appstore-fixes (no paywall/restore in iOS).
- "Do you or your third-party partners collect data from this app?" -> **No, we do not collect data from this app** -> label "Data Not Collected".
  Why: no accounts, ads, analytics or SDKs in the iOS app; location is used on-device only; routing runs on-device;
  "Report a problem" opens the user's own Mail app; OSM tiles / Photon search requests are served in real time and not retained by us.
- If build 12 as-is (Stripe restore-by-email still in iOS) were submitted instead: Contact Info > Email Address,
  purpose App Functionality, linked to the user, not used for tracking.
- If analytics (D1 / Cloudflare) is ever added to the native app: Usage Data > Product Interaction, Analytics, not linked, not tracking.
