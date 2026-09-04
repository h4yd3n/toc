import SwiftUI

struct ContentView: View {
    @Environment(COPStore.self) private var store

    var body: some View {
        @Bindable var store = store
        TabView {
            MapScreen().tabItem { Label("COP", systemImage: "map") }
            PersonnelScreen().tabItem { Label("S1", systemImage: "person.3") }
            IntelScreen().tabItem { Label("S2", systemImage: "eye") }
            OpsScreen().tabItem { Label("S3", systemImage: "calendar") }
        }
        .tint(Theme.blue)
        .safeAreaInset(edge: .top, spacing: 0) { VStack(spacing: 0) { PostureBar(); FlashStrip() } }
        .sheet(item: $store.selection) { sel in
            DetailView(selection: sel).presentationDetents([.medium, .large]).presentationBackground(Theme.panel)
        }
        .overlay(alignment: .bottom) {
            if let err = store.error {
                Text(err).font(.system(size: 11, design: .monospaced)).lineLimit(2).padding(8)
                    .background(Theme.red.opacity(0.9), in: RoundedRectangle(cornerRadius: 6)).padding(.bottom, 60)
                    .onTapGesture { store.error = nil }
            } else if let busy = store.busy {
                Text(busy.uppercased()).font(.system(size: 10, weight: .semibold, design: .monospaced)).tracking(1.5).padding(8)
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 6)).padding(.bottom, 60)
            }
        }
        .background(Theme.bg)
    }
}

struct PostureBar: View {
    @Environment(COPStore.self) private var store
    var body: some View {
        let s = store.snapshot?.summary
        let posture = s?.posture ?? "normal"
        VStack(spacing: 6) {
            HStack(spacing: 10) {
                Text("TOC").font(.system(size: 18, weight: .heavy, design: .monospaced)).tracking(3)
                Menu {
                    ForEach((s?.defconLevels ?? []).sorted { $0.defcon > $1.defcon }) { l in
                        Button { } label: { Label("DEFCON \(l.defcon) · \(l.posture.uppercased())" + (l.defcon == s?.defcon ? "  ← now" : "") + (l.sites > 0 ? "  (\(l.sites))" : ""), systemImage: l.defcon == s?.defcon ? "checkmark.circle.fill" : "circle") }
                    }
                    Divider()
                    Text("The wall reads the worst site. Set a site's level from its card.")
                } label: {
                    if store.postureHeader {
                        Text("DEFCON \(s?.defcon.map(String.init) ?? "—")").font(.system(size: 14, weight: .heavy, design: .monospaced)).tracking(2.5).foregroundStyle(Theme.posture(posture))
                            .padding(.horizontal, 12).padding(.vertical, 6).overlay(RoundedRectangle(cornerRadius: 4).stroke(Theme.posture(posture), lineWidth: 2))
                    } else {
                        Chip(text: "DEFCON \(s?.defcon.map(String.init) ?? "—")", color: Theme.posture(posture))
                    }
                }
                Spacer()
                Menu {
                    Toggle("Lean labels", isOn: Binding(get: { store.leanLabels }, set: { store.leanLabels = $0 }))
                    Toggle("Posture header", isOn: Binding(get: { store.postureHeader }, set: { store.postureHeader = $0 }))
                } label: { Text("DISPLAY ▾").font(.system(size: 9, weight: .semibold, design: .monospaced)).tracking(1.5).foregroundStyle(Theme.dim).padding(.horizontal, 6).padding(.vertical, 4).overlay(RoundedRectangle(cornerRadius: 3).stroke(Theme.line, lineWidth: 1)) }
                Text(clock(store.now)).font(.system(size: 12, design: .monospaced)).foregroundStyle(Theme.dim)
            }
            if let w = store.snapshot?.watch {
                HStack(spacing: 8) {
                    Text("\(w.name.uppercased()) WATCH").font(.system(size: 10, weight: .heavy, design: .monospaced)).foregroundStyle(Theme.blue)
                    Text(w.battleCaptain.map { "BC \($0)" } ?? "UNASSIGNED").font(.system(size: 10, design: .monospaced))
                    Spacer()
                    Text(w.status == "pending_ack" ? "HANDOVER PENDING" : w.overdue ? "OVERDUE" : "\(hm(w.elapsedH)) · → \(w.nextWatch.split(separator: " ").first.map(String.init) ?? w.nextWatch) in \(hm(w.remainingH))")
                        .font(.system(size: 10, design: .monospaced)).foregroundStyle(w.status == "pending_ack" || w.overdue ? Theme.red : w.inOverlap ? Theme.amber : Theme.dim)
                }
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    Stat("PERSONNEL", s?.totalPeople); Stat("TRAVELING", s?.traveling, Theme.blue); Stat("VIP OUT", s?.vipsTraveling, Theme.gold)
                    Stat("THREATS", s?.activeThreats, Theme.red); Stat("CONFIRMED", s?.confirmedLinks, Theme.red)
                    if (s?.flash ?? 0) > 0 { Stat("FLASH", s?.flash, Theme.red) }
                    if (s?.unaccounted ?? 0) > 0 { Stat("UNACCOUNTED", s?.unaccounted, Theme.red) }
                    if (s?.unreachable ?? 0) > 0 { Stat("UNREACHABLE", s?.unreachable, Theme.red) }
                    if !store.postureHeader {  // the full counter row
                        Stat("PRESENT", s?.present); Stat("CHECKED IN", s?.checkedInFresh, Theme.green); Stat("SEC ON SHIFT", s?.securityOnShift, Theme.green)
                        Stat("OPEN PIRs", s?.openPirs, Theme.amber); Stat("EVENTS", s?.upcomingEvents)
                    }
                }
            }
        }
        .padding(.horizontal, 14).padding(.top, 6).padding(.bottom, 8)
        .background(Theme.panel)
        .overlay(alignment: .bottom) { Rectangle().fill(Theme.line).frame(height: 1) }
    }
    func hm(_ h: Double) -> String { let a = abs(h); return "\(Int(a))h\(String(format: "%02d", Int((a - Double(Int(a))) * 60)))" }
    func clock(_ d: Date) -> String { let f = DateFormatter(); f.dateFormat = "HH:mm:ss'Z'"; f.timeZone = TimeZone(identifier: "UTC"); return f.string(from: d) }
}

