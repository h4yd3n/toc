import SwiftUI

/// §5.6b the subject of concern on the phone. The wall opens files, rates them and works the inbox; the phone reads
/// the files and the inbox, shows on a principal who is directed at them, and files a contact from the field — the
/// in-person door of the mailroom (someone approached the principal at the venue; a letter was handed to the desk).
/// Nothing here rates a person: that is the S2 analyst's, at the wall. Everything is empty unless the signed-in role
/// is cleared for the files; the tally in the summary is what an uncleared reader sees.

private let RATING_COLOR: [String: Color] = ["green": Theme.green, "amber": Theme.amber, "red": Theme.red]
private func ratingColor(_ r: String) -> Color { RATING_COLOR[r] ?? Theme.line }
private let DIRECT_LABEL: [String: String] = ["directed": "DIRECTED", "conditional": "CONDITIONAL", "veiled": "VEILED", "none": "NO THREAT"]
private func directColor(_ d: String) -> Color { d == "directed" ? Theme.red : d == "conditional" ? Theme.orange : d == "veiled" ? Theme.amber : Theme.dim }
private func ago(_ d: Double?) -> String { guard let d else { return "never assessed" }; return d < 1 ? "today" : "\(Int(d.rounded()))d ago" }

/// The row of ratings, one block per indicator in the configured order.
struct RatingBlocks: View {
    var strip: [String]
    var body: some View {
        HStack(spacing: 2) { ForEach(Array(strip.enumerated()), id: \.offset) { _, r in RoundedRectangle(cornerRadius: 2).fill(ratingColor(r)).frame(width: 8, height: 8) } }
    }
}

/// What a principal or a site carries about a file: the name, the strip, the worst of it as a word.
struct SubjectStripRow: View {
    @Environment(COPStore.self) private var store
    var s: SubjectCompact
    var body: some View {
        Button { store.selection = .subject(s.id) } label: {
            HStack(spacing: 6) {
                Text(s.name).font(.system(size: 12, weight: .semibold)).lineLimit(1)
                RatingBlocks(strip: s.strip)
                if s.unassessed { Chip(text: "UNASSESSED", color: Theme.amber) } else { Chip(text: s.worst.uppercased(), color: ratingColor(s.worst), filled: s.worst == "red") }
                Spacer()
                if s.contactCount > 0 { Text("\(s.contactCount) contact\(s.contactCount == 1 ? "" : "s")").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim) }
                if s.stale { Chip(text: "STALE", color: Theme.amber) }
            }
        }.buttonStyle(.plain)
    }
}

/// The S2 tab section: every live file worst first, then what nobody has attributed yet.
struct SubjectsSection: View {
    @Environment(COPStore.self) private var store
    var cleared: Bool { ["battle_captain", "ep", "analyst"].contains(store.snapshot?.me?.role ?? store.client.role) }
    var body: some View {
        let live = store.liveSubjects
        let rest = (store.snapshot?.subjects ?? []).filter { !$0.live }
        let inbox = store.subjectInbox
        let tally = store.snapshot?.summary
        Section(header: HStack { SectionLabel(text: "WHO IS DIRECTED AT US · \(tally?.subjectsOpen ?? live.count) OPEN · \(tally?.subjectsRed ?? live.filter { $0.worst == "red" }.count) RED"); Spacer(); if cleared { ContactButton(subjectId: nil, compact: true) } }) {
            if !cleared {
                Text("Subject files name private individuals. Battle Captain, Executive Protection or the S2 analyst only.").font(.system(size: 11)).foregroundStyle(Theme.dim)
            } else {
                ForEach(live + rest) { s in
                    Button { store.selection = .subject(s.id) } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 6) {
                                Text(s.name).font(.system(size: 12, weight: .semibold)).lineLimit(1)
                                if s.unassessed { Chip(text: "UNASSESSED", color: Theme.amber) } else { Chip(text: s.worst.uppercased(), color: ratingColor(s.worst), filled: s.worst == "red") }
                                if s.status != "open" { Chip(text: s.status.uppercased(), color: s.status == "monitoring" ? Theme.blue : s.status == "referred" ? Theme.gold : Theme.dim) }
                                Spacer()
                            }
                            HStack(spacing: 6) {
                                RatingBlocks(strip: (s.assessment?.ratings ?? []).map(\.rating))
                                Text([s.principalName.isEmpty ? (s.worstIndicator ?? "nothing rated") : "directed at \(s.principalName)",
                                      s.contactCount > 0 ? "\(s.contactCount) contact\(s.contactCount == 1 ? "" : "s")" : nil,
                                      s.worstDirectness != "none" ? DIRECT_LABEL[s.worstDirectness]?.lowercased() : nil,
                                      s.assessedAt == nil ? "never assessed" : ago(s.ageDays)].compactMap { $0 }.joined(separator: " · "))
                                    .font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).lineLimit(1)
                            }
                        }.opacity(s.live ? 1 : 0.55)
                    }.buttonStyle(.plain)
                }
                if live.isEmpty && rest.isEmpty { Text("No file is open on anyone.").font(.system(size: 11)).foregroundStyle(Theme.dim) }
                if !inbox.isEmpty {
                    SectionLabel(text: "INBOX · \(inbox.count) ATTRIBUTED TO NOBODY")
                    ForEach(inbox) { c in
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 6) {
                                Chip(text: c.channel.uppercased().replacingOccurrences(of: "_", with: " "), color: Theme.dim)
                                Text(c.fromLabel.isEmpty ? "sender not given" : c.fromLabel).font(.system(size: 11, weight: .semibold)).lineLimit(1)
                                Spacer()
                                Chip(text: DIRECT_LABEL[c.directness] ?? c.directness.uppercased(), color: directColor(c.directness), filled: c.directness == "directed")
                            }
                            Text(c.text).font(.system(size: 11)).foregroundStyle(.secondary).lineLimit(3)
                            Text("\(ISO.rel(c.receivedAt, now: store.now))" + (c.principalName.isEmpty ? " · names nobody we hold" : " · names \(c.principalName)") + " · attributed at the wall")
                                .font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).lineLimit(1)
                        }
                    }
                }
            }
        }.listRowBackground(Theme.panel)
    }
}

