package com.toc.coptoc

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNamingStrategy
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.put
import java.net.HttpURLConnection
import java.net.URL

class ApiError(val status: Int, message: String) : Exception(message)

/** The COP backend client — same contract as the web app and the iOS app. Role and actor travel as headers. */
@OptIn(ExperimentalSerializationApi::class)
class CopClient(var baseUrl: String = BuildConfig.TOC_API, var role: String = "battle_captain", var actor: String = "Battle Captain (Android)") {
    private val json = Json { ignoreUnknownKeys = true; namingStrategy = JsonNamingStrategy.SnakeCase; explicitNulls = false; coerceInputValues = true; isLenient = true }

    suspend fun snapshot(restricted: Boolean): Snapshot = json.decodeFromString(get("/v1/cop/snapshot?restricted=$restricted"))
    suspend fun requirements(): List<Requirement> = json.decodeFromString(get("/v1/s2/requirements?status=active"))
    suspend fun intsums(): List<IntsumHead> = json.decodeFromString(get("/v1/s2/intsum"))
    suspend fun cases(): List<CaseHead> = json.decodeFromString(get("/v1/s2/cases"))
    suspend fun operation(id: String): Operation = json.decodeFromString(get("/v1/cop/operations/$id"))
    suspend fun releaseWarning(id: String) = send("POST", "/v1/s2/warnings/$id/release", buildJsonObject { })
    suspend fun cancelWarning(id: String) = send("POST", "/v1/s2/warnings/$id/cancel", buildJsonObject { })
    suspend fun runWarningRule() = send("POST", "/v1/s2/warnings/suggest", buildJsonObject { })
    suspend fun ackProduct(ptype: String, pid: String) = send("POST", "/v1/s2/products/$ptype/$pid/ack", buildJsonObject { })
    suspend fun releaseIntsum(id: String) = send("POST", "/v1/s2/intsum/$id/release", buildJsonObject { })
    suspend fun draftIntsum() = send("POST", "/v1/s2/intsum/draft", buildJsonObject { })
    suspend fun updateTask(opId: String, taskId: String, status: String) = send("PATCH", "/v1/cop/operations/$opId/tasks/$taskId", buildJsonObject { put("status", status) })

    suspend fun setPosture(siteId: String, posture: String) = send("PATCH", "/v1/cop/locations/$siteId/posture", buildJsonObject { put("posture", posture); put("reason", "Set from Android") })
    suspend fun confirmLink(threatId: String, targetType: String, targetId: String) = send("POST", "/v1/cop/threats/$threatId/links", buildJsonObject { put("target_type", targetType); put("target_id", targetId) })
    suspend fun removeLink(threatId: String, linkId: Int) = send("DELETE", "/v1/cop/threats/$threatId/links/$linkId", null)
    suspend fun draftAssessment(subjectType: String, subjectId: String) = send("POST", "/v1/cop/assessments/draft", buildJsonObject { put("subject_type", subjectType); put("subject_id", subjectId) })
    suspend fun setAssessmentStatus(id: String, status: String) = send("PATCH", "/v1/cop/assessments/$id", buildJsonObject { put("status", status) })
    suspend fun refreshIntel() = send("POST", "/v1/cop/intel/refresh", null)
    suspend fun checkIn(personId: String, lat: Double, lon: Double, note: String) = send("POST", "/v1/cop/people/$personId/checkin", buildJsonObject { put("lat", lat); put("lon", lon); put("note", note) })
    suspend fun openRollCall(locationId: String?, threatId: String?) = send("POST", "/v1/cop/incidents", buildJsonObject { locationId?.let { put("location_id", it) }; threatId?.let { put("threat_id", it) } })
    suspend fun updateRoster(incidentId: String, personId: String, status: String) = send("PATCH", "/v1/cop/incidents/$incidentId/roster/$personId", buildJsonObject { put("status", status); put("method", "call") })
    suspend fun requestCheckins(incidentId: String) = send("POST", "/v1/cop/incidents/$incidentId/request-checkins", buildJsonObject { })
    suspend fun closeIncident(id: String) = send("PATCH", "/v1/cop/incidents/$id/close", buildJsonObject { })
    // §7 / §8 — the background boards
    suspend fun updateSupply(id: String, onHand: Double, note: String?) = send("PATCH", "/v1/cop/supply/$id", buildJsonObject { put("on_hand", onHand); if (!note.isNullOrBlank()) put("note", note) })
    suspend fun updateShipment(id: String, status: String) = send("PATCH", "/v1/cop/shipments/$id", buildJsonObject { put("status", status) })
    suspend fun updateSystem(id: String, status: String, note: String?) = send("PATCH", "/v1/cop/systems/$id", buildJsonObject { put("status", status); if (!note.isNullOrBlank()) put("note", note) })
    suspend fun takeWatch(name: String) = send("POST", "/v1/cop/watch/take", buildJsonObject { put("battle_captain", name) })

    private suspend fun get(path: String): String = withContext(Dispatchers.IO) {
        val c = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply { requestMethod = "GET"; connectTimeout = 8000; readTimeout = 20000; headers() }
        read(c)
    }

    private suspend fun send(method: String, path: String, body: kotlinx.serialization.json.JsonObject?): String = withContext(Dispatchers.IO) {
        val c = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = if (method == "PATCH") "POST" else method
            if (method == "PATCH") setRequestProperty("X-HTTP-Method-Override", "PATCH")
            connectTimeout = 8000; readTimeout = 30000; headers()
            if (body != null) { doOutput = true; setRequestProperty("Content-Type", "application/json"); outputStream.use { it.write(body.toString().toByteArray()) } }
        }
        read(c)
    }

    private fun HttpURLConnection.headers() { setRequestProperty("X-TOC-Role", role); setRequestProperty("X-TOC-Actor", actor); setRequestProperty("Accept", "application/json") }

    private fun read(c: HttpURLConnection): String {
        val code = c.responseCode
        val text = (if (code < 400) c.inputStream else c.errorStream)?.bufferedReader()?.readText() ?: ""
        if (code >= 400) {
            val detail = runCatching { json.parseToJsonElement(text).let { (it as kotlinx.serialization.json.JsonObject)["detail"] as? JsonPrimitive }?.content }.getOrNull()
            throw ApiError(code, detail ?: "HTTP $code")
        }
        return text
    }
}
