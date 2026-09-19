import Foundation
import SwiftUI
import CoreLocation

// Mirrors apps/coptoc/COP_API_CONTRACT.md. Decoded with .convertFromSnakeCase.

struct Watch: Decodable {
    var id: String, name: String, battleCaptain: String?, status: String, startedAt: String, endsAt: String
    var elapsedH: Double, remainingH: Double, overdue: Bool, inOverlap: Bool, overlapMinutes: Int, nextWatch: String, pattern: String
    var nstr: Bool, outgoingNotes: String?, handedOverAt: String?, acknowledgedBy: String?, acknowledgedAt: String?
}
struct Estimate: Decodable, Identifiable { var section: String, assessment: String, recommendation: String, updatedBy: String?, updatedAt: String?; var id: String { section } }

struct SectionCfg: Decodable, Identifiable, Hashable { var code: String, title: String, hint: String, enabled: Bool; var label: String?, showCode: Bool?; var id: String { code } }
struct SupplyLine: Decodable, Identifiable, Hashable { var id: String, locationId: String?, locationName: String, category: String, item: String, onHand: Double, required: Double, unit: String, pct: Int, status: String, note: String, updatedBy: String }
struct Shipment: Decodable, Identifiable, Hashable { var id: String, description: String, category: String, quantity: String, fromName: String, toName: String, eta: String, hoursToEta: Double, status: String, priority: String, carrier: String, ref: String?, health: String, note: String }
struct S4Counts: Decodable, Hashable { var red: Int, amber: Int, inbound: Int, late: Int }
struct S4Board: Decodable, Hashable { var status: String, supplies: [SupplyLine], shipments: [Shipment], exceptions: [String], counts: S4Counts }
struct SystemLine: Decodable, Identifiable, Hashable { var id: String, name: String, category: String, locationId: String?, locationName: String, pace: String?, status: String, health: String, hours: Double, note: String, updatedBy: String }
struct PaceSite: Decodable, Hashable { var locationName: String, nets: [String: String], inUse: String? }
struct S6Counts: Decodable, Hashable { var down: Int, degraded: Int, total: Int }
struct S6Board: Decodable, Hashable { var status: String, systems: [SystemLine], pace: [String: PaceSite], exceptions: [String], counts: S6Counts }

struct Me: Decodable, Hashable {
    var userId: String?
    var name: String
    var role: String
    var perms: [String: String]
    var battleCaptain: Bool
    var admin: Bool
    var sectionsVisible: [String]
}
struct UserInfo: Decodable, Identifiable, Hashable {
    var id: String
    var name: String
    var title: String?
    var preset: String
    var battleCaptain: Bool
}

struct Tasking: Decodable, Identifiable, Hashable {
    var id: String, kind: String, title: String, fromSection: String, toSection: String, subjectName: String, asset: String
    var windowFrom: String?, windowTo: String?, priority: String, status: String, notes: String, result: String, requestedBy: String, ageH: Double
    var ownedBy: String?, open: Bool, overdue: Bool, health: String
}
struct TaskingCounts: Decodable, Hashable { var inbox: Int, outbox: Int, overdue: Int }
struct TaskingBoard: Decodable, Hashable { var items: [Tasking], open: Int, overdue: Int, perSection: [String: TaskingCounts] }

/// §3.1 — where the wall opens: the declared AO, else the box holding our sites, else nothing known yet.
struct MapFrame: Decodable {
    var centerLat: Double?, centerLon: Double?, radiusKm: Double?
    var source: String
    var coordinate: CLLocationCoordinate2D? {
        guard let centerLat, let centerLon else { return nil }
        return .init(latitude: centerLat, longitude: centerLon)
    }
}

