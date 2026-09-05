import SwiftUI
import MapKit

struct MapScreen: View {
    @Environment(COPStore.self) private var store
    @State private var camera: MapCameraPosition = .region(MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 38, longitude: -60), span: MKCoordinateSpan(latitudeDelta: 90, longitudeDelta: 140)))
    @State private var showThreats = true
    @State private var showRoutes = true

    var body: some View {
        @Bindable var store = store
        ZStack(alignment: .topLeading) {
            Map(position: $camera) {
                if let snap = store.snapshot {
                    if showThreats {
                        ForEach(snap.threats) { t in
                            MapCircle(center: t.coordinate, radius: t.radiusKm * 1000)
                                .foregroundStyle(Theme.severity(t.severity).opacity(0.16))
                                .stroke(Theme.severity(t.severity), lineWidth: 1.5)
                        }
                    }
                    ForEach(store.openIncidents) { inc in
                        MapCircle(center: inc.coordinate, radius: inc.radiusKm * 1000)
                            .foregroundStyle(Theme.red.opacity(0.10)).stroke(Theme.red, style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
                    }
                    if showRoutes {
                        ForEach(snap.trips) { tr in
                            MapPolyline(coordinates: [CLLocationCoordinate2D(latitude: tr.originLat, longitude: tr.originLon),
                                                      CLLocationCoordinate2D(latitude: tr.destLat, longitude: tr.destLon)])
                                .stroke(tr.status == "active" ? Theme.blue : Theme.dim, style: StrokeStyle(lineWidth: tr.status == "active" ? 2 : 1.5, dash: tr.status == "active" ? [] : [4, 4]))
                        }
                    }
                    ForEach(snap.locations) { l in
                        Annotation(l.name, coordinate: l.coordinate) { SiteMarker(site: l).onTapGesture { store.selection = .site(l.id) } }.annotationTitles(.hidden)
                    }
                    ForEach(snap.events.filter { $0.venueLocationId == nil }) { e in
                        Annotation(e.name, coordinate: e.coordinate) { EventMarker(event: e).onTapGesture { store.selection = .event(e.id) } }.annotationTitles(.hidden)
                    }
                    ForEach(store.travelers) { p in
                        Annotation(p.name, coordinate: p.coordinate) { PersonMarker(person: p).onTapGesture { store.selection = .person(p.id) } }.annotationTitles(.hidden)
                    }
                }
            }
            .mapStyle(.standard(elevation: .flat, pointsOfInterest: .excludingAll))
            .mapControls { MapCompass(); MapScaleView() }

            HStack(spacing: 6) {
                Toggle("threats", isOn: $showThreats).toggleStyle(.button).font(.system(size: 10, design: .monospaced))
                Toggle("routes", isOn: $showRoutes).toggleStyle(.button).font(.system(size: 10, design: .monospaced))
                Toggle(store.snapshot?.restrictedDenied == true ? "⚿ residences · DENIED" : "⚿ residences", isOn: $store.showRestricted).toggleStyle(.button).font(.system(size: 10, design: .monospaced)).tint(store.snapshot?.restrictedDenied == true ? Theme.red : Theme.amber)
            }
            .padding(8)
        }
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
    var glyph: String { ["hq": "◆", "office": "■", "datacenter": "▣", "residence": "⌂", "airfield": "✈", "cp": "▲", "fob": "⬢", "farp": "⛽", "range": "◎", "venue": "★"][site.type] ?? "■" }
    var body: some View {
        let color = site.effectivePosture == "normal" ? Theme.blue : Theme.posture(site.effectivePosture)
        ZStack(alignment: .topTrailing) {
            Text(glyph).font(.system(size: 15)).foregroundStyle(color).frame(width: 30, height: 30)
                .background(Theme.panel.opacity(0.92), in: RoundedRectangle(cornerRadius: site.type == "residence" ? 15 : 6))
                .overlay(RoundedRectangle(cornerRadius: site.type == "residence" ? 15 : 6).stroke(color, style: StrokeStyle(lineWidth: 1.5, dash: site.type == "residence" ? [3, 3] : [])))
                .shadow(color: color.opacity(0.6), radius: 8)
                .overlay { if !site.threatIdsInArea.isEmpty { RoundedRectangle(cornerRadius: 8).stroke(Theme.amber, style: StrokeStyle(lineWidth: 1.2, dash: [3, 3])).padding(-6) } }
            Text("\(site.present)").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(.white)
                .padding(.horizontal, 4).frame(minWidth: 18, minHeight: 16).background(Theme.blue, in: Capsule()).offset(x: 10, y: -8)
        }
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
