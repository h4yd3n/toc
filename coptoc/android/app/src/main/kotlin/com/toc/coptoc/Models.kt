package com.toc.coptoc

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.double

// Mirrors coptoc/api/COP_API_CONTRACT.md. Decoded with a snake_case naming strategy and unknown keys ignored,
// so the wall can grow without breaking the phone.

@Serializable data class Watch(val id: String = "", val name: String = "", val battleCaptain: String? = null, val status: String = "open", val startedAt: String = "", val endsAt: String = "",
                               val elapsedH: Double = 0.0, val remainingH: Double = 0.0, val overdue: Boolean = false, val inOverlap: Boolean = false, val nextWatch: String = "", val pattern: String = "")
@Serializable data class Estimate(val section: String, val assessment: String = "", val recommendation: String = "", val updatedBy: String? = null, val updatedAt: String? = null)
@Serializable data class Summary(val s2Actors: Int = 0, val s2ReportsPending: Int = 0, val movementRisks: Int = 0, val s4Status: String = "green", val s6Status: String = "green", val totalPeople: Int = 0, val present: Int = 0, val traveling: Int = 0, val vipsTraveling: Int = 0, val securityOnShift: Int = 0, val activeThreats: Int = 0,
                                 val realThreats: Int = 0, val confirmedLinks: Int = 0, val checkedInFresh: Int = 0, val openPirs: Int = 0, val upcomingEvents: Int = 0, val openIncidents: Int = 0,
                                 val unaccounted: Int = 0, val posture: String = "normal", val defcon: Int = 5, val defconLevels: List<DefconLevel> = emptyList(), val flash: Int = 0, val warningsPending: Int = 0, val offDuty: Int = 0, val unreachable: Int = 0)
@Serializable data class Site(val s4Status: String? = null, val s6Status: String? = null, val s4Red: Int = 0, val s4Lines: Int = 0, val s6Down: Int = 0, val s6Systems: Int = 0, val s6InUse: String? = null, val id: String, val name: String, val type: String = "", val lat: Double, val lon: Double, val city: String = "", val country: String = "", val posture: String = "normal",
                              val effectivePosture: String = "normal", val sensitivity: String = "standard", val isToc: Boolean = false, val assigned: Int = 0, val present: Int = 0, val securityOnShift: Int = 0, val vipsPresent: Int = 0,
                              val threatIdsInArea: List<String> = emptyList(), val confirmedThreatIds: List<String> = emptyList(), val area: AreaCompact? = null)
@Serializable data class Person(val shortName: String? = null, val rank: String? = null, val grade: String? = null, val lastName: String? = null, val firstName: String? = null, val teamId: String = "", val id: String, val name: String, val role: String = "", val teamName: String = "", val homeLocationId: String = "", val locationId: String? = null, val isVip: Boolean = false,
                                val onShift: Boolean = false, val status: String = "at_post", val lat: Double = 0.0, val lon: Double = 0.0, val tripId: String? = null, val positionSource: String = "derived",
                                val checkinAgeH: Double? = null, val checkinStale: Boolean = false, val lastCheckinNote: String? = null, val threatIdsInArea: List<String> = emptyList(),
                                val phone: String? = null, val email: String? = null, val incidentStatus: String? = null, val availability: String = "available")
@Serializable data class OperationSummary(val id: String, val title: String = "", val status: String = "planned", val tasksTotal: Int = 0, val tasksDone: Int = 0, val blocked: Int = 0, val resourcesOpen: Int = 0, val pct: Int = 0, val fromProductId: String? = null)
@Serializable data class Leg(val id: String, val kind: String, val label: String = "", val ref: String? = null, val fromName: String? = null, val toName: String = "", val toLat: Double = 0.0, val toLon: Double = 0.0,
                             val startAt: String = "", val endAt: String = "", val status: String = "planned", val note: String = "", val source: String = "") {
    val icon get() = when (kind) { "flight" -> "✈"; "lodging" -> "🏨"; else -> "🚗" }
}
@Serializable data class Trip(val legs: List<Leg> = emptyList(), val currentLeg: Leg? = null, val id: String, val personId: String, val personName: String = "", val isVip: Boolean = false, val originName: String = "", val originLat: Double = 0.0, val originLon: Double = 0.0,
                              val destName: String = "", val destLat: Double = 0.0, val destLon: Double = 0.0, val departAt: String = "", val returnAt: String = "", val purpose: String = "", val status: String = "planned",
                              val eventId: String? = null, val operation: OperationSummary? = null)
