# Golf Cart Maps 1.0: App Store submit checklist (Oct 18, 2026, 9:40 PM ET)

ASC app 6823958385 · version 1.0 (5eff07f6-…) · state PREPARE_FOR_SUBMISSION · bundle com.matchimus.golfcartmaps

## Status
| Item | State |
|---|---|
| App Store fixes in the iOS build (hide BETA badges, charger paywall/restore, Venmo tip, **Risky mode**; native share + haptics; bundled Leaflet) | merged to master 5e96be4, ios-release 18ab57d; test_appstore.py ALL PASS; web unchanged |
| iPhone-only (TARGETED_DEVICE_FAMILY=1), arm64 | in ios-release (ios-appstore-fixes) |
| Analytics in the native app + CarPlay hooks | in ios-release (ios-analytics); simulator check passed (GCMTrack session ok, route_started ok) |
| New TestFlight build (16) with all of the above | building from ios-release 18ab57d (push 9:35 PM ET) |
| Metadata, keywords, screenshots, age rating 4+, price $0 US only, export compliance | set via API (README.md) |
| Review notes | **updated via API Oct 18** (analytics disclosed, Golf cart mode, no risky haptic) |
| Listing copy | no "free", no "verified"; name "Golf Cart Maps" (unchanged) |
| **App Privacy labels** | **NOT SET. No public ASC API exists** (GET /v1/apps/{id}/dataUsages -> 404 "relationship does not exist"); website only. Required before submit. |
| Submit | blocked on App Privacy |

## App Privacy answers (App Store Connect website > App > App Privacy > Get Started / Edit)
1. "Do you or your third-party partners collect data from this app?" -> **Yes, we collect data from this app**
2. Data types: tick only
   - **Usage Data > Product Interaction**
   - **Identifiers > Device ID**
   (Nothing else: no Location (location stays on device), no Contact Info (no paywall/restore in iOS; "Report a problem" opens the user's own Mail app), no Diagnostics, no Search History (search text never leaves the device in analytics), no Purchases.)
3. For **Product Interaction**: purpose **Analytics** only · Linked to the user? **No** · Used for tracking? **No**
4. For **Device ID**: purpose **Analytics** only · Linked to the user? **No** · Used for tracking? **No**
5. Publish. Resulting label: "Data Not Linked to You: Usage Data, Identifiers". Privacy policy URL already https://golfcartmap.com/privacy (live, effective Oct 18, 2026, describes these events).

Why: track.js sends session / town_viewed / route_searched / route_started / route_completed / road_report_filed with a random
install ID (localStorage) and session ID, town level only, no coordinates, IP not stored, no ads/SDKs, never shared or sold.

## Submit (one command once App Privacy is published and build 16 is VALID)
```
/workspace/ascapi/.venv/bin/python /workspace/gcm-appstore/submit.py            # attaches newest VALID build >= 16, prints it
/workspace/ascapi/.venv/bin/python /workspace/gcm-appstore/submit.py --submit   # creates the review submission and submits
```
Check afterwards: `python3 /workspace/ascapi/q.py GET /v1/apps/6823958385/appStoreVersions` -> WAITING_FOR_REVIEW.

## Before pressing submit
- [x] Build 16 VALID, attached to 1.0 (export compliance set) 9:45 PM ET
- [ ] Real-phone smoke test of build 16 via TestFlight: no BETA, no Risky chip, no chargers/Venmo, share sheet works, Settings > Golf cart mode works, location prompt
- [ ] App Privacy published (above)
- [ ] Max's OK (given 9:15 PM ET for fixes + submit)

## Notes / risks
- Apple warns on every build: ITMS-90068, deployment target iOS 14.0; iOS 15+ required from April 2027. Not blocking now.
- Copyright still "2026 Matchimus LLC" and seller is Max Greenwald (individual account). Naming plan leaves the listing alone for now.
- Description says green = legal for "your cart or low-speed vehicle" at 35 mph or under; the app defaults to LSV rules, with Golf cart mode in
  Settings. Consider adding one line: "Plain golf carts: turn on Golf cart mode in Settings for stricter limits (25 mph in California)." (not changed)
- CarPlay entitlement not granted, so build 16 ships without CarPlay (entitlement gated off in the workflow).
