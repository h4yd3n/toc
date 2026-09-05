import SwiftUI

struct PersonnelScreen: View {
    @Environment(COPStore.self) private var store
    @State private var addingSite = false
    var body: some View {
        List {
            Section { EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S1" }) }.listRowBackground(Theme.panel)
            TaskingsSection(section: "S1")
            if !store.openIncidents.isEmpty {
                Section(header: SectionLabel(text: "S6 · ROLL CALLS")) {
                    ForEach(store.openIncidents) { inc in
                        Button { store.selection = .incident(inc.id) } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack { Text("☎ \(inc.title)").font(.system(size: 13, weight: .semibold)); Spacer(); Text("\(inc.accounted)/\(inc.total)").font(.system(size: 12, weight: .bold, design: .monospaced)).foregroundStyle(inc.pct == 100 ? Theme.green : Theme.red) }
                                ProgressView(value: Double(inc.accounted), total: Double(max(inc.total, 1))).tint(inc.pct == 100 ? Theme.green : Theme.red)
                            }
                        }.foregroundStyle(.primary)
                    }
                }.listRowBackground(Theme.red.opacity(0.08))
            }
            TaskOrgSection()
            Section(header: HStack {
                SectionLabel(text: "LOCATIONS")
                if store.can("S3", "edit") {
                    Spacer()
                    Button("+ SITE") { addingSite = true }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered)
                }
            }) {
                ForEach(store.snapshot?.locations ?? []) { l in
                    Button { store.selection = .site(l.id) } label: {
                        HStack(spacing: 8) {
                            Circle().fill(Theme.posture(l.effectivePosture)).frame(width: 7, height: 7).shadow(color: Theme.posture(l.effectivePosture), radius: 4)
                            if l.isToc == true { Text("◈").foregroundStyle(Theme.blue) }
                            Text(l.name).lineLimit(1)
                            if l.sensitivity == "restricted" { Text("⚿").foregroundStyle(Theme.amber) }
                            Spacer()
                            if !l.confirmedThreatIds.isEmpty { Text("▲\(l.confirmedThreatIds.count)").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Theme.red) }
                            else if !l.threatIdsInArea.isEmpty { Text("△\(l.threatIdsInArea.count)").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.amber) }
                            Text("\(l.present)").font(.system(size: 12, weight: .semibold, design: .monospaced)) + Text("/\(l.assigned)").font(.system(size: 12, design: .monospaced)).foregroundStyle(Theme.dim)
                            if l.securityOnShift > 0 { Text("·\(l.securityOnShift)⛨").font(.system(size: 11, design: .monospaced)).foregroundStyle(Theme.green) }
                        }
                    }.foregroundStyle(.primary)
                }
            }.listRowBackground(Theme.panel)
            Section(header: SectionLabel(text: "TRAVELING \(store.travelers.count)")) {
                ForEach(store.travelers) { p in
                    Button { store.selection = .person(p.id) } label: {
                        HStack(spacing: 8) {
                            Circle().fill(p.confirmedThreatIds.isEmpty ? Theme.blue : Theme.red).frame(width: 7, height: 7)
                            if p.isVip { Text("★").foregroundStyle(Theme.gold) }
                            Text(p.name).lineLimit(1)
                            PresenceChip(person: p)
                            Spacer()
                            Text(store.trip(p.tripId)?.destName.split(separator: ",").first.map(String.init) ?? "").font(.system(size: 11, design: .monospaced)).foregroundStyle(Theme.dim)
                        }
                    }.foregroundStyle(.primary)
                }
            }.listRowBackground(Theme.panel)
        }
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg).drivesDock(store)
        .sheet(isPresented: $addingSite) { SiteForm { addingSite = false } }
    }
}

struct PresenceChip: View {
    var person: Person
    var body: some View {
        if person.positionSource == "checkin" { Chip(text: "✓\(Int((person.checkinAgeH ?? 0).rounded()))h", color: Theme.green) }
        else if person.checkinStale { Chip(text: "STALE", color: Theme.amber) }
    }
}