@Serializable data class CopEvent(val id: String, val name: String, val eventType: String = "", val venueName: String = "", val venueLat: Double = 0.0, val venueLon: Double = 0.0, val startAt: String = "", val endAt: String = "",
                                  val status: String = "upcoming", val daysUntil: Int = 0, val description: String = "", val attendeeCount: Int = 0, val vipCount: Int = 0, val securityCount: Int = 0,
                                  val tripsGenerated: Int = 0, val threatIdsInArea: List<String> = emptyList(), val operation: OperationSummary? = null, val coverage: CoverageInfo? = null)
@Serializable data class ConfirmedLink(val linkId: Int, val targetType: String, val targetId: String, val targetName: String = "", val confirmedBy: String = "", val note: String? = null)
@Serializable data class Threat(val id: String, val title: String, val summary: String = "", val lat: Double, val lon: Double, val radiusKm: Double = 0.0, val severity: String = "low", val eventType: String? = null,
                                val source: String = "", val url: String? = null, val confidence: String = "low", val observedAt: String = "", val synthetic: Boolean = true,
                                val confirmedLinks: List<ConfirmedLink> = emptyList(), val country: String? = null, val scope: String = "point")
@Serializable data class PIR(val id: String, val question: String, val priority: Int = 2, val status: String = "OPEN", val subjectType: String? = null, val subjectId: String? = null)
@Serializable data class Judgment(val claim: String, val likelihood: String, val band: String = "", val confidence: String = "")
@Serializable data class Assessment(val id: String, val title: String, val subjectType: String = "", val subjectId: String = "", val likelihood: String = "", val band: String = "", val confidence: String = "",
                                    val bluf: String = "", val keyJudgments: List<Judgment> = emptyList(), val gaps: List<String> = emptyList(), val author: String = "", val status: String = "draft", val approvedBy: String? = null)
@Serializable data class Delivery(val channel: String, val status: String, val at: String = "", val error: String? = null)
@Serializable data class RosterEntry(val personId: String, val name: String, val role: String = "", val isVip: Boolean = false, val phone: String? = null, val status: String = "unaccounted", val basis: String = "in_area",
                                     val checkinRequestedAt: String? = null, val deliveries: List<Delivery> = emptyList(), val attempts: Int = 0, val updatedBy: String? = null, val note: String? = null)
@Serializable data class Incident(val id: String, val title: String, val kind: String = "site", val locationId: String? = null, val threatId: String? = null, val lat: Double = 0.0, val lon: Double = 0.0, val radiusKm: Double = 0.0, val status: String = "open", val openedBy: String = "",
                                  val openedAt: String = "", val closedAt: String? = null, val notes: String? = null, val total: Int = 0, val accounted: Int = 0, val pct: Int = 0,
                                  val counts: Map<String, Int> = emptyMap(), val checkinsRequested: Int = 0, val roster: List<RosterEntry> = emptyList())