/// The detail card for one file: who he is, the assessment as the analyst wrote it, what has arrived from him.
struct SubjectDetail: View {
    @Environment(COPStore.self) private var store
    var s: Subject
    func kicker(_ t: String) -> some View { Text(t).font(.system(size: 10, design: .monospaced)).tracking(1.4).foregroundStyle(Theme.dim) }
    func kv(_ k: String, _ v: String) -> some View { HStack(alignment: .top, spacing: 10) { Text(k).foregroundStyle(Theme.dim).frame(width: 64, alignment: .leading); Text(v) }.font(.system(size: 12)) }
    var body: some View {
        kicker("SUBJECT OF CONCERN · RESTRICTED · \(s.status.uppercased())" + (s.assessment.map { " · \($0.assessedBy)" } ?? ""))
        HStack(spacing: 8) {
            Text(s.name).font(.system(size: 20, weight: .bold))
            if s.unassessed { Chip(text: "NEVER ASSESSED", color: Theme.amber) } else { Chip(text: s.worst.uppercased(), color: ratingColor(s.worst), filled: s.worst == "red") }
            if s.stale { Chip(text: "STALE", color: Theme.amber) }
        }
        if !s.aliases.isEmpty { Text("also: " + s.aliases.joined(separator: " · ")).font(.system(size: 11)).foregroundStyle(Theme.dim) }
        if !s.summary.isEmpty { Text(s.summary).font(.system(size: 12)).foregroundStyle(.secondary) }
        HStack(spacing: 8) {
            if let pid = s.principalId { Button("⌖ \(s.principalName)") { store.selection = .person(pid) }.font(.system(size: 11, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue) }
            if let lid = s.locationId, store.site(lid) != nil { Button("⌖ SITE") { store.selection = .site(lid) }.font(.system(size: 11, weight: .semibold, design: .monospaced)).buttonStyle(.bordered).tint(Theme.blue) }
        }
        if s.status == "referred", let r = s.referredTo { kv("Referred", r) }
        if s.status == "closed", let r = s.closedReason { kv("Closed", r) }
        if let seen = s.lastSeenPlace { kv("Last seen", seen + (s.lastSeenAt.map { " · \(ISO.rel($0, now: store.now))" } ?? "")) }

        SectionLabel(text: "THE ASSESSMENT" + (s.unassessed ? " · NONE YET" : " · \(ago(s.ageDays)) · nothing summed"))
        if s.unassessed {
            Text("Nobody has rated this person. That is an exception in its own right; it is not a green file. Rating is done at the wall.").font(.system(size: 11)).foregroundStyle(Theme.dim)
        } else if let a = s.assessment {
            ForEach(a.ratings, id: \.indicator) { r in
                HStack(alignment: .top, spacing: 8) {
                    Rectangle().fill(ratingColor(r.rating)).frame(width: 3, height: 30)
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 6) { Text(r.label).font(.system(size: 12, weight: .semibold)); Chip(text: r.rating == "unknown" ? "—" : r.rating.uppercased(), color: ratingColor(r.rating)) }
                        Text(r.note.isEmpty ? "no justification recorded" : r.note).font(.system(size: 11)).foregroundStyle(r.note.isEmpty ? Theme.dim : .secondary).lineLimit(3)
                    }
                }
            }
            if !a.summary.isEmpty { Text(a.summary).font(.system(size: 12)).foregroundStyle(.secondary).padding(.top, 2) }
        }