struct IntelScreen: View {
    @Environment(COPStore.self) private var store
    var body: some View {
        List {
            Section {
                HStack { Spacer()
                    Button("⟳ COLLECT") { store.act("collecting") { try await store.client.refreshIntel() } }
                        .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue).disabled(store.busy != nil) }
                EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S2" })
            }.listRowBackground(Theme.panel)
            TaskingsSection(section: "S2")
            Section(header: SectionLabel(text: "WARNINGS · \(store.pendingWarnings.count) AWAITING RELEASE")) {
                if store.pendingWarnings.isEmpty {
                    HStack { Text("Nothing suggested. Confirm a link on an elevated threat, or collect a critical one.").font(.system(size: 11)).foregroundStyle(Theme.dim)
                        Spacer(); Button("RUN RULE") { store.act("running the warning rule") { try await store.client.runWarningRule() } }.font(.system(size: 9, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil) }
                }
                ForEach(store.pendingWarnings) { w in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack { Chip(text: w.severity.uppercased(), color: w.severity == "critical" ? Theme.red : Theme.amber, filled: true); Chip(text: w.status.uppercased(), color: Theme.dim); Text(w.shortTitle).font(.system(size: 12, weight: .semibold)).lineLimit(2) }
                        Text("\(w.suggestedBy) · \(w.subjectType) \(w.subjectName)").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                        HStack {
                            if store.client.role == "battle_captain" { Button("RELEASE · SMS + CHAT") { store.act("releasing FLASH") { try await store.client.releaseWarning(id: w.id) } }.tint(Theme.red) }
                            else { Text("Battle Captain releases").font(.system(size: 10)).foregroundStyle(Theme.dim) }
                            if store.client.role == "battle_captain" || store.client.role == "analyst" { Button("CANCEL") { store.act("cancelling warning") { try await store.client.cancelWarning(id: w.id) } } }
                        }.font(.system(size: 9, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
                    }
                }
            }.listRowBackground(Theme.panel)
            if let i = store.intsums.first {
                Section(header: SectionLabel(text: "INTSUM · \(i.status.uppercased())")) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(i.headline).font(.system(size: 12)).foregroundStyle(i.nstr ? Theme.green : .primary)
                        HStack {
                            if i.status != "released" && store.client.role == "battle_captain" { Button("RELEASE") { store.act("releasing INTSUM") { try await store.client.releaseIntsum(id: i.id) } }.tint(Theme.green) }
                            else if let by = i.releasedBy { Text("released by \(by)").font(.system(size: 10)).foregroundStyle(Theme.dim) }
                            Spacer()
                            if store.client.role == "battle_captain" || store.client.role == "analyst" { Button("DRAFT NOW") { store.act("drafting INTSUM") { try await store.client.draftIntsum() } } }
                        }.font(.system(size: 9, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
                    }
                }.listRowBackground(Theme.panel)
            }
            Section(header: SectionLabel(text: "REQUIREMENTS · \(store.requirements.count) ACTIVE · \(store.requirements.isEmpty ? 0 : store.requirements.map(\.coverage.pct).reduce(0, +) / store.requirements.count)% AVG COVERAGE")) {
                ForEach(store.requirements.sorted { $0.priority < $1.priority }.prefix(12)) { r in
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 6) {
                            Chip(text: "P\(r.priority)", color: r.priority == 1 ? Theme.red : r.priority == 2 ? Theme.amber : Theme.dim, filled: true)
                            Chip(text: r.kind == "directed" ? "DIRECTED" : r.subjectType.uppercased(), color: Theme.dim)
                            Text(r.subjectName).font(.system(size: 12)).lineLimit(1); Spacer()
                            Text("\(r.coverage.covered)/\(r.coverage.total)").font(.system(size: 10, design: .monospaced)).foregroundStyle(r.coverage.pct == 100 ? Theme.green : Theme.amber)
                        }
                        ProgressView(value: Double(r.coverage.pct), total: 100).tint(r.coverage.pct == 100 ? Theme.green : Theme.amber)
                    }
                }
            }.listRowBackground(Theme.panel)
            if !store.cases.isEmpty {
                Section(header: SectionLabel(text: "CASES · \(store.cases.filter { $0.status == "open" }.count) OPEN")) {
                    ForEach(store.cases) { c in
                        HStack(spacing: 8) {
                            Chip(text: c.kind.uppercased(), color: c.kind == "person" ? Theme.amber : Theme.dim); Text(c.title).font(.system(size: 12, weight: .semibold)).lineLimit(1); Spacer()
                            if (c.pendingReview ?? 0) > 0 { Chip(text: "\(c.pendingReview!) TO REVIEW", color: Theme.amber) } else { Chip(text: c.status.uppercased(), color: c.status == "open" ? Theme.green : Theme.dim) }
                        }
                    }
                }.listRowBackground(Theme.panel)
            }
            Section(header: SectionLabel(text: "THREATS \(store.snapshot?.threats.count ?? 0) · \(store.snapshot?.summary.realThreats ?? 0) LIVE")) {
                ForEach(store.snapshot?.threats ?? []) { t in
                    Button { store.selection = .threat(t.id) } label: {
                        HStack(spacing: 8) {
                            Chip(text: String(t.severity.prefix(3)).uppercased(), color: Theme.severity(t.severity), filled: t.severity == "elevated" || t.severity == "critical")
                            Text(t.title).lineLimit(1)
                            if !t.synthetic { Chip(text: "LIVE", color: Theme.green) }
                            Spacer()
                            if !t.confirmedLinks.isEmpty { Text("▲\(t.confirmedLinks.count)").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Theme.red) }
                            Text(ISO.rel(t.observedAt, now: store.now)).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                        }
                    }.foregroundStyle(.primary)
                }
            }.listRowBackground(Theme.panel)
            Section(header: SectionLabel(text: "ASSESSMENTS")) {
                ForEach(store.snapshot?.assessments ?? []) { a in AssessmentCard(a: a) }
            }.listRowBackground(Theme.panel)
            Section(header: SectionLabel(text: "PIRs · \(store.snapshot?.summary.openPirs ?? 0) OPEN")) {
                ForEach(store.snapshot?.pirs ?? []) { p in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack { Text(p.id).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.blue); Text("P\(p.priority)").font(.system(size: 9, design: .monospaced)).foregroundStyle(Theme.amber); Spacer(); Chip(text: p.status, color: p.status == "OPEN" ? Theme.amber : p.status == "COLLECTING" ? Theme.blue : Theme.dim) }
                        Text(p.question).font(.system(size: 12)).foregroundStyle(.secondary)
                    }
                }
            }.listRowBackground(Theme.panel)
        }
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg).drivesDock(store)
    }
}

struct AssessmentCard: View {
    @Environment(COPStore.self) private var store
    var a: Assessment
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack { Text(a.id).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.blue); Text(a.title).font(.system(size: 13, weight: .semibold)).lineLimit(1); Spacer(); Chip(text: a.status.uppercased(), color: a.status == "approved" ? Theme.green : a.status == "review" ? Theme.amber : Theme.dim) }
            if a.confidence == "insufficient" {
                Text("COLLECTION GAP · refused to assess").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Theme.amber)
            } else {
                HStack(spacing: 4) { Text(a.likelihood).bold(); Text("(\(a.band))").foregroundStyle(Theme.dim); Text("·"); Text("\(a.confidence) confidence").foregroundStyle(Theme.confidence(a.confidence)) }.font(.system(size: 12))
            }
            Text(a.bluf).font(.system(size: 12)).foregroundStyle(.secondary)
            HStack {
                Text(a.author).font(.system(size: 10)).foregroundStyle(Theme.dim); Spacer()
                if a.status == "draft" { Button("→ REVIEW") { store.act("sending to review") { try await store.client.setAssessmentStatus(id: a.id, status: "review") } } }
                if a.status == "review" && a.confidence != "insufficient" { Button("✓ APPROVE") { store.act("approving") { try await store.client.setAssessmentStatus(id: a.id, status: "approved") } }.tint(Theme.green) }
            }.font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
        }
        .padding(.leading, 6).overlay(alignment: .leading) { Rectangle().fill(a.confidence == "insufficient" ? Theme.amber : .clear).frame(width: 2) }
    }
}

