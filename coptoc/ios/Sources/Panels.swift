import SwiftUI

struct PersonnelScreen: View {
    @Environment(COPStore.self) private var store
    var body: some View {
        List {
            Section { PanelHead(code: "S1", title: "PERSONNEL", hint: "Blue Force"); EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S1" }) }.listRowBackground(Theme.panel)
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
            Section(header: SectionLabel(text: "LOCATIONS")) {
                ForEach(store.snapshot?.locations ?? []) { l in
                    Button { store.selection = .site(l.id) } label: {
                        HStack(spacing: 8) {
                            Circle().fill(Theme.posture(l.effectivePosture)).frame(width: 7, height: 7).shadow(color: Theme.posture(l.effectivePosture), radius: 4)
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
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg)
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
                HStack { PanelHead(code: "S2", title: "INTELLIGENCE", hint: "Sigtoc")
                    Button("⟳ COLLECT") { store.act("collecting") { try await store.client.refreshIntel() } }
                        .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue).disabled(store.busy != nil) }
                EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S2" })
            }.listRowBackground(Theme.panel)
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
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg)
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
    var cursorDay: Date {  // the day whose header is at or above the top of the agenda; today before anything has scrolled
        tops.filter { $0.value <= 24 }.max { $0.value < $1.value }?.key ?? agenda.first?.day ?? cal.startOfDay(for: store.now)
    }
    var body: some View {
        let days = agenda
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    Color.clear.frame(height: 0).background(GeometryReader { g in Color.clear.preference(key: ScrollTopKey.self, value: g.frame(in: .named("agenda")).minY) })
                    PanelHead(code: "S3", title: "OPERATIONS", hint: "Agenda").padding(.horizontal, 14).padding(.top, 8)
                    EstimateLine(e: store.snapshot?.estimates?.first { $0.section == "S3" }).padding(.horizontal, 14)
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
            .coordinateSpace(name: "agenda")
            .onPreferenceChange(DayTopKey.self) { new in withAnimation(.easeInOut(duration: 0.25)) { tops.merge(new) { $1 } } }
            .onPreferenceChange(ScrollTopKey.self) { y in scrollY = y; if y < -8, expanded { withAnimation(.easeInOut(duration: 0.25)) { expanded = false } } }
            .safeAreaInset(edge: .top, spacing: 0) {
            CalendarStrip(cursor: cursorDay, today: cal.startOfDay(for: store.now), marked: Set(days.map(\.day)), eventDays: eventDays, expanded: $expanded, month: $month) { picked in
                // jump to the picked day, or the first day after it that has something
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
                }.padding(.horizontal, 14).padding(.vertical, 8).frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
            }.foregroundStyle(.primary).buttonStyle(.plain)
        }
    }
}

/// The calendar strip: one week that follows the scroll, unfolding into the month on a tap of its name.
struct CalendarStrip: View {
    var cursor: Date; var today: Date; var marked: Set<Date>; var eventDays: Set<Date>
    @Binding var expanded: Bool; @Binding var month: Date?
    var onPick: (Date) -> Void
    let cal = Calendar(identifier: .gregorian)
    var body: some View {
        let shownMonth = expanded ? (month ?? cal.date(from: cal.dateComponents([.year, .month], from: cursor))!) : cal.date(from: cal.dateComponents([.year, .month], from: cursor))!
        VStack(spacing: 4) {
            HStack {
                Button { withAnimation(.spring(duration: 0.3)) { expanded.toggle(); month = nil } } label: {
                    HStack(spacing: 6) { Text(shownMonth.formatted(.dateTime.month(.wide).year()).uppercased()).font(.system(size: 10, weight: .bold, design: .monospaced)).tracking(1.8); Text(expanded ? "▴" : "▾").font(.system(size: 9)).foregroundStyle(Theme.dim) }
                }.buttonStyle(.plain)
                Spacer()
                if expanded {
                    Button("‹") { month = cal.date(byAdding: .month, value: -1, to: shownMonth) }.buttonStyle(.plain).foregroundStyle(Theme.dim)
                    Button("›") { month = cal.date(byAdding: .month, value: 1, to: shownMonth) }.buttonStyle(.plain).foregroundStyle(Theme.dim).padding(.leading, 14)
                } else {
                    Text(cursor == today ? "TODAY" : "\(cal.dateComponents([.day], from: today, to: cursor).day ?? 0) DAYS OUT").font(.system(size: 9, design: .monospaced)).foregroundStyle(Theme.dim)
                }
            }.padding(.horizontal, 4)
            HStack(spacing: 0) { ForEach(["M", "T", "W", "T", "F", "S", "S"], id: \.self) { d in Text(d).font(.system(size: 8, design: .monospaced)).foregroundStyle(Theme.dim).frame(maxWidth: .infinity) } }
            if expanded {
                let first = shownMonth, offset = (cal.component(.weekday, from: first) + 5) % 7, count = cal.range(of: .day, in: .month, for: first)!.count
                ForEach(0..<Int(ceil(Double(offset + count) / 7)), id: \.self) { r in
                    HStack(spacing: 0) { ForEach(0..<7, id: \.self) { c in let i = r * 7 + c - offset
                        if i >= 0 && i < count, let d = cal.date(byAdding: .day, value: i, to: first) { dayCell(d) } else { Color.clear.frame(maxWidth: .infinity).frame(height: 35) } } }
                }
            } else {
                let weekStart = cal.date(byAdding: .day, value: -((cal.component(.weekday, from: cursor) + 5) % 7), to: cursor)!
                HStack(spacing: 0) { ForEach(0..<7, id: \.self) { i in dayCell(cal.date(byAdding: .day, value: i, to: weekStart)!) } }
            }
        }
        .padding(.horizontal, 10).padding(.top, 6).padding(.bottom, 6)
        .fixedSize(horizontal: false, vertical: true)
        .background(Theme.panel).overlay(alignment: .bottom) { Rectangle().fill(Theme.line).frame(height: 1) }
    }
    func dayCell(_ d: Date) -> some View {
        let isToday = d == today, isCursor = d == cursor, hasEvent = eventDays.contains(d), hasAny = marked.contains(d)
        return VStack(spacing: 2) {
            Text("\(cal.component(.day, from: d))").font(.system(size: 12, weight: isToday || isCursor ? .bold : .regular, design: .monospaced))
                .foregroundStyle(isCursor ? Color.black : d < today ? Theme.dim : .primary)
                .frame(width: 26, height: 26).background(isCursor ? Theme.blue : .clear, in: Circle()).overlay(Circle().stroke(isToday ? Theme.red : .clear, lineWidth: 1.5))
                .animation(.easeInOut(duration: 0.25), value: isCursor)
            Circle().fill(hasEvent ? Theme.purple : hasAny ? Theme.blue : .clear).frame(width: 5, height: 5)
        }.frame(maxWidth: .infinity).frame(height: 35).contentShape(Rectangle()).onTapGesture { onPick(d) }
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
