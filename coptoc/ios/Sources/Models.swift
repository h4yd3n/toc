import Foundation
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

struct Snapshot: Decodable {
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
}

struct Summary: Decodable {
    var totalPeople: Int, present: Int, traveling: Int, vipsTraveling: Int, securityOnShift: Int
    var activeThreats: Int, realThreats: Int, confirmedLinks: Int, checkedInFresh: Int, openPirs: Int, upcomingEvents: Int
    var openIncidents: Int, unaccounted: Int
    var s4Status: String?, s6Status: String?
    var posture: String
    var flash: Int?, warningsPending: Int?, offDuty: Int?, unreachable: Int?
    var defcon: Int?, defconLevels: [DefconLevel]?
}
struct DefconLevel: Decodable, Identifiable, Hashable { var defcon: Int, posture: String, meaning: String, sites: Int; var id: Int { defcon } }

struct Site: Decodable, Identifiable, Hashable {
    var id: String, name: String, type: String, lat: Double, lon: Double, city: String, country: String
    var posture: String, effectivePosture: String, sensitivity: String
    var assigned: Int, present: Int, securityOnShift: Int, vipsPresent: Int
    var threatIdsInArea: [String], confirmedThreatIds: [String]
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
}

struct Team: Decodable, Identifiable, Hashable { var id: String, name: String, locationId: String, function: String, isSecurity: Bool; var parentId: String?, echelon: String?, short: String?, equipment: String? }

struct Person: Decodable, Identifiable, Hashable {
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
    case site(String), person(String), threat(String), event(String), incident(String)
    var id: String {
        switch self {
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