struct Snapshot: Decodable {
    var view: MapFrame?
    var taskings: TaskingBoard?
    var me: Me?
    var profile: String?, sections: [SectionCfg]?, s4: S4Board?, s6: S6Board?
    var generatedAt: String
    var restrictedIncluded: Bool
    var restrictedDenied: Bool?
    var role: String?
    var watch: Watch?
    var estimates: [Estimate]?
    var summary: Summary
    var locations: [Site]
    var teams: [Team]
    var people: [Person]
    var trips: [Trip]
    var events: [CopEvent]
    var threats: [Threat]
    var pirs: [PIR]
    var assessments: [Assessment]
    var incidents: [Incident]
    var log: [LogEntry]
    var warnings: [Warning]?
    var operations: [OperationSummary]?
    var nais: [NAI]?, movements: [Movement]?   // §3.4 the derived overlays
    var graphics: [Graphic]?                    // §3.4 the control measures a section drew
    var s2Actors: [S2Actor]?, s2Sightings: [S2Sighting]?, s2Reports: [S2Report]?, movementRisks: [MovementRisk]?   // §5.10b the live S2 picture
    var decisionPoints: [SnapDecisionPoint]?   // §5.10b Phase 3, on the strip and in the S2 panel: what we decide, and when
    var ccir: CcirBoard?                        // §3.6 the commander's list: what has to wake him
    var exercise: ExerciseBoard?                // §3.7 whether this wall is running a scenario
}

/// §3.7 — the phone reads one thing about an exercise and reads it loudly: that there is one. Exercise control is
/// the wall's seat; what a phone must never do is let a drill read as real.
struct ExerciseRun: Decodable, Hashable {
    var id: String, name: String, scenario: String, status: String, speed: Double
    var startedAt: String?, endedAt: String?, elapsedMin: Double?
    var fired: Int, failed: Int, pending: Int, total: Int
}

struct ExerciseBoard: Decodable, Hashable {
    var running: Bool
    var exercise: ExerciseRun?
}

/// §3.6 — one line of the commander's critical information requirements. Written on the wall, read here: the phone
/// shows what is tripped and what each section owns, and never edits the commander's list.
struct CcirLine: Decodable, Identifiable, Hashable {
    var id: String, kind: String, text: String, ownerSection: String, priority: Int, status: String
    var metric: String?, unit: String, condition: String, state: String
    var value: Double?, trips: Int, trippedMin: Int?
    var tripped: Bool { state == "tripped" }
}

struct CcirBoard: Decodable, Hashable {
    struct Counts: Decodable, Hashable { var tripped: Int, unmeasured: Int, active: Int, total: Int }
    var lines: [CcirLine]
    var counts: Counts
}

/// §5.10b Phase 3 — a decision the commander owes, with the time it has to be made by. The matrix lives on the wall;
/// what the phone needs is the decision, what would trigger it, what happens, and whether the clock has run out.
struct SnapDecisionPoint: Decodable, Identifiable, Hashable {
    var id: String, title: String, subjectType: String, subjectId: String, operationId: String?
    var decision: String, trigger: String, action: String, ownerSection: String
    var latestTime: String?, overdue: Bool, status: String, note: String
    var pirId: String?, naiIds: [String], coaIds: [String]
}

