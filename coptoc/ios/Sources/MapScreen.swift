import SwiftUI
import MapKit

struct MapScreen: View {
    @Environment(COPStore.self) private var store
    /// §3.4 the overlays: a section's tab brings its own things forward and dims the rest — an overlay sits on the base, the base stays.
    /// S2 draws the NAIs and the threats in full; S3 draws every movement leg by leg; S4 / S6 color every site by its health.
    var layer: String? = nil
    var showsSites: Bool { store.showSites }
    var showsThreatsLayer: Bool { store.showThreats }
    var showsRoutesLayer: Bool { store.showRoutes }
    var threatAlpha: Double { layer == nil || layer == "S2" ? 1 : 0.3 }
    var routeAlpha: Double { layer == nil || layer == "S3" ? 1 : layer == "S4" ? 0.6 : 0.3 }
    var peopleAlpha: Double { layer == nil || layer == "S1" || layer == "S3" ? 1 : 0.3 }
    var eventAlpha: Double { layer == nil || layer == "S3" ? 1 : 0.3 }
    var showsNAIs: Bool { layer == "S2" }
    var showsTravelers: Bool { store.showTravelers }
    var showsEvents: Bool { store.showEvents }
    /// Where a phone that remembers nothing and cannot reach the API opens: the Bay Area. Replaced on appear by the
    /// board this device was left on, and on the first snapshot by the server's answer for this deployment.
    @State private var camera: MapCameraPosition = .region(MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.72, longitude: -122.16), latitudinalMeters: 140_000, longitudinalMeters: 140_000))
    @State private var currentRegion: MKCoordinateRegion = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.72, longitude: -122.16), latitudinalMeters: 140_000, longitudinalMeters: 140_000)
    @State private var showOverlayMenu = false

    var viewportWidthMiles: Double {
        let lat = currentRegion.center.latitude
        let metersPerDegLon = 111_319.5 * cos(lat * Double.pi / 180.0)
        let meters = max(1.0, currentRegion.span.longitudeDelta * metersPerDegLon)
        return meters / 1609.344
    }

    var viewportWidthKm: Double {
        let lat = currentRegion.center.latitude
        let metersPerDegLon = 111_319.5 * cos(lat * Double.pi / 180.0)
        let meters = max(1.0, currentRegion.span.longitudeDelta * metersPerDegLon)
        return meters / 1000.0
    }

    var body: some View {
        @Bindable var store = store
        ZStack(alignment: .topLeading) {
            Map(position: $camera) {
                if let snap = store.snapshot {
                    threatsContent(snap: snap)
                    graphicsContent(snap: snap)
                    routesContent(snap: snap)
                    markersContent(snap: snap)
                }
            }
            .mapStyle(.standard(elevation: .flat, pointsOfInterest: .excludingAll))
            .mapControls { MapCompass() }

            // Tap background to dismiss overlay menu when open
            if showOverlayMenu {
                Color.black.opacity(0.001)
                    .ignoresSafeArea()
                    .onTapGesture {
                        withAnimation(.snappy(duration: 0.18)) { showOverlayMenu = false }
                    }
            }

            // Floating layers icon button & dropdown menu
            VStack(alignment: .leading, spacing: 6) {
                Button {
                    withAnimation(.snappy(duration: 0.2)) {
                        showOverlayMenu.toggle()
                    }
                } label: {
                    Image(systemName: "square.3.layers.3d")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(showOverlayMenu ? .white : Color.white)
                        .frame(width: 38, height: 38)
                        .background(showOverlayMenu ? Theme.blue : Theme.panel.opacity(0.94), in: RoundedRectangle(cornerRadius: 8))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(showOverlayMenu ? Theme.blue : Theme.line, lineWidth: 1))
                        .shadow(color: .black.opacity(0.4), radius: 6, y: 2)
                }
                .buttonStyle(.plain)

                if showOverlayMenu {
                    let allOn = store.showSites && store.showTravelers && store.showRoutes && store.showThreats && store.showEvents
                    let threatMode: String = {
                        if !store.showThreats { return "OFF" }
                        return store.outlineOnlyThreats ? "OUTLINE" : "FILL"
                    }()
                    VStack(alignment: .leading, spacing: 8) {
                        // Single line: 2-stage LAYERS toggle and multi-stage THREAT toggle
                        HStack(spacing: 6) {
                            // 2-stage Layers toggle
                            Button {
                                withAnimation(.snappy(duration: 0.15)) {
                                    let target = !allOn
                                    store.showSites = target
                                    store.showTravelers = target
                                    store.showRoutes = target
                                    store.showThreats = target
                                    store.showEvents = target
                                }
                            } label: {
                                HStack(spacing: 3) {
                                    Circle()
                                        .fill(allOn ? Theme.blue : Theme.dim.opacity(0.4))
                                        .frame(width: 5, height: 5)
                                    Text(allOn ? "LAYERS · ON" : "LAYERS · OFF")
                                        .font(.system(size: 8, weight: allOn ? .bold : .medium, design: .monospaced))
                                        .foregroundStyle(allOn ? Color.white : Theme.dim)
                                        .lineLimit(1)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 6)
                                .padding(.horizontal, 2)
                                .background(allOn ? Theme.blue.opacity(0.2) : Theme.panel2, in: RoundedRectangle(cornerRadius: 6))
                                .overlay(RoundedRectangle(cornerRadius: 6).stroke(allOn ? Theme.blue : Theme.line, lineWidth: 1))
                            }
                            .buttonStyle(.plain)

                            // Multi-stage Threat toggle (FILL -> OUTLINE -> OFF)
                            Button {
                                withAnimation(.snappy(duration: 0.15)) {
                                    switch threatMode {
                                    case "FILL":
                                        store.outlineOnlyThreats = true
                                    case "OUTLINE":
                                        store.showThreats = false
                                    default: // OFF
                                        store.showThreats = true
                                        store.outlineOnlyThreats = false
                                    }
                                }
                            } label: {
                                HStack(spacing: 3) {
                                    Text(threatMode == "FILL" ? "●" : threatMode == "OUTLINE" ? "○" : "✕")
                                        .font(.system(size: 8.5, weight: .bold))
                                        .foregroundStyle(threatMode == "FILL" ? Theme.amber : threatMode == "OUTLINE" ? Theme.blue : Theme.dim.opacity(0.4))
                                    Text("THREAT · \(threatMode)")
                                        .font(.system(size: 8, weight: threatMode != "OFF" ? .bold : .medium, design: .monospaced))
                                        .foregroundStyle(threatMode != "OFF" ? Color.white : Theme.dim)
                                        .lineLimit(1)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 6)
                                .padding(.horizontal, 2)
                                .background(
                                    threatMode == "FILL" ? Theme.amber.opacity(0.2) :
                                    threatMode == "OUTLINE" ? Theme.blue.opacity(0.12) : Theme.panel2,
                                    in: RoundedRectangle(cornerRadius: 6)
                                )
                                .overlay(
                                    RoundedRectangle(cornerRadius: 6)
                                        .stroke(
                                            threatMode == "FILL" ? Theme.amber :
                                            threatMode == "OUTLINE" ? Theme.blue : Theme.line,
                                            lineWidth: 1
                                        )
                                )
                            }
                            .buttonStyle(.plain)
                        }

                        // Miles or Kilometers toggle
                        HStack(spacing: 2) {
                            let isMi = store.distanceUnit == "mi"
                            Button {
                                withAnimation(.snappy(duration: 0.15)) {
                                    store.distanceUnit = "mi"
                                }
                            } label: {
                                Text("MILES")
                                    .font(.system(size: 8, weight: isMi ? .bold : .medium, design: .monospaced))
                                    .foregroundStyle(isMi ? Color.white : Theme.dim)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 5)
                                    .background(isMi ? Theme.blue : Color.clear, in: RoundedRectangle(cornerRadius: 4))
                            }
                            .buttonStyle(.plain)

                            Button {
                                withAnimation(.snappy(duration: 0.15)) {
                                    store.distanceUnit = "km"
                                }
                            } label: {
                                Text("KILOMETERS")
                                    .font(.system(size: 8, weight: !isMi ? .bold : .medium, design: .monospaced))
                                    .foregroundStyle(!isMi ? Color.white : Theme.dim)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 5)
                                    .background(!isMi ? Theme.blue : Color.clear, in: RoundedRectangle(cornerRadius: 4))
                            }
                            .buttonStyle(.plain)
                        }
                        .padding(2)
                        .background(Theme.panel2, in: RoundedRectangle(cornerRadius: 6))
                        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Theme.line, lineWidth: 1))

                        Divider().overlay(Theme.line)

                        // Selectable layer pills
                        VStack(alignment: .leading, spacing: 6) {
                            LayerPill(label: "Sites & Facilities", icon: "◆", isOn: Binding(get: { store.showSites }, set: { store.showSites = $0 }))
                            LayerPill(label: "Moving Personnel", icon: "●", isOn: Binding(get: { store.showTravelers }, set: { store.showTravelers = $0 }))
                            LayerPill(label: "Routes & Convoys", icon: "↗", isOn: Binding(get: { store.showRoutes }, set: { store.showRoutes = $0 }))
                            LayerPill(label: "Threats & Hazards", icon: "⚠", isOn: Binding(get: { store.showThreats }, set: { store.showThreats = $0 }))
                            LayerPill(label: "Operations & Events", icon: "★", isOn: Binding(get: { store.showEvents }, set: { store.showEvents = $0 }))
                            LayerPill(label: store.snapshot?.restrictedDenied == true ? "Residences · DENIED" : "Residences",
                                      icon: "⚿",
                                      isOn: Binding(get: { store.showRestricted }, set: { store.showRestricted = $0 }),
                                      disabled: store.snapshot?.restrictedDenied == true)
                        }
                    }
                    .padding(10)
                    .frame(width: 220)
                    .background(Theme.panel.opacity(0.96), in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.line, lineWidth: 1))
                    .shadow(color: .black.opacity(0.6), radius: 16, y: 6)
                    .transition(.opacity.combined(with: .scale(scale: 0.95, anchor: .topLeading)))
                }
            }
            .padding(.top, 8)
            .padding(.leading, 12)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .onAppear { if let r = store.board { camera = .region(r); currentRegion = r } }         // this section inherits the board as it stands
        .onChange(of: store.framedAt) { if let r = store.board { camera = .region(r); currentRegion = r } }
        .onMapCameraChange(frequency: .continuous) { ctx in currentRegion = ctx.region; store.board = ctx.region }   // wherever it is left is where every section finds it
        .onChange(of: store.selection) { _, sel in fly(to: sel) }
    }

    @MapContentBuilder
    private func threatsContent(snap: Snapshot) -> some MapContent {
        if showsNAIs, let nais = snap.nais {
            ForEach(nais) { n in
                MapCircle(center: n.coordinate, radius: n.radiusKm * 1000)
                    .foregroundStyle(healthColor(n.health).opacity(n.priority == 1 ? 0.10 : 0.05))
                    .stroke(healthColor(n.health), style: StrokeStyle(lineWidth: n.priority == 1 ? 1.8 : 1, dash: [5, 4]))
                Annotation(n.name, coordinate: n.labelCoordinate, anchor: .bottom) {
                    NAILabel(nai: n).onTapGesture {
                        if n.subjectType == "location", let id = n.subjectId {
                            store.selection = .site(id)
                        } else if n.subjectType == "event", let id = n.subjectId {
                            store.selection = .event(id)
                        }
                    }
                }
                .annotationTitles(.hidden)
            }
        }
        if showsThreatsLayer {
            ForEach(snap.threats) { t in
                MapCircle(center: t.coordinate, radius: t.radiusKm * 1000)
                    .foregroundStyle(Theme.severity(t.severity).opacity(store.outlineOnlyThreats ? 0.0 : 0.16 * threatAlpha))
                    .stroke(Theme.severity(t.severity).opacity(threatAlpha), style: StrokeStyle(lineWidth: t.confirmedLinks.isEmpty ? 1.5 : 2.2, dash: t.confirmedLinks.isEmpty ? [3, 3] : []))
            }
        }
        ForEach(store.openIncidents) { inc in
            MapCircle(center: inc.coordinate, radius: inc.radiusKm * 1000)
                .foregroundStyle(Theme.red.opacity(store.outlineOnlyThreats ? 0.0 : 0.10))
                .stroke(Theme.red, style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
        }
    }

    @MapContentBuilder
    private func graphicsContent(snap: Snapshot) -> some MapContent {
        if let gfx = snap.graphics {
            ForEach(gfx) { g in
                let a = (layer == nil || layer == g.section ? 1.0 : 0.3) * (g.windowFrom != nil && !g.inWindow ? 0.45 : 1.0)
                let color = g.swiftColor
                if g.kind == "polygon", case .path(let ps) = g.geometry, ps.count >= 3 {
                    MapPolygon(coordinates: g.geometry.coordinates)
                        .foregroundStyle(color.opacity((g.type == "range" && g.inWindow ? 0.22 : 0.07) * a))
                        .stroke(color.opacity(a), style: StrokeStyle(lineWidth: 2, dash: g.dash ? [5, 4] : []))
                } else if case .path(let ps) = g.geometry, ps.count >= 2 {
                    MapPolyline(coordinates: g.geometry.coordinates)
                        .stroke(color.opacity(a), style: StrokeStyle(lineWidth: g.type == "boundary" || g.type == "phase_line" ? 1.5 : 2.5, dash: g.dash ? [5, 4] : []))
                }
                Annotation(g.name, coordinate: g.kind == "point" ? g.geometry.coordinates[0] : g.centerCoordinate, anchor: g.kind == "point" ? .center : .bottom) {
                    GraphicMarker(g: g).opacity(a)
                }
                .annotationTitles(.hidden)
            }
        }
    }

    @MapContentBuilder
    private func routesContent(snap: Snapshot) -> some MapContent {
        if showsRoutesLayer {
            if let moves = snap.movements {
                ForEach(moves) { mv in
                    ForEach(Array(mv.legs.enumerated()), id: \.offset) { _, lg in
                        if let fla = lg.fromLat, let flo = lg.fromLon, lg.kind != "lodging" {
                            MapPolyline(coordinates: [CLLocationCoordinate2D(latitude: fla, longitude: flo), CLLocationCoordinate2D(latitude: lg.toLat, longitude: lg.toLon)])
                                .stroke(movementColor(mv).opacity((lg.status == "done" ? 0.35 : lg.status == "current" ? 0.95 : 0.7) * routeAlpha),
                                        style: StrokeStyle(lineWidth: lg.status == "current" ? (mv.pax >= 3 ? 3 : 2.2) : 1.4, dash: mv.kind == "shipment" ? [5, 3] : lg.status == "planned" ? [3, 4] : []))
                        }
                    }
                    if mv.kind != "individual", let c = mv.head ?? (mv.legs.first.flatMap { lg in lg.fromLat.flatMap { la in lg.fromLon.map { CLLocationCoordinate2D(latitude: (la + lg.toLat) / 2, longitude: ($0 + lg.toLon) / 2) } } }) {
                        Annotation(mv.name, coordinate: c, anchor: .top) {
                            MovementHead(mv: mv).opacity(routeAlpha).onTapGesture {
                                if let pid = mv.personIds.first { store.selection = .person(pid) }
                            }
                        }
                        .annotationTitles(.hidden)
                    }
                }
            } else {
                ForEach(snap.trips) { tr in
                    MapPolyline(coordinates: [CLLocationCoordinate2D(latitude: tr.originLat, longitude: tr.originLon),
                                              CLLocationCoordinate2D(latitude: tr.destLat, longitude: tr.destLon)])
                        .stroke((tr.status == "active" ? Theme.blue : Theme.dim).opacity(routeAlpha), style: StrokeStyle(lineWidth: tr.status == "active" ? 2 : 1.5, dash: tr.status == "active" ? [] : [4, 4]))
                }
            }
        }
    }

    @MapContentBuilder
    private func markersContent(snap: Snapshot) -> some MapContent {
        if showsSites {
            ForEach(snap.locations) { l in
                Annotation(l.name, coordinate: l.coordinate) {
                    SiteMarker(site: l, section: layer).onTapGesture { store.selection = .site(l.id) }
                }
                .annotationTitles(.hidden)
            }
        }
        if showsEvents {
            ForEach(snap.events.filter { $0.venueLocationId == nil }) { e in
                Annotation(e.name, coordinate: e.coordinate) {
                    EventMarker(event: e).opacity(eventAlpha).onTapGesture { store.selection = .event(e.id) }
                }
                .annotationTitles(.hidden)
            }
        }
        if showsTravelers {
            ForEach(store.travelers) { p in
                Annotation(p.name, coordinate: p.coordinate) {
                    PersonMarker(person: p).opacity(peopleAlpha).onTapGesture { store.selection = .person(p.id) }
                }
                .annotationTitles(.hidden)
            }
        }
    }

    func fly(to sel: Selection?) {
        guard let sel else { return }
        var target: (CLLocationCoordinate2D, CLLocationDistance)? = nil
        switch sel {
        case .site(let id): if let s = store.site(id) { target = (s.coordinate, 20_000) }
        case .person(let id): if let p = store.person(id) { target = (p.coordinate, 80_000) }
        case .event(let id): if let e = store.event(id) { target = (e.coordinate, 40_000) }
        case .threat(let id): if let t = store.threat(id) { target = (t.coordinate, max(t.radiusKm * 4_000, 30_000)) }
        case .incident(let id): if let i = store.incident(id) { target = (i.coordinate, max(i.radiusKm * 4_000, 20_000)) }
        }
        if let (c, d) = target { withAnimation(.easeInOut(duration: 1.2)) { camera = .camera(MapCamera(centerCoordinate: c, distance: d)) } }
    }
}