@Serializable data class LogEntry(val id: String, val at: String, val type: String, val actor: String = "", val actorType: String = "", val summary: String = "")
@Serializable data class SectionCfg(val code: String, val title: String = "", val hint: String = "", val enabled: Boolean = true, val label: String = code, val showCode: Boolean = true)
@Serializable data class SupplyLine(val id: String, val locationId: String? = null, val locationName: String = "", val category: String = "", val item: String = "", val onHand: Double = 0.0, val required: Double = 0.0, val unit: String = "", val pct: Int = 0, val status: String = "green", val note: String = "", val updatedBy: String = "")
@Serializable data class Shipment(val id: String, val description: String = "", val category: String = "", val quantity: String = "", val fromName: String = "", val toName: String = "", val eta: String = "", val hoursToEta: Double = 0.0, val status: String = "planned", val priority: String = "routine", val carrier: String = "", val ref: String? = null, val health: String = "green", val note: String = "")
@Serializable data class S4Counts(val red: Int = 0, val amber: Int = 0, val inbound: Int = 0, val late: Int = 0)
@Serializable data class S4Board(val status: String = "green", val supplies: List<SupplyLine> = emptyList(), val shipments: List<Shipment> = emptyList(), val exceptions: List<String> = emptyList(), val counts: S4Counts = S4Counts())
@Serializable data class SystemLine(val id: String, val name: String = "", val category: String = "", val locationId: String? = null, val locationName: String = "", val pace: String? = null, val status: String = "up", val health: String = "green", val hours: Double = 0.0, val note: String = "", val updatedBy: String = "")
@Serializable data class PaceSite(val locationName: String = "", val nets: Map<String, String> = emptyMap(), val inUse: String? = null)
@Serializable data class S6Counts(val down: Int = 0, val degraded: Int = 0, val total: Int = 0)
@Serializable data class S6Board(val status: String = "green", val systems: List<SystemLine> = emptyList(), val pace: Map<String, PaceSite> = emptyMap(), val exceptions: List<String> = emptyList(), val counts: S6Counts = S6Counts())
@Serializable data class Team(val id: String, val name: String = "", val locationId: String = "", val function: String = "", val isSecurity: Boolean = false, val parentId: String? = null, val echelon: String = "company", val short: String? = null, val equipment: String? = null)
@Serializable data class Me(val userId: String? = null, val name: String = "", val role: String = "", val perms: Map<String, String> = emptyMap(), val battleCaptain: Boolean = false, val admin: Boolean = false, val sectionsVisible: List<String> = emptyList())
@Serializable data class UserInfo(val id: String, val name: String = "", val title: String? = null, val preset: String = "custom", val battleCaptain: Boolean = false)
@Serializable data class UsersOut(val users: List<UserInfo> = emptyList())
@Serializable data class Tasking(val id: String, val kind: String = "other", val title: String = "", val fromSection: String = "", val toSection: String = "", val subjectName: String = "", val asset: String = "",
                                 val windowFrom: String? = null, val windowTo: String? = null, val priority: String = "routine", val status: String = "requested", val notes: String = "", val result: String = "",
                                 val requestedBy: String = "", val ageH: Double = 0.0, val ownedBy: String? = null, val open: Boolean = true, val overdue: Boolean = false, val health: String = "green")
@Serializable data class TaskingCounts(val inbox: Int = 0, val outbox: Int = 0, val overdue: Int = 0)
@Serializable data class TaskingBoard(val items: List<Tasking> = emptyList(), val open: Int = 0, val overdue: Int = 0, val perSection: Map<String, TaskingCounts> = emptyMap())
/** §3.1 — where the wall opens: the declared AO, else the box holding our sites, else nothing known yet. */
// §3.4 the derived overlays: every active requirement as an NAI; everything that moves as a movement (Decision Z)
@Serializable data class Nai(val id: String, val nai: Int = 0, val name: String = "", val subjectName: String = "", val subjectType: String = "", val subjectId: String? = null, val kind: String = "standing", val lat: Double, val lon: Double, val radiusKm: Double = 50.0,
                             val priority: Int = 3, val windowFrom: String? = null, val windowTo: String? = null, val question: String = "", val coveragePct: Int = 0, val gaps: Int = 0, val pirIds: List<String> = emptyList(), val health: String = "red")
