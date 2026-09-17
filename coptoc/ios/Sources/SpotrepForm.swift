import SwiftUI
import MapKit

/// §5.10b the SPOTREP: what the field files, in SALUTE order, with the place taken from the board or typed. Cop Talk
/// files it; Sigtoc disposes of it (corroborate, link, promote, dismiss). Graded A2 until corroborated, like every
/// report from our own people.
struct SpotrepButton: View {
    @Environment(COPStore.self) private var store
    var compact: Bool
    @State private var open = false
    var body: some View {
        Button { open = true } label: {
            HStack(spacing: 5) { Text("+").font(.system(size: compact ? 10 : 14, weight: .heavy)); Text("SPOTREP").font(.system(size: compact ? 9 : 11, weight: .bold, design: .monospaced)).tracking(1) }
                .foregroundStyle(.white).padding(.horizontal, compact ? 8 : 12).padding(.vertical, compact ? 4 : 9)
                .background(Theme.amber.opacity(compact ? 0.35 : 0.9), in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.amber, lineWidth: 1))
                .shadow(color: .black.opacity(compact ? 0 : 0.4), radius: 6, y: 2)
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $open) { SpotrepForm { open = false } }
    }
}

struct SpotrepForm: View {
    @Environment(COPStore.self) private var store
    var onDone: () -> Void
    @State private var size = ""; @State private var activity = ""; @State private var unit = ""; @State private var equipment = ""; @State private var place = ""; @State private var notes = ""
    @State private var lat = ""; @State private var lon = ""
    @State private var kind = "spot"
    @State private var source = ""
    @State private var problem: String? = nil
    var body: some View {
        NavigationStack {
            Form {
                Section("What you saw") {
                    Picker("Kind", selection: $kind) { Text("SPOTREP").tag("spot"); Text("SITREP").tag("sitrep"); Text("NOTE").tag("note"); Text("LIAISON").tag("liaison") }.pickerStyle(.segmented)
                    if kind == "liaison" {
                        TextField("Liaison source (SFPD Southern Station)", text: $source)
                        Text("An unknown name becomes a source at F until the analyst grades it.").font(.system(size: 10)).foregroundStyle(Theme.dim)
                    }
                    TextField("Size — how many, of what", text: $size)
                    TextField("Activity — what they were doing", text: $activity)
                    TextField("Unit / description — who", text: $unit)
                    TextField("Equipment — vehicles, weapons, gear", text: $equipment)
                }
                Section("Where") {
                    TextField("Place name (e.g. bridge north of the FARP)", text: $place)
                    HStack { TextField("Latitude", text: $lat).keyboardType(.numbersAndPunctuation); TextField("Longitude", text: $lon).keyboardType(.numbersAndPunctuation) }
                    Button("Use the centre of the board") { if let c = store.board?.center { lat = String(format: "%.5f", c.latitude); lon = String(format: "%.5f", c.longitude) } }.font(.system(size: 12))
                }
                Section("Anything else") { TextField("Notes", text: $notes, axis: .vertical).lineLimit(2...5) }
                Section { Text("Filed by \(store.me?.name ?? store.client.actor) · \(kind == "liaison" ? "graded at the source's reliability" : "graded A2 until an analyst corroborates") · time is now").font(.system(size: 11)).foregroundStyle(Theme.dim) }
                if let problem { Text(problem).font(.system(size: 12)).foregroundStyle(Theme.red) }
            }
            .navigationTitle("SPOTREP")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { onDone() } }
                ToolbarItem(placement: .confirmationAction) { Button("File") { file() }.disabled(activity.trim().isEmpty && size.trim().isEmpty && notes.trim().isEmpty) }
            }
        }
        .onAppear { if lat.isEmpty, let c = store.board?.center { lat = String(format: "%.5f", c.latitude); lon = String(format: "%.5f", c.longitude) } }
    }
    private func file() {
        let lines = [("SIZE", size), ("ACTIVITY", activity), ("UNIT", unit), ("EQUIPMENT", equipment)].filter { !$0.1.trim().isEmpty }.map { "\($0.0): \($0.1.trim())" }
        let text = (lines + (notes.trim().isEmpty ? [] : [notes.trim()])).joined(separator: "\n")
        guard !text.isEmpty else { problem = "Say what you saw."; return }
        var body: [String: Any] = ["text": text, "kind": kind, "reported_by": store.me?.name ?? store.client.actor, "reporter_role": store.me?.role ?? store.client.role]
        if kind == "liaison", !source.trim().isEmpty { body["liaison_source"] = source.trim() }
        if let la = Double(lat), let lo = Double(lon), abs(la) <= 90, abs(lo) <= 180 { body["lat"] = la; body["lon"] = lo }
        if !place.trim().isEmpty { body["place"] = place.trim() }
        store.act("filing SPOTREP") { try await store.client.fileReport(body) }
        onDone()
    }
}

private extension String { func trim() -> String { trimmingCharacters(in: .whitespacesAndNewlines) } }