struct SiteMarker: View {
    var site: Site
    var section: String? = nil  // "S4" / "S6": wear that section's health instead of the posture
    var health: String? { section == "S4" ? site.s4Status : section == "S6" ? site.s6Status : section == "S2" ? site.area.map { $0.worst == "unknown" ? "none" : $0.worst } : nil }
    var glyph: String { ["hq": "◆", "office": "■", "datacenter": "▣", "residence": "⌂", "airfield": "✈", "cp": "▲", "fob": "⬢", "farp": "⛽", "range": "◎", "venue": "★"][site.type] ?? "■" }
    var body: some View {
        let color = health.map { healthColor($0) } ?? (site.effectivePosture == "normal" ? Theme.blue : Theme.posture(site.effectivePosture))
        ZStack(alignment: .topTrailing) {
            Text(glyph).font(.system(size: 15)).foregroundStyle(color).frame(width: 30, height: 30)
                .background(Theme.panel.opacity(0.92), in: RoundedRectangle(cornerRadius: site.type == "residence" ? 15 : 6))
                .overlay(RoundedRectangle(cornerRadius: site.type == "residence" ? 15 : 6).stroke(color, style: StrokeStyle(lineWidth: 1.5, dash: site.type == "residence" ? [3, 3] : [])))
                .shadow(color: color.opacity(0.6), radius: 8)
                .overlay { if !site.threatIdsInArea.isEmpty { RoundedRectangle(cornerRadius: 8).stroke(Theme.amber, style: StrokeStyle(lineWidth: 1.2, dash: [3, 3])).padding(-6) } }
            if let h = health, h != "none" {  // the section's badge: red count for S4 lines short, systems down for S6, the rating on S2
                Text(section == "S4" ? "S4\((site.s4Red ?? 0) > 0 ? " \(site.s4Red!)" : "")" : section == "S6" ? "S6\((site.s6Down ?? 0) > 0 ? " \(site.s6Down!)" : "")" : String(h.prefix(1)).uppercased()).font(.system(size: 9, weight: .heavy, design: .monospaced))
                    .foregroundStyle(h == "amber" ? .black : .white).padding(.horizontal, 4).frame(minHeight: 16).background(healthColor(h), in: Capsule()).offset(x: 10, y: -8)
            } else if section == nil || section == "S1" {
                Text("\(site.present)").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(.white)
                    .padding(.horizontal, 4).frame(minWidth: 18, minHeight: 16).background(Theme.blue, in: Capsule()).offset(x: 10, y: -8)
            }
        }
    }
}