/// §5.10b the other side as a thing with a name: an enemy unit or a threat actor, with its last known position.
struct S2Actor: Decodable, Identifiable, Hashable {
    var id: String, kind: String, name: String, aliases: [String], echelon: String, strength: String, equipment: [String], ttps: [String], assessedIntent: String, status: String
    var caseId: String?, owner: String, lat: Double?, lon: Double?, place: String?, lastSeenAt: String?, sightingIds: [String]
    var coordinate: CLLocationCoordinate2D? { lat.flatMap { la in lon.map { .init(latitude: la, longitude: $0) } } }
    var glyph: String { kind == "unit" ? "◆" : kind == "individual" ? "●" : kind == "organization" ? "▣" : "◈" }
}
/// One observation of an actor; the chain is the track.
struct S2Sighting: Decodable, Identifiable, Hashable {
    var id: String, actorId: String, at: String, lat: Double, lon: Double, place: String?, naiId: String?, sourceType: String, sourceId: String?, reliability: String, credibility: Int, grade: String, what: String, confidence: String
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
}
/// A SPOTREP from our own people, on the map until Sigtoc disposes of it.
struct S2Report: Decodable, Identifiable, Hashable {
    var id: String, kind: String, reportedBy: String, reporterRole: String, at: String, lat: Double?, lon: Double?, place: String?, text: String, caseId: String?, grade: String, source: String, status: String
    var disposition: String?, dispositionTargetType: String?, dispositionTargetId: String?, disposedBy: String?, disposedAt: String?, dispositionNote: String?
    var coordinate: CLLocationCoordinate2D? { lat.flatMap { la in lon.map { .init(latitude: la, longitude: $0) } } }
}
/// A movement leg that crosses a live S2 threat graphic — derived on the server, never stored.
struct MovementRisk: Decodable, Identifiable, Hashable {
    var id: String, movementId: String, movementName: String, legLabel: String, graphicId: String, graphicName: String, graphicType: String, confidence: String, basis: String, severity: String, reason: String
}

/// §3.4 a control measure a section drew by hand: a point, a line, or a polygon, typed from the catalog.
struct Graphic: Decodable, Identifiable, Hashable {
    var id: String, type: String, kind: String, section: String, name: String, label: String, geometry: Geometry, center: [Double]
    var windowFrom: String?, windowTo: String?, inWindow: Bool, status: String, note: String, subjectType: String?, subjectId: String?, createdBy: String
    var color: String, dash: Bool, glyph: String
    enum Geometry: Decodable, Hashable {
        case point([Double]), path([[Double]])
        init(from decoder: Decoder) throws {
            let c = try decoder.singleValueContainer()
            if let p = try? c.decode([[Double]].self) { self = .path(p) } else { self = .point(try c.decode([Double].self)) }
        }
        var coordinates: [CLLocationCoordinate2D] { switch self { case .point(let p): return [.init(latitude: p[1], longitude: p[0])]; case .path(let ps): return ps.map { .init(latitude: $0[1], longitude: $0[0]) } } }
    }
    var centerCoordinate: CLLocationCoordinate2D { .init(latitude: center[1], longitude: center[0]) }
    var swiftColor: Color { Color(hex: color) }
}

extension Color {
    /// "#rrggbb" → Color; the catalog's colors come over the wire as hex.
    init(hex: String) {
        var v: UInt64 = 0; Scanner(string: hex.replacingOccurrences(of: "#", with: "")).scanHexInt64(&v)
        self.init(red: Double((v >> 16) & 0xff) / 255, green: Double((v >> 8) & 0xff) / 255, blue: Double(v & 0xff) / 255)
    }
}

/// §3.4 an active requirement as a named area of interest: where S2 is looking, why, and how well.
struct NAI: Decodable, Identifiable, Hashable {
    var id: String, nai: Int, name: String, subjectName: String, subjectType: String, subjectId: String?, kind: String, lat: Double, lon: Double, radiusKm: Double, priority: Int
    var windowFrom: String?, windowTo: String?, question: String, coveragePct: Int, gaps: Int, pirIds: [String], health: String
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
    var labelCoordinate: CLLocationCoordinate2D { .init(latitude: lat + radiusKm / 111.0, longitude: lon) }
}
struct MovementLeg: Decodable, Hashable { var kind: String, label: String, fromLat: Double?, fromLon: Double?, toLat: Double, toLon: Double, startAt: String?, endAt: String?, status: String }
/// §3.4 everything that moves: a serial, a delegation, one named person, or a shipment (Decision Z).
struct Movement: Decodable, Identifiable, Hashable {
    var id: String, kind: String, owner: String, name: String, unit: String?, pax: Int, personIds: [String], isVip: Bool, purpose: String, originName: String, destName: String, destLat: Double, destLon: Double
    var departAt: String?, returnAt: String, hoursToEta: Double?, status: String, mode: String, headLat: Double?, headLon: Double?, currentLeg: String?, legs: [MovementLeg], health: String
    var riskFlags: [MovementRisk]?
    var head: CLLocationCoordinate2D? { headLat.flatMap { la in headLon.map { .init(latitude: la, longitude: $0) } } }
}
struct AreaCompact: Decodable, Hashable { var id: String, place: String, worst: String, worstIndicator: String?, strip: [String], assessedBy: String, assessedAt: String, ageDays: Double, stale: Bool }

