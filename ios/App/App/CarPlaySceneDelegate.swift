import UIKit
import CarPlay
import MapKit
import CoreLocation

// MARK: - Models decoded from GCMCarPlay.plan()

struct GCMManeuver {
    // meters = length of the road after this maneuver; toMeters = distance driven to reach it.
    // turn = signed turn angle in degrees (+ right, - left); used for the junction diagram and junctionExitAngle.
    let type: String, text: String, short: String, road: String, meters: Double, toMeters: Double, turn: Double, mph: Int?, risky: Bool, coord: CLLocationCoordinate2D
    let outBrg: Double?   // bearing of the road after this maneuver (turn advance, t451u)
    init?(_ d: [String: Any]) {
        guard let t = d["type"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return nil }
        type = t; text = d["text"] as? String ?? ""; road = d["road"] as? String ?? ""
        short = d["short"] as? String ?? text
        meters = (d["meters"] as? NSNumber)?.doubleValue ?? 0; risky = d["risky"] as? Bool ?? false
        toMeters = (d["toMeters"] as? NSNumber)?.doubleValue ?? 0
        turn = (d["turn"] as? NSNumber)?.doubleValue ?? 0
        outBrg = (d["outBrg"] as? NSNumber)?.doubleValue
        mph = (d["mph"] as? NSNumber)?.intValue
        coord = CLLocationCoordinate2D(latitude: lat, longitude: lon)
    }
    var isTurn: Bool { ["left", "right", "slight_left", "slight_right", "uturn"].contains(type) }
    var symbol: String {
        switch type {
        case "left": return "arrow.turn.up.left"
        case "right": return "arrow.turn.up.right"
        case "slight_left": return "arrow.up.left"
        case "slight_right": return "arrow.up.right"
        case "uturn": return "arrow.uturn.down"
        case "arrive": return "mappin.circle.fill"
        case "depart": return "location.north.fill"
        default: return "arrow.up"
        }
    }
    @available(iOS 17.4, *)
    var cpType: CPManeuverType {
        switch type {
        case "left": return .leftTurn
        case "right": return .rightTurn
        case "slight_left": return .slightLeftTurn
        case "slight_right": return .slightRightTurn
        case "uturn": return .uTurn
        case "arrive": return .arriveAtDestination
        case "depart": return .startRoute
        default: return .straightAhead
        }
    }
}

struct GCMPlan {
    let meters: Double, miles: Double, roundTrip: Double, minutes: Double
    let rangeStatus: String, rangePct: Int, rangeMi: Double, riskyCount: Int
    let line: [CLLocationCoordinate2D], maneuvers: [GCMManeuver]
    init?(_ any: Any?) {
        guard let d = any as? [String: Any], d["ok"] as? Bool == true else { return nil }
        meters = (d["meters"] as? NSNumber)?.doubleValue ?? 0
        miles = (d["miles"] as? NSNumber)?.doubleValue ?? 0
        roundTrip = (d["roundTripMiles"] as? NSNumber)?.doubleValue ?? 0
        minutes = (d["minutes"] as? NSNumber)?.doubleValue ?? 1
        let r = d["range"] as? [String: Any] ?? [:]
        rangeStatus = r["status"] as? String ?? "ok"; rangePct = (r["pct"] as? NSNumber)?.intValue ?? 0
        rangeMi = (r["eff"] as? NSNumber)?.doubleValue ?? 0
        riskyCount = (d["risky"] as? [Any])?.count ?? 0
        line = (d["line"] as? [[Double]] ?? []).compactMap { $0.count == 2 ? CLLocationCoordinate2D(latitude: $0[0], longitude: $0[1]) : nil }
        maneuvers = (d["maneuvers"] as? [[String: Any]] ?? []).compactMap(GCMManeuver.init)
    }
    /// average planned speed (m/s) used for per-maneuver time estimates
    var speed: Double { max(3, meters / max(60, minutes * 60)) }
    var rangeText: String {
        switch rangeStatus {
        case "ok": return "Round trip \(String(format: "%.1f", roundTrip)) mi · battery OK (\(rangePct)%)"
        case "tight": return "Round trip \(String(format: "%.1f", roundTrip)) mi · tight, charge first (\(rangePct)%)"
        default: return "Round trip \(String(format: "%.1f", roundTrip)) mi · not enough range (\(rangePct)%)"
        }
    }
}

final class RouteLine: MKPolyline {}
/// Finish-flag pin at the destination (t446u).
final class DestPin: MKPointAnnotation {}
final class OkLine: MKPolyline {}
final class AvoidLine: MKPolyline {}

// MARK: - Map view controller shown in the CarPlay window

final class CarPlayMapViewController: UIViewController, MKMapViewDelegate {
    let map = MKMapView()
    var onRegionChange: ((MKCoordinateRegion) -> Void)?
    var guiding = false { didSet { if guiding != oldValue { layoutMap(); refreshPuck() } } }
    override func viewDidLoad() {
        super.viewDidLoad()
        map.frame = view.bounds
        map.delegate = self
        map.showsUserLocation = true
        map.pointOfInterestFilter = .excludingAll
        view.addSubview(map)
    }
    // CarPlay shrinks the safe area when the maneuver panel or nav bar is showing. Size the map so its center
    // (where follow mode puts the location dot) sits in the uncovered part, a bit below the middle, while the
    // map still fills the whole screen.
    override func viewSafeAreaInsetsDidChange() { super.viewSafeAreaInsetsDidChange(); layoutMap() }
    override func viewDidLayoutSubviews() { super.viewDidLayoutSubviews(); layoutMap() }
    func layoutMap() {
        let b = view.bounds, safe = b.inset(by: view.safeAreaInsets)
        guard safe.width > 0, safe.height > 0 else { map.frame = b; return }
        let f = CarPlayStartView.mapFrame(bounds: b, safe: safe, guiding: guiding)
        if map.frame != f {
            map.frame = f
            #if DEBUG
            NSLog("GCMCarPlay layout bounds=%@ safe=%@ guiding=%d map=%@ dot=%@", NSCoder.string(for: b), NSCoder.string(for: safe), guiding ? 1 : 0, NSCoder.string(for: f), NSCoder.string(for: CGPoint(x: f.midX, y: f.midY)))
            #endif
        }
    }
    func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
        guard let pl = overlay as? MKPolyline else { return MKOverlayRenderer(overlay: overlay) }
        let r = MKPolylineRenderer(polyline: pl)
        switch pl {
        case is RouteLine: r.strokeColor = UIColor(red: 0.11, green: 0.44, blue: 0.88, alpha: 1); r.lineWidth = 7
        case is AvoidLine: r.strokeColor = UIColor(red: 0.9, green: 0.28, blue: 0.3, alpha: 0.7); r.lineWidth = 3
        default: r.strokeColor = UIColor(red: 0.07, green: 0.63, blue: 0.31, alpha: 0.8); r.lineWidth = 3
        }
        return r
    }
    func mapView(_ mapView: MKMapView, regionDidChangeAnimated animated: Bool) { onRegionChange?(mapView.region) }

    // MARK: map icon (Max t434u): during guidance the dot becomes the phone's icon, cart E or the user's photo.
    var puck: CarPlayPuckView?
    func mapView(_ mapView: MKMapView, viewFor annotation: MKAnnotation) -> MKAnnotationView? {
        if annotation is DestPin {
            let v = MKMarkerAnnotationView(annotation: annotation, reuseIdentifier: nil)
            v.markerTintColor = UIColor(red: 0.9, green: 0.28, blue: 0.3, alpha: 1)
            v.glyphImage = UIImage(systemName: "flag.checkered") ?? UIImage(systemName: "flag.fill")
            v.displayPriority = .required; v.canShowCallout = false
            return v
        }
        // Our view replaces the system blue dot entirely, so the location is never drawn twice.
        guard annotation is MKUserLocation else { return nil }
        let v = CarPlayPuckView(annotation: annotation, reuseIdentifier: nil)
        if guiding { v.setIcon(CarPlayPuckView.savedPhoto()) } else { v.setDot() }
        puck = v
        #if DEBUG
        NSLog("GCMCarPlay puck %@", CarPlayPuckView.savedPhoto() == nil ? "cart" : "photo")
        #endif
        return v
    }
    /// MapKit only asks for the user location view once, so toggle it to swap dot and icon.
    func refreshPuck() {
        puck = nil
        map.showsUserLocation = false
        map.showsUserLocation = true
    }
}