func movementColor(_ mv: Movement) -> Color { mv.kind == "shipment" ? (mv.health == "red" ? Theme.red : Theme.orange) : mv.isVip ? Theme.gold : mv.status == "active" ? Theme.blue : Theme.dim }

/// §3.4 the NAI label at the top of its ring: number, subject, coverage.
struct NAILabel: View {
    var nai: NAI
    var body: some View {
        HStack(spacing: 4) {
            Text(nai.name).font(.system(size: 9, weight: .heavy, design: .monospaced)).foregroundStyle(.white)
            Text(nai.subjectName.components(separatedBy: " — ").first ?? nai.subjectName).font(.system(size: 9, design: .monospaced)).lineLimit(1)
            Text("\(nai.coveragePct)%").font(.system(size: 9, weight: .bold, design: .monospaced)).foregroundStyle(healthColor(nai.health))
            if !nai.pirIds.isEmpty { Text("PIR").font(.system(size: 8, weight: .heavy, design: .monospaced)).foregroundStyle(Theme.red) }
        }
        .foregroundStyle(Theme.amber).padding(.horizontal, 6).padding(.vertical, 2)
        .background(Theme.panel.opacity(0.92), in: RoundedRectangle(cornerRadius: 3)).overlay(RoundedRectangle(cornerRadius: 3).stroke(healthColor(nai.health), lineWidth: 1))
        .opacity(nai.priority == 1 ? 1 : 0.85)
    }
}