struct OpsScreen: View {
    @Environment(COPStore.self) private var store
    @State private var tops: [Date: CGFloat] = [:] // last known top of each day header in the agenda's space — the strip follows the one that just passed the top
    @State private var scrollY: CGFloat = 0        // top of the content; below zero once the agenda has scrolled
    @State private var scrubbed: Date? = nil       // the ribbon is driving; a finger on the agenda hands the cursor back
    @State private var expanded = false            // the strip unfolded into the month
    @State private var month: Date? = nil          // the month shown when unfolded (defaults to the cursor's)
    let cal = Calendar(identifier: .gregorian)
    struct AgendaItem: Identifiable { enum Kind { case event(CopEvent), trip(Trip) }; var id: String; var day: Date; var kind: Kind }
    var agenda: [(day: Date, items: [AgendaItem])] {
        guard let snap = store.snapshot else { return [] }
        var items: [AgendaItem] = snap.events.compactMap { e in ISO.date(e.startAt).map { AgendaItem(id: e.id, day: cal.startOfDay(for: $0), kind: .event(e)) } }
        items += snap.trips.filter { $0.eventId == nil }.compactMap { t in ISO.date(t.departAt).map { AgendaItem(id: t.id, day: cal.startOfDay(for: max($0, cal.startOfDay(for: store.now))), kind: .trip(t)) } }
        let grouped = Dictionary(grouping: items, by: \.day)
        return grouped.keys.sorted().map { (day: $0, items: grouped[$0]!.sorted { a, b in if case .event = a.kind, case .trip = b.kind { return true }; return a.id < b.id }) }
    }
    var eventDays: Set<Date> {
        var out = Set<Date>()
        for e in store.snapshot?.events ?? [] { guard let a = ISO.date(e.startAt), let b = ISO.date(e.endAt) else { continue }
            var d = cal.startOfDay(for: a); while d <= b { out.insert(d); d = cal.date(byAdding: .day, value: 1, to: d)! } }
        return out
    }
    static func key(_ d: Date) -> String { "d:\(Int(d.timeIntervalSince1970))" }
    /// The day the panel is on: the one the finger is holding on the ribbon, else the day whose header is at or
    /// above the top of the agenda, else today.
    var cursorDay: Date {
        if let scrubbed { return scrubbed }
        if let passed = tops.filter({ $0.value <= 24 }).max(by: { $0.value < $1.value })?.key { return passed }
        if let coming = tops.min(by: { $0.value < $1.value })?.key { return coming }   // nothing has passed the top yet
        return agenda.first?.day ?? cal.startOfDay(for: store.now)
    }
    var body: some View {
        let days = agenda
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    Color.clear.frame(height: 0).background(GeometryReader { g in Color.clear.preference(key: ScrollTopKey.self, value: g.frame(in: .named("agenda")).minY) })
                    EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S3" }).padding(.horizontal, 14)
                    TaskingsSection(section: "S3", plain: true)
                    ForEach(Array(days.enumerated()), id: \.element.day) { idx, d in
                        if idx > 0, let gap = cal.dateComponents([.day], from: days[idx - 1].day, to: d.day).day, gap > 1 {
                            Text("— nothing for \(gap - 1) day\(gap - 1 == 1 ? "" : "s") —").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).frame(maxWidth: .infinity).padding(.vertical, 10).id("g:\(Int(d.day.timeIntervalSince1970))")
                        }
                        DayHeader(day: d.day, now: store.now).padding(.horizontal, 14).padding(.top, 12).padding(.bottom, 4).id(Self.key(d.day))
                            .background(GeometryReader { g in Color.clear.preference(key: DayTopKey.self, value: [d.day: g.frame(in: .named("agenda")).minY]) })
                        ForEach(d.items) { item in
                            AgendaRow(item: item).id("r:\(Int(d.day.timeIntervalSince1970)):\(item.id)")
                            Divider().overlay(Theme.line).padding(.leading, 14)
                        }
                    }
                    if days.isEmpty { Text("Nothing planned.").font(.system(size: 12)).foregroundStyle(Theme.dim).padding(14) }
                    SectionLabel(text: "BATTLE LOG · hash-chained").padding(.horizontal, 14).padding(.top, 16)
                    ForEach(store.snapshot?.log ?? []) { e in
                        HStack(alignment: .firstTextBaseline, spacing: 8) {
                            Text(ISO.rel(e.at, now: store.now)).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).frame(width: 52, alignment: .leading)
                            Text(e.type.replacingOccurrences(of: "cop.", with: "")).font(.system(size: 9, design: .monospaced)).foregroundStyle(e.actorType == "human" ? Theme.blue : Theme.amber)
                            Text(e.summary ?? "").font(.system(size: 11)).lineLimit(1)
                            Spacer(); Text(e.actor).font(.system(size: 10)).foregroundStyle(Theme.dim).lineLimit(1)
                        }.padding(.horizontal, 14).padding(.vertical, 3)
                    }
                    Color.clear.frame(height: 90)
                }
            }
            .drivesDock(store)
            .onScrollPhaseChange { _, phase in if phase == .interacting { scrubbed = nil } }  // a hand on the agenda takes the cursor back
            .coordinateSpace(name: "agenda")
            // Only the day headers still on screen: merging kept days that had scrolled away at their last known
            // position, and a stale one would win the "closest to the top" test over the day actually up there.
            .onPreferenceChange(DayTopKey.self) { new in
                guard !new.isEmpty else { return }
                withAnimation(.easeInOut(duration: 0.25)) { tops = new }
            }
            .onPreferenceChange(ScrollTopKey.self) { y in scrollY = y; if y < -8, expanded { withAnimation(.easeInOut(duration: 0.25)) { expanded = false } } }
            .safeAreaInset(edge: .top, spacing: 0) {
            CalendarStrip(cursor: cursorDay, today: cal.startOfDay(for: store.now), marked: Set(days.map(\.day)), eventDays: eventDays, expanded: $expanded, month: $month,
                          onScrub: { day in
                // Scrolling the ribbon scrolls the agenda with it — no tap needed. The agenda only holds days that
                // have something, so an empty day carries you to the next one that does.
                scrubbed = day
                guard let target = days.first(where: { $0.day >= day }) ?? days.last else { return }
                proxy.scrollTo(Self.key(target.day), anchor: .top)
            }) { picked in
                // jump to the picked day, or the first day after it that has something
                scrubbed = picked
                guard let target = days.first(where: { $0.day >= picked }) else { return }
                let wasExpanded = expanded
                withAnimation(.easeInOut(duration: 0.25)) { expanded = false }
                Task { @MainActor in   // let the strip fold first, so the jump lands against the folded inset
                    if wasExpanded { try? await Task.sleep(for: .milliseconds(280)) }
                    withAnimation(.easeInOut(duration: 0.35)) { proxy.scrollTo(Self.key(target.day), anchor: .top) }
                }
            }
            }
        }
        .background(Theme.bg)
    }
}