@Serializable data class MovementLeg(val kind: String = "route", val label: String = "", val fromLat: Double? = null, val fromLon: Double? = null, val toLat: Double = 0.0, val toLon: Double = 0.0, val startAt: String? = null, val endAt: String? = null, val status: String = "planned")
@Serializable data class Movement(val riskFlags: List<MovementRisk> = emptyList(), val id: String, val kind: String = "individual", val owner: String = "S3", val name: String = "", val unit: String? = null, val pax: Int = 0, val personIds: List<String> = emptyList(), val isVip: Boolean = false, val purpose: String = "",
                                  val originName: String = "", val destName: String = "", val destLat: Double = 0.0, val destLon: Double = 0.0, val departAt: String? = null, val returnAt: String = "", val hoursToEta: Double? = null,
                                  val status: String = "planned", val mode: String = "unknown", val headLat: Double? = null, val headLon: Double? = null, val currentLeg: String? = null, val legs: List<MovementLeg> = emptyList(), val health: String = "green")
@Serializable data class AreaCompact(val id: String, val place: String = "", val worst: String = "unknown", val worstIndicator: String? = null, val strip: List<String> = emptyList(), val assessedBy: String = "", val assessedAt: String = "", val ageDays: Double = 0.0, val stale: Boolean = false)
// §3.4 a control measure a section drew by hand: a point [lon, lat] or a path [[lon, lat], …], typed from the catalog
@Serializable data class Graphic(val id: String, val type: String = "", val kind: String = "point", val section: String = "S3", val name: String = "", val label: String = "", val geometry: JsonElement, val center: List<Double> = emptyList(),
                                 val windowFrom: String? = null, val windowTo: String? = null, val inWindow: Boolean = true, val status: String = "active", val note: String = "", val subjectType: String? = null, val subjectId: String? = null,
                                 val createdBy: String = "", val color: String = "#94a3b8", val dash: Boolean = false, val glyph: String = "·") {
    /** The path as (lon, lat) pairs; a point is a path of one. */
    val path: List<Pair<Double, Double>> get() = try {
        val a = geometry.jsonArray
        if (a.isNotEmpty() && a[0] is kotlinx.serialization.json.JsonArray) a.map { it.jsonArray[0].jsonPrimitive.double to it.jsonArray[1].jsonPrimitive.double } else listOf(a[0].jsonPrimitive.double to a[1].jsonPrimitive.double)
    } catch (e: Exception) { emptyList() }
}
// §5.10b the live S2 picture, Sigtoc's: actors at their last known position, their sightings, the reports still to be disposed of, and the movement legs Intel flagged
@Serializable data class S2Actor(val id: String, val kind: String = "group", val name: String = "", val aliases: List<String> = emptyList(), val echelon: String = "", val strength: String = "", val equipment: List<String> = emptyList(), val ttps: List<String> = emptyList(),
                                 val assessedIntent: String = "", val status: String = "active", val caseId: String? = null, val owner: String = "S2", val lat: Double? = null, val lon: Double? = null, val place: String? = null, val lastSeenAt: String? = null, val sightingIds: List<String> = emptyList()) {
    val glyph get() = when (kind) { "unit" -> "◆"; "individual" -> "●"; "organization" -> "▣"; else -> "◈" }
}
@Serializable data class S2Sighting(val id: String, val actorId: String, val at: String = "", val lat: Double, val lon: Double, val place: String? = null, val naiId: String? = null, val sourceType: String = "report", val sourceId: String? = null,
                                    val reliability: String = "A", val credibility: Int = 2, val grade: String = "", val what: String = "", val confidence: String = "probable")
@Serializable data class S2Report(val id: String, val kind: String = "spot", val reportedBy: String = "", val reporterRole: String = "", val at: String = "", val lat: Double? = null, val lon: Double? = null, val place: String? = null, val text: String = "",
                                  val caseId: String? = null, val grade: String = "", val source: String = "", val status: String = "filed", val disposition: String? = null, val disposedBy: String? = null, val dispositionNote: String? = null)
@Serializable data class MovementRisk(val id: String, val movementId: String = "", val movementName: String = "", val legLabel: String = "", val graphicId: String = "", val graphicName: String = "", val graphicType: String = "", val confidence: String = "", val basis: String = "", val severity: String = "low", val reason: String = "")
@Serializable data class MapFrame(val centerLat: Double? = null, val centerLon: Double? = null, val radiusKm: Double? = null, val source: String = "none")