/// §3.4 the head of a group movement: the unit or delegation and its count, or the shipment and its ETA.
struct MovementHead: View {
    var mv: Movement
    var body: some View {
        let color = movementColor(mv)
        HStack(spacing: 5) {
            Text(mv.kind == "shipment" ? "⛽" : mv.mode == "air" ? "✈" : "▶").font(.system(size: 10)).foregroundStyle(color)
            if mv.kind == "shipment" { Text("\(mv.name.components(separatedBy: " → ").first ?? mv.name) · ETA \(Int((mv.hoursToEta ?? 0).rounded()))h").font(.system(size: 10, weight: .semibold, design: .monospaced)) }
            else { Text("\(mv.unit ?? mv.name.components(separatedBy: " · ").first ?? mv.name) · \(mv.pax) pax").font(.system(size: 11, weight: .semibold)) }
        }
        .foregroundStyle(.white).padding(.horizontal, 8).padding(.vertical, 3)
        .background(Theme.panel.opacity(0.94), in: RoundedRectangle(cornerRadius: 6)).overlay(RoundedRectangle(cornerRadius: 6).stroke(color, style: StrokeStyle(lineWidth: 1.5, dash: mv.status == "planned" ? [3, 3] : [])))
        .shadow(color: color.opacity(0.5), radius: 8)
    }
}