/// §5.6 — released warnings, red, under the header, with the reader's acknowledgement.
struct FlashStrip: View {
    @Environment(COPStore.self) private var store
    var body: some View {
        if !store.liveWarnings.isEmpty {
            VStack(spacing: 4) {
                ForEach(store.liveWarnings) { w in
                    HStack(spacing: 8) {
                        Text("FLASH").font(.system(size: 9, weight: .heavy, design: .monospaced)).tracking(2).padding(.horizontal, 6).padding(.vertical, 2).background(Theme.red, in: RoundedRectangle(cornerRadius: 3)).foregroundStyle(.white)
                        Text(w.shortTitle).font(.system(size: 12, weight: .semibold)).foregroundStyle(Color(red: 1, green: 0.79, blue: 0.79)).lineLimit(1)
                        Spacer()
                        Text("\(w.releasedBy ?? "") · \(w.ageMin ?? 0)m").font(.system(size: 9, design: .monospaced)).foregroundStyle(Theme.dim)
                        Button("ACK") { store.act("acknowledging") { try await store.client.ackProduct("warning", w.id) } }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.green).disabled(store.busy != nil)
                    }
                    .contentShape(Rectangle()).onTapGesture { store.selection = w.subjectType == "location" ? .site(w.subjectId) : w.subjectType == "person" ? .person(w.subjectId) : .event(w.subjectId) }
                }
            }
            .padding(.horizontal, 12).padding(.vertical, 6).background(Theme.red.opacity(0.14))
            .overlay(alignment: .bottom) { Rectangle().fill(Theme.red.opacity(0.6)).frame(height: 1) }
        }
    }
}

struct Stat: View {
    var label: String; var value: Int?; var color: Color
    init(_ label: String, _ value: Int?, _ color: Color = .white) { self.label = label; self.value = value; self.color = color }
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value.map(String.init) ?? "—").font(.system(size: 18, weight: .bold, design: .monospaced)).foregroundStyle(color)
            Text(label).font(.system(size: 8, design: .monospaced)).tracking(1.2).foregroundStyle(Theme.dim)
        }
    }
}
