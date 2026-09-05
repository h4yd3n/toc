import SwiftUI
import Foundation
import MapKit
import Observation

@Observable
@MainActor
final class COPStore {
    var snapshot: Snapshot?
    /// §3.1 — the wall has one board. Every section draws on the same ground, so moving between S1 and S2 changes
    /// the overlay and never the view. Held here rather than in MapScreen, whose state a tab switch throws away, and
    /// held as a region rather than a MapCameraPosition: a position the operator panned by hand does not survive
    /// being handed to a freshly built Map, but a region does.
    var board: MKCoordinateRegion? = nil
    /// Bumps once, when the opening frame is applied — the only signal that should ever pull the map somewhere.
    var framedAt = 0
    private var framed = false
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
    var users: [UserInfo] = []
    var tab = "COP"  // the phone's tab; a header counter can jump it
    func signIn(_ id: String) { client.userId = id; UserDefaults.standard.set(id, forKey: "toc.user"); Task { await load() } }
    func loadUsers() async { users = (try? await client.users()) ?? [] }
    var me: Me? { snapshot?.me }
    func can(_ section: String, _ level: String = "view") -> Bool {  // the server's answer for view; edit needs the grid, the floor, or nobody signed in
        guard let me else { return true }
        if me.userId == nil || me.battleCaptain { return true }
        return level == "view" ? me.sectionsVisible.contains(section) : me.perms[section] == "edit"
    }
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
        if users.isEmpty { await loadUsers() }
        do {
            snapshot = try await client.snapshot(restricted: showRestricted); error = nil
            frameOpening()
            async let r = client.requirements(); async let i = client.intsums(); async let w = client.warnings(); async let c = client.cases()
            requirements = (try? await r) ?? []; intsums = (try? await i) ?? []; warnings = (try? await w) ?? []; cases = (try? await c) ?? []
        }
        catch let e as DecodingError { self.error = "contract drift: \(e)" }  // name the missing key, not just "data is missing"
        catch { self.error = error.localizedDescription }
    }

    /// Frame the AO the Battle Captain declared, or the box that holds our sites. Once — a later refresh must not
    /// haul the map back while someone is working it.
    private func frameOpening() {
        guard !framed, let v = snapshot?.view, let c = v.coordinate else { return }
        framed = true
        let meters = max((v.radiusKm ?? 250) * 2_000, 20_000)   // radius to span, floored so one site is not street level
        board = MKCoordinateRegion(center: c, latitudinalMeters: meters, longitudinalMeters: meters)
        framedAt += 1
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