struct DayTopKey: PreferenceKey { static var defaultValue: [Date: CGFloat] = [:]; static func reduce(value: inout [Date: CGFloat], nextValue: () -> [Date: CGFloat]) { value.merge(nextValue()) { $1 } } }
struct ScrollTopKey: PreferenceKey { static var defaultValue: CGFloat = 0; static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() } }

/// One agenda row: an event or a standalone trip.
struct AgendaRow: View {
    @Environment(COPStore.self) private var store
    var item: OpsScreen.AgendaItem
    var body: some View {
        switch item.kind {
        case .event(let e):
            Button { store.selection = .event(e.id) } label: {
                VStack(alignment: .leading, spacing: 3) {
                    HStack { Chip(text: e.status == "active" ? "LIVE" : "T-\(e.daysUntil)d", color: Theme.purple); Text("★ \(e.name)").font(.system(size: 13, weight: .semibold)).lineLimit(1); Spacer()
                        if let op = e.operation { Chip(text: "OP \(op.tasksDone)/\(op.tasksTotal)", color: Theme.purple) }
                        if let c = e.coverage { Chip(text: "COVER \(c.assigned)/\(c.required)", color: c.gap > 0 ? Theme.red : Theme.green) } }
                    Text(e.venueName).font(.system(size: 12, design: .monospaced))
                    Text("\(ISO.short(e.startAt)) → \(ISO.short(e.endAt)) · \(e.attendeeCount) attending · \(e.vipCount) VIP · \(e.tripsGenerated) trips").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                }.padding(.horizontal, 14).padding(.vertical, 8).frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
            }.foregroundStyle(.primary).buttonStyle(.plain)
        case .trip(let t):
            Button { store.selection = .person(t.personId) } label: {
                VStack(alignment: .leading, spacing: 3) {
                    HStack { Chip(text: t.status.uppercased(), color: t.status == "active" ? Theme.blue : Theme.dim); if t.isVip { Text("★").foregroundStyle(Theme.gold) }; Text(t.personName).font(.system(size: 13, weight: .semibold))
                        if let op = t.operation { Chip(text: "OP \(op.tasksDone)/\(op.tasksTotal)", color: Theme.purple) } }
                    Text("\(t.originName.split(separator: " ").first.map(String.init) ?? "") → \(t.destName.split(separator: ",").first.map(String.init) ?? "") · ret \(ISO.rel(t.returnAt, now: store.now))").font(.system(size: 12, design: .monospaced))
                    Text(t.purpose).font(.system(size: 11)).foregroundStyle(.secondary).lineLimit(1)
                    if let l = t.currentLeg { Text("\(l.icon) \(l.label.isEmpty ? l.toName : l.label) · \(l.kind == "lodging" ? "until \(ISO.rel(l.endAt, now: store.now))" : "→ \(l.toName) \(ISO.rel(l.endAt, now: store.now))")").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.blue).lineLimit(1) }
                }.padding(.horizontal, 14).padding(.vertical, 8).frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
            }.foregroundStyle(.primary).buttonStyle(.plain)
        }
    }
}