struct Summary: Decodable {
    var totalPeople: Int, present: Int, traveling: Int, vipsTraveling: Int, securityOnShift: Int
    var activeThreats: Int, realThreats: Int, confirmedLinks: Int, checkedInFresh: Int, openPirs: Int, upcomingEvents: Int
    var openIncidents: Int, unaccounted: Int
    var s4Status: String?, s6Status: String?
    var posture: String
    var flash: Int?, warningsPending: Int?, offDuty: Int?, unreachable: Int?
    var defcon: Int?, defconLevels: [DefconLevel]?
    var s2Actors: Int?, s2ReportsPending: Int?, movementRisks: Int?
}
struct DefconLevel: Decodable, Identifiable, Hashable { var defcon: Int, posture: String, meaning: String, sites: Int; var id: Int { defcon } }

struct Site: Decodable, Identifiable, Hashable {
    var s4Status: String?, s6Status: String?, s4Red: Int?, s4Lines: Int?, s6Down: Int?, s6Systems: Int?, s6InUse: String?
    var id: String, name: String, type: String, lat: Double, lon: Double, city: String, country: String
    var posture: String, effectivePosture: String, sensitivity: String
    var isToc: Bool? = nil   // §3.1 the CP the TOC is running from; home station stays the site typed "hq"
    var assigned: Int, present: Int, securityOnShift: Int, vipsPresent: Int
    var threatIdsInArea: [String], confirmedThreatIds: [String]
    var area: AreaCompact?   // §5.6a what S2 judges about this place
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
}

struct Team: Decodable, Identifiable, Hashable { var id: String, name: String, locationId: String, function: String, isSecurity: Bool; var parentId: String?, echelon: String?, short: String?, equipment: String? }

struct Person: Decodable, Identifiable, Hashable {
    var shortName: String?, rank: String?, grade: String?, lastName: String?, firstName: String?
    var id: String, name: String, role: String, teamId: String, teamName: String
    var homeLocationId: String, locationId: String?, isVip: Bool, onShift: Bool, shiftRole: String?
    var status: String, lat: Double, lon: Double, tripId: String?
    var positionSource: String, checkinAgeH: Double?, checkinStale: Bool, lastCheckinAt: String?, lastCheckinNote: String?
    var threatIdsInArea: [String], confirmedThreatIds: [String]
    var phone: String?, email: String?, source: String, incidentStatus: String?, availability: String?
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
    var traveling: Bool { status == "traveling" }
}

struct Leg: Decodable, Identifiable, Hashable {
    var id: String, kind: String, label: String, ref: String?, fromName: String?, toName: String, toLat: Double, toLon: Double
    var startAt: String, endAt: String, status: String, note: String, source: String
    var icon: String { kind == "flight" ? "✈" : kind == "lodging" ? "🏨" : "🚗" }
}

struct Trip: Decodable, Identifiable, Hashable {
    var legs: [Leg]?, currentLeg: Leg?
    var id: String, personId: String, personName: String, isVip: Bool
    var originLocationId: String, originName: String, originLat: Double, originLon: Double
    var destLocationId: String?, destName: String, destLat: Double, destLon: Double
    var departAt: String, returnAt: String, purpose: String, status: String, eventId: String?, createdBy: String, source: String
    var operation: OperationSummary?
}

