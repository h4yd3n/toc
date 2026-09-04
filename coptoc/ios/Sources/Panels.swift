import SwiftUI

struct PersonnelScreen: View {
    @Environment(COPStore.self) private var store
    var body: some View {
        List {
            Section { PanelHead(code: "S1", title: "PERSONNEL", hint: "Blue Force") }.listRowBackground(Theme.panel)
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
                    Button("⟳ COLLECT") { store.act("collecting GDACS") { try await store.client.refreshIntel() } }
                        .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue).disabled(store.busy != nil) }
            }.listRowBackground(Theme.panel)
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
    var body: some View {
        List {
            Section { PanelHead(code: "S3", title: "OPERATIONS", hint: "Events · Travel") }.listRowBackground(Theme.panel)
            Section(header: SectionLabel(text: "EVENTS")) {
                ForEach(store.snapshot?.events ?? []) { e in
                    Button { store.selection = .event(e.id) } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack { Chip(text: e.status == "active" ? "LIVE" : "T-\(e.daysUntil)d", color: Theme.purple); Text("★ \(e.name)").font(.system(size: 13, weight: .semibold)); Spacer()
                                if !e.threatIdsInArea.isEmpty { Text("△\(e.threatIdsInArea.count)").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.amber) } }
                            Text(e.venueName).font(.system(size: 12, design: .monospaced))
                            Text("\(ISO.short(e.startAt)) → \(ISO.short(e.endAt))").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                            Text("\(e.attendeeCount) attending · \(e.vipCount) VIP · \(e.securityCount) sec · \(e.tripsGenerated) trips").font(.system(size: 11)).foregroundStyle(.secondary)
                        }
                    }.foregroundStyle(.primary)
                }
            }.listRowBackground(Theme.panel)
            Section(header: SectionLabel(text: "TRAVEL")) {
                ForEach(store.snapshot?.trips ?? []) { t in
                    Button { store.selection = .person(t.personId) } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack { Chip(text: t.status.uppercased(), color: t.status == "active" ? Theme.blue : Theme.dim); if t.isVip { Text("★").foregroundStyle(Theme.gold) }; Text(t.personName).font(.system(size: 13, weight: .semibold)); if t.eventId != nil { Chip(text: "EVT", color: Theme.purple) } }
                            Text("\(t.originName.split(separator: " ").first.map(String.init) ?? "") → \(t.destName.split(separator: ",").first.map(String.init) ?? "")").font(.system(size: 12, design: .monospaced))
                            Text("dep \(ISO.rel(t.departAt, now: store.now)) · ret \(ISO.rel(t.returnAt, now: store.now))").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                            Text(t.purpose).font(.system(size: 11)).foregroundStyle(.secondary).lineLimit(1)
                        }
                    }.foregroundStyle(.primary)
                }
            }.listRowBackground(Theme.panel)
            Section(header: SectionLabel(text: "BATTLE LOG · hash-chained")) {
                ForEach(store.snapshot?.log ?? []) { e in
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(ISO.rel(e.at, now: store.now)).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).frame(width: 52, alignment: .leading)
                        Text(e.type.replacingOccurrences(of: "cop.", with: "")).font(.system(size: 9, design: .monospaced)).foregroundStyle(e.actorType == "human" ? Theme.blue : Theme.amber)
                        Text(e.summary ?? "").font(.system(size: 11)).lineLimit(1)
                        Spacer(); Text(e.actor).font(.system(size: 10)).foregroundStyle(Theme.dim).lineLimit(1)
                    }
                }
            }.listRowBackground(Theme.panel)
        }
        .listStyle(.plain).scrollContentBackground(.hidden).background(Theme.bg)
    }
}
