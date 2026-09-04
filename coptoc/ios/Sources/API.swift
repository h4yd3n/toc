import Foundation

/// The COP backend client. Same contract as the web app: apps/coptoc/COP_API_CONTRACT.md.
struct COPClient {
    // Simulator reaches the Mac's FastAPI on localhost. Override with TOC_API in the scheme environment.
    // Scheme environment first (Xcode runs), then the value baked into Info.plist at build time (device installs), then the Mac's localhost (simulator).
    var baseURL: URL = URL(string: ProcessInfo.processInfo.environment["TOC_API"]
        ?? (Bundle.main.object(forInfoDictionaryKey: "TOC_API") as? String).flatMap { $0.isEmpty || $0.hasPrefix("$(") ? nil : $0 }
        ?? "http://localhost:8000")!
    var actor = "Battle Captain (iOS)"
    var role = "battle_captain"  // Decision C: only battle_captain / ep may see the restricted layer

    private var decoder: JSONDecoder { let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase; return d }

    func snapshot(restricted: Bool) async throws -> Snapshot {
        var c = URLComponents(url: baseURL.appending(path: "/v1/cop/snapshot"), resolvingAgainstBaseURL: false)!
        c.queryItems = [URLQueryItem(name: "restricted", value: restricted ? "true" : "false")]
        var req = URLRequest(url: c.url!)
        req.setValue(role, forHTTPHeaderField: "X-TOC-Role")
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp, data)
        return try decoder.decode(Snapshot.self, from: data)
    }

    func confirmLink(threatId: String, targetType: String, targetId: String) async throws {
        try await send("POST", "/v1/cop/threats/\(threatId)/links", ["target_type": targetType, "target_id": targetId])
    }
    func removeLink(threatId: String, linkId: Int) async throws { try await send("DELETE", "/v1/cop/threats/\(threatId)/links/\(linkId)", nil) }
    func setPosture(siteId: String, posture: String) async throws {
        try await send("PATCH", "/v1/cop/locations/\(siteId)/posture", ["posture": posture, "reason": "Set from iOS"])
    }
    func draftAssessment(subjectType: String, subjectId: String) async throws {
        try await send("POST", "/v1/cop/assessments/draft", ["subject_type": subjectType, "subject_id": subjectId])
    }
    func setAssessmentStatus(id: String, status: String) async throws { try await send("PATCH", "/v1/cop/assessments/\(id)", ["status": status]) }
    func refreshIntel() async throws { try await send("POST", "/v1/cop/intel/refresh", nil) }
    func checkIn(personId: String, lat: Double, lon: Double, note: String) async throws {
        try await send("POST", "/v1/cop/people/\(personId)/checkin", ["lat": lat, "lon": lon, "note": note])
    }

    func openRollCall(locationId: String?, threatId: String?) async throws {
        var body: [String: Any] = [:]
        if let locationId { body["location_id"] = locationId }
        if let threatId { body["threat_id"] = threatId }
        try await send("POST", "/v1/cop/incidents", body)
    }
    func updateRoster(incidentId: String, personId: String, status: String, note: String? = nil) async throws {
        var body: [String: Any] = ["status": status, "method": "call"]
        if let note { body["note"] = note }
        try await send("PATCH", "/v1/cop/incidents/\(incidentId)/roster/\(personId)", body)
    }
    func requestCheckins(incidentId: String) async throws { try await send("POST", "/v1/cop/incidents/\(incidentId)/request-checkins", [:]) }
    func closeIncident(id: String) async throws { try await send("PATCH", "/v1/cop/incidents/\(id)/close", [:]) }

    // Sigtoc reads
    func requirements() async throws -> [Requirement] { try await fetch("/v1/s2/requirements?status=active") }
    func intsums() async throws -> [IntsumHead] { try await fetch("/v1/s2/intsum") }
    func warnings() async throws -> [Warning] { try await fetch("/v1/s2/warnings") }
    func cases() async throws -> [CaseHead] { try await fetch("/v1/s2/cases") }
    func distribution(_ ptype: String, _ pid: String) async throws -> Distribution { try await fetch("/v1/s2/products/\(ptype)/\(pid)/distribution") }
    // Sigtoc writes
    func releaseWarning(id: String) async throws { try await send("POST", "/v1/s2/warnings/\(id)/release", [:]) }
    func cancelWarning(id: String) async throws { try await send("POST", "/v1/s2/warnings/\(id)/cancel", [:]) }
    func ackProduct(_ ptype: String, _ pid: String) async throws { try await send("POST", "/v1/s2/products/\(ptype)/\(pid)/ack", [:]) }
    func draftIntsum() async throws { try await send("POST", "/v1/s2/intsum/draft", [:]) }
    func releaseIntsum(id: String) async throws { try await send("POST", "/v1/s2/intsum/\(id)/release", [:]) }
    func runWarningRule() async throws { try await send("POST", "/v1/s2/warnings/suggest", [:]) }

    private func fetch<T: Decodable>(_ path: String) async throws -> T {
        var req = URLRequest(url: baseURL.appending(path: path.split(separator: "?").first.map(String.init) ?? path))
        if let q = path.split(separator: "?").dropFirst().first { var c = URLComponents(url: req.url!, resolvingAgainstBaseURL: false)!; c.query = String(q); req.url = c.url }
        req.setValue(role, forHTTPHeaderField: "X-TOC-Role"); req.setValue(actor, forHTTPHeaderField: "X-TOC-Actor")
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp, data)
        return try decoder.decode(T.self, from: data)
    }

    private func send(_ method: String, _ path: String, _ body: [String: Any]?) async throws {
        var req = URLRequest(url: baseURL.appending(path: path))
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(actor, forHTTPHeaderField: "X-TOC-Actor")
        req.setValue(role, forHTTPHeaderField: "X-TOC-Role")
        if let body { req.httpBody = try JSONSerialization.data(withJSONObject: body) }
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp, data)
    }

    private func check(_ resp: URLResponse, _ data: Data) throws {
        guard let http = resp as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "COP", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: "HTTP \(http.statusCode): \(String(data: data, encoding: .utf8) ?? "")"])
        }
    }
}
