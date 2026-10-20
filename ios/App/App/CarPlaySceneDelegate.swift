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

// Junction diagram for CPManeuver.junctionImage: approach road from the bottom, exit road at the real turn angle,
// drawn from the route geometry (no lane data exists in our road graph, so no lane arrows).
enum JunctionArt {
    static func image(turn: Double, size: CGFloat = 120) -> UIImage {
        UIGraphicsImageRenderer(size: CGSize(width: size, height: size)).image { ctx in
            let g = ctx.cgContext, c = CGPoint(x: size / 2, y: size * 0.55)
            g.setLineCap(.round); g.setLineJoin(.round)
            // cross street stubs (grey), then approach + exit (white)
            g.setStrokeColor(UIColor(white: 0.55, alpha: 1).cgColor); g.setLineWidth(size * 0.1)
            for a in [-90.0, 90.0, 0.0] where abs(a - turn) > 20 { g.move(to: c); g.addLine(to: pt(c, a, size * 0.42)) }
            g.strokePath()
            g.setStrokeColor(UIColor.white.cgColor); g.setLineWidth(size * 0.12)
            g.move(to: CGPoint(x: c.x, y: size)); g.addLine(to: c); g.addLine(to: pt(c, turn, size * 0.42)); g.strokePath()
            // arrow head on the exit
            let tip = pt(c, turn, size * 0.46), l = pt(tip, turn + 150, size * 0.16), r = pt(tip, turn - 150, size * 0.16)
            g.setFillColor(UIColor.white.cgColor); g.move(to: tip); g.addLine(to: l); g.addLine(to: r); g.closePath(); g.fillPath()
        }
    }
    // angle 0 = straight up, + = clockwise (right)
    static func pt(_ c: CGPoint, _ deg: Double, _ r: CGFloat) -> CGPoint {
        let a = deg * .pi / 180
        return CGPoint(x: c.x + r * CGFloat(sin(a)), y: c.y - r * CGFloat(cos(a)))
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
final class OkLine: MKPolyline {}
final class AvoidLine: MKPolyline {}

// MARK: - Map view controller shown in the CarPlay window

final class CarPlayMapViewController: UIViewController, MKMapViewDelegate {
    let map = MKMapView()
    var onRegionChange: ((MKCoordinateRegion) -> Void)?
    override func viewDidLoad() {
        super.viewDidLoad()
        map.frame = view.bounds
        map.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        map.delegate = self
        map.showsUserLocation = true
        map.pointOfInterestFilter = .excludingAll
        view.addSubview(map)
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
        refreshButtons()
        interfaceController.setRootTemplate(mapTemplate, animated: false, completion: { _, _ in })
        loc.delegate = self
        loc.requestWhenInUseAuthorization()
        loc.startUpdatingLocation()
        #if DEBUG
        NSLog("GCMCarPlay scene connected")
        #endif
        GCMBridge.shared.track("session")
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
            if self.loc.location == nil, let c = d["center"] as? [Double], c.count == 2 {
                self.mapVC.map.setRegion(MKCoordinateRegion(center: CLLocationCoordinate2D(latitude: c[0], longitude: c[1]), latitudinalMeters: 2500, longitudinalMeters: 2500), animated: false)
            }
        }
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
        mapTemplate.trailingNavigationBarButtons = []
        let recenter = CPMapButton { [weak self] _ in
            guard let self = self, let c = self.loc.location?.coordinate else { return }
            self.mapVC.map.setRegion(MKCoordinateRegion(center: c, latitudinalMeters: 1500, longitudinalMeters: 1500), animated: true)
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
    func choose(_ d: [String: Any]) {
        guard let name = d["name"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return }
        recents = [d] + recents.filter { ($0["name"] as? String) != name }
        if (interface?.templates.count ?? 0) > 1 { interface?.popToRootTemplate(animated: true, completion: { _, e in if let e = e { NSLog("CarPlay template op: %@", e.localizedDescription) } }) }
        guard let from = loc.location?.coordinate ?? Optional(mapVC.map.centerCoordinate) else { return }
        let to = CLLocationCoordinate2D(latitude: lat, longitude: lon)
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
        GCMBridge.shared.track("route_started", ["mi": p.miles])
        step = p.maneuvers.count > 1 ? 1 : 0
        pushManeuvers(s, p)
        mapTemplate.update(estimates(p.meters, p.minutes * 60), for: trip, with: .default)
        let end = CPBarButton(title: "End") { [weak self] _ in self?.endTrip(arrived: false) }
        mapTemplate.trailingNavigationBarButtons = [end]
        if let c = loc.location?.coordinate {
            mapVC.map.setRegion(MKCoordinateRegion(center: c, latitudinalMeters: 600, longitudinalMeters: 600), animated: true)
            mapVC.map.setUserTrackingMode(.followWithHeading, animated: true)
        }
    }
    // CPManeuver from one step of the legal-road route (public/carplay.js maneuvers()).
    func cpManeuver(_ m: GCMManeuver) -> CPManeuver {
        let c = CPManeuver()
        let speed = plan?.speed ?? 9.8
        // longest first; CarPlay picks the variant that fits the guidance card
        c.instructionVariants = [m.text, m.short, m.road.isEmpty ? m.short : m.road]
        c.dashboardInstructionVariants = [m.short]
        c.notificationInstructionVariants = [m.text]
        let cfg = UIImage.SymbolConfiguration(pointSize: 40, weight: .bold)
        c.symbolImage = UIImage(systemName: m.symbol, withConfiguration: cfg)?.withRenderingMode(.alwaysTemplate)
        c.dashboardSymbolImage = c.symbolImage
        c.notificationSymbolImage = c.symbolImage
        c.initialTravelEstimates = estimates(m.toMeters, m.toMeters / speed)
        if m.isTurn { c.junctionImage = JunctionArt.image(turn: m.turn) }
        if m.risky { c.attributedInstructionVariants = [NSAttributedString(string: "⚠️ " + m.text)] }
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
    func endTrip(arrived: Bool) {
        if arrived, session != nil { GCMBridge.shared.track("route_completed", ["mi": plan?.miles ?? 0]) }
        if arrived { session?.finishTrip() } else { session?.cancelTrip() }
        session = nil; plan = nil
        mapVC.map.removeOverlays(mapVC.map.overlays.filter { $0 is RouteLine })
        mapVC.map.setUserTrackingMode(.none, animated: false)
        refreshButtons()
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let here = locations.last else { return }
        progress(here)
    }
    func progress(_ here: CLLocation) {
        guard let s = session, let p = plan, step < p.maneuvers.count else { return }
        let next = p.maneuvers[step]
        let d = here.distance(from: CLLocation(latitude: next.coord.latitude, longitude: next.coord.longitude))
        if d < 25 {
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