/// The calendar strip: a continuous ribbon of days that keeps the agenda's day in the middle, unfolding into the month on a tap of its name.
struct CalendarStrip: View {
    var cursor: Date; var today: Date; var marked: Set<Date>; var eventDays: Set<Date>
    @Binding var expanded: Bool; @Binding var month: Date?
    var onScrub: (Date) -> Void   // the ribbon dragged under the finger: the agenda follows it, day by day
    var onPick: (Date) -> Void
    @State private var stripDay: Date?
    @State private var scrubbing = false   // true while the finger owns the ribbon, so the agenda cannot pull it back
    let cal = Calendar(identifier: .gregorian)
    var ribbon: [Date] {  // two months back to four past the last marked day — enough tape in both directions
        let last = max(marked.max() ?? today, today)
        let start = cal.date(byAdding: .day, value: -60, to: today)!, end = cal.date(byAdding: .day, value: 120, to: last)!
        var out: [Date] = []; var d = start; while d <= end { out.append(d); d = cal.date(byAdding: .day, value: 1, to: d)! }
        return out
    }
    var body: some View {
        let shownMonth = expanded ? (month ?? cal.date(from: cal.dateComponents([.year, .month], from: cursor))!) : cal.date(from: cal.dateComponents([.year, .month], from: cursor))!
        VStack(spacing: 4) {
            HStack {
                HStack(spacing: 6) { Text(shownMonth.formatted(.dateTime.month(.wide).year()).uppercased()).font(.system(size: 10, weight: .bold, design: .monospaced)).tracking(1.8); Text(expanded ? "▴" : "▾").font(.system(size: 9)).foregroundStyle(Theme.dim) }
                Spacer()
                if expanded {
                    Button("‹") { month = cal.date(byAdding: .month, value: -1, to: shownMonth) }.buttonStyle(.plain).foregroundStyle(Theme.dim)
                    Button("›") { month = cal.date(byAdding: .month, value: 1, to: shownMonth) }.buttonStyle(.plain).foregroundStyle(Theme.dim).padding(.leading, 14)
                } else {
                    Text(cursor == today ? "TODAY" : "\(cal.dateComponents([.day], from: today, to: cursor).day ?? 0) DAYS OUT").font(.system(size: 9, design: .monospaced)).foregroundStyle(Theme.dim)
                }
            }.padding(.horizontal, 4).contentShape(Rectangle()).onTapGesture { setExpanded(!expanded) }
            if expanded {
                HStack(spacing: 0) { ForEach(["M", "T", "W", "T", "F", "S", "S"], id: \.self) { d in Text(d).font(.system(size: 8, design: .monospaced)).foregroundStyle(Theme.dim).frame(maxWidth: .infinity) } }
                let first = shownMonth, offset = (cal.component(.weekday, from: first) + 5) % 7, count = cal.range(of: .day, in: .month, for: first)!.count
                ForEach(0..<Int(ceil(Double(offset + count) / 7)), id: \.self) { r in
                    HStack(spacing: 0) { ForEach(0..<7, id: \.self) { c in let i = r * 7 + c - offset
                        if i >= 0 && i < count, let d = cal.date(byAdding: .day, value: i, to: first) { dayCell(d, weekday: false) } else { Color.clear.frame(maxWidth: .infinity).frame(height: 35) } } }
                }
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(spacing: 0) {
                        ForEach(ribbon, id: \.self) { d in dayCell(d, weekday: true).containerRelativeFrame(.horizontal, count: 7, spacing: 0).id(d) }
                    }.scrollTargetLayout()
                }
                .scrollTargetBehavior(.viewAligned)
                .scrollPosition(id: $stripDay, anchor: .center)
                .onScrollPhaseChange { _, phase in scrubbing = phase != .idle }
                .onChange(of: stripDay) { _, d in if scrubbing, let d { onScrub(d) } }   // the agenda follows the ribbon
                .onChange(of: cursor) { _, c in                                          // and the ribbon follows the agenda
                    guard !scrubbing, stripDay != c else { return }
                    withAnimation(.easeInOut(duration: 0.35)) { stripDay = c }
                }
                .onAppear { stripDay = cursor }
                .frame(height: 48)
            }
            Capsule().fill(Theme.dim.opacity(0.5)).frame(width: 36, height: 4).padding(.top, 2)  // the grabber: drag down for the month, up for the ribbon
        }
        .padding(.horizontal, 10).padding(.top, 6).padding(.bottom, 5)
        .fixedSize(horizontal: false, vertical: true)
        .background(Theme.panel).overlay(alignment: .bottom) { Rectangle().fill(Theme.line).frame(height: 1) }
        .simultaneousGesture(DragGesture(minimumDistance: 14).onEnded { v in
            guard abs(v.translation.height) > abs(v.translation.width) else { return }
            if v.translation.height > 20 { setExpanded(true) } else if v.translation.height < -20 { setExpanded(false) }
        })
    }
    func setExpanded(_ on: Bool) { withAnimation(.spring(duration: 0.35)) { expanded = on; month = nil } }
    func dayCell(_ d: Date, weekday: Bool) -> some View {
        let isToday = d == today, isCursor = d == cursor, hasEvent = eventDays.contains(d), hasAny = marked.contains(d)
        return VStack(spacing: 2) {
            if weekday { Text(d.formatted(.dateTime.weekday(.narrow))).font(.system(size: 8, design: .monospaced)).foregroundStyle(isCursor ? Theme.blue : Theme.dim) }
            Text("\(cal.component(.day, from: d))").font(.system(size: 12, weight: isToday || isCursor ? .bold : .regular, design: .monospaced))
                .foregroundStyle(isCursor ? Color.black : d < today ? Theme.dim : .primary)
                .frame(width: 26, height: 26).background(isCursor ? Theme.blue : .clear, in: Circle()).overlay(Circle().stroke(isToday ? Theme.red : .clear, lineWidth: 1.5))
                .animation(.easeInOut(duration: 0.25), value: isCursor)
            Circle().fill(hasEvent ? Theme.purple : hasAny ? Theme.blue : .clear).frame(width: 5, height: 5)
        }.frame(maxWidth: .infinity).frame(height: weekday ? 48 : 35).contentShape(Rectangle()).onTapGesture { onPick(d) }
    }
}

/// A day header on the agenda: weekday, date, and how far away it is.
struct DayHeader: View {
    var day: Date; var now: Date
    var body: some View {
        let f = DateFormatter(); let _ = f.dateFormat = "EEE d MMM"
        let days = Calendar(identifier: .gregorian).dateComponents([.day], from: Calendar(identifier: .gregorian).startOfDay(for: now), to: day).day ?? 0
        HStack { Text(f.string(from: day).uppercased()).font(.system(size: 10, weight: .bold, design: .monospaced)).tracking(1.5).foregroundStyle(days == 0 ? Theme.red : .primary)
            Text(days == 0 ? "TODAY" : days == 1 ? "TOMORROW" : days < 0 ? "STARTED" : "IN \(days) DAYS").font(.system(size: 9, design: .monospaced)).foregroundStyle(Theme.dim) }
    }
}


// MARK: - §7 S4 Logistics and §8 S6 Signal — the background boards on the phone

func healthColor(_ h: String) -> Color { h == "red" ? Theme.red : h == "amber" ? Theme.amber : Theme.green }

