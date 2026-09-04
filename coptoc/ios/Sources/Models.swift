import Foundation
import CoreLocation

// Mirrors apps/coptoc/COP_API_CONTRACT.md. Decoded with .convertFromSnakeCase.

struct Watch: Decodable {
    var id: String, name: String, battleCaptain: String?, status: String, startedAt: String, endsAt: String
    var elapsedH: Double, remainingH: Double, overdue: Bool, inOverlap: Bool, overlapMinutes: Int, nextWatch: String, pattern: String
    var nstr: Bool, outgoingNotes: String?, handedOverAt: String?, acknowledgedBy: String?, acknowledgedAt: String?
}
struct Estimate: Decodable, Identifiable { var section: String, assessment: String, recommendation: String, updatedBy: String?, updatedAt: String?; var id: String { section } }

struct Snapshot: Decodable {
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
}

struct Summary: Decodable {
    var totalPeople: Int, present: Int, traveling: Int, vipsTraveling: Int, securityOnShift: Int
    var activeThreats: Int, realThreats: Int, confirmedLinks: Int, checkedInFresh: Int, openPirs: Int, upcomingEvents: Int
    var openIncidents: Int, unaccounted: Int
    var posture: String
}

struct Site: Decodable, Identifiable, Hashable {
    var id: String, name: String, type: String, lat: Double, lon: Double, city: String, country: String
    var posture: String, effectivePosture: String, sensitivity: String
    var assigned: Int, present: Int, securityOnShift: Int, vipsPresent: Int
    var threatIdsInArea: [String], confirmedThreatIds: [String]
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
}

struct Team: Decodable, Identifiable { var id: String, name: String, locationId: String, function: String, isSecurity: Bool }

struct Person: Decodable, Identifiable, Hashable {
    var id: String, name: String, role: String, teamId: String, teamName: String
    var homeLocationId: String, locationId: String?, isVip: Bool, onShift: Bool, shiftRole: String?
    var status: String, lat: Double, lon: Double, tripId: String?
    var positionSource: String, checkinAgeH: Double?, checkinStale: Bool, lastCheckinAt: String?, lastCheckinNote: String?
    var threatIdsInArea: [String], confirmedThreatIds: [String]
    var phone: String?, email: String?, source: String, incidentStatus: String?
    var coordinate: CLLocationCoordinate2D { .init(latitude: lat, longitude: lon) }
    var traveling: Bool { status == "traveling" }
}

struct Trip: Decodable, Identifiable, Hashable {
    var id: String, personId: String, personName: String, isVip: Bool
    var originLocationId: String, originName: String, originLat: Double, originLon: Double
    var destLocationId: String?, destName: String, destLat: Double, destLon: Double
    var departAt: String, returnAt: String, purpose: String, status: String, eventId: String?, createdBy: String, source: String
}

struct CopEvent: Decodable, Identifiable, Hashable {
    var id: String, name: String, eventType: String, venueLocationId: String?, venueName: String, venueLat: Double, venueLon: Double
    var startAt: String, endAt: String, status: String, daysUntil: Int, description: String, securityPlan: String?
    var attendeeIds: [String], attendeeCount: Int, vipCount: Int, securityCount: Int, tripsGenerated: Int, threatIdsInArea: [String], source: String
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