/// §3.4 the glyph and the name of a control measure, in its section's color.
struct GraphicMarker: View {
    var g: Graphic
    var body: some View {
        HStack(spacing: 4) {
            Text(g.glyph).font(.system(size: 11, weight: .heavy, design: .monospaced)).foregroundStyle(g.swiftColor)
            Text(g.name).font(.system(size: 10, weight: .semibold)).lineLimit(1)
        }
        .foregroundStyle(.white).padding(.horizontal, 6).padding(.vertical, 2)
        .background(Theme.panel.opacity(g.kind == "point" ? 0.92 : 0.8), in: RoundedRectangle(cornerRadius: 4))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(g.swiftColor, style: StrokeStyle(lineWidth: g.kind == "point" ? 1.5 : 1, dash: g.status == "planned" ? [3, 3] : [])))
    }
}

struct PersonMarker: View {
    var person: Person
    var body: some View {
        let color = !person.confirmedThreatIds.isEmpty ? Theme.red : person.isVip ? Theme.gold : Theme.blue
        HStack(spacing: 5) {
            Circle().fill(color).frame(width: 8, height: 8)
            Text(person.shortName ?? person.name.split(separator: " ").first.map(String.init) ?? person.name).font(.system(size: 11, weight: .semibold, design: .monospaced))
            if person.positionSource == "checkin" { Text("✓").font(.system(size: 10, weight: .bold)).foregroundStyle(Theme.green) }
        }
        .padding(.horizontal, 8).padding(.vertical, 4).foregroundStyle(.white)
        .background(Theme.panel.opacity(0.92), in: Capsule())
        .overlay(Capsule().stroke(color, lineWidth: person.positionSource == "checkin" ? 2.5 : 1.5))
        .shadow(color: color.opacity(0.6), radius: 8)
    }
}