struct LogisticsScreen: View {
    @Environment(COPStore.self) private var store
    @State private var all = false
    @State private var editing: SupplyLine? = nil
    @State private var onHandText = ""
    var body: some View {
        let board = store.snapshot?.s4
        let title = store.snapshot?.sections?.first { $0.code == "S4" }?.title ?? "LOGISTICS"
        List {
            Section {
                EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S4" })
                if let b = board {
                    HStack(spacing: 8) { Chip(text: "S4 \(b.status.uppercased())", color: healthColor(b.status), filled: b.status != "green")
                        Text("\(b.counts.red) red · \(b.counts.amber) amber · \(b.counts.inbound) inbound" + (b.counts.late > 0 ? " · \(b.counts.late) late" : "")).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                        Spacer(); Button(all ? "EXCEPTIONS" : "ALL") { all.toggle() }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue) }
                }
            }.listRowBackground(Theme.bg).listRowSeparator(.hidden)
            TaskingsSection(section: "S4")
            if let b = board {
                let lines = all ? b.supplies : b.supplies.filter { $0.status != "green" }
                Section(header: SectionLabel(text: "SUPPLY & EQUIPMENT · \(lines.count)" + (all ? "" : " OF \(b.supplies.count)"))) {
                    if lines.isEmpty { Text("All lines at or above required.").font(.system(size: 11)).foregroundStyle(Theme.dim) }
                    ForEach(lines) { x in
                        Button { if store.client.role == "battle_captain" || store.client.role == "logistics" { editing = x; onHandText = String(format: "%g", x.onHand) } } label: {
                            HStack(spacing: 8) {
                                Chip(text: x.status == "green" ? "OK" : x.status.prefix(3).uppercased(), color: healthColor(x.status), filled: x.status != "green")
                                VStack(alignment: .leading, spacing: 2) { Text(x.item).font(.system(size: 12, weight: .semibold)); Text(x.locationName + (x.note.isEmpty ? "" : " · \(x.note)")).font(.system(size: 10)).foregroundStyle(Theme.dim).lineLimit(1) }
                                Spacer()
                                VStack(alignment: .trailing, spacing: 3) {
                                    Text("\(String(format: "%g", x.onHand))/\(String(format: "%g", x.required)) \(x.unit)").font(.system(size: 10, design: .monospaced))
                                    GeometryReader { g in ZStack(alignment: .leading) { Capsule().fill(Theme.line); Capsule().fill(healthColor(x.status)).frame(width: g.size.width * CGFloat(min(100, x.pct)) / 100) } }.frame(width: 54, height: 4)
                                }
                            }
                        }.buttonStyle(.plain)
                    }
                }.listRowBackground(Theme.bg)
                let inbound = b.shipments.filter { !["arrived", "cancelled"].contains($0.status) }
                Section(header: SectionLabel(text: "INBOUND · \(inbound.count)")) {
                    if inbound.isEmpty { Text("Nothing inbound.").font(.system(size: 11)).foregroundStyle(Theme.dim) }
                    ForEach(inbound) { x in
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 8) { Chip(text: x.priority == "urgent" ? "URG" : x.priority == "priority" ? "PRI" : "RTN", color: healthColor(x.health), filled: x.health != "green"); Text(x.description).font(.system(size: 12, weight: .semibold)); Spacer()
                                Text(x.status.replacingOccurrences(of: "_", with: " ").uppercased()).font(.system(size: 9, weight: .bold, design: .monospaced)).foregroundStyle(x.health == "green" ? Theme.dim : healthColor(x.health)) }
                            Text("\(x.quantity) → \(x.toName) · " + (x.hoursToEta < 0 ? "\(Int(-x.hoursToEta.rounded()))h late" : "ETA \(Int(x.hoursToEta.rounded()))h") + (x.note.isEmpty ? "" : " · \(x.note)")).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).lineLimit(2)
                            if store.client.role == "battle_captain" || store.client.role == "logistics" {
                                HStack(spacing: 6) {
                                    if x.status != "in_transit" { Button("MOVING") { store.act("updating shipment") { try await store.client.updateShipment(x.id, status: "in_transit") } }.tint(Theme.blue) }
                                    if x.status != "delayed" { Button("DELAYED") { store.act("updating shipment") { try await store.client.updateShipment(x.id, status: "delayed") } }.tint(Theme.amber) }
                                    Button("ARRIVED") { store.act("updating shipment") { try await store.client.updateShipment(x.id, status: "arrived") } }.tint(Theme.green)
                                }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
                            }
                        }
                    }
                }.listRowBackground(Theme.bg)
            } else { Text("No logistics board yet.").font(.system(size: 11)).foregroundStyle(Theme.dim).listRowBackground(Theme.bg) }
            Color.clear.frame(height: 70).listRowBackground(Theme.bg)
        }
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg).drivesDock(store)
        .alert("On hand", isPresented: Binding(get: { editing != nil }, set: { if !$0 { editing = nil } })) {
            TextField("On hand", text: $onHandText).keyboardType(.decimalPad)
            Button("Save") { if let x = editing, let v = Double(onHandText) { store.act("updating the supply line") { try await store.client.updateSupply(x.id, onHand: v, note: nil) } }; editing = nil }
            Button("Cancel", role: .cancel) { editing = nil }
        } message: { Text("\(editing?.item ?? "") at \(editing?.locationName ?? "") (\(editing?.unit ?? ""))") }
    }
}