struct CopEvent: Decodable, Identifiable, Hashable {
    var id: String, name: String, eventType: String, venueLocationId: String?, venueName: String, venueLat: Double, venueLon: Double
    var startAt: String, endAt: String, status: String, daysUntil: Int, description: String, securityPlan: String?
    var attendeeIds: [String], attendeeCount: Int, vipCount: Int, securityCount: Int, tripsGenerated: Int, threatIdsInArea: [String], source: String
    var operation: OperationSummary?, coverage: Coverage?
    var coordinate: CLLocationCoordinate2D { .init(latitude: venueLat, longitude: venueLon) }
}

struct LinkTarget: Decodable, Hashable { var targetType: String, targetId: String, targetName: String }
struct ConfirmedLink: Decodable, Hashable, Identifiable {
    var linkId: Int, targetType: String, targetId: String, targetName: String, confirmedBy: String, confirmedAt: String, note: String?
    var id: Int { linkId }
}

struct Threat: Decodable, Identifiable, Hashable {
    var id: String, externalId: String?, title: String, summary: String, lat: Double, lon: Double, radiusKm: Double
    var severity: String, eventType: String?, source: String, url: String?, confidence: String, observedAt: String, synthetic: Bool
    var suggestedTargets: [LinkTarget], confirmedLinks: [ConfirmedLink]
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
}

struct PIR: Decodable, Identifiable, Hashable {
    var id: String, question: String, status: String, owner: String, priority: Int
    var subjectType: String?, subjectId: String?, createdAt: String, expiresAt: String?
}

struct Judgment: Decodable, Hashable { var claim: String, likelihood: String, band: String, confidence: String }
struct Evidence: Decodable, Hashable { var threatId: String, title: String, source: String, confidence: String, severity: String?, distanceKm: Double?, confirmed: Bool?, synthetic: Bool? }
struct Assessment: Decodable, Identifiable, Hashable {
    var id: String, title: String, subjectType: String, subjectId: String, likelihood: String, band: String, confidence: String, bluf: String
    var keyJudgments: [Judgment], evidence: [Evidence], gaps: [String], author: String, status: String, createdAt: String
    var approvedBy: String?, approvedAt: String?
}

struct LogEntry: Decodable, Identifiable, Hashable {
    var id: String, at: String, type: String, actor: String, actorType: String, subject: String
    var old: String?, new: String?, summary: String?
}

struct Delivery: Decodable, Hashable { var channel: String, status: String, at: String, error: String? }

struct RosterEntry: Decodable, Identifiable, Hashable {
    var personId: String, name: String, role: String, isVip: Bool, phone: String?, email: String?
    var status: String, basis: String, checkinRequestedAt: String?
    var deliveries: [Delivery]?
    var method: String?, attempts: Int, lastAttemptAt: String?, updatedBy: String?, updatedAt: String?, note: String?
    var id: String { personId }
}

/// S6 — a roll call. `counts` keys: unaccounted, contacted, safe, injured, assist, unreachable.
struct Incident: Decodable, Identifiable, Hashable {
    var id: String, title: String, kind: String, locationId: String?, threatId: String?, lat: Double, lon: Double, radiusKm: Double
    var status: String, openedBy: String, openedAt: String, closedAt: String?, notes: String?
    var total: Int, accounted: Int, pct: Int, counts: [String: Int], checkinsRequested: Int
    var channels: [String]?, deliverySummary: [String: [String: Int]]?
    var roster: [RosterEntry]
    var simulated: Bool { (deliverySummary ?? [:]).values.contains { ($0["simulated"] ?? 0) > 0 } }
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
}

enum Selection: Identifiable, Hashable {
    case site(String), person(String), threat(String), event(String), incident(String), actor(String), report(String)
    var id: String {
        switch self {
        case .actor(let s): "actor:\(s)"
        case .report(let s): "report:\(s)"
        case .site(let s): "site:\(s)"
        case .person(let s): "person:\(s)"
        case .threat(let s): "threat:\(s)"
        case .event(let s): "event:\(s)"
        case .incident(let s): "incident:\(s)"
        }
    }
}

// MARK: - Time helpers