@Serializable data class Snapshot(val s2Actors: List<S2Actor> = emptyList(), val s2Sightings: List<S2Sighting> = emptyList(), val s2Reports: List<S2Report> = emptyList(), val movementRisks: List<MovementRisk> = emptyList(), val graphics: List<Graphic> = emptyList(), val nais: List<Nai> = emptyList(), val movements: List<Movement> = emptyList(), val view: MapFrame? = null, val taskings: TaskingBoard? = null, val me: Me? = null, val profile: String = "military", val teams: List<Team> = emptyList(), val sections: List<SectionCfg> = emptyList(), val s4: S4Board? = null, val s6: S6Board? = null, val generatedAt: String = "", val restrictedIncluded: Boolean = false, val restrictedDenied: Boolean = false, val watch: Watch? = null, val estimates: List<Estimate> = emptyList(), val summary: Summary = Summary(),
                                  val locations: List<Site> = emptyList(), val people: List<Person> = emptyList(), val trips: List<Trip> = emptyList(), val events: List<CopEvent> = emptyList(),
                                  val threats: List<Threat> = emptyList(), val pirs: List<PIR> = emptyList(), val assessments: List<Assessment> = emptyList(), val incidents: List<Incident> = emptyList(),
                                  val log: List<LogEntry> = emptyList(), val operations: List<OperationSummary> = emptyList(), val warnings: List<Warning> = emptyList(),
                                  val decisionPoints: List<SnapDecisionPoint> = emptyList(), val ccir: CcirBoard? = null, val exercise: ExerciseBoard? = null)

/** §3.7 — the phone reads one thing about an exercise and reads it loudly: that there is one. Exercise control is
 *  the wall's seat; what a phone must never do is let a drill read as real. */
@Serializable data class ExerciseRun(val id: String, val name: String = "", val scenario: String = "", val status: String = "planned", val speed: Double = 1.0,
                                     val startedAt: String? = null, val endedAt: String? = null, val elapsedMin: Double? = null,
                                     val fired: Int = 0, val failed: Int = 0, val pending: Int = 0, val total: Int = 0)
@Serializable data class ExerciseBoard(val running: Boolean = false, val exercise: ExerciseRun? = null)

/** §3.6 — the commander's critical information requirements. Written on the wall, read here; the phone never
 *  edits the commander's list. An EEFI never trips: nothing in the data measures our own signature. */
@Serializable data class CcirLine(val id: String, val kind: String = "ffir", val text: String = "", val ownerSection: String = "S3", val priority: Int = 2,
                                  val status: String = "active", val metric: String? = null, val unit: String = "", val condition: String = "",
                                  val state: String = "green", val value: Double? = null, val trips: Int = 0, val trippedMin: Int? = null) {
    val tripped: Boolean get() = state == "tripped"
}
@Serializable data class CcirCounts(val tripped: Int = 0, val unmeasured: Int = 0, val active: Int = 0, val total: Int = 0)
@Serializable data class CcirBoard(val lines: List<CcirLine> = emptyList(), val counts: CcirCounts = CcirCounts())

/** §5.10b Phase 3 — a decision the commander owes, with the time it has to be made by. The matrix lives on the wall;
 *  the phone shows the decision, its trigger, what happens, and whether the clock has run out. */
@Serializable data class SnapDecisionPoint(val id: String, val title: String = "", val subjectType: String = "", val subjectId: String = "", val operationId: String? = null,
                                           val decision: String = "", val trigger: String = "", val action: String = "", val ownerSection: String = "S3",
                                           val latestTime: String? = null, val overdue: Boolean = false, val status: String = "open", val note: String = "",
                                           val pirId: String? = null, val naiIds: List<String> = emptyList(), val coaIds: List<String> = emptyList())