struct SignalScreen: View {
    @Environment(COPStore.self) private var store
    @State private var all = false
    var body: some View {
        let board = store.snapshot?.s6
        let title = store.snapshot?.sections?.first { $0.code == "S6" }?.title ?? "SIGNAL"
        let canEdit = store.client.role == "battle_captain" || store.client.role == "signal"
        List {
            Section {
                EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S6" })
                if let b = board {
                    HStack(spacing: 8) { Chip(text: "S6 \(b.status.uppercased())", color: healthColor(b.status), filled: b.status != "green")
                        Text("\(b.counts.down) down · \(b.counts.degraded) degraded · \(b.counts.total) systems").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                        Spacer(); Button(all ? "EXCEPTIONS" : "ALL") { all.toggle() }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue) }
                }
            }.listRowBackground(Theme.bg).listRowSeparator(.hidden)
            TaskingsSection(section: "S6")
            if let b = board {
                Section(header: SectionLabel(text: "PACE · HOW TO REACH EACH SITE")) {
                    ForEach(b.pace.keys.sorted(), id: \.self) { site in
                        let p = b.pace[site]!
                        HStack(spacing: 8) {
                            Text(p.locationName).font(.system(size: 12, weight: .semibold)); Spacer()
                            ForEach(["primary", "alternate", "contingency", "emergency"], id: \.self) { r in
                                let st = p.nets[r]
                                Text(String(r.prefix(1)).uppercased()).font(.system(size: 9, weight: .heavy, design: .monospaced)).frame(width: 18, height: 18)
                                    .foregroundStyle(st == "up" ? Theme.green : st == "degraded" ? Theme.amber : st == "down" ? Theme.red : Theme.dim)
                                    .background(p.inUse == r ? Theme.green.opacity(0.18) : .clear, in: RoundedRectangle(cornerRadius: 3))
                                    .overlay(RoundedRectangle(cornerRadius: 3).stroke(Theme.line)).strikethrough(st == "down")
                            }
                            Text(p.inUse.map { "on \($0.uppercased())" } ?? "NO NET").font(.system(size: 9, design: .monospaced)).foregroundStyle(p.inUse == nil ? Theme.red : Theme.dim).frame(width: 90, alignment: .trailing)
                        }
                    }
                }.listRowBackground(Theme.bg)
                let systems = all ? b.systems : b.systems.filter { $0.health != "green" }
                Section(header: SectionLabel(text: "SYSTEMS · \(systems.count)" + (all ? "" : " OF \(b.systems.count)"))) {
                    if systems.isEmpty { Text("Everything up.").font(.system(size: 11)).foregroundStyle(Theme.dim) }
                    ForEach(systems) { x in
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 8) {
                                Chip(text: x.status == "up" ? "UP" : x.status == "degraded" ? "DEG" : "DOWN", color: healthColor(x.health), filled: x.health != "green")
                                VStack(alignment: .leading, spacing: 1) { Text(x.name).font(.system(size: 12, weight: .semibold)); Text(x.locationName + (x.pace.map { " · \($0.uppercased())" } ?? "") + (x.note.isEmpty || x.status == "up" ? "" : " · \(x.note)")).font(.system(size: 10)).foregroundStyle(Theme.dim).lineLimit(2) }
                                Spacer(); Text(x.hours < 48 ? "\(Int(x.hours.rounded()))h" : "\(Int((x.hours / 24).rounded()))d").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                            }
                            if canEdit {
                                HStack(spacing: 6) {
                                    if x.status != "up" { Button("UP") { store.act("updating system") { try await store.client.updateSystem(x.id, status: "up", note: nil) } }.tint(Theme.green) }
                                    if x.status != "degraded" { Button("DEGRADED") { store.act("updating system") { try await store.client.updateSystem(x.id, status: "degraded", note: nil) } }.tint(Theme.amber) }
                                    if x.status != "down" { Button("DOWN") { store.act("updating system") { try await store.client.updateSystem(x.id, status: "down", note: nil) } }.tint(Theme.red) }
                                }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
                            }
                        }
                    }
                }.listRowBackground(Theme.bg)
                let open = (store.snapshot?.incidents ?? []).filter { $0.status == "open" }
                if !open.isEmpty {
                    Section(header: SectionLabel(text: "ACCOUNTABILITY · OPEN ROLL CALLS · \(open.count)")) {
                        ForEach(open) { i in Button { store.selection = .incident(i.id) } label: { HStack { Text(i.title).font(.system(size: 12, weight: .semibold)); Spacer(); Text("\(i.accounted)/\(i.total)").font(.system(size: 11, design: .monospaced)).foregroundStyle(i.pct == 100 ? Theme.green : Theme.red) } }.buttonStyle(.plain) }
                    }.listRowBackground(Theme.bg)
                }
            } else { Text("No signal board yet.").font(.system(size: 11)).foregroundStyle(Theme.dim).listRowBackground(Theme.bg) }
            Color.clear.frame(height: 70).listRowBackground(Theme.bg)
        }
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg).drivesDock(store)
    }
}


// MARK: - §4 the task organization on the phone: brigade → battalions → companies

struct TaskOrgSection: View {
    @Environment(COPStore.self) private var store
    @State private var open: Set<String> = []
    var body: some View {
        let teams = store.snapshot?.teams ?? []
        let roots = teams.filter { t in t.parentId == nil && teams.contains { c in c.parentId == t.id } }
        if !roots.isEmpty {
            Section(header: SectionLabel(text: "TASK ORGANIZATION · present/assigned · ↗ away")) {
                ForEach(roots) { r in rows(r, depth: 0, teams: teams) }
            }.listRowBackground(Theme.bg)
        }
    }
    func members(_ id: String, _ teams: [Team]) -> [Person] {
        let people = store.snapshot?.people ?? []
        return people.filter { $0.teamId == id } + teams.filter { $0.parentId == id }.flatMap { members($0.id, teams) }
    }
    @ViewBuilder func rows(_ t: Team, depth: Int, teams: [Team]) -> some View {
        let kids = teams.filter { $0.parentId == t.id }
        let m = members(t.id, teams); let away = m.filter { $0.status == "traveling" }.count; let bad = m.filter { $0.availability == "unreachable" || !$0.confirmedThreatIds.isEmpty }.count
        let isOpen = open.contains(t.id) || depth == 0
        Button {
            if kids.isEmpty { store.selection = .site(t.locationId) } else if open.contains(t.id) { open.remove(t.id) } else { open.insert(t.id) }
        } label: {
            HStack(spacing: 6) {
                Text(kids.isEmpty ? " " : (isOpen ? "▾" : "▸")).font(.system(size: 10)).foregroundStyle(Theme.dim).frame(width: 10)
                Text(t.short ?? t.name).font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundStyle(depth == 0 ? Theme.blue : .primary).frame(minWidth: 44, alignment: .leading)
                Text(depth == 0 ? t.name : (t.equipment ?? t.function)).font(.system(size: 11)).foregroundStyle(Theme.dim).lineLimit(1)
                Spacer()
                if bad > 0 { Text("▲\(bad)").font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Theme.red) }
                (Text("\(m.count - away)").font(.system(size: 12, weight: .semibold, design: .monospaced)) + Text("/\(m.count)").font(.system(size: 12, design: .monospaced)).foregroundColor(Theme.dim) + Text(away > 0 ? " ·\(away)↗" : "").font(.system(size: 11, design: .monospaced)).foregroundColor(Theme.blue))
            }.padding(.leading, CGFloat(depth) * 14)
        }.foregroundStyle(.primary).buttonStyle(.plain)
        if isOpen { ForEach(kids) { k in AnyView(rows(k, depth: depth + 1, teams: teams)) } }
    }
}