enum ISO {
    static let frac: ISO8601DateFormatter = { let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return f }()
    static let plain: ISO8601DateFormatter = { let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime]; return f }()
    static func date(_ s: String?) -> Date? { guard let s else { return nil }; return frac.date(from: s) ?? plain.date(from: s) }
    static func rel(_ s: String?, now: Date = Date()) -> String {
        guard let d = date(s) else { return "—" }
        let secs = d.timeIntervalSince(now); let a = abs(secs); let past = secs < 0
        let n: String = a < 3600 ? "\(Int(a / 60))m" : a < 86400 ? "\(Int(a / 3600))h" : "\(Int(a / 86400))d"
        return past ? "\(n) ago" : "in \(n)"
    }
    static func short(_ s: String?) -> String {
        guard let d = date(s) else { return "—" }
        let f = DateFormatter(); f.dateFormat = "dd MMM HH:mm'Z'"; f.timeZone = TimeZone(identifier: "UTC"); return f.string(from: d)
    }
}


// MARK: - Sigtoc on the phone (§5.2, §5.6, §5.10, §5.11)

struct OperationSummary: Decodable, Hashable { var id: String, title: String, status: String, tasksTotal: Int, tasksDone: Int, blocked: Int?, resourcesOpen: Int?, pct: Int?, fromProductId: String? }
struct Coverage: Decodable, Hashable { var required: Int, assigned: Int, gap: Int, rule: String }
struct Warning: Decodable, Identifiable, Hashable {
    var id: String, title: String, text: String, subjectType: String, subjectId: String, subjectName: String, threatId: String?
    var severity: String, status: String, suggestedBy: String, createdAt: String, releasedBy: String?, releasedAt: String?, ageMin: Int?
    var shortTitle: String { title.replacingOccurrences(of: "FLASH — ", with: "") }
}
struct CoverageStat: Decodable, Hashable { var covered: Int, total: Int, pct: Int, gaps: [String] }
struct Requirement: Decodable, Identifiable, Hashable {
    var id: String, kind: String, subjectType: String, subjectName: String, question: String, priority: Int, status: String, owner: String
    var windowFrom: String?, windowTo: String?, coverage: CoverageStat
}
struct IntsumHead: Decodable, Identifiable, Hashable { var id: String, status: String, headline: String, nstr: Bool, releasedBy: String? }
struct CaseHead: Decodable, Identifiable, Hashable { var id: String, title: String, kind: String, status: String, openedBy: String, entities: Int?, relationships: Int?, events: Int?, pendingReview: Int? }
struct Distribution: Decodable, Hashable { var sent: Int, acknowledged: Int, unacknowledged: [String] }

// §5.10b Phase 3–4 read on the phone: what the other side may do, who else reports to us, and the staff products.
/// A threat course of action, carrying an ICD 203 likelihood word — never a number.
struct ThreatCoa: Decodable, Identifiable, Hashable {
    var id: String, title: String, subjectType: String, subjectId: String, subjectName: String
    var actorId: String?, actorName: String?, narrative: String, likelihood: String, confidence: String
    var mostLikely: Bool, mostDangerous: Bool, indicators: [String], naiIds: [String], graphicIds: [String], status: String
}
/// A source outside our own people, graded A–F by the analyst; the record is what became of its reports.
struct LiaisonSource: Decodable, Identifiable, Hashable {
    struct Record: Decodable, Hashable { var reports: Int, filed: Int, corroborated: Int, linked: Int, promoted: Int, dismissed: Int, disposed: Int, borneOut: Int, lastReportAt: String? }
    var id: String, name: String, kind: String, reliability: String, notes: String
    var gradedBy: String?, gradedAt: String?, record: Record
}
/// The head of a staff product: the IPB, the estimate, or Annex B, approved by the analyst or released by the BC.
struct StaffProductHead: Decodable, Identifiable, Hashable {
    var id: String, kind: String, title: String, subjectName: String, operationId: String?, status: String, draftedBy: String, draftedAt: String, decidedBy: String?
}
