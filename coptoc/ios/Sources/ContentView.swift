import SwiftUI

struct ContentView: View {
    @Environment(COPStore.self) private var store

    var body: some View {
        @Bindable var store = store
        ZStack(alignment: .bottom) {
            ZStack(alignment: .bottom) {
                Group {
                    switch store.tab {
                    case "COP": MapScreen()
                    case "S1": PersonnelScreen()
                    case "S2": IntelScreen()
                    case "S3": OpsScreen()
                    case "S4": LogisticsScreen()
                    default: SignalScreen()
                    }
                }.frame(maxWidth: .infinity, maxHeight: .infinity)
                .safeAreaInset(edge: .top, spacing: 0) { VStack(spacing: 0) { PostureBar(); FlashStrip() } }  // the map runs under the header; lists start below it
                TabBar(tab: Binding(get: { store.tab }, set: { store.tab = $0 }))
            }
        }
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
    @State private var pendingProfile: String? = nil
    var body: some View { bar.alert("Switch profile?", isPresented: Binding(get: { pendingProfile != nil }, set: { if !$0 { pendingProfile = nil } })) {
        Button("Switch", role: .destructive) { if let p = pendingProfile { store.act("switching to \(p)") { try await store.client.setProfile(p) }; pendingProfile = nil } }
        Button("Cancel", role: .cancel) { pendingProfile = nil }
    } message: { Text(pendingProfile == "military" ? "S1–S6 and the Combat Aviation Brigade. This reloads the sample data." : "S1–S3 and the executive-protection sample. This reloads the sample data.") } }
    @ViewBuilder var bar: some View {
        let s = store.snapshot?.summary
        let posture = s?.posture ?? "normal"
        VStack(spacing: 0) {
            ZStack {
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
            HStack(spacing: 10) {
                Text(clock(store.now)).font(.system(size: 12, design: .monospaced)).foregroundStyle(Theme.dim)
                Spacer()
                Menu {
                    Menu("Signed in as" + (store.users.first { $0.id == store.client.userId }.map { " · \($0.name)" } ?? "")) {
                        ForEach(store.users) { u in
                            Button { store.signIn(u.id) } label: { Label("\(u.name)\(u.title.map { " · \($0)" } ?? "")", systemImage: store.client.userId == u.id ? "checkmark" : (u.battleCaptain ? "star" : "person")) }
                        }
                    }
                    if store.me?.admin ?? (store.client.role == "battle_captain") {
                        // Buttons, not a Picker: a Picker's binding can fire without a tap; these fire only when chosen, and then ask.
                        let current = store.snapshot?.profile ?? "military"
                        Menu("Profile · \(current.capitalized)") {
                            Button { if current != "military" { pendingProfile = "military" } } label: { Label("Military · S1–S6, the brigade", systemImage: current == "military" ? "checkmark" : "") }
                            Button { if current != "corporate" { pendingProfile = "corporate" } } label: { Label("Corporate · S1–S3", systemImage: current == "corporate" ? "checkmark" : "") }
                        }
                    }
                    if store.client.userId.isEmpty {
                        Picker("Role", selection: Binding(get: { store.client.role }, set: { store.client.role = $0; Task { await store.load() } })) {
                            ForEach(["battle_captain", "ep", "security", "analyst", "ea", "logistics", "signal"], id: \.self) { Text($0.replacingOccurrences(of: "_", with: " ").capitalized).tag($0) }
                        }
                    }
                    Menu("Display") {
                        Toggle("Lean labels", isOn: Binding(get: { store.leanLabels }, set: { store.leanLabels = $0 }))
                        Toggle("Posture header", isOn: Binding(get: { store.postureHeader }, set: { store.postureHeader = $0 }))
                    }
                } label: { Image(systemName: "gearshape.fill").font(.system(size: 17)).foregroundStyle(Theme.dim).padding(6) }
            }
            }
            .padding(.horizontal, 14).padding(.top, 4).padding(.bottom, 8)
            .background(Theme.panel.opacity(0.88))   // the header: darker, less translucent
            .overlay(alignment: .bottom) { Rectangle().fill(Theme.line).frame(height: 0.5) }
            VStack(spacing: 6) {
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
            .padding(.horizontal, 12).padding(.vertical, 8)
            .background(Theme.panel.opacity(0.72), in: RoundedRectangle(cornerRadius: 12))   // the watch and the counters: a lighter card floating over the picture (dark enough to read over bright map)
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.line, lineWidth: 0.5))
            .padding(.horizontal, 10).padding(.top, 8)
        }
        .padding(.bottom, 6)
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
    @Environment(COPStore.self) private var store
    static let section: [String: String] = ["PERSONNEL": "S1", "PRESENT": "S1", "CHECKED IN": "S1", "SEC ON SHIFT": "S1", "UNACCOUNTED": "S1", "UNREACHABLE": "S1", "TRAVELING": "S3", "VIP OUT": "S3", "EVENTS": "S3", "THREATS": "S2", "CONFIRMED": "S2", "FLASH": "S2", "OPEN PIRs": "S2"]
    var label: String; var value: Int?; var color: Color
    init(_ label: String, _ value: Int?, _ color: Color = .white) { self.label = label; self.value = value; self.color = color }
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value.map(String.init) ?? "—").font(.system(size: 18, weight: .bold, design: .monospaced)).foregroundStyle(color)
            Text(label).font(.system(size: 8, design: .monospaced)).tracking(1.2).foregroundStyle(Theme.dim)
        }
        .contentShape(Rectangle()).onTapGesture { if let sec = Self.section[label] { withAnimation { store.tab = sec; store.expandBar() } } }  // a counter opens its section
    }
}


