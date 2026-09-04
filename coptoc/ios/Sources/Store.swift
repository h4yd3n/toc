import Foundation
import Observation

@Observable
@MainActor
final class COPStore {
    var snapshot: Snapshot?
    var error: String?
    var busy: String?
    var selection: Selection?
    /// Decision 1: the restricted layer (residences) is off by default.
    var showRestricted = false { didSet { Task { await load() } } }
    var now = Date()

    let client = COPClient()
    private var polling = false

    func start() async {
        guard !polling else { return }
        polling = true
        await load()
        Task { while true { try? await Task.sleep(for: .seconds(30)); await load() } }
        Task { while true { try? await Task.sleep(for: .seconds(1)); now = Date() } }
    }

    func load() async {
        do { snapshot = try await client.snapshot(restricted: showRestricted); error = nil }
        catch let e as DecodingError { self.error = "contract drift: \(e)" }  // name the missing key, not just "data is missing"
        catch { self.error = error.localizedDescription }
    }

    func act(_ label: String, _ op: @escaping () async throws -> Void) {
        Task {
            busy = label
            defer { busy = nil }
            do { try await op(); await load() } catch { self.error = error.localizedDescription }
        }
    }

    // Lookups
    func site(_ id: String?) -> Site? { snapshot?.locations.first { $0.id == id } }
    func person(_ id: String?) -> Person? { snapshot?.people.first { $0.id == id } }
    func threat(_ id: String?) -> Threat? { snapshot?.threats.first { $0.id == id } }
    func trip(_ id: String?) -> Trip? { snapshot?.trips.first { $0.id == id } }
    func event(_ id: String?) -> CopEvent? { snapshot?.events.first { $0.id == id } }
    func incident(_ id: String?) -> Incident? { snapshot?.incidents.first { $0.id == id } }
    var openIncidents: [Incident] { snapshot?.incidents.filter { $0.status == "open" } ?? [] }
    var travelers: [Person] { snapshot?.people.filter(\.traveling) ?? [] }
}
