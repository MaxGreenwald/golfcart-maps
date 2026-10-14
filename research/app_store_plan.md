# Golf Cart Maps — App Store / Play Store plan (branch `native-app`)

## Done (on the box, committed locally, not pushed)
- Capacitor 7 project: `capacitor.config.json` (appId `com.matchimus.golfcartmaps`, name "Golf Cart Maps", webDir `public/`, so the app bundles the site and all road data offline-by-default).
- Plugins installed: @capacitor/geolocation, @capacitor/share, @capacitor/haptics (not yet wired into app.js — see 4.2 list).
- `android/` and `ios/` platforms added. iOS `Info.plist` has `NSLocationWhenInUseUsageDescription`; Android manifest has COARSE/FINE location (GPS feature optional).
- Icons + splash generated from `public/icon-512.png` (source in `assets/`; regenerate with `npm run assets`). Note: source is only 512px upscaled to 1024 — replace `assets/icon.png` with a true 1024×1024 master before submission.
- **Android debug APK built on the box**: `/workspace/golfcart-maps-debug.apk` (~10 MB). Sideload to an Android phone to test.
- `.github/workflows/native-build.yml` (manual trigger): Android debug APK on ubuntu, unsigned iOS simulator build on `macos-14` — the no-Mac cloud build path.
- Note: existing `navigator.geolocation` already works inside the Capacitor WebView once permissions exist; the plugin gives better permission prompts/background handling.

