import SwiftUI
import Foundation
import Observation

@Observable
@MainActor
final class COPStore {
    var snapshot: Snapshot?
    var requirements: [Requirement] = []
    var intsums: [IntsumHead] = []
    var warnings: [Warning] = []
    var cases: [CaseHead] = []
    var error: String?
    var busy: String?
    var selection: Selection?
    /// Decision 1: the restricted layer (residences) is off by default.
    var showRestricted = false { didSet { Task { await load() } } }
    var now = Date()
    /// DISPLAY toggles, the same two as the wall. Lean labels drop hints and empty estimate lines; the posture header
    /// leads with posture and keeps five counters. Both default on; persisted per device.
    var leanLabels: Bool = UserDefaults.standard.object(forKey: "toc.leanLabels") as? Bool ?? true { didSet { UserDefaults.standard.set(leanLabels, forKey: "toc.leanLabels") } }
    var postureHeader: Bool = UserDefaults.standard.object(forKey: "toc.postureHeader") as? Bool ?? true { didSet { UserDefaults.standard.set(postureHeader, forKey: "toc.postureHeader") } }

    var client = COPClient()
    // The collapsing dock (ported from SoriStory's NavBarChrome): scrolling down folds the tab bar — labels go,
    // icons shrink, the capsule narrows; any upward scroll or a tab tap springs it back. Never folds near the top.
    var barCollapsed = false
    private var lastBarY: CGFloat = 0
    func trackBarScroll(_ y: CGFloat) {
        let delta = y - lastBarY; lastBarY = y
        if y > -16 { setBar(false) } else if delta < -4 { setBar(true) } else if delta > 3 { setBar(false) }
    }
    func expandBar() { lastBarY = 0; setBar(false) }
    private func setBar(_ v: Bool) { guard barCollapsed != v else { return }; withAnimation(.spring(response: 0.34, dampingFraction: 0.85)) { barCollapsed = v } }
    private var polling = false

    func start() async {
        guard !polling else { return }
        polling = true
        await load()
        Task { while true { try? await Task.sleep(for: .seconds(30)); await load() } }
        Task { while true { try? await Task.sleep(for: .seconds(1)); now = Date() } }
    }

    func load() async {
        do {
            snapshot = try await client.snapshot(restricted: showRestricted); error = nil
            async let r = client.requirements(); async let i = client.intsums(); async let w = client.warnings(); async let c = client.cases()
            requirements = (try? await r) ?? []; intsums = (try? await i) ?? []; warnings = (try? await w) ?? []; cases = (try? await c) ?? []
        }
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
    // §11.2 what a section is called here: "S1" on a military desk, nothing (just the title) on a corporate one
    func sectionCode(_ code: String) -> String { (snapshot?.sections?.first { $0.code == code }?.showCode ?? true) ? code : "" }
    func sectionTitle(_ code: String, _ fallback: String) -> String { snapshot?.sections?.first { $0.code == code }?.title ?? fallback }
    func sectionLabel(_ code: String) -> String { snapshot?.sections?.first { $0.code == code }?.label ?? code }
    func event(_ id: String?) -> CopEvent? { snapshot?.events.first { $0.id == id } }
    func incident(_ id: String?) -> Incident? { snapshot?.incidents.first { $0.id == id } }
    var openIncidents: [Incident] { snapshot?.incidents.filter { $0.status == "open" } ?? [] }
    var travelers: [Person] { snapshot?.people.filter(\.traveling) ?? [] }
    var liveWarnings: [Warning] { warnings.filter { $0.status == "released" } }
    var pendingWarnings: [Warning] { warnings.filter { $0.status == "suggested" || $0.status == "draft" } }
}
