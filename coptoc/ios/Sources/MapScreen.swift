import SwiftUI
import MapKit

struct MapScreen: View {
    @Environment(COPStore.self) private var store
    /// §3.4 the overlays: a section's tab brings its own things forward and dims the rest — an overlay sits on the base, the base stays.
    /// S2 draws the NAIs and the threats in full; S3 draws every movement leg by leg; S4 / S6 color every site by its health.
    var layer: String? = nil
    var showsSites: Bool { true }
    var showsThreatsLayer: Bool { layer == nil ? showThreats : true }
    var showsRoutesLayer: Bool { layer == nil ? showRoutes : true }
    var threatAlpha: Double { layer == nil || layer == "S2" ? 1 : 0.3 }
    var routeAlpha: Double { layer == nil || layer == "S3" ? 1 : layer == "S4" ? 0.6 : 0.3 }
    var peopleAlpha: Double { layer == nil || layer == "S1" || layer == "S3" ? 1 : 0.3 }
    var eventAlpha: Double { layer == nil || layer == "S3" ? 1 : 0.3 }
    var showsNAIs: Bool { layer == "S2" }
    var showsTravelers: Bool { true }
    var showsEvents: Bool { true }
    /// Where a phone that remembers nothing and cannot reach the API opens: the Bay Area. Replaced on appear by the
    /// board this device was left on, and on the first snapshot by the server's answer for this deployment.
    @State private var camera: MapCameraPosition = .region(MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.72, longitude: -122.16), latitudinalMeters: 140_000, longitudinalMeters: 140_000))
    @State private var showThreats = true
    @State private var showRoutes = true

    var body: some View {
        @Bindable var store = store
        ZStack(alignment: .topLeading) {
            Map(position: $camera) {
                if let snap = store.snapshot {
                    if showsNAIs, let nais = snap.nais {   // §3.4 S2: every active requirement as a named area, colored by how well it is collected
                        ForEach(nais) { n in
                            MapCircle(center: n.coordinate, radius: n.radiusKm * 1000)
                                .foregroundStyle(healthColor(n.health).opacity(n.priority == 1 ? 0.10 : 0.05))
                                .stroke(healthColor(n.health), style: StrokeStyle(lineWidth: n.priority == 1 ? 1.8 : 1, dash: [5, 4]))
                            Annotation(n.name, coordinate: n.labelCoordinate, anchor: .bottom) { NAILabel(nai: n).onTapGesture { if n.subjectType == "location", let id = n.subjectId { store.selection = .site(id) } else if n.subjectType == "event", let id = n.subjectId { store.selection = .event(id) } } }.annotationTitles(.hidden)
                        }
                    }
                    if showsThreatsLayer {
                        ForEach(snap.threats) { t in
                            MapCircle(center: t.coordinate, radius: t.radiusKm * 1000)
                                .foregroundStyle(Theme.severity(t.severity).opacity(0.16 * threatAlpha))
                                .stroke(Theme.severity(t.severity).opacity(threatAlpha), style: StrokeStyle(lineWidth: t.confirmedLinks.isEmpty ? 1.5 : 2.2, dash: t.confirmedLinks.isEmpty ? [3, 3] : []))
                        }
                    }
                    ForEach(store.openIncidents) { inc in
                        MapCircle(center: inc.coordinate, radius: inc.radiusKm * 1000)
                            .foregroundStyle(Theme.red.opacity(0.10)).stroke(Theme.red, style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
                    }
                    if showsRoutesLayer {
                        if let moves = snap.movements {   // §3.4 S3: everything that moves, leg by leg — a serial, a delegation, a person, a shipment
                            ForEach(moves) { mv in
                                ForEach(Array(mv.legs.enumerated()), id: \.offset) { _, lg in
                                    if let fla = lg.fromLat, let flo = lg.fromLon, lg.kind != "lodging" {
                                        MapPolyline(coordinates: [CLLocationCoordinate2D(latitude: fla, longitude: flo), CLLocationCoordinate2D(latitude: lg.toLat, longitude: lg.toLon)])
                                            .stroke(movementColor(mv).opacity((lg.status == "done" ? 0.35 : lg.status == "current" ? 0.95 : 0.7) * routeAlpha),
                                                    style: StrokeStyle(lineWidth: lg.status == "current" ? (mv.pax >= 3 ? 3 : 2.2) : 1.4, dash: mv.kind == "shipment" ? [5, 3] : lg.status == "planned" ? [3, 4] : []))
                                    }
                                }
                                if mv.kind != "individual", let c = mv.head ?? (mv.legs.first.flatMap { lg in lg.fromLat.flatMap { la in lg.fromLon.map { CLLocationCoordinate2D(latitude: (la + lg.toLat) / 2, longitude: ($0 + lg.toLon) / 2) } } }) {
                                    Annotation(mv.name, coordinate: c, anchor: .top) { MovementHead(mv: mv).opacity(routeAlpha).onTapGesture { if let pid = mv.personIds.first { store.selection = .person(pid) } } }.annotationTitles(.hidden)
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
                    ForEach(snap.locations) { l in
                        Annotation(l.name, coordinate: l.coordinate) { SiteMarker(site: l, section: layer).onTapGesture { store.selection = .site(l.id) } }.annotationTitles(.hidden)
                    }
                    if showsEvents {
                        ForEach(snap.events.filter { $0.venueLocationId == nil }) { e in
                            Annotation(e.name, coordinate: e.coordinate) { EventMarker(event: e).opacity(eventAlpha).onTapGesture { store.selection = .event(e.id) } }.annotationTitles(.hidden)
                        }
                    }
                    if showsTravelers {
                        ForEach(store.travelers) { p in
                            Annotation(p.name, coordinate: p.coordinate) { PersonMarker(person: p).opacity(peopleAlpha).onTapGesture { store.selection = .person(p.id) } }.annotationTitles(.hidden)
                        }
                    }
                }
            }
            .mapStyle(.standard(elevation: .flat, pointsOfInterest: .excludingAll))
            .mapControls { MapCompass(); MapScaleView() }

            if layer == nil { HStack(spacing: 6) {
                Toggle("threats", isOn: $showThreats).toggleStyle(.button).font(.system(size: 10, design: .monospaced))
                Toggle("routes", isOn: $showRoutes).toggleStyle(.button).font(.system(size: 10, design: .monospaced))
                Toggle(store.snapshot?.restrictedDenied == true ? "⚿ residences · DENIED" : "⚿ residences", isOn: $store.showRestricted).toggleStyle(.button).font(.system(size: 10, design: .monospaced)).tint(store.snapshot?.restrictedDenied == true ? Theme.red : Theme.amber)
            }
            .padding(8) }
        }
        .onAppear { if let r = store.board { camera = .region(r) } }         // this section inherits the board as it stands
        .onChange(of: store.framedAt) { if let r = store.board { camera = .region(r) } }
        .onMapCameraChange(frequency: .onEnd) { ctx in store.board = ctx.region }   // wherever it is left is where every section finds it
        .onChange(of: store.selection) { _, sel in fly(to: sel) }
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