## Needs a Mac or the Apple account
- iOS compile/sign/upload needs Xcode → use the GitHub Actions macOS runner (free minutes on public repo; ~10× minutes on private) or Codemagic (500 free build min/mo, handles signing + TestFlight upload). Fastlane `match` + App Store Connect API key stored as repo secrets.
- Apple Developer Program enrollment (Max's legal name, 2FA on his iPhone, $99/yr). Convert to Matchimus LLC later via Apple Support with D-U-N-S.
- Register bundle id, create App Store Connect record, API key (.p8) for CI.
- Device testing: TestFlight on Max's iPhone (no Mac needed).

## Guideline 4.2 (minimum functionality) — native touches to add before review
1. Offline region data: data already bundled; add "Download region" + offline map tiles cache (OSM tile policy forbids bulk prefetch — use a licensed provider e.g. MapTiler/Protomaps PMTiles for offline).
2. Native geolocation via @capacitor/geolocation with follow-me mode, heading.
3. Native share sheet (@capacitor/share) for a route/place link.
4. Haptics on turn alerts / when route enters a forbidden road.
5. Turn-by-turn voice guidance / "approaching 40 mph road" alerts (strongest differentiator).
6. Saved places (home/rental shop), dark mode, city picker (ties to expansion plan).
7. No external-browser-only flows; hide the Venmo donate link in iOS (could trip 3.1.1 in-app purchase rules).

## Draft App Store listing
- **Name:** Golf Cart Maps
- **Subtitle (≤30):** Cart-legal routes in San Diego
- **Keywords (≤100):** golf cart,LSV,low speed vehicle,cart route,street legal,NEV,Coronado,Carlsbad,beach,map
- **Description:** Golf Cart Maps (beta) shows which streets are legal for golf carts and low-speed vehicles, and routes you around roads posted 40 mph or higher. Built from OpenStreetMap, street-sign imagery and city speed-limit changes, covering coastal San Diego County from Imperial Beach to Oceanside. Search a destination, see your location, and get a cart-friendly route. This is a beta: always obey posted signs and local laws; road data can be wrong — report fixes in the app. (No "free" promise.)
- **Support URL:** https://golfcartmap.com (add a /support or mailto contact section). **Marketing URL:** https://golfcartmap.com
- **Privacy policy URL:** https://golfcartmap.com/privacy (page needs to be created — text below).
- **Category:** Navigation (secondary Travel). **Age rating:** all "None" answers → 4+. No unrestricted web access (links open externally), no UGC, no gambling, no mature content.
- **App Privacy (nutrition label):** "Data Not Collected" is defensible — see audit below.
- **Screenshots plan:** iPhone 6.9" (1320×2868) and 6.5" required; 5 shots: (1) map overview green/red streets, (2) route Coronado → beach, (3) search, (4) locate-me, (5) legend / speed-limit explanation. Generate from the existing Playwright screenshot setup at phone viewport; add caption overlays. Play: 2+ phone shots + 512 icon + 1024×500 feature graphic (reuse og image).

### What the app actually sends (audit of public/app.js / index.html)
- No analytics, cookies, accounts, or tracking. Location used on-device only for the blue dot/routing; never sent to our server.
- Third parties contacted: OpenStreetMap tile servers (map area viewed), Photon (komoot) and Nominatim for search text + map center, Google Fonts, unpkg (Leaflet). Bundle Leaflet + fonts locally in the app to cut these.

### Privacy policy text (draft)
> Golf Cart Maps does not collect, store, or sell personal data. There are no accounts and no analytics. If you allow location access, your location is used only on your device to show your position and plan routes; it is never sent to us. Map images are loaded from OpenStreetMap servers, and text you type into search is sent to the Photon and Nominatim geocoding services to find places; those services receive your IP address under their own privacy policies. Questions: maxgreenwald.assistant@gmail.com. Last updated: Oct 2026.

## Submission checklist
### Apple
1. Enroll in Apple Developer Program (Max, 2FA, $99/yr).
2. Certificates, Identifiers & Profiles → register `com.matchimus.golfcartmaps`.
3. App Store Connect → New App; create API key; add secrets to GitHub (or connect Codemagic).
4. Implement 4.2 native touches; publish privacy page.
5. CI: signed archive → upload to TestFlight; test on iPhone.
6. Fill listing, privacy label, age rating, screenshots, export compliance (uses only standard HTTPS → exempt).
7. Submit for review with notes explaining LSV-routing purpose and offline data.
### Google Play
1. Play Console account ($25 one-time). New personal accounts must run a closed test with ≥12 testers for 14 days before production.
2. Create upload keystore; build signed AAB (`./gradlew bundleRelease`), enroll Play App Signing.
3. Data safety form (no data collected/shared; location on-device), content rating (IARC → Everyone), target audience, privacy URL.
4. Internal → closed test → production.

## Costs
- Apple Developer Program: $99/year. Google Play: $25 one-time. CI: GitHub Actions macOS minutes (free tier/paid) or Codemagic free tier. Optional offline tile provider (MapTiler free tier / Protomaps self-hosted).

## CarPlay (branch `carplay`, built Oct 13 2026)
Branch `carplay` = `native-app` + `multi-region` merged + CarPlay. CI workflow `.github/workflows/carplay-ios.yml` (macos-15, runs on every push to `carplay`).

**Architecture (why):** the routing engine stays in one place, the web app's JS (`public/app.js` A* + rules + region data). `public/carplay.js` exposes `window.GCMCarPlay` (`status`, `setMode`, `plan`, `overlay`, `search`) returning plain JSON. Native Swift calls it with `WKWebView.callAsyncJavaScript` (`ios/App/App/GCMBridge.swift`). No Swift port of the rules means CarPlay can never disagree with the phone/web map. If CarPlay launches without the phone UI, a headless Capacitor web view is parked inside the CarPlay window so JS keeps running. Tested in Chromium: `scripts/test_carplay.py` (SD + Villages, both modes, turns, overlay, search).

**Native pieces:**
- `Info.plist` `UIApplicationSceneManifest`: phone scene (`SceneDelegate`, Main storyboard) + `CPTemplateApplicationSceneSessionRoleApplication` (`CarPlaySceneDelegate`).
- `CarPlaySceneDelegate.swift`: MapKit `MKMapView` base map; `CPMapTemplate` with Search, Recent, mode button (LSV / Golf cart), recenter, legal-road layer toggle, zoom. Legal overlay: green OK / red avoid polylines for the visible area (hidden above ~8 km span). Trip preview: `CPTrip` + `CPRouteChoice` showing miles, risky count and battery round-trip check; Go → `CPNavigationSession` with `CPManeuver`s (left/right/slight/U-turn/arrive with SF Symbols, derived from street-name changes + bearings), estimates updated from GPS, advance at 25 m, auto-finish on arrival. Search: region POIs + street names first, then Apple Maps `MKLocalSearch`. Recents saved in UserDefaults.
- `App.entitlements`: `com.apple.developer.carplay-maps` (wired via `CODE_SIGN_ENTITLEMENTS`).

**Steps to ship CarPlay:**
1. Wait for Apple to finish the ID review (developer account active).
2. Submit the CarPlay Navigation entitlement request (draft: `research/carplay_request.md`). Apple can take weeks; approval is not guaranteed.
3. After approval: in Certificates, Identifiers & Profiles enable CarPlay Navigation on the `com.matchimus.golfcartmaps` App ID, regenerate the provisioning profile (it must include the entitlement).
4. Add signing secrets to CI (App Store Connect API key + cert/profile or fastlane match), build signed archive → TestFlight.
5. Test on a real CarPlay head unit / cart screen (DACH Apollo etc.) and in Xcode's CarPlay Simulator.

**Verified in CI (run 38511945626, macos-15, Xcode iOS 18.5 simulator):** unsigned build passes; ad-hoc simulator build embeds `com.apple.developer.carplay-maps`; app launches on iPhone sim, appears on the CarPlay external display, CarPlay demo hook (`-GCMCarPlayDemo YES`, DEBUG only) plans La Jolla → Crystal Pier through the JS router (3.4 mi, round trip 6.8 mi, battery OK 23%), shows the trip preview and starts guidance ("Turn left onto Draper Avenue", next "Bonair Way") with the green/red legal overlay. Screenshots are uploaded as the `carplay-shots` artifact.
Fixes found on the way: Swift `callAsyncJavaScript` (Result overlay) links `libswiftWebKit.dylib` and crashed at launch on iOS 18 → bridge uses `evaluateJavaScript` + a `WKScriptMessageHandler`; CarPlay template calls with nil completion throw on error → all calls pass completion blocks.

**Remaining work / known gaps:**
- Voice prompts (AVSpeechSynthesizer) and lane/turn distance callouts; rerouting when off-route (currently no auto-reroute; choose destination again).
- Maneuver extraction is name-change based; unnamed service roads produce extra "continue" steps. Consider merging short unnamed segments.
- Real CarPlay panning (`mapTemplate(_:panWith:)`), dashboard (`CPTemplateApplicationDashboardScene`) and instrument cluster support.
- Base map is Apple Maps (MapKit) on CarPlay vs OSM tiles on the phone; fine for now, MapLibre native later if we need offline tiles.
- Headless web view path (CarPlay-only launch) needs a real device test.
- The scene manifest switches the phone app to scene lifecycle; regression-test deep links/share on device.

## Android Auto (follow-on)
Android Auto navigation apps use the Android for Cars App Library (`androidx.car.app`, `NavigationTemplate`, `RoutePreviewNavigationTemplate`, `Trip`/`Step`/`Maneuver`) and need the `androidx.car.app.category.NAVIGATION` category; Google reviews them during Play submission (no separate entitlement request, but the Play closed-test rule still applies). Same design: a `CarAppService` calls `window.GCMCarPlay` in the Capacitor web view (`evaluateJavascript`) for routes, draws the map on the `SurfaceCallback` surface. Plan after CarPlay is approved and the Play account exists.