        HStack { SectionLabel(text: "WHAT HAS ARRIVED · \(s.contactCount)"); Spacer(); if s.live { ContactButton(subjectId: s.id, compact: true) } }
        if s.contacts.isEmpty { Text("Nothing has been attributed to this file.").font(.system(size: 11)).foregroundStyle(Theme.dim) }
        ForEach(s.contacts) { c in
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Chip(text: c.channel.uppercased().replacingOccurrences(of: "_", with: " "), color: Theme.dim)
                    Text(c.fromLabel.isEmpty ? "sender not given" : c.fromLabel).font(.system(size: 11, weight: .semibold)).lineLimit(1)
                    Spacer()
                    Chip(text: DIRECT_LABEL[c.directness] ?? c.directness.uppercased(), color: directColor(c.directness), filled: c.directness == "directed")
                    Chip(text: "\(c.reliability)/\(c.credibility)", color: Theme.dim)
                }
                Text(c.text).font(.system(size: 11)).foregroundStyle(.secondary)
                Text("\(ISO.rel(c.receivedAt, now: store.now))" + (c.principalName.isEmpty ? "" : " · names \(c.principalName)") + (c.note.map { " · \($0)" } ?? ""))
                    .font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).lineLimit(2)
            }.padding(.vertical, 2)
        }
        Text("Opened by \(s.openedBy) · \(ISO.rel(s.openedAt, now: store.now))" + (s.caseId.map { " · case \($0)" } ?? "") + ". Rated, referred and closed at the wall.").font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim).padding(.top, 4)
    }
}

// ---------------------------------------------------------------- the field door of the mailroom

struct ContactButton: View {
    var subjectId: String?
    var compact: Bool
    @State private var open = false
    var body: some View {
        Button { open = true } label: {
            HStack(spacing: 5) { Text("+").font(.system(size: compact ? 10 : 14, weight: .heavy)); Text("CONTACT").font(.system(size: compact ? 9 : 11, weight: .bold, design: .monospaced)).tracking(1) }
                .foregroundStyle(.white).padding(.horizontal, compact ? 8 : 12).padding(.vertical, compact ? 4 : 9)
                .background(Theme.blue.opacity(compact ? 0.35 : 0.9), in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.blue, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $open) { ContactForm(subjectId: subjectId) { open = false } }
    }
}

/// Something arrived, or someone approached. It lands graded F/6 — an unknown sender cannot be judged — and, unless
/// filed from a subject's own card, in the inbox: the phone never guesses whose it is.
struct ContactForm: View {
    @Environment(COPStore.self) private var store
    var subjectId: String?
    var onDone: () -> Void
    @State private var channel = "in_person"
    @State private var from = ""; @State private var text = ""; @State private var directness = "none"; @State private var principal = ""
    @State private var problem: String? = nil
    private let channels = [("in_person", "IN PERSON"), ("phone", "PHONE"), ("letter", "LETTER"), ("email", "EMAIL"), ("dm", "DM"), ("form", "FORM"), ("other", "OTHER")]
    var subject: Subject? { store.subject(subjectId) }
    var body: some View {
        NavigationStack {
            Form {
                Section(subject.map { "Onto the file: \($0.name)" } ?? "Into the inbox — attributed at the wall") {
                    Picker("Channel", selection: $channel) { ForEach(channels, id: \.0) { Text($0.1).tag($0.0) } }
                    TextField(channel == "in_person" ? "Who — as they gave it, or a description" : "From — address, handle or return address as it arrived", text: $from)
                    TextField("What was said or written, in the words it arrived in", text: $text, axis: .vertical).lineLimit(3...8)
                }
                Section("How the threat is worded — the wording, not your view of the risk") {
                    Picker("Threat", selection: $directness) { Text("NO THREAT").tag("none"); Text("VEILED").tag("veiled"); Text("CONDITIONAL").tag("conditional"); Text("DIRECTED").tag("directed") }.pickerStyle(.segmented)
                }
                if subject == nil {
                    Section("Who it names, if one of ours") {
                        Picker("Principal", selection: $principal) { Text("— nobody named —").tag(""); ForEach((store.snapshot?.people ?? []).filter(\.isVip)) { Text($0.name).tag($0.id) } }
                    }
                }
                Section { Text("Filed by \(store.me?.name ?? store.client.actor) · graded F/6 on arrival — an unknown sender cannot be judged · time is now").font(.system(size: 11)).foregroundStyle(Theme.dim) }
                if let problem { Text(problem).font(.system(size: 12)).foregroundStyle(Theme.red) }
            }
            .navigationTitle("CONTACT")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { onDone() } }
                ToolbarItem(placement: .confirmationAction) { Button("File") { file() }.disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) }
            }
        }
    }
    private func file() {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { problem = "Say what arrived, in the words it arrived in."; return }
        var body: [String: Any] = ["text": t, "channel": channel, "from_label": from.trimmingCharacters(in: .whitespacesAndNewlines), "directness": directness,
                                   "received_by": store.me?.name ?? store.client.actor]
        if let subjectId { body["subject_id"] = subjectId }
        if !principal.isEmpty { body["principal_id"] = principal }
        store.act("filing the contact") { try await store.client.fileContact(body) }
        onDone()
    }
}