/// 48 pt icon kept upright on the map. The cart flips left/right by on-screen travel direction (same rule as
/// navfollow.js); a photo is never mirrored. A small teal chevron above it turns with the heading.
final class CarPlayPuckView: MKAnnotationView {
    private let img = UIImageView()
    private let chev = UIImageView(image: UIImage(systemName: "chevron.up", withConfiguration: UIImage.SymbolConfiguration(pointSize: 14, weight: .heavy)))
    private var isPhoto = false, side: Double = 1
    override init(annotation: MKAnnotation?, reuseIdentifier: String?) {
        super.init(annotation: annotation, reuseIdentifier: reuseIdentifier)
        frame = CGRect(x: 0, y: 0, width: 48, height: 48)
        img.frame = bounds; img.contentMode = .scaleAspectFit
        chev.tintColor = UIColor(red: 0.04, green: 0.6, blue: 0.66, alpha: 1)
        chev.frame = CGRect(x: 16, y: -20, width: 16, height: 16)
        addSubview(img); addSubview(chev)
        canShowCallout = false; zPriority = .max
    }
    required init?(coder: NSCoder) { fatalError() }
    static func savedPhoto() -> UIImage? {
        guard let d = UserDefaults.standard.data(forKey: CarPlayIcon.key) else { return nil }
        return UIImage(data: d)
    }
    /// Save the web setting natively so a CarPlay-only cold start still has it. nil = default cart.
    static func save(dataURL: String?) {
        if let d = CarPlayIcon.decode(dataURL), UIImage(data: d) != nil { UserDefaults.standard.set(d, forKey: CarPlayIcon.key) }
        else { UserDefaults.standard.removeObject(forKey: CarPlayIcon.key) }
    }
    func setIcon(_ photo: UIImage?) {
        isPhoto = photo != nil
        img.image = photo ?? UIImage(named: "CartE")
        img.layer.cornerRadius = isPhoto ? 24 : 0
        img.layer.borderWidth = isPhoto ? 3 : 0
        img.layer.borderColor = UIColor.white.cgColor
        img.clipsToBounds = isPhoto
        img.transform = .identity
    }
    /// Not guiding: a blue dot with the same chevron (t435u: the plain system dot showed no direction).
    func setDot() {
        isPhoto = true
        let r = UIGraphicsImageRenderer(size: CGSize(width: 22, height: 22)).image { _ in
            UIColor.white.setFill(); UIBezierPath(ovalIn: CGRect(x: 0, y: 0, width: 22, height: 22)).fill()
            UIColor(red: 0.11, green: 0.44, blue: 0.88, alpha: 1).setFill(); UIBezierPath(ovalIn: CGRect(x: 3, y: 3, width: 16, height: 16)).fill()
        }
        img.image = r; img.contentMode = .center; img.transform = .identity
        img.layer.borderWidth = 0; img.clipsToBounds = false
    }
    /// heading = travel direction, mapHeading = camera heading (both degrees).
    func point(heading: Double, mapHeading: Double) {
        chev.transform = CGAffineTransform(rotationAngle: CGFloat((heading - mapHeading) * .pi / 180))
        guard !isPhoto else { return }
        side = CarPlayIcon.faceSide(heading: heading, mapHeading: mapHeading, prev: side)
        img.transform = CGAffineTransform(scaleX: CGFloat(side), y: 1)
    }
}

// MARK: - CarPlay scene

final class CarPlaySceneDelegate: UIResponder, CPTemplateApplicationSceneDelegate, CPMapTemplateDelegate, CPSearchTemplateDelegate, CLLocationManagerDelegate {
    var interface: CPInterfaceController?
    var window: CPWindow?
    let mapVC = CarPlayMapViewController()
    let mapTemplate = CPMapTemplate()
    let loc = CLLocationManager()
    var session: CPNavigationSession?
    var plan: GCMPlan?
    var step = 0
    var voiceObs: NSObjectProtocol?
    var lastTrip: CPTrip?
    var overlayTimer: Timer?
    var showLegal = true
    var cam = CarPlayFollow()   // follow mode + the driver's zoom (t456u)
    var following: Bool { get { cam.following } set { newValue ? cam.resume() : (cam.following = false) } }
    var idleTimer: Timer?
    var gotFix = false
    var panLast = CGPoint.zero
    var tour: CarPlayTour?
    var lastTrim = Date.distantPast
    var rerouting = false
    var dest: (CLLocationCoordinate2D, String)?
    var camHeading: Double?
    // Guidance decisions come from the phone's engine (public/carplay.js navFix, AGENTS.md rule 35). We only render.
    var nav: [String: Any]? = nil      // last navFix answer
    var navBusy = Date.distantPast     // a navFix call in flight since
    var navLog = CarPlayNavLog(lines: UserDefaults.standard.stringArray(forKey: CarPlayNavLog.key) ?? [])
    var rerouteTimeout: Timer?
    var destAddress: String?
    var mode: String { "lsv" }