// Sigtoc (read side on the phone)
@Serializable data class Coverage(val covered: Int = 0, val total: Int = 0, val pct: Int = 0, val gaps: List<String> = emptyList())
@Serializable data class Requirement(val id: String, val kind: String = "standing", val subjectType: String = "", val subjectName: String = "", val question: String = "", val priority: Int = 2,
                                     val status: String = "active", val owner: String = "", val windowFrom: String? = null, val windowTo: String? = null, val coverage: Coverage = Coverage())
@Serializable data class IntsumHead(val id: String, val status: String = "draft", val headline: String = "", val nstr: Boolean = false, val releasedBy: String? = null)
/** §5.10b Phase 3 — what the other side may do, in ICD 203 words. Written on the wall; the phone reads it. */
@Serializable data class ThreatCoa(val id: String, val title: String = "", val subjectName: String = "", val actorName: String? = null, val narrative: String = "",
                                   val likelihood: String = "unassessed", val confidence: String = "low", val mostLikely: Boolean = false, val mostDangerous: Boolean = false,
                                   val indicators: List<String> = emptyList(), val naiIds: List<String> = emptyList(), val graphicIds: List<String> = emptyList(), val status: String = "candidate")
/** §5.10b Phase 4 (LOE 5) — a source outside our own people, graded A–F by the analyst. */
@Serializable data class LiaisonRecord(val reports: Int = 0, val filed: Int = 0, val corroborated: Int = 0, val linked: Int = 0, val promoted: Int = 0, val dismissed: Int = 0, val disposed: Int = 0, val borneOut: Int = 0, val lastReportAt: String? = null)
@Serializable data class LiaisonSource(val id: String, val name: String = "", val kind: String = "other", val reliability: String = "F", val notes: String = "", val gradedBy: String? = null, val record: LiaisonRecord = LiaisonRecord())
/** §5.10b Phase 3 — the head of a staff product: the IPB, the estimate, or Annex B. */
@Serializable data class StaffProductHead(val id: String, val kind: String = "ipb", val title: String = "", val subjectName: String = "", val status: String = "draft", val draftedBy: String = "", val draftedAt: String = "", val decidedBy: String? = null)

sealed interface Selection {
    data class SiteSel(val id: String) : Selection
    data class PersonSel(val id: String) : Selection
    data class ThreatSel(val id: String) : Selection
    data class EventSel(val id: String) : Selection
    data class IncidentSel(val id: String) : Selection
    data class ActorSel(val id: String) : Selection
    data class ReportSel(val id: String) : Selection
}

@Serializable data class CoverageInfo(val required: Int = 0, val assigned: Int = 0, val gap: Int = 0, val rule: String = "")
@Serializable data class Warning(val id: String, val title: String = "", val text: String = "", val subjectType: String = "", val subjectId: String = "", val subjectName: String = "", val threatId: String? = null,
                                 val severity: String = "elevated", val status: String = "suggested", val suggestedBy: String = "", val createdAt: String = "", val releasedBy: String? = null, val releasedAt: String? = null, val ageMin: Int? = null) {
    val shortTitle get() = title.removePrefix("FLASH — ")
}
@Serializable data class CaseHead(val id: String, val title: String = "", val kind: String = "general", val status: String = "open", val openedBy: String = "", val entities: Int = 0, val relationships: Int = 0, val events: Int = 0, val pendingReview: Int = 0)
@Serializable data class OpTask(val id: String, val title: String = "", val section: String = "", val owner: String = "", val status: String = "todo")
@Serializable data class OpResource(val id: String, val item: String = "", val qty: Int = 1, val status: String = "requested")
@Serializable data class Operation(val id: String, val title: String = "", val status: String = "planned", val subjectName: String = "", val fromProductId: String? = null, val notes: String = "", val tasks: List<OpTask> = emptyList(), val resources: List<OpResource> = emptyList(), val tasksTotal: Int = 0, val tasksDone: Int = 0, val pct: Int = 0)

@Serializable data class DefconLevel(val defcon: Int, val posture: String = "", val meaning: String = "", val sites: Int = 0)
