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