// MARK: - §5.10 taskings on the phone: what a section owes and what it is waiting on

struct TaskingsSection: View {
    @Environment(COPStore.self) private var store
    var section: String
    var plain = false  // true inside a ScrollView (S3); false inside a List
    @State private var raising = false
    @State private var title = ""; @State private var asset = ""; @State private var to = "S3"; @State private var kind = "other"; @State private var priority = "routine"
    @State private var declining: Tasking? = nil; @State private var reason = ""
    var body: some View {
        Group {
            if plain { VStack(alignment: .leading, spacing: 8) { header; rows }.padding(.horizontal, 14).padding(.top, 10) }
            else { Section(header: header) { rows }.listRowBackground(Theme.bg) }
        }
        .alert("Decline — why?", isPresented: Binding(get: { declining != nil }, set: { if !$0 { declining = nil } })) {
            TextField("Reason", text: $reason)
            Button("Decline", role: .destructive) { if let t = declining { let r = reason; store.act("declining") { try await store.client.answerTasking(t.id, status: "declined", result: r) } }; declining = nil; reason = "" }
            Button("Cancel", role: .cancel) { declining = nil }
        }
    }
    var inbox: [Tasking] { (store.snapshot?.taskings?.items ?? []).filter { $0.toSection == section && $0.open } }
    var outbox: [Tasking] { (store.snapshot?.taskings?.items ?? []).filter { $0.fromSection == section && $0.open } }
    var header: some View {
        HStack { SectionLabel(text: "TASKINGS · \(inbox.count) TO DO · \(outbox.count) WAITING"); Spacer(); if store.can(section, "edit") { Button(raising ? "CANCEL" : "RAISE") { raising.toggle() }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue) } }
    }
    @ViewBuilder var rows: some View {
        let board = store.snapshot?.taskings
        let canEdit = store.can(section, "edit")
        let others = (store.snapshot?.sections ?? []).filter { $0.enabled && $0.code != section }.map { $0.code }
        let _ = board
            if raising {
                VStack(alignment: .leading, spacing: 6) {
                    HStack { Picker("To", selection: $to) { ForEach(others, id: \.self) { Text($0) } }.pickerStyle(.segmented) }
                    HStack { Picker("Kind", selection: $kind) { ForEach(["collection", "comms", "supply", "movement", "coverage", "other"], id: \.self) { Text($0) } }.pickerStyle(.menu)
                        Picker("Priority", selection: $priority) { ForEach(["routine", "priority", "urgent"], id: \.self) { Text($0) } }.pickerStyle(.menu) }
                    TextField("What", text: $title).textFieldStyle(.roundedBorder).font(.system(size: 12))
                    TextField("Asset or capability wanted", text: $asset).textFieldStyle(.roundedBorder).font(.system(size: 12))
                    Button("RAISE ON \(to)") { let t = title, a = asset, k = kind, p = priority, dest = to; store.act("raising a tasking") { try await store.client.raiseTasking(from: section, to: dest, kind: k, title: t, asset: a, priority: p) }; raising = false; title = ""; asset = "" }
                        .font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.green).disabled(title.trimmingCharacters(in: .whitespaces).isEmpty || store.busy != nil)
                }.padding(.vertical, 4)
            }
            if inbox.isEmpty && outbox.isEmpty { Text("Nothing open.").font(.system(size: 11)).foregroundStyle(Theme.dim) }
            ForEach(inbox) { t in row(t, mine: true, canEdit: canEdit) }
            ForEach(outbox) { t in row(t, mine: false, canEdit: false) }
    }
    @ViewBuilder func row(_ t: Tasking, mine: Bool, canEdit: Bool) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 6) {
                Chip(text: t.priority == "urgent" ? "URG" : t.priority == "priority" ? "PRI" : "RTN", color: healthColor(t.health), filled: t.health != "green")
                Text(mine ? "\(t.fromSection) →" : "→ \(t.toSection)").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                Text(t.title).font(.system(size: 12, weight: .semibold)).lineLimit(2)
                Spacer()
                Chip(text: t.status.uppercased() + (t.overdue ? " · LATE" : ""), color: t.status == "requested" ? Theme.amber : t.status == "complete" ? Theme.green : Theme.blue)
            }
            Text([t.asset, t.subjectName, t.windowFrom.map { ISO.short($0) } ?? ""].filter { !$0.isEmpty }.joined(separator: " · ")).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).lineLimit(2)
            if mine && canEdit {
                HStack(spacing: 6) {
                    if t.status == "requested" { Button("ACCEPT") { store.act("accepting") { try await store.client.answerTasking(t.id, status: "accepted", result: nil) } }.tint(Theme.blue) }
                    if t.status != "scheduled" { Button("SCHEDULE") { store.act("scheduling") { try await store.client.answerTasking(t.id, status: "scheduled", result: nil) } }.tint(Theme.blue) }
                    Button("COMPLETE") { store.act("completing") { try await store.client.answerTasking(t.id, status: "complete", result: nil) } }.tint(Theme.green)
                    Button("DECLINE") { declining = t }.tint(Theme.red)
                }.font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
            }
        }
    }
}