struct EventMarker: View {
    var event: CopEvent
    var body: some View {
        HStack(spacing: 5) {
            Text("★").foregroundStyle(Theme.purple)
            Text("T-\(event.daysUntil)d").font(.system(size: 11, weight: .semibold, design: .monospaced))
        }
        .padding(.horizontal, 8).padding(.vertical, 4).foregroundStyle(.white)
        .background(Theme.panel.opacity(0.92), in: RoundedRectangle(cornerRadius: 6))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Theme.purple, lineWidth: 1.5))
        .shadow(color: Theme.purple.opacity(0.6), radius: 8)
    }
}


private struct LayerPill: View {
    let label: String
    let icon: String
    @Binding var isOn: Bool
    var disabled: Bool = false

    var body: some View {
        Button {
            if !disabled {
                withAnimation(.snappy(duration: 0.15)) {
                    isOn.toggle()
                }
            }
        } label: {
            HStack(spacing: 8) {
                Text(icon)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(disabled ? Theme.dim.opacity(0.4) : isOn ? Theme.amber : Theme.dim)
                Text(label)
                    .font(.system(size: 11, weight: isOn ? .semibold : .regular, design: .monospaced))
                    .foregroundStyle(disabled ? Theme.dim.opacity(0.4) : isOn ? Color.white : Theme.dim)
                    .lineLimit(1)
                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                disabled ? Theme.panel.opacity(0.4) :
                isOn ? Theme.blue.opacity(0.18) : Theme.panel2.opacity(0.6),
                in: RoundedRectangle(cornerRadius: 6)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(disabled ? Theme.line : isOn ? Theme.blue : Theme.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .disabled(disabled)
    }
}


struct TacticalRuler: View {
    let widthMiles: Double
    let widthKm: Double
    var unit: String = "mi"

    private let candidateSteps: [Double] = [
        0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0
    ]

    private var activeDist: Double {
        unit == "km" ? widthKm : widthMiles
    }

    private var stepSize: Double {
        for step in candidateSteps {
            let count = activeDist / step
            if count <= 7.0 && count >= 2.5 {
                return step
            }
        }
        return candidateSteps.first(where: { activeDist / $0 < 3.0 }) ?? 10.0
    }

    private func formatDistance(_ d: Double) -> String {
        if d >= 10 {
            return String(format: "%.0f", d)
        } else if d >= 1 {
            return d.truncatingRemainder(dividingBy: 1.0) == 0 ? String(format: "%.0f", d) : String(format: "%.1f", d)
        } else {
            return String(format: "%.2f", d)
        }
    }

    private func formatBadge(_ val: Double) -> String {
        if val >= 100 {
            return String(format: "%.0f", val)
        } else if val >= 10 {
            return String(format: "%.1f", val)
        } else {
            return String(format: "%.1f", val)
        }
    }

    var body: some View {
        GeometryReader { proxy in
            let totalW = proxy.size.width
            let step = stepSize
            let maxDist = max(0.001, activeDist)

            ZStack(alignment: .leading) {
                // Background HUD strip
                Rectangle()
                    .fill(Color(red: 0.05, green: 0.07, blue: 0.11).opacity(0.88))

                // Fine hairline bottom divider
                VStack(spacing: 0) {
                    Spacer()
                    Rectangle()
                        .fill(Color.white.opacity(0.2))
                        .frame(height: 0.5)
                }

                // Ticks and labels
                Canvas { context, size in
                    let w = size.width
                    let h = size.height
                    guard maxDist > 0 else { return }

                    // Zero tick and label at start
                    var zeroPath = Path()
                    zeroPath.move(to: CGPoint(x: 6, y: h - 7))
                    zeroPath.addLine(to: CGPoint(x: 6, y: h))
                    context.stroke(zeroPath, with: .color(Color.white.opacity(0.6)), lineWidth: 1)

                    let zeroText = Text("0")
                        .font(.system(size: 7.5, weight: .medium, design: .monospaced))
                        .foregroundStyle(Color.white.opacity(0.6))
                    context.draw(context.resolve(zeroText), at: CGPoint(x: 6, y: 1), anchor: .top)

                    // Draw ticks across width
                    var d = step
                    while d < maxDist {
                        let x = CGFloat(d / maxDist) * w
                        if x > w - 70 { break }

                        // Major tick
                        var majorPath = Path()
                        majorPath.move(to: CGPoint(x: x, y: h - 7))
                        majorPath.addLine(to: CGPoint(x: x, y: h))
                        context.stroke(majorPath, with: .color(Color.white.opacity(0.7)), lineWidth: 1)

                        // Minor tick (midpoint)
                        let midD = d - step / 2.0
                        if midD > 0 {
                            let midX = CGFloat(midD / maxDist) * w
                            if midX < w - 70 {
                                var minorPath = Path()
                                minorPath.move(to: CGPoint(x: midX, y: h - 4))
                                minorPath.addLine(to: CGPoint(x: midX, y: h))
                                context.stroke(minorPath, with: .color(Color.white.opacity(0.35)), lineWidth: 0.75)
                            }
                        }

                        // Text label for major tick
                        let labelText = formatDistance(d)
                        let text = Text(labelText)
                            .font(.system(size: 7.5, weight: .medium, design: .monospaced))
                            .foregroundStyle(Color.white.opacity(0.7))
                        context.draw(context.resolve(text), at: CGPoint(x: x, y: 1), anchor: .top)

                        d += step
                    }
                }

                // Total AO Span badge at trailing end
                HStack(spacing: 3) {
                    Text("AO:")
                        .font(.system(size: 7.5, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Theme.blue)
                    let text = unit == "km"
                        ? "\(formatBadge(widthKm)) km"
                        : "\(formatBadge(widthMiles)) mi"
                    Text(text)
                        .font(.system(size: 7.5, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.white)
                }
                .padding(.horizontal, 5)
                .padding(.vertical, 2)
                .background(Theme.panel2.opacity(0.85), in: RoundedRectangle(cornerRadius: 3))
                .overlay(RoundedRectangle(cornerRadius: 3).stroke(Theme.line, lineWidth: 0.5))
                .frame(maxWidth: .infinity, alignment: .trailing)
                .padding(.trailing, 6)
            }
        }
        .frame(height: 20)
    }
}

struct RulerBottomPreferenceKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        let n = nextValue()
        if n > 0 { value = n }
    }
}

struct TacticalRulerVertical: View {
    let heightMiles: Double
    let heightKm: Double
    var unit: String = "mi"

    private let candidateSteps: [Double] = [
        0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0
    ]

    private var activeDist: Double {
        unit == "km" ? heightKm : heightMiles
    }

    private var stepSize: Double {
        for step in candidateSteps {
            let count = activeDist / step
            if count <= 9.0 && count >= 3.0 {
                return step
            }
        }
        return candidateSteps.first(where: { activeDist / $0 < 4.0 }) ?? 10.0
    }

    private func formatDistance(_ d: Double) -> String {
        if d >= 10 {
            return String(format: "%.0f", d)
        } else if d >= 1 {
            return d.truncatingRemainder(dividingBy: 1.0) == 0 ? String(format: "%.0f", d) : String(format: "%.1f", d)
        } else {
            return String(format: "%.2f", d)
        }
    }

    private func formatBadge(_ val: Double) -> String {
        if val >= 100 {
            return String(format: "%.0f", val)
        } else {
            return String(format: "%.1f", val)
        }
    }

    var body: some View {
        GeometryReader { proxy in
            let totalH = proxy.size.height
            let step = stepSize
            let maxDist = max(0.001, activeDist)
            let cutoffY = totalH - 40

            ZStack(alignment: .topTrailing) {
                // Background HUD strip
                Rectangle()
                    .fill(Color(red: 0.05, green: 0.07, blue: 0.11).opacity(0.88))

                // Hairline left divider
                HStack(spacing: 0) {
                    Rectangle()
                        .fill(Color.white.opacity(0.2))
                        .frame(width: 0.5)
                    Spacer()
                }

                // Ticks, labels, and bottom vertical badge
                Canvas { context, size in
                    let h = size.height
                    guard maxDist > 0 else { return }

                    // Calculate badge dimensions and tick cutoff
                    let vText = Text("V ").font(.system(size: 7, weight: .bold, design: .monospaced)).foregroundStyle(Theme.blue)
                    let distText = Text(formatBadge(activeDist) + " ").font(.system(size: 7.5, weight: .bold, design: .monospaced)).foregroundStyle(Color.white)
                    let unitText = Text(unit).font(.system(size: 6.5, design: .monospaced)).foregroundStyle(Theme.dim)
                    let badgeContent = vText + distText + unitText
                    let resolved = context.resolve(badgeContent)
                    let measured = resolved.measure(in: CGSize(width: 200, height: 50))

                    let padH: CGFloat = 4
                    let padV: CGFloat = 2.5
                    let badgeW = measured.width + padH * 2
                    let badgeH = measured.height + padV * 2

                    let badgeCenterY = h - 8 - (badgeW / 2)
                    let tickCutoff = badgeCenterY - (badgeW / 2) - 6

                    // Zero tick and label at start (top edge)
                    var zeroPath = Path()
                    zeroPath.move(to: CGPoint(x: 0, y: 0))
                    zeroPath.addLine(to: CGPoint(x: 4.5, y: 0))
                    context.stroke(zeroPath, with: .color(Color.white.opacity(0.6)), lineWidth: 1)

                    var zeroCtx = context
                    zeroCtx.translateBy(x: 12, y: 6)
                    zeroCtx.rotate(by: .degrees(90))
                    let zeroText = Text("0")
                        .font(.system(size: 7.5, weight: .medium, design: .monospaced))
                        .foregroundStyle(Color.white.opacity(0.75))
                    zeroCtx.draw(context.resolve(zeroText), at: .zero, anchor: .center)

                    // Draw ticks down the height
                    var d = step
                    while d < maxDist {
                        let y = CGFloat(d / maxDist) * h
                        if y > tickCutoff { break }

                        // Major tick
                        var majorPath = Path()
                        majorPath.move(to: CGPoint(x: 0, y: y))
                        majorPath.addLine(to: CGPoint(x: 4.5, y: y))
                        context.stroke(majorPath, with: .color(Color.white.opacity(0.7)), lineWidth: 1)

                        // Minor tick (midpoint)
                        let midD = d - step / 2.0
                        if midD > 0 {
                            let midY = CGFloat(midD / maxDist) * h
                            if midY < tickCutoff {
                                var minorPath = Path()
                                minorPath.move(to: CGPoint(x: 0, y: midY))
                                minorPath.addLine(to: CGPoint(x: 2.5, y: midY))
                                context.stroke(minorPath, with: .color(Color.white.opacity(0.35)), lineWidth: 0.75)
                            }
                        }

                        // Text label aligned vertically with screen edge
                        let labelText = formatDistance(d)
                        let text = Text(labelText)
                            .font(.system(size: 7.5, weight: .medium, design: .monospaced))
                            .foregroundStyle(Color.white.opacity(0.75))
                        var tickCtx = context
                        tickCtx.translateBy(x: 12, y: y)
                        tickCtx.rotate(by: .degrees(90))
                        tickCtx.draw(context.resolve(text), at: .zero, anchor: .center)

                        d += step
                    }

                    // Draw bottom badge aligned vertically with screen edge
                    var badgeCtx = context
                    badgeCtx.translateBy(x: 12, y: badgeCenterY)
                    badgeCtx.rotate(by: .degrees(90))

                    let badgeRect = CGRect(x: -badgeW / 2, y: -badgeH / 2, width: badgeW, height: badgeH)
                    badgeCtx.fill(Path(roundedRect: badgeRect, cornerRadius: 3), with: .color(Theme.panel2.opacity(0.88)))
                    badgeCtx.stroke(Path(roundedRect: badgeRect, cornerRadius: 3), with: .color(Theme.line), lineWidth: 0.5)
                    badgeCtx.draw(resolved, at: .zero, anchor: .center)
                }
            }
        }
        .frame(width: 24)
    }
}

