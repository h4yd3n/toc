package com.toc.coptoc

import kotlinx.serialization.Serializable

// Mirrors coptoc/api/COP_API_CONTRACT.md. Decoded with a snake_case naming strategy and unknown keys ignored,
// so the wall can grow without breaking the phone.

@Serializable data class Watch(val id: String = "", val name: String = "", val battleCaptain: String? = null, val status: String = "open", val startedAt: String = "", val endsAt: String = "",
                               val elapsedH: Double = 0.0, val remainingH: Double = 0.0, val overdue: Boolean = false, val inOverlap: Boolean = false, val nextWatch: String = "", val pattern: String = "")
@Serializable data class Estimate(val section: String, val assessment: String = "", val recommendation: String = "", val updatedBy: String? = null, val updatedAt: String? = null)
@Serializable data class Summary(val s4Status: String = "green", val s6Status: String = "green", val totalPeople: Int = 0, val present: Int = 0, val traveling: Int = 0, val vipsTraveling: Int = 0, val securityOnShift: Int = 0, val activeThreats: Int = 0,
                                 val realThreats: Int = 0, val confirmedLinks: Int = 0, val checkedInFresh: Int = 0, val openPirs: Int = 0, val upcomingEvents: Int = 0, val openIncidents: Int = 0,
                                 val unaccounted: Int = 0, val posture: String = "normal", val defcon: Int = 5, val defconLevels: List<DefconLevel> = emptyList(), val flash: Int = 0, val warningsPending: Int = 0, val offDuty: Int = 0, val unreachable: Int = 0)
@Serializable data class Site(val s4Status: String? = null, val s6Status: String? = null, val s4Red: Int = 0, val s4Lines: Int = 0, val s6Down: Int = 0, val s6Systems: Int = 0, val s6InUse: String? = null, val id: String, val name: String, val type: String = "", val lat: Double, val lon: Double, val city: String = "", val country: String = "", val posture: String = "normal",
                              val effectivePosture: String = "normal", val sensitivity: String = "standard", val isToc: Boolean = false, val assigned: Int = 0, val present: Int = 0, val securityOnShift: Int = 0, val vipsPresent: Int = 0,
                              val threatIdsInArea: List<String> = emptyList(), val confirmedThreatIds: List<String> = emptyList())
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
@Serializable data class Incident(val id: String, val title: String, val kind: String = "site", val locationId: String? = null, val threatId: String? = null, val status: String = "open", val openedBy: String = "",
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
@Serializable data class MapFrame(val centerLat: Double? = null, val centerLon: Double? = null, val radiusKm: Double? = null, val source: String = "none")

@Serializable data class Snapshot(val view: MapFrame? = null, val taskings: TaskingBoard? = null, val me: Me? = null, val profile: String = "military", val teams: List<Team> = emptyList(), val sections: List<SectionCfg> = emptyList(), val s4: S4Board? = null, val s6: S6Board? = null, val generatedAt: String = "", val restrictedIncluded: Boolean = false, val watch: Watch? = null, val estimates: List<Estimate> = emptyList(), val summary: Summary = Summary(),
                                  val locations: List<Site> = emptyList(), val people: List<Person> = emptyList(), val trips: List<Trip> = emptyList(), val events: List<CopEvent> = emptyList(),
                                  val threats: List<Threat> = emptyList(), val pirs: List<PIR> = emptyList(), val assessments: List<Assessment> = emptyList(), val incidents: List<Incident> = emptyList(),
                                  val log: List<LogEntry> = emptyList(), val operations: List<OperationSummary> = emptyList(), val warnings: List<Warning> = emptyList())

// Sigtoc (read side on the phone)
@Serializable data class Coverage(val covered: Int = 0, val total: Int = 0, val pct: Int = 0, val gaps: List<String> = emptyList())
@Serializable data class Requirement(val id: String, val kind: String = "standing", val subjectType: String = "", val subjectName: String = "", val question: String = "", val priority: Int = 2,
                                     val status: String = "active", val owner: String = "", val windowFrom: String? = null, val windowTo: String? = null, val coverage: Coverage = Coverage())
@Serializable data class IntsumHead(val id: String, val status: String = "draft", val headline: String = "", val nstr: Boolean = false, val releasedBy: String? = null)

sealed interface Selection {
    data class SiteSel(val id: String) : Selection
    data class PersonSel(val id: String) : Selection
    data class ThreatSel(val id: String) : Selection
    data class EventSel(val id: String) : Selection
    data class IncidentSel(val id: String) : Selection
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
