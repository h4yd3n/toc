import SwiftUI

struct DetailView: View {
    @Environment(COPStore.self) private var store
    var selection: Selection

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                switch selection {
                case .site(let id): if let s = store.site(id) { siteView(s) }
                case .person(let id): if let p = store.person(id) { personView(p) }
                case .threat(let id): if let t = store.threat(id) { threatView(t) }
                case .event(let id): if let e = store.event(id) { eventView(e) }
                case .incident(let id): if let i = store.incident(id) { incidentView(i) }
                }
            }
            .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.panel)
    }

    func kicker(_ s: String) -> some View { Text(s).font(.system(size: 10, design: .monospaced)).tracking(1.4).foregroundStyle(Theme.dim) }
    func title(_ s: String) -> some View { Text(s).font(.system(size: 20, weight: .bold)) }
    func kv(_ k: String, _ v: String) -> some View { HStack(alignment: .top, spacing: 10) { Text(k).foregroundStyle(Theme.dim).frame(width: 64, alignment: .leading); Text(v) }.font(.system(size: 12)) }

    @ViewBuilder func threatRows(ids: [String], confirmed: [String], targetType: String, targetId: String) -> some View {
        let all = Array(NSOrderedSet(array: confirmed + ids)) as? [String] ?? ids
        if !all.isEmpty {
            SectionLabel(text: "THREATS IN AREA · proximity suggests · analyst confirms")
            ForEach(all, id: \.self) { tid in
                if let t = store.threat(tid) {
                    HStack(spacing: 8) {
                        Chip(text: String(t.severity.prefix(3)).uppercased(), color: Theme.severity(t.severity), filled: true)
                        Button(t.title) { store.selection = .threat(t.id) }.font(.system(size: 12)).foregroundStyle(.primary).lineLimit(2)
                        Spacer()
                        if confirmed.contains(tid) { Chip(text: "CONFIRMED", color: Theme.red) }
                        else { Button("CONFIRM") { store.act("confirming link") { try await store.client.confirmLink(threatId: tid, targetType: targetType, targetId: targetId) } }
                                .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue).disabled(store.busy != nil) }
                    }
                }
            }
        }
    }

    @ViewBuilder func rollCallButton(locationId: String? = nil, threatId: String? = nil) -> some View {
        if store.client.role != "battle_captain" { Text("☎ roll call · Battle Captain only").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim) } else {
        Button("☎ OPEN ROLL CALL") { store.act("opening roll call") { try await store.client.openRollCall(locationId: locationId, threatId: threatId) } }
            .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.borderedProminent).tint(Theme.red).disabled(store.busy != nil)
        }
    }

    @ViewBuilder func incidentView(_ inc: Incident) -> some View {
        kicker("S6 ACCOUNTABILITY · \(inc.kind.uppercased()) · opened \(ISO.rel(inc.openedAt, now: store.now)) by \(inc.openedBy)")
        title(inc.title)
        Text("\(inc.accounted)/\(inc.total) accounted").font(.system(size: 16, weight: .bold, design: .monospaced)).foregroundStyle(inc.pct == 100 ? Theme.green : Theme.red).lineLimit(1)
        ScrollView(.horizontal, showsIndicators: false) { HStack(spacing: 6) {
            ForEach(["unaccounted", "unreachable", "assist", "injured", "safe"], id: \.self) { k in if let n = inc.counts[k], n > 0 { Chip(text: "\(k.uppercased()) \(n)", color: rosterColor(k)) } } } }
        ProgressView(value: Double(inc.accounted), total: Double(max(inc.total, 1))).tint(inc.pct == 100 ? Theme.green : Theme.red)
        if let n = inc.notes { kv("Notes", n) }
        if inc.status == "open" {
            let pending = (inc.counts["unaccounted"] ?? 0) + (inc.counts["unreachable"] ?? 0)
            HStack(spacing: 8) {
                Button("📲 REQUEST CHECK-INS · SMS + CHAT (\(pending))") { store.act("requesting check-ins") { try await store.client.requestCheckins(incidentId: inc.id) } }
                    .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.borderedProminent).tint(Theme.green).disabled(store.busy != nil || pending == 0)
                Button("CLOSE") { store.act("closing roll call") { try await store.client.closeIncident(id: inc.id) } }
                    .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).disabled(store.busy != nil)
            }
            if inc.checkinsRequested > 0 { HStack(spacing: 6) { Text("\(inc.checkinsRequested) requested · work by exception").font(.system(size: 10)).foregroundStyle(Theme.dim); if inc.simulated { Chip(text: "SIMULATED", color: Theme.amber) } } }
        } else { Chip(text: "CLOSED \(ISO.rel(inc.closedAt, now: store.now))") }
        SectionLabel(text: "ROSTER · call every name")
        ForEach(inc.roster) { r in
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Circle().fill(rosterColor(r.status)).frame(width: 8, height: 8)
                    if r.isVip { Text("★").foregroundStyle(Theme.gold) }
                    Text(r.name).font(.system(size: 13, weight: .semibold)); Text(r.role).font(.system(size: 11)).foregroundStyle(Theme.dim).lineLimit(1); Spacer()
                    if r.basis == "assigned" { Chip(text: "AWAY", color: Theme.amber) } else if r.basis == "in_area" { Chip(text: "NEARBY") }
                    Chip(text: r.status.uppercased(), color: rosterColor(r.status))
                }
                HStack(spacing: 8) {
                    if let ph = r.phone { Link(ph, destination: URL(string: "tel:\(ph.filter { !$0.isWhitespace })")!).font(.system(size: 12, design: .monospaced)) }
                    if r.attempts > 0 { Text("\(r.attempts) attempt\(r.attempts == 1 ? "" : "s")\(r.method == "app" ? " · via app" : "")").font(.system(size: 10)).foregroundStyle(Theme.dim) }
                    if let at = r.checkinRequestedAt, r.status == "unaccounted" || r.status == "unreachable" { Text("📲 \(ISO.rel(at, now: store.now))").font(.system(size: 10)).foregroundStyle(Theme.green) }
                    ForEach(r.deliveries ?? [], id: \.self) { dl in Chip(text: "\(dl.channel == "sms" ? "📱" : "💬") \(dl.status == "sent" ? "✓" : dl.status == "simulated" ? "SIM" : "✗")", color: dl.status == "sent" ? Theme.green : dl.status == "failed" ? Theme.red : Theme.dim) }
                    if let n = r.note { Text(n).font(.system(size: 11)).foregroundStyle(.secondary).lineLimit(1) }
                }
                if inc.status == "open" {
                    HStack(spacing: 6) {
                        ForEach([("safe", "SAFE"), ("unreachable", "NO ANSWER"), ("assist", "ASSIST"), ("injured", "INJURED")], id: \.0) { (st, label) in
                            Button(label) { store.act("logging contact") { try await store.client.updateRoster(incidentId: inc.id, personId: r.personId, status: st) } }
                                .font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(rosterColor(st)).disabled(store.busy != nil)
                        }
                    }
                }
            }.padding(.vertical, 4)
        }
    }

    func rosterColor(_ s: String) -> Color {
        switch s { case "safe", "contacted": Theme.green; case "assist", "injured": Theme.red; case "unreachable": Theme.amber; default: Theme.dim }
    }

    func draftButton(_ type: String, _ id: String) -> some View {
        Button("✎ DRAFT S2 ASSESSMENT") { store.act("drafting S2 assessment") { try await store.client.draftAssessment(subjectType: type, subjectId: id) } }
            .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.amber).disabled(store.busy != nil)
    }

    @ViewBuilder func siteView(_ s: Site) -> some View {
        kicker("\(s.type.uppercased()) · \(s.city), \(s.country)\(s.sensitivity == "restricted" ? " · ⚿ RESTRICTED" : "")")
        title(s.name)
        HStack(spacing: 14) { stat(s.present, "present"); stat(s.assigned, "assigned"); stat(s.securityOnShift, "sec on shift"); stat(s.vipsPresent, "VIP") }
        HStack(spacing: 6) {
            Text("posture").font(.system(size: 12)).foregroundStyle(Theme.dim)
            ForEach(["normal", "guarded", "elevated", "high", "critical"], id: \.self) { p in
                Button(p.uppercased()) { store.act("setting posture") { try await store.client.setPosture(siteId: s.id, posture: p) } }
                    .font(.system(size: 9, weight: .bold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.posture(p)).opacity(s.posture == p ? 1 : 0.5).disabled(store.busy != nil)
            }
            if s.effectivePosture != s.posture { Chip(text: "EFFECTIVE \(s.effectivePosture.uppercased())", color: Theme.posture(s.effectivePosture)) }
        }
        threatRows(ids: s.threatIdsInArea, confirmed: s.confirmedThreatIds, targetType: "location", targetId: s.id)
        HStack { draftButton("location", s.id); rollCallButton(locationId: s.id) }
        let teams = store.snapshot?.teams.filter { $0.locationId == s.id } ?? []
        let visiting = store.snapshot?.people.filter { $0.locationId == s.id && $0.homeLocationId != s.id } ?? []
        if !visiting.isEmpty { SectionLabel(text: "VISITING"); ForEach(visiting) { personRow($0) } }
        ForEach(teams) { t in
            let members = store.snapshot?.people.filter { $0.teamId == t.id } ?? []
            let away = members.filter(\.traveling).count
            SectionLabel(text: "\(t.isSecurity ? "⛨ " : "")\(t.name.uppercased()) · \(members.count - away)/\(members.count)\(t.isSecurity ? " · \(members.filter { $0.onShift && !$0.traveling }.count) ON SHIFT" : "")")
            ForEach(members) { personRow($0) }
        }
    }

    func personRow(_ p: Person) -> some View {
        Button { store.selection = .person(p.id) } label: {
            HStack(spacing: 7) {
                Circle().fill(p.traveling ? Theme.blue : p.onShift ? Theme.green : Theme.line).frame(width: 6, height: 6)
                if p.isVip { Text("★").foregroundStyle(Theme.gold) }
                Text(p.name); PresenceChip(person: p); if let st = p.incidentStatus { Chip(text: st.uppercased(), color: rosterColor(st)) }; Spacer()
                Text(p.traveling ? "away" : (p.onShift ? (p.shiftRole ?? "") : p.role)).foregroundStyle(Theme.dim).lineLimit(1)
            }.font(.system(size: 12)).opacity(p.traveling ? 0.6 : 1)
        }.foregroundStyle(.primary)
    }

    func stat(_ v: Int, _ l: String) -> some View { HStack(spacing: 3) { Text("\(v)").bold(); Text(l).foregroundStyle(Theme.dim) }.font(.system(size: 12)) }

    @ViewBuilder func personView(_ p: Person) -> some View {
        let trip = store.trip(p.tripId)
        kicker("\(p.isVip ? "VIP · " : "")\(p.teamName)")
        title("\(p.isVip ? "★ " : "")\(p.name)")
        Text(p.role).foregroundStyle(.secondary)
        HStack(spacing: 6) {
            Chip(text: p.traveling ? "TRAVELING" : "AT POST", color: p.traveling ? Theme.blue : Theme.green)
            if p.onShift { Chip(text: "ON SHIFT · \(p.shiftRole ?? "")", color: Theme.green) }
            if p.positionSource == "checkin" { Chip(text: "CHECKED IN \(Int((p.checkinAgeH ?? 0).rounded()))h AGO", color: Theme.green) }
            else if p.checkinStale { Chip(text: "CHECK-IN STALE", color: Theme.amber) }
            else { Chip(text: "POSITION DERIVED") }
        }
        if let st = p.incidentStatus { Chip(text: "ROLL CALL · \(st.uppercased())", color: rosterColor(st)) }
        if let note = p.lastCheckinNote { kv("Check-in", note) }
        if let ph = p.phone { kv("Phone", ph) }
        if let em = p.email { kv("Email", em) }
        kv("Source", p.source)
        kv("Home", store.site(p.homeLocationId)?.name ?? "⚿ restricted")
        if let trip {
            SectionLabel(text: "TRIP · \(trip.id)")
            kv("To", trip.destName); kv("Depart", "\(ISO.short(trip.departAt)) (\(ISO.rel(trip.departAt, now: store.now)))")
            kv("Return", "\(ISO.short(trip.returnAt)) (\(ISO.rel(trip.returnAt, now: store.now)))"); kv("Purpose", trip.purpose); kv("Source", trip.source)
            if let e = store.event(trip.eventId) { Button("★ \(e.name)") { store.selection = .event(e.id) }.font(.system(size: 12)) }
        }
        threatRows(ids: p.threatIdsInArea, confirmed: p.confirmedThreatIds, targetType: "person", targetId: p.id)
        if let trip { draftButton("trip", trip.id) }
        Button("📍 CHECK IN HERE (demo)") { store.act("checking in") { try await store.client.checkIn(personId: p.id, lat: p.lat, lon: p.lon, note: "Checked in from iOS") } }
            .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.green).disabled(store.busy != nil)
    }

    @ViewBuilder func eventView(_ e: CopEvent) -> some View {
        kicker("S3 EVENT · \(e.eventType.replacingOccurrences(of: "_", with: " ").uppercased()) · \(e.status == "active" ? "IN PROGRESS" : "T-\(e.daysUntil) DAYS")")
        title(e.name)
        Text(e.venueName).foregroundStyle(.secondary)
        HStack(spacing: 14) { stat(e.attendeeCount, "attending"); stat(e.vipCount, "VIP"); stat(e.securityCount, "security"); stat(e.tripsGenerated, "trips") }
        kv("Window", "\(ISO.short(e.startAt)) → \(ISO.short(e.endAt))"); kv("Brief", e.description)
        if let plan = e.securityPlan { kv("Sec plan", plan) }
        if !e.threatIdsInArea.isEmpty {
            SectionLabel(text: "THREATS IN AREA")
            ForEach(e.threatIdsInArea, id: \.self) { tid in if let t = store.threat(tid) { Button { store.selection = .threat(t.id) } label: { HStack { Chip(text: String(t.severity.prefix(3)).uppercased(), color: Theme.severity(t.severity), filled: true); Text(t.title).font(.system(size: 12)) } }.foregroundStyle(.primary) } }
        }
        draftButton("event", e.id)
        SectionLabel(text: "ATTENDEES")
        ForEach(e.attendeeIds.compactMap { store.person($0) }) { personRow($0) }
    }

    @ViewBuilder func threatView(_ t: Threat) -> some View {
        HStack(spacing: 6) { Chip(text: t.severity.uppercased(), color: Theme.severity(t.severity), filled: true); Chip(text: t.synthetic ? "SYNTHETIC" : "LIVE · \(t.source.uppercased())", color: t.synthetic ? Theme.dim : Theme.green); if let et = t.eventType { Text(et).font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim) } }
        title(t.title)
        HStack(spacing: 12) { kv("radius", "\(Int(t.radiusKm)) km"); Text("observed \(ISO.rel(t.observedAt, now: store.now))").font(.system(size: 12)); Text("\(t.confidence) source confidence").font(.system(size: 12)).foregroundStyle(Theme.confidence(t.confidence)) }
        kv("Source", t.source)
        rollCallButton(threatId: t.id)
        Text(t.summary).font(.system(size: 13)).foregroundStyle(.secondary)
        if !t.confirmedLinks.isEmpty {
            SectionLabel(text: "CONFIRMED LINKS")
            ForEach(t.confirmedLinks) { l in
                HStack { Text("▲").foregroundStyle(Theme.red); Button(l.targetName) { store.selection = l.targetType == "location" ? .site(l.targetId) : .person(l.targetId) }.foregroundStyle(.primary); Spacer()
                    Text("\(l.confirmedBy) · \(ISO.rel(l.confirmedAt, now: store.now))").font(.system(size: 10)).foregroundStyle(Theme.dim)
                    Button("×") { store.act("removing link") { try await store.client.removeLink(threatId: t.id, linkId: l.linkId) } }.buttonStyle(.bordered).disabled(store.busy != nil) }.font(.system(size: 12))
            }
        }
        let pending = t.suggestedTargets.filter { s in !t.confirmedLinks.contains { $0.targetType == s.targetType && $0.targetId == s.targetId } }
        if !pending.isEmpty {
            SectionLabel(text: "IN AREA · suggested by proximity — confirm to change posture")
            ForEach(pending, id: \.self) { s in
                HStack { Text("△").foregroundStyle(Theme.amber); Button(s.targetName) { store.selection = s.targetType == "location" ? .site(s.targetId) : .person(s.targetId) }.foregroundStyle(.primary); Spacer()
                    Button("CONFIRM") { store.act("confirming link") { try await store.client.confirmLink(threatId: t.id, targetType: s.targetType, targetId: s.targetId) } }
                        .font(.system(size: 10, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue).disabled(store.busy != nil) }.font(.system(size: 12))
            }
        }
    }
}
