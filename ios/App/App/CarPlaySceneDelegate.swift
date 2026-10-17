import UIKit
import CarPlay
import MapKit
import CoreLocation

// MARK: - Models decoded from GCMCarPlay.plan()

struct GCMManeuver {
    let type: String, text: String, road: String, meters: Double, risky: Bool, coord: CLLocationCoordinate2D
    init?(_ d: [String: Any]) {
        guard let t = d["type"] as? String, let lat = d["lat"] as? Double, let lon = d["lon"] as? Double else { return nil }
        type = t; text = d["text"] as? String ?? ""; road = d["road"] as? String ?? ""
        meters = (d["meters"] as? NSNumber)?.doubleValue ?? 0; risky = d["risky"] as? Bool ?? false
        coord = CLLocationCoordinate2D(latitude: lat, longitude: lon)
    }
    var symbol: String {
        switch type {
        case "left": return "arrow.turn.up.left"
        case "right": return "arrow.turn.up.right"
        case "slight_left": return "arrow.up.left"
        case "slight_right": return "arrow.up.right"
        case "uturn": return "arrow.uturn.down"
        case "arrive": return "mappin.circle.fill"
        default: return "arrow.up"
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
        // CI screenshot hook: `simctl launch <dev> <bundle> -GCMCarPlayDemo YES` plans a demo trip, then starts guidance.
        if UserDefaults.standard.bool(forKey: "GCMCarPlayDemo") {
            DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
                self?.choose(["name": "Crystal Pier", "lat": 32.7950, "lon": -117.2560])
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
                guard let self = self, let trip = self.lastTrip, let c = trip.routeChoices.first else { return }
                self.mapTemplate(self.mapTemplate, startedTrip: trip, using: c)
            }
        }
        #endif
        GCMBridge.shared.call("status()") { [weak self] any in
            guard let self = self, let d = any as? [String: Any] else { return }
            if let m = d["mode"] as? String { self.mode = m; self.refreshButtons() }
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
    func estimates(_ m: Double, _ s: Double) -> CPTravelEstimates {
        CPTravelEstimates(distanceRemaining: Measurement(value: m / 1609.34, unit: UnitLength.miles), timeRemaining: s)
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
        step = p.maneuvers.count > 1 ? 1 : 0
        s.upcomingManeuvers = p.maneuvers.dropFirst(step).prefix(2).map(cpManeuver)
        let end = CPBarButton(title: "End") { [weak self] _ in self?.endTrip(arrived: false) }
        mapTemplate.trailingNavigationBarButtons = [end]
        if let c = loc.location?.coordinate {
            mapVC.map.setRegion(MKCoordinateRegion(center: c, latitudinalMeters: 600, longitudinalMeters: 600), animated: true)
            mapVC.map.setUserTrackingMode(.followWithHeading, animated: true)
        }
    }
    func cpManeuver(_ m: GCMManeuver) -> CPManeuver {
        let c = CPManeuver()
        c.instructionVariants = [m.text, m.road.isEmpty ? m.text : m.road]
        c.symbolImage = UIImage(systemName: m.symbol)
        c.initialTravelEstimates = estimates(m.meters, m.meters / 9.8)
        if m.risky { c.attributedInstructionVariants = [NSAttributedString(string: "⚠️ " + m.text)] }
        return c
    }
    func endTrip(arrived: Bool) {
        if arrived { session?.finishTrip() } else { session?.cancelTrip() }
        session = nil; plan = nil
        mapVC.map.removeOverlays(mapVC.map.overlays.filter { $0 is RouteLine })
        mapVC.map.setUserTrackingMode(.none, animated: false)
        refreshButtons()
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let s = session, let p = plan, let here = locations.last, step < p.maneuvers.count else { return }
        let next = p.maneuvers[step]
        let d = here.distance(from: CLLocation(latitude: next.coord.latitude, longitude: next.coord.longitude))
        if d < 25 {
            if next.type == "arrive" { endTrip(arrived: true); return }
            step += 1
            s.upcomingManeuvers = p.maneuvers.dropFirst(step).prefix(2).map(cpManeuver)
        }
        if let cur = s.upcomingManeuvers.first {
            s.updateEstimates(estimates(d, d / 9.8), for: cur)
        }
        let rest = p.maneuvers.dropFirst(step).reduce(d) { $0 + $1.meters }
        mapTemplate.update(estimates(rest, rest / 9.8), for: s.trip, with: .default)
    }
}