    // Scene lifecycle
    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didConnect interfaceController: CPInterfaceController, to window: CPWindow) {
        interface = interfaceController
        self.window = window
        window.rootViewController = mapVC
        GCMBridge.shared.attachHeadlessIfNeeded(to: mapVC.view)
        mapVC.onRegionChange = { [weak self] _ in self?.scheduleOverlay() }
        mapTemplate.mapDelegate = self
        mapTemplate.automaticallyHidesNavigationBar = false
        // Neutral system-style guidance card (it picked up a bright red), white text, dark trip estimates.
        mapTemplate.guidanceBackgroundColor = UIColor(white: 0.13, alpha: 1)
        mapTemplate.tripEstimateStyle = .dark
        refreshButtons()
        voiceObs = NotificationCenter.default.addObserver(forName: GCMVoice.mutedChanged, object: nil, queue: .main) { [weak self] _ in self?.refreshButtons() }
        interfaceController.setRootTemplate(mapTemplate, animated: false, completion: { _, _ in })
        loc.delegate = self
        loc.desiredAccuracy = kCLLocationAccuracyBestForNavigation
        loc.activityType = .automotiveNavigation
        loc.distanceFilter = kCLDistanceFilterNone   // every fix, so turns are judged on fresh positions (t451u)
        loc.pausesLocationUpdatesAutomatically = false
        // CarPlay runs with the phone locked, i.e. in the background. Without this (and UIBackgroundModes
        // location) updates stop: gray dot, card never advances, no reroute.
        loc.allowsBackgroundLocationUpdates = true
        if loc.authorizationStatus == .notDetermined { loc.requestWhenInUseAuthorization() }
        loc.startUpdatingLocation()
        showStartView()
        #if DEBUG
        NSLog("GCMCarPlay scene connected")
        #endif
        GCMBridge.shared.track("session")
        syncMapIcon()
        #if DEBUG
        // CI screenshot hook: `simctl launch <dev> <bundle> -GCMCarPlayDemo YES` plans a demo trip, then starts guidance.
        // CI screenshot hook (t451u): -GCMCarPlayCelebrateLoop YES runs the arrival celebration every 20 s.
        if UserDefaults.standard.bool(forKey: "GCMCarPlayCelebrateLoop") {
            Timer.scheduledTimer(withTimeInterval: 20, repeats: true) { [weak self] _ in self?.celebrate() }
        }
        if UserDefaults.standard.bool(forKey: "GCMCarPlayDemo") {
            DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
                // -GCMCarPlayDemoTo "lat,lon,Name" (default Crystal Pier)
                let a = (UserDefaults.standard.string(forKey: "GCMCarPlayDemoTo") ?? "32.7950,-117.2560,Crystal Pier").split(separator: ",", maxSplits: 2).map(String.init)
                if a.count == 3, let lat = Double(a[0]), let lon = Double(a[1]) { self?.choose(["name": a[2], "lat": lat, "lon": lon]) }
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
                guard let self = self, let trip = self.lastTrip, let c = trip.routeChoices.first else { return }
                self.mapTemplate(self.mapTemplate, startedTrip: trip, using: c)
                let every = UserDefaults.standard.double(forKey: "GCMCarPlayDemoDrive")
                if every > 0 { self.demoDrive(every: every) }
            }
        }
        #endif
        GCMBridge.shared.call("status()") { [weak self] any in
            guard let self = self, let d = any as? [String: Any] else { return }
            // The phone's last town only matters while there is still no GPS fix and nothing better was shown.
            if !self.gotFix, self.loc.location == nil, UserDefaults.standard.array(forKey: Self.savedKey) == nil,
               let c = d["center"] as? [Double], c.count == 2 {
                self.setStart(CarPlayStartView.pick(lastFix: nil, savedCenter: nil, phoneTown: (c[0], c[1]), towns: []))
            }
        }
    }

    // Initial view: never the zoomed-out US default. See CarPlayStartView for the order.
    static let savedKey = "gcm-cp-last-center"
    func bundledTowns() -> [CarPlayStartView.Town] {
        guard let u = Bundle.main.url(forResource: "regions", withExtension: "json", subdirectory: "public/data"),
              let d = try? Data(contentsOf: u) else { return [] }
        return CarPlayStartView.towns(from: d)
    }
    func showStartView() {
        let fix = loc.location.map { ($0.coordinate.latitude, $0.coordinate.longitude) }
        let saved = (UserDefaults.standard.array(forKey: Self.savedKey) as? [Double]).flatMap { $0.count == 2 ? ($0[0], $0[1]) : nil }
        setStart(CarPlayStartView.pick(lastFix: fix, savedCenter: saved, phoneTown: nil, towns: bundledTowns()))
        if fix != nil { startFollowing(animated: false) }
    }
    func setStart(_ p: CarPlayStartView.Pick?) {
        guard let p = p else { return }
        mapVC.map.setRegion(MKCoordinateRegion(center: CLLocationCoordinate2D(latitude: p.lat, longitude: p.lon), latitudinalMeters: p.meters, longitudinalMeters: p.meters), animated: false)
    }
    /// Center on the driver at about 1 km across and follow the dot.
    func startFollowing(animated: Bool) {
        guard let c = loc.location?.coordinate else { return }
        following = true; idleTimer?.invalidate()
        moveCamera(c, distance: cam.distance(default: Self.cameraDistance(meters: CarPlayStartView.drivingMeters)), heading: session == nil ? 0 : camHeading, animated: animated)
        refreshRecenter()
    }
    /// Region width in meters to an MKMapCamera distance (roughly what setRegion gave before).
    static func cameraDistance(meters: Double) -> Double { meters * 1.2 }
    /// Our own follow: never MKMapView .follow tracking, which re-zooms to MapKit's default each time it turns on.
    func moveCamera(_ c: CLLocationCoordinate2D, distance: Double, heading: Double?, animated: Bool) {
        let m = mapVC.map
        if m.userTrackingMode != .none { m.setUserTrackingMode(.none, animated: false) }
        let cm = MKMapCamera(lookingAtCenter: c, fromDistance: distance, pitch: 0, heading: heading ?? m.camera.heading)
        m.setCamera(cm, animated: animated)
    }
    /// Pan pauses follow; resume after CarPlayFollow.idleResume s with no further pan.
    func pausedByPan() {
        cam.pan(now: Date().timeIntervalSince1970)
        if mapVC.map.userTrackingMode != .none { mapVC.map.setUserTrackingMode(.none, animated: false) }
        idleTimer?.invalidate()
        idleTimer = Timer.scheduledTimer(withTimeInterval: CarPlayFollow.idleResume, repeats: false) { [weak self] _ in
            guard let self = self, self.cam.shouldAutoResume(now: Date().timeIntervalSince1970) else { return }
            self.startFollowing(animated: true)
        }
        refreshRecenter()
    }
    var recenterBtn: CPMapButton?
    func refreshRecenter() { recenterBtn?.image = UIImage(systemName: following ? "location.fill" : "location") }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways: manager.startUpdatingLocation()
        default: break
        }
    }
    // Panning on the CarPlay screen stops follow mode; the location button turns it back on.
    func mapTemplateDidShowPanningInterface(_ mapTemplate: CPMapTemplate) { stopFollowing() }
    func mapTemplateDidEndPanGesture(_ mapTemplate: CPMapTemplate, velocity: CGPoint) { pausedByPan() }
    func mapTemplate(_ mapTemplate: CPMapTemplate, panWith direction: CPMapTemplate.PanDirection) {
        stopFollowing()
        var r = mapVC.map.region
        let dy = r.span.latitudeDelta / 3, dx = r.span.longitudeDelta / 3
        if direction.contains(.up) { r.center.latitude += dy }
        if direction.contains(.down) { r.center.latitude -= dy }
        if direction.contains(.left) { r.center.longitude -= dx }
        if direction.contains(.right) { r.center.longitude += dx }
        mapVC.map.setRegion(r, animated: true)
    }
    func mapTemplateDidBeginPanGesture(_ mapTemplate: CPMapTemplate) { stopFollowing(); panLast = .zero }
    func mapTemplate(_ mapTemplate: CPMapTemplate, didUpdatePanGestureWithTranslation translation: CGPoint, velocity: CGPoint) {
        if following { stopFollowing(); panLast = .zero }   // in case begin was not delivered
        // translation is cumulative since the gesture began; apply only the new part.
        let dx = translation.x - panLast.x, dy = translation.y - panLast.y; panLast = translation
        let m = mapVC.map, mid = CGPoint(x: m.bounds.midX - dx, y: m.bounds.midY - dy)
        m.setCenter(m.convert(mid, toCoordinateFrom: m), animated: false)
    }
    func stopFollowing() { pausedByPan() }

    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didDisconnectInterfaceController interfaceController: CPInterfaceController, from window: CPWindow) {
        loc.stopUpdatingLocation()
        session?.cancelTrip()
        if let o = voiceObs { NotificationCenter.default.removeObserver(o); voiceObs = nil }
        GCMVoice.shared.stop()
        session = nil; interface = nil; self.window = nil
    }

    // Buttons
    func refreshButtons() {
        let searchBtn = CPBarButton(title: "Search") { [weak self] _ in self?.openSearch() }
        let savedBtn = CPBarButton(title: "Places") { [weak self] _ in self?.openRecents() }
        mapTemplate.leadingNavigationBarButtons = [searchBtn, savedBtn]
        mapTemplate.trailingNavigationBarButtons = [CPBarButton(title: "Experiences") { [weak self] _ in self?.openExperiences() }]
        let recenter = CPMapButton { [weak self] _ in
            self?.startFollowing(animated: true)
        }
        recenter.image = UIImage(systemName: following ? "location.fill" : "location")
        recenterBtn = recenter
        let layers = CPMapButton { [weak self] _ in
            guard let self = self else { return }
            self.showLegal.toggle(); self.scheduleOverlay(now: true)
        }
        layers.image = UIImage(systemName: showLegal ? "road.lanes" : "map")
        let zin = CPMapButton { [weak self] _ in self?.zoom(0.5) }
        zin.image = UIImage(systemName: "plus.magnifyingglass")
        let zout = CPMapButton { [weak self] _ in self?.zoom(2) }
        zout.image = UIImage(systemName: "minus.magnifyingglass")
        // Voice on/off (t455u), same switch as the phone nav screen. Muted: music only, no spoken directions.
        let voice = CPMapButton { [weak self] _ in
            GCMVoice.shared.muted.toggle()
            self?.refreshButtons()
        }
        voice.image = UIImage(systemName: GCMVoice.shared.muted ? "speaker.slash.fill" : "speaker.wave.2.fill")
        mapTemplate.mapButtons = [recenter, voice, layers, zin, zout]
    }

    func zoom(_ f: Double) {
        let m = mapVC.map
        let d = cam.zoom(current: m.camera.centerCoordinateDistance, factor: f)
        // Keep following at the new zoom (build 42 turned MapKit tracking back on here, which reset the zoom).
        let c = following ? (loc.location?.coordinate ?? m.centerCoordinate) : m.centerCoordinate
        moveCamera(c, distance: d, heading: nil, animated: true)
    }

    // Legal-road overlay (green = OK for current mode, red = avoid), same classification as the phone map
    func scheduleOverlay(now: Bool = false) {
        overlayTimer?.invalidate()
        overlayTimer = Timer.scheduledTimer(withTimeInterval: now ? 0.05 : 0.8, repeats: false) { [weak self] _ in self?.loadOverlay() }
    }
    func loadOverlay() {
        let m = mapVC.map
        m.removeOverlays(m.overlays.filter { $0 is OkLine || $0 is AvoidLine })
        guard showLegal, m.region.span.latitudeDelta < 0.08 else { return }
        let r = m.region
        let args: [String: Any] = ["s": r.center.latitude - r.span.latitudeDelta / 2, "w": r.center.longitude - r.span.longitudeDelta / 2,
                                   "n": r.center.latitude + r.span.latitudeDelta / 2, "e": r.center.longitude + r.span.longitudeDelta / 2]
        GCMBridge.shared.call("overlay(s,w,n,e,1500)", args) { [weak self] any in
            guard let self = self, let d = any as? [String: Any] else { return }
            func lines<T: MKPolyline>(_ k: String, _ t: T.Type) -> [MKOverlay] {
                (d[k] as? [[[Double]]] ?? []).map { pts in
                    var c = pts.compactMap { $0.count == 2 ? CLLocationCoordinate2D(latitude: $0[0], longitude: $0[1]) : nil }
                    return T(coordinates: &c, count: c.count)
                }
            }
            self.mapVC.map.addOverlays(lines("ok", OkLine.self) + lines("bad", AvoidLine.self), level: .aboveRoads)
        }
    }

    // Search (local POIs + street names from the region data, then Apple Maps as fallback)
    func openSearch() {
        let t = CPSearchTemplate()
        t.delegate = self
        interface?.pushTemplate(t, animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } })
    }
    // t451u: Apple owns the keyboard and the row size, so: short rows (title <= 28, subtitle <= 32 chars), best match
    // first, and Home / Favorite beach / recents listed before typing so most trips need no keyboard at all.
    func searchItem(_ name: String, _ sub: String?, _ lat: Double, _ lon: Double, address: String? = nil) -> CPListItem {
        let it = CPListItem(text: CarPlaySearchText.clip(name, CarPlaySearchText.titleMax), detailText: CarPlaySearchText.clip(sub, CarPlaySearchText.subMax))
        var info: [String: Any] = ["name": name, "lat": lat, "lon": lon]
        if let a = address ?? sub { info["address"] = a }
        it.userInfo = info
        return it
    }
    func quickPicks(_ done: @escaping ([CPListItem]) -> Void) {
        GCMBridge.shared.call("places()") { [weak self] any in
            guard let self = self else { return }
            let saved = (any as? [[String: Any]] ?? []).compactMap { d -> CPListItem? in
                guard let n = d["name"] as? String, let lat = (d["lat"] as? NSNumber)?.doubleValue, let lon = (d["lon"] as? NSNumber)?.doubleValue else { return nil }
                return self.searchItem(n, d["sub"] as? String, lat, lon)
            }
            let names = Set(saved.compactMap { ($0.userInfo as? [String: Any])?["name"] as? String })
            let rec = self.recents.filter { !names.contains($0["name"] as? String ?? "") }.prefix(8).compactMap { d -> CPListItem? in
                guard let n = d["name"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return nil }
                return self.searchItem(n, "Recent", lat, lon, address: d["address"] as? String)
            }
            done(Array((saved + rec).prefix(CarPlaySearchText.maxResults)))
        }
    }
    func searchTemplate(_ searchTemplate: CPSearchTemplate, updatedSearchText searchText: String, completionHandler: @escaping ([CPListItem]) -> Void) {
        guard searchText.count >= 2 else { quickPicks(completionHandler); return }
        let c = loc.location?.coordinate ?? mapVC.map.centerCoordinate
        let here = CLLocation(latitude: c.latitude, longitude: c.longitude)
        GCMBridge.shared.call("search(q,lat,lon)", ["q": searchText, "lat": c.latitude, "lon": c.longitude]) { [weak self] any in
            guard let self = self else { return }
            let raw = (any as? [[String: Any]] ?? []).compactMap { d -> (String, String?, Double, Double)? in
                guard let n = d["name"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return nil }
                return (n, d["sub"] as? String, lat, lon)
            }
            if !raw.isEmpty {
                let order = CarPlaySearchText.rank(raw.map { ($0.0, here.distance(from: CLLocation(latitude: $0.2, longitude: $0.3))) }, query: searchText)
                completionHandler(order.prefix(CarPlaySearchText.maxResults).map { let r = raw[$0]; return self.searchItem(r.0, r.1, r.2, r.3) })
                return
            }
            let req = MKLocalSearch.Request()
            req.naturalLanguageQuery = searchText
            req.region = MKCoordinateRegion(center: c, latitudinalMeters: 20000, longitudinalMeters: 20000)
            MKLocalSearch(request: req).start { resp, _ in
                let mis = resp?.mapItems ?? []
                let order = CarPlaySearchText.rank(mis.map { ($0.name ?? "", $0.placemark.location.map { here.distance(from: $0) }) }, query: searchText)
                completionHandler(order.prefix(8).map { i in
                    let mi = mis[i]
                    return self.searchItem(mi.name ?? "Place", CarPlaySearchText.shortAddress(mi.placemark.title), mi.placemark.coordinate.latitude, mi.placemark.coordinate.longitude, address: mi.placemark.title)
                })
            }
        }
    }
    func searchTemplate(_ searchTemplate: CPSearchTemplate, selectedResult item: CPListItem, completionHandler: @escaping () -> Void) {
        if let d = item.userInfo as? [String: Any] { choose(d) }
        completionHandler()
    }

    // Recents (saved destinations)
    var recents: [[String: Any]] {
        get { UserDefaults.standard.array(forKey: "gcm-cp-recents") as? [[String: Any]] ?? [] }
        set { UserDefaults.standard.set(Array(newValue.prefix(12)), forKey: "gcm-cp-recents") }
    }
    /// Home, Favorite beach and favorites from the phone (Settings > Saved places), then recents: one tap, no keyboard (t451u).
    func openRecents() {
        quickPicks { [weak self] picks in
            guard let self = self else { return }
            let items: [CPListItem] = picks.map { it in
                it.handler = { [weak self] item, done in if let d = (item as? CPListItem)?.userInfo as? [String: Any] { self?.choose(d) }; done() }
                return it
            }
            let t = CPListTemplate(title: "Places", sections: [CPListSection(items: items)])
            t.emptyViewTitleVariants = ["No saved or recent places"]
            t.emptyViewSubtitleVariants = ["Save Home or a favorite beach in the phone app"]
            self.push(t)
        }
    }

    // Trip preview
    func choose(_ d: [String: Any], remember: Bool = true) {
        guard let name = d["name"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return }
        if remember { recents = [d] + recents.filter { ($0["name"] as? String) != name } }
        if (interface?.templates.count ?? 0) > 1 { interface?.popToRootTemplate(animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }
        guard let from = loc.location?.coordinate ?? Optional(mapVC.map.centerCoordinate) else { return }
        let to = CLLocationCoordinate2D(latitude: lat, longitude: lon)
        dest = (to, name); destAddress = d["address"] as? String
        GCMBridge.shared.call("plan(f,t,m,false,null,d)", ["f": ["lat": from.latitude, "lon": from.longitude], "t": ["lat": lat, "lon": lon], "m": mode, "d": name]) { [weak self] any in
            guard let self = self else { return }
            guard let p = GCMPlan(any) else {
                let reason = (any as? [String: Any])?["reason"] as? String ?? "No legal route found."
                let alert = CPAlertTemplate(titleVariants: ["No legal route", reason], actions: [CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.interface?.dismissTemplate(animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }])
                self.interface?.presentTemplate(alert, animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } })
                return
            }
            self.plan = p
            self.drawRoute(p)
            let dest = MKMapItem(placemark: MKPlacemark(coordinate: to)); dest.name = name
            let origin = MKMapItem(placemark: MKPlacemark(coordinate: from))
            let label = "cart / LSV"
            let choice = CPRouteChoice(summaryVariants: ["\(label) legal · \(String(format: "%.1f", p.miles)) mi" + (p.riskyCount > 0 ? " · \(p.riskyCount) risky" : "")],
                                       additionalInformationVariants: [p.rangeText], selectionSummaryVariants: [p.rangeText])
            let trip = CPTrip(origin: origin, destination: dest, routeChoices: [choice])
            let cfg = CPTripPreviewTextConfiguration(startButtonTitle: "Go", additionalRoutesButtonTitle: nil, overviewButtonTitle: nil)
            self.lastTrip = trip
            self.mapTemplate.showTripPreviews([trip], textConfiguration: cfg)
            self.mapTemplate.update(self.estimates(p.meters, p.minutes * 60), for: trip, with: .default)
        }
    }
    // Under 0.1 mi CarPlay shows feet (rounded to 50 ft) instead of "0 mi".
    func estimates(_ m: Double, _ s: Double) -> CPTravelEstimates {
        let mi = m / 1609.34
        let d = mi < 0.1 ? Measurement(value: max(50, (m * 3.28084 / 50).rounded() * 50), unit: UnitLength.feet) : Measurement(value: (mi * 10).rounded() / 10, unit: UnitLength.miles)
        return CPTravelEstimates(distanceRemaining: d, timeRemaining: max(0, s))
    }
    func drawRoute(_ p: GCMPlan) {
        let m = mapVC.map
        m.removeOverlays(m.overlays.filter { $0 is RouteLine })
        var c = p.line
        let pl = RouteLine(coordinates: &c, count: c.count)
        m.addOverlay(pl, level: .aboveLabels)
        m.removeAnnotations(m.annotations.filter { $0 is DestPin })
        if let last = p.line.last { let pin = DestPin(); pin.coordinate = last; m.addAnnotation(pin) }
        m.setVisibleMapRect(pl.boundingMapRect, edgePadding: UIEdgeInsets(top: 40, left: 40, bottom: 40, right: 40), animated: true)
    }

    func mapTemplate(_ mapTemplate: CPMapTemplate, selectedPreviewFor trip: CPTrip, using routeChoice: CPRouteChoice) {
        if let p = plan { drawRoute(p) }
    }

    // Guidance
    func mapTemplate(_ mapTemplate: CPMapTemplate, startedTrip trip: CPTrip, using routeChoice: CPRouteChoice) {
        guard let p = plan else { return }
        mapTemplate.hideTripPreviews()
        let s = mapTemplate.startNavigationSession(for: trip)
        session = s
        mapVC.guiding = true
        syncMapIcon()
        GCMBridge.shared.track("route_started", ["mi": p.miles])
        step = p.maneuvers.count > 1 ? 1 : 0
        pushManeuvers(s, p)
        nav = nil; navBusy = .distantPast
        GCMBridge.shared.call("navStart()") { [weak self] any in
            let r = any as? [String: Any]
            self?.log("navStart \(r?["ok"] as? Bool == true ? "ok" : "failed: \(String(describing: any))")")
            if let say = r?["say"] as? String { GCMVoice.shared.speak(say) }
        }
        mapTemplate.update(estimates(p.meters, p.minutes * 60), for: trip, with: .default)
        let end = CPBarButton(title: "End") { [weak self] _ in self?.endTrip(arrived: false) }
        mapTemplate.trailingNavigationBarButtons = [end]
        if let c = loc.location?.coordinate {
            following = true; camHeading = nil; idleTimer?.invalidate()
            moveCamera(c, distance: cam.distance(default: Self.cameraDistance(meters: 600)), heading: nil, animated: true)
        }
    }
    // CPManeuver from one step of the legal-road route (public/carplay.js maneuvers()).
    func cpManeuver(_ m: GCMManeuver) -> CPManeuver {
        let c = CPManeuver()
        let speed = plan?.speed ?? 9.8
        // longest first; CarPlay picks the variant that fits the guidance card
        let arrive = CarPlayArrive.text(name: dest?.1, address: destAddress)
        let short = m.type == "arrive" ? arrive : m.short, text = m.type == "arrive" ? arrive : m.text
        c.instructionVariants = m.type == "arrive" ? [arrive, "Arrive"] : [m.short, m.road.isEmpty ? m.short : m.road]  // short first keeps the card compact
        c.dashboardInstructionVariants = [short]
        c.notificationInstructionVariants = [text]
        let cfg = UIImage.SymbolConfiguration(pointSize: 40, weight: .bold)
        c.symbolImage = UIImage(systemName: m.symbol, withConfiguration: cfg)?.withRenderingMode(.alwaysTemplate)
        c.dashboardSymbolImage = c.symbolImage
        c.notificationSymbolImage = c.symbolImage
        c.initialTravelEstimates = estimates(m.toMeters, m.toMeters / speed)
        // No junctionImage: CarPlay draws it in place of the instruction text, and our road graph has no lane or
        // junction artwork worth showing at simple intersections. Junction geometry goes in junctionExitAngle below.
        if m.risky { c.attributedInstructionVariants = [NSAttributedString(string: "⚠️ " + short)] }
        c.userInfo = ["road": m.road, "mph": m.mph ?? 0]
        if #available(iOS 17.4, *) {
            c.maneuverType = m.cpType
            c.trafficSide = .right
            if !m.road.isEmpty { c.roadFollowingManeuverVariants = [m.road] }
            if m.isTurn {
                c.junctionType = .intersection
                c.junctionExitAngle = Measurement(value: m.turn, unit: UnitAngle.degrees)
            }
        }
        return c
    }
    // current maneuver + the one after it (CarPlay shows the second as the "then" row)
    func pushManeuvers(_ s: CPNavigationSession, _ p: GCMPlan) {
        s.upcomingManeuvers = p.maneuvers.dropFirst(step).prefix(2).map(cpManeuver)
        if #available(iOS 17.4, *) {
            let road = p.maneuvers[max(0, step - 1)].road
            s.currentRoadNameVariants = road.isEmpty ? [] : [road]
        }
    }
    /// Heading-up like the phone (t453u): the shared engine's map heading target (road ahead on the route, else GPS
    /// course). Camera via moveCamera only, never MapKit .follow (it resets rotation and zoom, PR #58).
    func headingUp(_ here: CLLocation, bearing: Double?) {
        if let h = here.course >= 0 ? here.course : camHeading { mapVC.puck?.point(heading: h, mapHeading: mapVC.map.camera.heading) }
        guard following else { return }
        if let b = bearing, camHeading.map({ abs(($0 - b + 540).truncatingRemainder(dividingBy: 360) - 180) >= 5 }) ?? true { camHeading = b }
        moveCamera(here.coordinate, distance: mapVC.map.camera.centerCoordinateDistance, heading: camHeading, animated: true)
    }
    func log(_ line: String) {
        NSLog("GCMCarPlay nav %@", line)
        navLog.add(line); UserDefaults.standard.set(navLog.lines, forKey: CarPlayNavLog.key)
    }
    /// Map icon (t434u): read Settings > Your map icon from the web layer on connect and at each trip start,
    /// save it natively (UserDefaults) for CarPlay-only cold starts, and swap the guidance icon if it changed.
    func syncMapIcon() {
        // Read the same localStorage key the phone uses (navfollow.js ICON_KEY); no web change needed, native validates it.
        GCMBridge.shared.call("version&&localStorage.getItem('gcm_map_icon')") { [weak self] any in
            DispatchQueue.main.async {
                let before = UserDefaults.standard.data(forKey: CarPlayIcon.key)
                CarPlayPuckView.save(dataURL: any as? String)
                if UserDefaults.standard.data(forKey: CarPlayIcon.key) != before, self?.mapVC.guiding == true { self?.mapVC.refreshPuck() }
            }
        }
    }
    /// Same as the phone: replan from here to the same destination, then swap the line, card and estimates.
    func reroute(from here: CLLocation, course hd: Double?) {
        guard let s = session, let to = dest?.0 else { return }
        rerouting = true
        NSLog("GCMCarPlay reroute from %.5f,%.5f", here.coordinate.latitude, here.coordinate.longitude)
        if #available(iOS 15.4, *) { s.pauseTrip(for: .rerouting, description: "Rerouting on legal roads", turnCardColor: nil) } else { s.pauseTrip(for: .rerouting, description: "Rerouting on legal roads") }
        // Driving (>= 1.5 m/s with a valid course): replan forward on this road, no U-turn first (Max t433u).
        // t451u: build 41 used here.course only if >= 0 at >= 1.5 m/s right now, so slowing down (or iOS reporting -1)
        // dropped the heading and the plan said turn around. Use the last good course from the past 10 s instead.
        let h: Any = hd ?? NSNull()
        NSLog("GCMCarPlay reroute heading %@ (gps course %.0f, speed %.1f)", hd.map { String(format: "%.0f", $0) } ?? "none", here.course, here.speed)
        // If the web view never answers (e.g. iOS suspended it), resume the old guidance so the next check can retry.
        rerouteTimeout?.invalidate()
        rerouteTimeout = Timer.scheduledTimer(withTimeInterval: 12, repeats: false) { [weak self] _ in
            guard let self = self, self.rerouting else { return }
            NSLog("GCMCarPlay reroute timed out")
            self.rerouting = false; self.log("reroute bridge timeout (12 s)")
            if let s = self.session, let p = self.plan { self.pushManeuvers(s, p) }
        }
        GCMBridge.shared.call("plan(f,t,m,false,h,d)", ["f": ["lat": here.coordinate.latitude, "lon": here.coordinate.longitude], "t": ["lat": to.latitude, "lon": to.longitude], "m": mode, "h": h, "d": dest?.1 ?? ""]) { [weak self] any in
            guard let self = self, self.rerouting else { return }
            self.rerouteTimeout?.invalidate()
            defer { self.rerouting = false }
            guard let s = self.session, let p = GCMPlan(any) else {
                self.log("reroute bridge failed: \(String(describing: any).prefix(80))")
                if let s = self.session, let p = self.plan { self.pushManeuvers(s, p) }   // resume the old guidance
                return
            }
            self.plan = p
            self.step = p.maneuvers.count > 1 ? 1 : 0
            let m = self.mapVC.map
            m.removeOverlays(m.overlays.filter { $0 is RouteLine })
            var c = p.line
            m.addOverlay(RouteLine(coordinates: &c, count: c.count), level: .aboveLabels)
            self.pushManeuvers(s, p)
            self.mapTemplate.update(self.estimates(p.meters, p.minutes * 60), for: s.trip, with: .default)
            self.log(String(format: "rerouted: %d maneuvers, %.0f m", p.maneuvers.count, p.meters))
            NSLog("GCMCarPlay rerouted: %d maneuvers, %.0f m", p.maneuvers.count, p.meters)   // CI greps this
            self.nav = nil
            GCMBridge.shared.call("navStart()") { [weak self] any in self?.log("navStart after reroute \((any as? [String: Any])?["ok"] as? Bool == true ? "ok" : "failed")") }
            if let here = self.loc.location { self.progress(here) }
        }
    }
    func endTrip(arrived: Bool) {
        if arrived, session != nil { GCMBridge.shared.track("route_completed", ["mi": plan?.miles ?? 0]) }
        if arrived { session?.finishTrip() } else { session?.cancelTrip(); GCMVoice.shared.stop() }
        session = nil; plan = nil; nav = nil; rerouting = false; rerouteTimeout?.invalidate()
        GCMBridge.shared.call("navEnd()") { _ in }
        mapVC.guiding = false
        mapVC.map.removeOverlays(mapVC.map.overlays.filter { $0 is RouteLine })
        mapVC.map.removeAnnotations(mapVC.map.annotations.filter { $0 is DestPin })
        refreshButtons()
        startFollowing(animated: true)
        if arrived { celebrate(); tourArrived() } else { endTour() }
    }

    // MARK: Arrival celebration (t446u, longer and bigger in t451u): ~15 s of unicorns on varied wavy paths, confetti
    // and a rainbow over our own map view, non-interactive, only after arrival. The banner sits centered in the safe
    // area (below the nav bar buttons, which cut it off in build 41). Reduce Motion: banner only, 4 s, no flying.
    // Falls back to a short alert if the map view is not on screen.
    func celebrate() {
        let host = mapVC.view!
        guard host.window != nil, let art = UIImage(named: "Unicorn") else {
            presentAlert(["Have a wonderful life, you legend! 🦄", "You made it! 🦄"], [CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.dismiss() }])
            return
        }
        let reduced = UIAccessibility.isReduceMotionEnabled, total = reduced ? CarPlayCelebrate.reducedSeconds : CarPlayCelebrate.seconds
        let layer = UIView(frame: host.bounds); layer.isUserInteractionEnabled = false
        layer.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        let b = host.bounds, safe = b.inset(by: host.safeAreaInsets)
        host.addSubview(layer)
        if !reduced {
            // Rainbow arc behind everything
            let arc = CAShapeLayer(), r = min(safe.width, safe.height * 1.6) * 0.48
            arc.path = UIBezierPath(arcCenter: CGPoint(x: safe.midX, y: safe.maxY + r * 0.15), radius: r, startAngle: .pi, endAngle: 0, clockwise: true).cgPath
            arc.fillColor = nil; arc.lineWidth = 0
            let colors: [UIColor] = [.systemRed, .systemOrange, .systemYellow, .systemGreen, .systemBlue, .systemPurple]
            for (i, col) in colors.enumerated() {
                let band = CAShapeLayer()
                band.path = UIBezierPath(arcCenter: CGPoint(x: safe.midX, y: safe.maxY + r * 0.15), radius: r - CGFloat(i) * 9, startAngle: .pi, endAngle: 0, clockwise: true).cgPath
                band.fillColor = nil; band.strokeColor = col.withAlphaComponent(0.55).cgColor; band.lineWidth = 9; band.strokeEnd = 0
                layer.layer.addSublayer(band)
                let grow = CABasicAnimation(keyPath: "strokeEnd"); grow.fromValue = 0; grow.toValue = 1; grow.duration = 1.4; grow.beginTime = CACurrentMediaTime() + 0.2 + Double(i) * 0.08
                grow.fillMode = .forwards; grow.isRemovedOnCompletion = false
                band.add(grow, forKey: "grow")
            }
            // Confetti
            let em = CAEmitterLayer(); em.emitterPosition = CGPoint(x: safe.midX, y: safe.minY - 6); em.emitterShape = .line
            em.emitterSize = CGSize(width: safe.width, height: 1); em.frame = b
            em.emitterCells = colors.map { col in
                let c = CAEmitterCell(); c.birthRate = 6; c.lifetime = 7; c.velocity = 90; c.velocityRange = 40; c.emissionLongitude = .pi
                c.emissionRange = .pi / 5; c.spin = 3; c.spinRange = 4; c.scale = 0.6; c.scaleRange = 0.3; c.yAcceleration = 40
                c.color = col.cgColor; c.contents = UIGraphicsImageRenderer(size: CGSize(width: 10, height: 6)).image { ctx in UIColor.white.setFill(); ctx.fill(CGRect(x: 0, y: 0, width: 10, height: 6)) }.cgImage
                return c
            }
            layer.layer.addSublayer(em)
            DispatchQueue.main.asyncAfter(deadline: .now() + total - 3) { em.birthRate = 0 }
            // Unicorns: 8 of them on different lanes, sizes, speeds and directions, each bobbing on its own wave.
            for (i, ln) in CarPlayCelebrate.lanes(count: 8, safe: safe).enumerated() {
                let v = UIImageView(image: art), w = ln.size * 1.2
                v.frame = CGRect(x: ln.rtl ? b.maxX + 10 : -w - 10, y: ln.y, width: w, height: ln.size)
                if ln.rtl { v.transform = CGAffineTransform(scaleX: -1, y: 1) }
                layer.addSubview(v)
                let path = UIBezierPath(), x0 = ln.rtl ? b.maxX + w : -w, x1 = ln.rtl ? -w : b.maxX + w, yc = ln.y + ln.size / 2
                path.move(to: CGPoint(x: x0, y: yc))
                let hops = 4
                for k in 1...hops {
                    let xe = x0 + (x1 - x0) * CGFloat(k) / CGFloat(hops), xm = x0 + (x1 - x0) * (CGFloat(k) - 0.5) / CGFloat(hops)
                    path.addQuadCurve(to: CGPoint(x: xe, y: yc), controlPoint: CGPoint(x: xm, y: yc - ln.amp * (k % 2 == 0 ? -1 : 1) * 2))
                }
                let fly = CAKeyframeAnimation(keyPath: "position"); fly.path = path.cgPath; fly.duration = ln.dur
                fly.repeatCount = Float(max(1, (total - 1.5 - ln.delay) / ln.dur).rounded(.down))
                fly.beginTime = CACurrentMediaTime() + ln.delay; fly.fillMode = .backwards
                v.layer.add(fly, forKey: "fly")
                let spin = CABasicAnimation(keyPath: "transform.rotation.z"); spin.fromValue = -0.12; spin.toValue = 0.12
                spin.duration = 0.35 + Double(i % 3) * 0.1; spin.autoreverses = true; spin.repeatCount = .infinity
                v.layer.add(spin, forKey: "wiggle")
            }
        }
        let label = UILabel(); label.text = "Have a wonderful life, you legend! 🦄"
        label.font = .systemFont(ofSize: 24, weight: .heavy); label.textColor = .white; label.textAlignment = .center
        label.adjustsFontSizeToFitWidth = true; label.minimumScaleFactor = 0.5
        label.backgroundColor = UIColor(red: 0.42, green: 0.25, blue: 0.75, alpha: 0.9); label.layer.cornerRadius = 16; label.clipsToBounds = true
        label.frame = CarPlayCelebrate.bannerFrame(bounds: b, safe: safe)
        layer.addSubview(label)
        if !reduced {
            label.transform = CGAffineTransform(scaleX: 0.3, y: 0.3)
            UIView.animate(withDuration: 0.6, delay: 0.1, usingSpringWithDamping: 0.5, initialSpringVelocity: 0.8, options: []) { label.transform = .identity }
            UIView.animate(withDuration: 0.9, delay: 0.8, options: [.autoreverse, .repeat, .allowUserInteraction]) { label.transform = CGAffineTransform(scaleX: 1.05, y: 1.05) }
        }
        #if DEBUG
        NSLog("GCMCarPlay celebrate %.0fs banner=%@ safe=%@", total, NSCoder.string(for: label.frame), NSCoder.string(for: safe))
        #endif
        UIView.animate(withDuration: 0.6, delay: total - 0.6, options: []) { layer.alpha = 0 } completion: { _ in layer.removeFromSuperview() }
    }

    func presentAlert(_ titles: [String], _ actions: [CPAlertAction]) {
        interface?.presentTemplate(CPAlertTemplate(titleVariants: titles, actions: actions), animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } })
    }
    func dismiss() { interface?.dismissTemplate(animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }
    func push(_ t: CPTemplate) { interface?.pushTemplate(t, animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }

    // MARK: Partner experiences (Max t437s2290). Data: public/carplay.js experiences() / stops(id) from the
    // renter unlock saved on the phone. Short text only; coupon codes only when parked.
    func openExperiences() {
        GCMBridge.shared.call("experiences()") { [weak self] any in
            DispatchQueue.main.async {
                guard let self = self else { return }
                let d = any as? [String: Any] ?? [:]
                guard d["ok"] as? Bool == true else {
                    self.presentAlert([d["reason"] as? String ?? "Open your rental shop link on your phone to unlock experiences.", "Open your shop link on your phone"],
                                      [CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.dismiss() }])
                    return
                }
                let shop = d["shop"] as? [String: Any] ?? [:], veh = shop["vehicle"] as? String ?? "golf_cart"
                let speed = self.loc.location?.speed ?? -1
                let xs = (d["experiences"] as? [[String: Any]] ?? []).map { e -> CPListItem in
                    let n = (e["stops"] as? NSNumber)?.intValue ?? 0
                    let it = CPListItem(text: e["title"] as? String ?? "Experience", detailText: "\(n) \(n == 1 ? "stop" : "stops")")
                    it.handler = { [weak self] _, done in self?.openStops(String(describing: e["id"] ?? ""), title: e["title"] as? String ?? "", veh: veh); done() }
                    return it
                }
                var sections = [CPListSection(items: xs)]
                if speed >= 0, speed < 1 {
                    let offers = (d["offers"] as? [[String: Any]] ?? []).filter { !($0["coupon"] as? String ?? "").isEmpty }.prefix(6).map {
                        CPListItem(text: $0["name"] as? String ?? "", detailText: "Code \($0["coupon"] as? String ?? "")")
                    }
                    if !offers.isEmpty { sections.append(CPListSection(items: Array(offers), header: "Offers", sectionIndexTitle: nil)) }
                }
                let t = CPListTemplate(title: shop["name"] as? String ?? "Experiences", sections: sections)
                t.emptyViewTitleVariants = ["No experiences yet"]
                self.push(t)
            }
        }
    }
    func openStops(_ id: String, title: String, veh: String) {
        let c = loc.location?.coordinate
        var args: [String: Any] = ["id": id]
        if let c = c { args["la"] = c.latitude; args["lo"] = c.longitude }
        GCMBridge.shared.call(c == nil ? "stops(id,null,null)" : "stops(id,la,lo)", args) { [weak self] any in
            DispatchQueue.main.async {
                guard let self = self, let d = any as? [String: Any], d["ok"] as? Bool == true else { return }
                let raw = d["stops"] as? [[String: Any]] ?? []
                let stops = raw.compactMap { s -> CarPlayTour.Stop? in
                    guard let la = (s["lat"] as? NSNumber)?.doubleValue, let lo = (s["lon"] as? NSNumber)?.doubleValue else { return nil }
                    return .init(name: s["name"] as? String ?? "Stop", lat: la, lon: lo)
                }
                let speed = self.loc.location?.speed ?? -1
                let start = CPListItem(text: "Start", detailText: stops.first.map { "Go to \($0.name)" })
                start.handler = { [weak self] _, done in self?.startTour(title: title, stops: stops, veh: veh); done() }
                let items = raw.enumerated().map { i, s in
                    CPListItem(text: "\(i + 1). \(s["name"] as? String ?? "Stop")",
                               detailText: CarPlayTour.detail(category: s["category"] as? String ?? "", meters: (s["meters"] as? NSNumber)?.doubleValue,
                                                              coupon: s["coupon"] as? String ?? "", speed: speed))
                }
                self.push(CPListTemplate(title: title.isEmpty ? "Stops" : title, sections: [CPListSection(items: [start]), CPListSection(items: items)]))
            }
        }
    }
    /// Use the shop's vehicle rules (LSV for Beach Mode) for the tour, put the phone's setting back after.
    func startTour(title: String, stops: [CarPlayTour.Stop], veh: String) {
        guard !stops.isEmpty else { return }
        GCMBridge.shared.call("status()") { [weak self] any in
            let prev = (any as? [String: Any])?["mode"] as? String
            GCMBridge.shared.call("setMode(m)", ["m": veh]) { _ in
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    self.tour = CarPlayTour(title: title, stops: stops, prevMode: prev == veh ? nil : prev)
                    self.goToTourStop()
                }
            }
        }
    }
    func goToTourStop() {
        guard let s = tour?.current else { return }
        choose(["name": s.name, "lat": s.lat, "lon": s.lon], remember: false)
    }
    func tourArrived() {
        guard var t = tour else { return }
        guard let next = t.advance() else { endTour(); return }
        tour = t
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.4) { [weak self] in
            self?.presentAlert(["Next stop: \(next.name)", "Next stop"], [
                CPAlertAction(title: "Next stop", style: .default) { [weak self] _ in self?.dismiss(); self?.goToTourStop() },
                CPAlertAction(title: "End", style: .cancel) { [weak self] _ in self?.dismiss(); self?.endTour() }])
        }
    }
    func endTour() {
        guard let t = tour else { return }
        tour = nil
        if let m = t.prevMode { GCMBridge.shared.call("setMode(m)", ["m": m]) { _ in } }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let here = locations.last else { return }
        if !gotFix, here.horizontalAccuracy >= 0, here.horizontalAccuracy < 1000 {
            gotFix = true
            startFollowing(animated: true)
        }
        UserDefaults.standard.set([here.coordinate.latitude, here.coordinate.longitude], forKey: Self.savedKey)
        // North-up / browsing: chevron follows GPS course (guidance also updates it in headingUp).
        if here.course >= 0 { mapVC.puck?.point(heading: here.course, mapHeading: mapVC.map.camera.heading) }
        // Browsing (no trip): follow the dot ourselves at the current zoom.
        if session == nil, following, gotFix { moveCamera(here.coordinate, distance: mapVC.map.camera.centerCoordinateDistance, heading: nil, animated: true) }
        progress(here)
    }
    /// One GPS fix during guidance: ask the shared engine (public/carplay.js navFix, same code as the phone) and render
    /// its answer. No accuracy gate, no native off-route/advance/heading rules (build 42 had its own, and never rerouted).
    func progress(_ here: CLLocation) {
        guard session != nil, plan != nil else { return }
        if let r = nav { headingUp(here, bearing: (r["bearing"] as? NSNumber)?.doubleValue) }   // camera keeps up between answers
        guard Date().timeIntervalSince(navBusy) > 3 else { return }   // one call in flight (stale after 3 s)
        navBusy = Date()
        let c = here.coordinate
        let f: [String: Any] = ["lat": c.latitude, "lon": c.longitude, "course": here.course, "speed": here.speed,
                                "accuracy": here.horizontalAccuracy, "t": here.timestamp.timeIntervalSince1970 * 1000]
        GCMBridge.shared.call("navFix(f)", ["f": f]) { [weak self] any in
            guard let self = self else { return }
            self.navBusy = .distantPast
            guard let r = any as? [String: Any] else { self.log("navFix no answer from web view"); return }
            self.apply(r, here)
        }
    }
    func apply(_ r: [String: Any], _ here: CLLocation) {
        guard let s = session, let p = plan else { return }
        let num = { (k: String) in (r[k] as? NSNumber)?.doubleValue }
        let wasOff = (num("off") ?? 0) > 30, prevOff = ((nav?["off"] as? NSNumber)?.doubleValue ?? 0) > 30
        nav = r
        if wasOff != prevOff { log(String(format: "%@ route, off %.0f m, course %.0f, speed %.1f, acc %.0f", wasOff ? "left" : "back on", num("off") ?? -1, here.course, here.speed, here.horizontalAccuracy)) }
        headingUp(here, bearing: num("bearing"))
        trimRoute(here, pts: p.line.map { ($0.latitude, $0.longitude) }, off: num("off") ?? 0)
        if rerouting { return }
        if let rr = r["reroute"] as? [String: Any] {
            log("reroute: \(rr["reason"] as? String ?? "?"), course \((rr["course"] as? NSNumber)?.intValue ?? -1)")
            GCMVoice.shared.speak("Rerouting")
            reroute(from: here, course: (rr["course"] as? NSNumber)?.doubleValue); return
        }
        if r["arrived"] as? Bool == true {
            GCMVoice.shared.speak(CarPlayArrive.text(name: dest?.1, address: destAddress))
            endTrip(arrived: true); return
        }
        let idx = min(max(1, (r["idx"] as? NSNumber)?.intValue ?? step), p.maneuvers.count - 1)
        if idx != step { step = idx; pushManeuvers(s, p) }
        if let say = r["say"] as? String { GCMVoice.shared.speak(say) }
        let d = num("toNext") ?? 0, rest = num("remaining") ?? 0
        if let cur = s.upcomingManeuvers.first {
            s.updateEstimates(estimates(d, d / p.speed), for: cur)
            if #available(iOS 17.4, *) { s.maneuverState = d < 60 ? .execute : d < 250 ? .prepare : .continue }
        }
        mapTemplate.update(estimates(rest, rest / p.speed), for: s.trip, with: .default)
    }

    /// Trim the drawn line behind the driver (t446u), at most once a second and only while on the route.
    /// plan.line stays whole for off-route checks and rerouting.
    func trimRoute(_ here: CLLocation, pts: [(Double, Double)], off: Double) {
        guard off < 30, Date().timeIntervalSince(lastTrim) >= 1 else { return }
        lastTrim = Date()
        var c = CarPlayTrim.ahead(of: (here.coordinate.latitude, here.coordinate.longitude), line: pts).map { CLLocationCoordinate2D(latitude: $0.0, longitude: $0.1) }
        let m = mapVC.map, old = m.overlays.filter { $0 is RouteLine }
        m.addOverlay(RouteLine(coordinates: &c, count: c.count), level: .aboveLabels)
        m.removeOverlays(old)
    }

    #if DEBUG
    // CI screenshot hook: pretend to drive. Places the car ~120 m before each maneuver in turn.
    func demoDrive(every sec: Double) {
        var shown = false
        Timer.scheduledTimer(withTimeInterval: sec, repeats: true) { [weak self] t in
            guard let self = self, let p = self.plan, let s = self.session else { t.invalidate(); return }
            if shown { self.step += 1; guard self.step < p.maneuvers.count else { t.invalidate(); return }; self.pushManeuvers(s, p) }
            let here = self.pointBefore(p.maneuvers[self.step].coord, on: p.line, meters: 120)
            self.mapVC.map.setRegion(MKCoordinateRegion(center: here.coordinate, latitudinalMeters: 700, longitudinalMeters: 700), animated: true)
            self.progress(here); shown = true
            NSLog("GCMCarPlay demo step %d: %@", self.step, s.upcomingManeuvers.first?.instructionVariants.first ?? "")
        }
    }
    func pointBefore(_ target: CLLocationCoordinate2D, on line: [CLLocationCoordinate2D], meters: Double) -> CLLocation {
        let L = line.map { CLLocation(latitude: $0.latitude, longitude: $0.longitude) }
        guard !L.isEmpty else { return CLLocation(latitude: target.latitude, longitude: target.longitude) }
        let t = CLLocation(latitude: target.latitude, longitude: target.longitude)
        var i = L.indices.min(by: { L[$0].distance(from: t) < L[$1].distance(from: t) }) ?? 0
        var left = meters
        while i > 0, left > 0 { left -= L[i].distance(from: L[i - 1]); i -= 1 }
        return L[i]
    }
    #endif
}