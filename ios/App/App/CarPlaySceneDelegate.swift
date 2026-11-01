import UIKit
import CarPlay
import MapKit
import CoreLocation

// MARK: - Models decoded from GCMCarPlay.plan()

struct GCMManeuver {
    // meters = length of the road after this maneuver; toMeters = distance driven to reach it.
    // turn = signed turn angle in degrees (+ right, - left); used for the junction diagram and junctionExitAngle.
    let type: String, text: String, short: String, road: String, meters: Double, toMeters: Double, turn: Double, mph: Int?, risky: Bool, coord: CLLocationCoordinate2D
    init?(_ d: [String: Any]) {
        guard let t = d["type"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return nil }
        type = t; text = d["text"] as? String ?? ""; road = d["road"] as? String ?? ""
        short = d["short"] as? String ?? text
        meters = (d["meters"] as? NSNumber)?.doubleValue ?? 0; risky = d["risky"] as? Bool ?? false
        toMeters = (d["toMeters"] as? NSNumber)?.doubleValue ?? 0
        turn = (d["turn"] as? NSNumber)?.doubleValue ?? 0
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
    var lastTrip: CPTrip?
    var overlayTimer: Timer?
    var showLegal = true
    var following = false      // map follows the location dot until the driver pans
    var gotFix = false
    var panLast = CGPoint.zero
    var offRoute = CarPlayOffRoute()
    var tour: CarPlayTour?
    var lastTrim = Date.distantPast
    var rerouting = false
    var dest: (CLLocationCoordinate2D, String)?
    var camHeading: Double?
    var mode: String { "lsv" }
    var codeSearch: CPSearchTemplate?   // rental code entry (Max t449u)

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
        interfaceController.setRootTemplate(mapTemplate, animated: false, completion: { _, _ in })
        loc.delegate = self
        loc.desiredAccuracy = kCLLocationAccuracyBestForNavigation
        loc.activityType = .automotiveNavigation
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
        following = true
        mapVC.map.setRegion(MKCoordinateRegion(center: c, latitudinalMeters: CarPlayStartView.drivingMeters, longitudinalMeters: CarPlayStartView.drivingMeters), animated: animated)
        mapVC.map.setUserTrackingMode(.follow, animated: animated)
    }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways: manager.startUpdatingLocation()
        default: break
        }
    }
    // Panning on the CarPlay screen stops follow mode; the location button turns it back on.
    func mapTemplateDidShowPanningInterface(_ mapTemplate: CPMapTemplate) { stopFollowing() }
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
        // translation is cumulative since the gesture began; apply only the new part.
        let dx = translation.x - panLast.x, dy = translation.y - panLast.y; panLast = translation
        let m = mapVC.map, mid = CGPoint(x: m.bounds.midX - dx, y: m.bounds.midY - dy)
        m.setCenter(m.convert(mid, toCoordinateFrom: m), animated: false)
    }
    func stopFollowing() {
        following = false
        mapVC.map.setUserTrackingMode(.none, animated: false)
    }

    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didDisconnectInterfaceController interfaceController: CPInterfaceController, from window: CPWindow) {
        loc.stopUpdatingLocation()
        session?.cancelTrip()
        session = nil; interface = nil; self.window = nil
    }

    // Buttons
    func refreshButtons() {
        let searchBtn = CPBarButton(title: "Search") { [weak self] _ in self?.openSearch() }
        let savedBtn = CPBarButton(title: "Recent") { [weak self] _ in self?.openRecents() }
        mapTemplate.leadingNavigationBarButtons = [searchBtn, savedBtn]
        let gear = CPBarButton(image: UIImage(systemName: "gearshape.fill") ?? UIImage()) { [weak self] _ in self?.openSettings() }
        mapTemplate.trailingNavigationBarButtons = [CPBarButton(title: "Experiences") { [weak self] _ in self?.openExperiences() }, gear]
        let recenter = CPMapButton { [weak self] _ in
            self?.startFollowing(animated: true)
        }
        recenter.image = UIImage(systemName: "location.fill")
        let layers = CPMapButton { [weak self] _ in
            guard let self = self else { return }
            self.showLegal.toggle(); self.scheduleOverlay(now: true)
        }
        layers.image = UIImage(systemName: showLegal ? "road.lanes" : "map")
        let zin = CPMapButton { [weak self] _ in self?.zoom(0.5) }
        zin.image = UIImage(systemName: "plus.magnifyingglass")
        let zout = CPMapButton { [weak self] _ in self?.zoom(2) }
        zout.image = UIImage(systemName: "minus.magnifyingglass")
        mapTemplate.mapButtons = [recenter, layers, zin, zout]
    }

    func zoom(_ f: Double) {
        var r = mapVC.map.region
        r.span.latitudeDelta = min(1, max(0.002, r.span.latitudeDelta * f))
        r.span.longitudeDelta = min(1, max(0.002, r.span.longitudeDelta * f))
        mapVC.map.setRegion(r, animated: true)
        // setRegion drops MKMapView tracking; keep following at the new zoom.
        if following { mapVC.map.setUserTrackingMode(.follow, animated: true) }
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
    func searchTemplate(_ searchTemplate: CPSearchTemplate, updatedSearchText searchText: String, completionHandler: @escaping ([CPListItem]) -> Void) {
        if searchTemplate === codeSearch {
            completionHandler(CarPlayRentalCode.rows(for: searchText).map { r in
                let it = CPListItem(text: r.text, detailText: r.detail)
                if let c = r.code { it.userInfo = ["rentalCode": c] }
                return it
            })
            return
        }
        guard searchText.count >= 2 else { completionHandler([]); return }
        let c = loc.location?.coordinate ?? mapVC.map.centerCoordinate
        GCMBridge.shared.call("search(q,lat,lon)", ["q": searchText, "lat": c.latitude, "lon": c.longitude]) { any in
            var items = (any as? [[String: Any]] ?? []).compactMap { d -> CPListItem? in
                guard let n = d["name"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return nil }
                let it = CPListItem(text: n, detailText: d["sub"] as? String)
                it.userInfo = ["name": n, "lat": lat, "lon": lon]
                return it
            }
            if !items.isEmpty { completionHandler(items); return }
            let req = MKLocalSearch.Request()
            req.naturalLanguageQuery = searchText
            req.region = MKCoordinateRegion(center: c, latitudinalMeters: 20000, longitudinalMeters: 20000)
            MKLocalSearch(request: req).start { resp, _ in
                items = (resp?.mapItems ?? []).prefix(8).map { mi in
                    let it = CPListItem(text: mi.name ?? "Place", detailText: mi.placemark.title)
                    it.userInfo = ["name": mi.name ?? "Place", "lat": mi.placemark.coordinate.latitude, "lon": mi.placemark.coordinate.longitude]
                    return it
                }
                completionHandler(items)
            }
        }
    }
    func searchTemplate(_ searchTemplate: CPSearchTemplate, selectedResult item: CPListItem, completionHandler: @escaping () -> Void) {
        if searchTemplate === codeSearch {
            if let c = (item.userInfo as? [String: Any])?["rentalCode"] as? String { enterCode(c) }
            completionHandler()
            return
        }
        if let d = item.userInfo as? [String: Any] { choose(d) }
        completionHandler()
    }

    // Recents (saved destinations)
    var recents: [[String: Any]] {
        get { UserDefaults.standard.array(forKey: "gcm-cp-recents") as? [[String: Any]] ?? [] }
        set { UserDefaults.standard.set(Array(newValue.prefix(12)), forKey: "gcm-cp-recents") }
    }
    func openRecents() {
        let items: [CPListItem] = recents.map { d in
            let it = CPListItem(text: d["name"] as? String ?? "Place", detailText: nil)
            it.handler = { [weak self] _, done in self?.choose(d); done() }
            return it
        }
        let t = CPListTemplate(title: "Recent", sections: [CPListSection(items: items)])
        t.emptyViewTitleVariants = ["No recent destinations"]
        interface?.pushTemplate(t, animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } })
    }

    // Trip preview
    func choose(_ d: [String: Any], remember: Bool = true) {
        guard let name = d["name"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return }
        if remember { recents = [d] + recents.filter { ($0["name"] as? String) != name } }
        if (interface?.templates.count ?? 0) > 1 { interface?.popToRootTemplate(animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }
        guard let from = loc.location?.coordinate ?? Optional(mapVC.map.centerCoordinate) else { return }
        let to = CLLocationCoordinate2D(latitude: lat, longitude: lon)
        dest = (to, name)
        GCMBridge.shared.call("plan(f,t,m,false)", ["f": ["lat": from.latitude, "lon": from.longitude], "t": ["lat": lat, "lon": lon], "m": mode]) { [weak self] any in
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
        mapTemplate.update(estimates(p.meters, p.minutes * 60), for: trip, with: .default)
        let end = CPBarButton(title: "End") { [weak self] _ in self?.endTrip(arrived: false) }
        mapTemplate.trailingNavigationBarButtons = [end]
        if let c = loc.location?.coordinate {
            mapVC.map.setRegion(MKCoordinateRegion(center: c, latitudinalMeters: 600, longitudinalMeters: 600), animated: true)
            following = true; camHeading = nil
            mapVC.map.setUserTrackingMode(.follow, animated: true)
        }
    }
    // CPManeuver from one step of the legal-road route (public/carplay.js maneuvers()).
    func cpManeuver(_ m: GCMManeuver) -> CPManeuver {
        let c = CPManeuver()
        let speed = plan?.speed ?? 9.8
        // longest first; CarPlay picks the variant that fits the guidance card
        c.instructionVariants = [m.short, m.road.isEmpty ? m.short : m.road]  // short first keeps the card compact
        c.dashboardInstructionVariants = [m.short]
        c.notificationInstructionVariants = [m.text]
        let cfg = UIImage.SymbolConfiguration(pointSize: 40, weight: .bold)
        c.symbolImage = UIImage(systemName: m.symbol, withConfiguration: cfg)?.withRenderingMode(.alwaysTemplate)
        c.dashboardSymbolImage = c.symbolImage
        c.notificationSymbolImage = c.symbolImage
        c.initialTravelEstimates = estimates(m.toMeters, m.toMeters / speed)
        // No junctionImage: CarPlay draws it in place of the instruction text, and our road graph has no lane or
        // junction artwork worth showing at simple intersections. Junction geometry goes in junctionExitAngle below.
        if m.risky { c.attributedInstructionVariants = [NSAttributedString(string: "⚠️ " + m.short)] }
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
    /// Heading-up like the phone: rotate the camera to the route bearing ~25 m ahead (GPS course off route).
    func headingUp(_ here: CLLocation, off: Double, line: [(Double, Double)]) {
        // Chevron along travel: GPS course, else the route-bearing camera heading (points up in heading-up).
        if let h = here.course >= 0 ? here.course : camHeading { mapVC.puck?.point(heading: h, mapHeading: mapVC.map.camera.heading) }
        guard following else { return }
        let me = (here.coordinate.latitude, here.coordinate.longitude)
        guard let h = CarPlayHeading.pick(current: camHeading, routeBearing: CarPlayHeading.routeBearing(from: me, line: line), offRouteM: off,
                                          course: here.course, speed: here.speed) else { return }
        camHeading = h
        let cam = mapVC.map.camera.copy() as! MKMapCamera
        cam.heading = h; cam.centerCoordinate = here.coordinate
        mapVC.map.setCamera(cam, animated: true)
        mapVC.map.setUserTrackingMode(.follow, animated: false)
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
    func reroute(from here: CLLocation) {
        guard let s = session, let to = dest?.0 else { return }
        rerouting = true
        NSLog("GCMCarPlay reroute from %.5f,%.5f", here.coordinate.latitude, here.coordinate.longitude)
        if #available(iOS 15.4, *) { s.pauseTrip(for: .rerouting, description: "Rerouting on legal roads", turnCardColor: nil) } else { s.pauseTrip(for: .rerouting, description: "Rerouting on legal roads") }
        // Driving (>= 1.5 m/s with a valid course): replan forward on this road, no U-turn first (Max t433u).
        let h: Any = (here.speed >= 1.5 && here.course >= 0) ? here.course : NSNull()
        GCMBridge.shared.call("plan(f,t,m,false,h)", ["f": ["lat": here.coordinate.latitude, "lon": here.coordinate.longitude], "t": ["lat": to.latitude, "lon": to.longitude], "m": mode, "h": h]) { [weak self] any in
            guard let self = self else { return }
            defer { self.rerouting = false; self.offRoute.reset() }
            guard let s = self.session, let p = GCMPlan(any) else {
                NSLog("GCMCarPlay reroute failed")
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
            NSLog("GCMCarPlay rerouted: %d maneuvers, %.0f m", p.maneuvers.count, p.meters)
            if let here = self.loc.location { self.progress(here) }
        }
    }
    func endTrip(arrived: Bool) {
        if arrived, session != nil { GCMBridge.shared.track("route_completed", ["mi": plan?.miles ?? 0]) }
        if arrived { session?.finishTrip() } else { session?.cancelTrip() }
        session = nil; plan = nil; offRoute.reset(); rerouting = false
        mapVC.guiding = false
        mapVC.map.removeOverlays(mapVC.map.overlays.filter { $0 is RouteLine })
        mapVC.map.removeAnnotations(mapVC.map.annotations.filter { $0 is DestPin })
        refreshButtons()
        startFollowing(animated: true)
        if arrived { celebrate(); tourArrived() } else { endTour() }
    }

    // MARK: Arrival celebration (t446u): ~3 s of cartoon unicorns over our own map view, non-interactive,
    // only after arrival. Falls back to a short alert if the map view is not on screen.
    func celebrate() {
        let host = mapVC.view!
        guard host.window != nil, let art = UIImage(named: "Unicorn") else {
            presentAlert(["Have a wonderful life, you legend! 🦄", "You made it! 🦄"], [CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.dismiss() }])
            return
        }
        let layer = UIView(frame: host.bounds); layer.isUserInteractionEnabled = false
        layer.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        let label = UILabel(); label.text = "Have a wonderful life, you legend! 🦄"
        label.font = .systemFont(ofSize: 22, weight: .heavy); label.textColor = .white; label.textAlignment = .center
        label.adjustsFontSizeToFitWidth = true; label.minimumScaleFactor = 0.5
        label.backgroundColor = UIColor(red: 0.42, green: 0.25, blue: 0.75, alpha: 0.85); label.layer.cornerRadius = 14; label.clipsToBounds = true
        let b = host.bounds, safe = b.inset(by: host.safeAreaInsets)
        label.frame = CGRect(x: safe.minX + 12, y: safe.minY + 10, width: safe.width - 24, height: 44)
        layer.addSubview(label); host.addSubview(layer)
        for i in 0..<3 {
            let h = min(90, safe.height / 3.2), w = h * 1.2
            let v = UIImageView(image: art); v.frame = CGRect(x: -w - CGFloat(i) * 70, y: safe.minY + 64 + CGFloat(i) * (h * 0.55), width: w, height: h)
            layer.addSubview(v)
            UIView.animate(withDuration: 2.6, delay: Double(i) * 0.15, options: [.curveEaseInOut]) { v.frame.origin.x = b.maxX + 20 }
            UIView.animate(withDuration: 0.3, delay: 0, options: [.autoreverse, .repeat, .allowUserInteraction]) { v.transform = CGAffineTransform(translationX: 0, y: -8) }
        }
        #if DEBUG
        NSLog("GCMCarPlay celebrate")
        #endif
        UIView.animate(withDuration: 0.4, delay: 3.0, options: []) { layer.alpha = 0 } completion: { _ in layer.removeFromSuperview() }
    }

    func presentAlert(_ titles: [String], _ actions: [CPAlertAction]) {
        interface?.presentTemplate(CPAlertTemplate(titleVariants: titles, actions: actions), animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } })
    }
    func dismiss() { interface?.dismissTemplate(animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }
    func push(_ t: CPTemplate) { interface?.pushTemplate(t, animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }

    // MARK: Settings / rental code (Max t449u). Typing uses CPSearchTemplate, the only CarPlay text entry;
    // the car may lock its keyboard while moving, so every screen also points to the phone's Settings.
    func openSettings() {
        GCMBridge.shared.call("rental()") { [weak self] any in
            DispatchQueue.main.async {
                guard let self = self else { return }
                let d = any as? [String: Any] ?? [:]
                var items: [CPListItem] = []
                if d["ok"] as? Bool == true {
                    let shop = d["shop"] as? String ?? "Rental shop"
                    let active = CPListItem(text: shop, detailText: "Active rental shop")
                    active.handler = { [weak self] _, done in self?.openExperiences(); done() }
                    let remove = CPListItem(text: "Remove \(shop)", detailText: "Stops showing its experiences")
                    remove.handler = { [weak self] _, done in
                        GCMBridge.shared.call("removeRental()") { _ in DispatchQueue.main.async { self?.interface?.popTemplate(animated: true, completion: nil) } }
                        done()
                    }
                    items = [active, remove]
                }
                let enter = CPListItem(text: "Enter rental code", detailText: "Or in Settings in the phone app")
                enter.handler = { [weak self] _, done in self?.openCodeEntry(); done() }
                items.append(enter)
                self.push(CPListTemplate(title: "Settings", sections: [CPListSection(items: items, header: "Rental code", sectionIndexTitle: nil)]))
            }
        }
    }
    func openCodeEntry() {
        let t = CPSearchTemplate()
        t.delegate = self
        codeSearch = t
        push(t)
    }
    func enterCode(_ code: String) {
        GCMBridge.shared.call("enterCode(c)", ["c": code]) { [weak self] any in
            DispatchQueue.main.async {
                guard let self = self else { return }
                let d = any as? [String: Any] ?? [:]
                if d["ok"] as? Bool == true {
                    let shop = d["shop"] as? String ?? "Rental shop"
                    self.presentAlert(["\(shop) unlocked", "Unlocked"], [CPAlertAction(title: "See experiences", style: .default) { [weak self] _ in
                        self?.dismiss()
                        self?.interface?.popToRootTemplate(animated: false, completion: nil)
                        self?.openExperiences()
                    }])
                } else {
                    self.presentAlert([d["reason"] as? String ?? "Could not unlock", "Could not unlock"],
                                      [CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.dismiss() }])
                }
            }
        }
    }

    // MARK: Partner experiences (Max t437s2290). Data: public/carplay.js experiences() / stops(id) from the
    // renter unlock saved on the phone. Short text only; coupon codes only when parked.
    func openExperiences() {
        GCMBridge.shared.call("experiences()") { [weak self] any in
            DispatchQueue.main.async {
                guard let self = self else { return }
                let d = any as? [String: Any] ?? [:]
                guard d["ok"] as? Bool == true else {
                    self.presentAlert([d["reason"] as? String ?? "No rental code yet. Tap the gear to enter one.", "No rental code yet"],
                                      [CPAlertAction(title: "Enter code", style: .default) { [weak self] _ in self?.dismiss(); self?.openCodeEntry() },
                                       CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.dismiss() }])
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
        progress(here)
    }
    func progress(_ here: CLLocation) {
        guard let s = session, let p = plan, step < p.maneuvers.count else { return }
        let pts = p.line.map { ($0.latitude, $0.longitude) }, me = (here.coordinate.latitude, here.coordinate.longitude)
        let off = CarPlayOffRoute.distance(from: me, toLine: pts)
        headingUp(here, off: off, line: pts)
        trimRoute(here, pts: pts, off: off)
        if !rerouting, here.horizontalAccuracy >= 0, here.horizontalAccuracy < 50 {
            if offRoute.update(offMeters: off, now: here.timestamp.timeIntervalSince1970) { reroute(from: here); return }
        }
        let next = p.maneuvers[step]
        let d = here.distance(from: CLLocation(latitude: next.coord.latitude, longitude: next.coord.longitude))
        // Passed it without coming within 25 m (GPS jitter or a cut corner): we're already closer to the one after.
        var passed = false
        if step + 1 < p.maneuvers.count {
            let after = CLLocation(latitude: p.maneuvers[step + 1].coord.latitude, longitude: p.maneuvers[step + 1].coord.longitude)
            passed = d < 60 && here.distance(from: after) < after.distance(from: CLLocation(latitude: next.coord.latitude, longitude: next.coord.longitude))
        }
        if d < 25 || passed {
            if next.type == "arrive" { endTrip(arrived: true); return }
            step += 1
            pushManeuvers(s, p)
            progress(here); return
        }
        if let cur = s.upcomingManeuvers.first {
            s.updateEstimates(estimates(d, d / p.speed), for: cur)
            if #available(iOS 17.4, *) { s.maneuverState = d < 60 ? .execute : d < 250 ? .prepare : .continue }
        }
        let rest = p.maneuvers.dropFirst(step + 1).reduce(d) { $0 + $1.toMeters }
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