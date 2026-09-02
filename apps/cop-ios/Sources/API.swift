import Foundation

/// The COP backend client. Same contract as the web app: apps/coptoc/COP_API_CONTRACT.md.
struct COPClient {
    // Simulator reaches the Mac's FastAPI on localhost. Override with TOC_API in the scheme environment.
    var baseURL: URL = URL(string: ProcessInfo.processInfo.environment["TOC_API"] ?? "http://localhost:8000")!
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