/// The tab bar, drawn by the app: the enabled staff sections in wall order, so a deployment with S4 and S6 gets six tabs and a
/// commercial desk four — the native bar caps at five and hides the rest behind "More".
struct TabBar: View {
    @Environment(COPStore.self) private var store
    @Binding var tab: String
    static let icons = ["COP": "map", "S1": "person.3", "S2": "eye", "S3": "calendar", "S4": "shippingbox", "S6": "antenna.radiowaves.left.and.right"]
    var tabs: [String] {
        let cfg = store.snapshot?.sections ?? []
        let on = { (c: String) in cfg.first { $0.code == c }?.enabled ?? (c != "S4" && c != "S6") }
        return ["COP", "S1", "S2", "S3", "S4", "S6"].filter { $0 == "COP" || (on($0) && store.can($0)) }
    }
    func badge(_ t: String) -> (Int, Color)? {
        let s = store.snapshot?.summary
        switch t {
        case "S1": let n = (store.snapshot?.incidents ?? []).filter { $0.status == "open" }.count; return n > 0 ? (n, Theme.red) : nil
        case "S2": let n = s?.warningsPending ?? 0; return n > 0 ? (n, Theme.red) : nil
        case "S4": return (s?.s4Status ?? "green") == "green" ? nil : (0, healthColor(s?.s4Status ?? "green"))
        case "S6": return (s?.s6Status ?? "green") == "green" ? nil : (0, healthColor(s?.s6Status ?? "green"))
        default: return nil
        }
    }
    var body: some View {
        let c = store.barCollapsed
        HStack(spacing: 0) {
            ForEach(tabs, id: \.self) { t in
                let on = t == tab
                Button { tab = t; store.selection = nil; store.expandBar() } label: {
                    VStack(spacing: c ? 0 : 3) {
                        ZStack(alignment: .topTrailing) {
                            Image(systemName: Self.icons[t] ?? "square").font(.system(size: c ? 17 : 20, weight: .medium)).frame(height: c ? 20 : 24)
                            if let (n, c) = badge(t) {
                                if n > 0 { Text("\(n)").font(.system(size: 9, weight: .bold)).foregroundStyle(.white).padding(.horizontal, 4).padding(.vertical, 1).background(c, in: Capsule()).offset(x: 10, y: -6) }
                                else { Circle().fill(c).frame(width: 8, height: 8).offset(x: 6, y: -3) }
                            }
                        }
                        if !c { Text(t == "COP" ? "COP" : store.sectionLabel(t)).font(.system(size: 10, weight: on ? .semibold : .regular)).transition(.opacity) }
                    }
                    .foregroundStyle(on ? Theme.blue : Theme.dim).frame(maxWidth: .infinity).padding(.vertical, c ? 5 : 8)
                    .background(on ? Theme.line.opacity(0.9) : .clear, in: Capsule())
                }.buttonStyle(.plain)
            }
        }
        .padding(c ? 3 : 4)
        .background(.ultraThinMaterial, in: Capsule())
        .overlay(Capsule().stroke(Theme.line, lineWidth: 0.5))
        .padding(.horizontal, c ? 48 : 20).padding(.bottom, c ? 4 : 6)
    }
}
