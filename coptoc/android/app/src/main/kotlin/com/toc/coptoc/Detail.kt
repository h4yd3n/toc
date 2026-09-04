package com.toc.coptoc

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** The detail card over the map — site, person, threat, event, roll call — with the wall's actions, role-gated the same way. */
@Composable
fun DetailSheet(sel: Selection, st: WallState, store: Store, onClose: () -> Unit) {
    val snap = st.snap ?: return
    val isBC = st.role == "battle_captain"; val busy = st.busy != null
    Column(Modifier.padding(10.dp).width(340.dp).fillMaxHeight().background(Palette.panel.copy(alpha = .97f), RoundedCornerShape(6.dp)).border(1.dp, Palette.line, RoundedCornerShape(6.dp)).padding(12.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(Modifier.fillMaxWidth()) { Spacer(Modifier.weight(1f)); Text("×", Modifier.clickable { onClose() }, color = Palette.dim, fontSize = 18.sp) }
        when (sel) {
            is Selection.SiteSel -> snap.locations.firstOrNull { it.id == sel.id }?.let { l ->
                Kicker("S1 SITE · ${l.type.uppercase()} · ${l.city}, ${l.country}"); Title(l.name)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { Chip("POSTURE ${l.posture.uppercase()}", Palette.posture(l.posture), filled = true); if (l.effectivePosture != l.posture) Chip("EFFECTIVE ${l.effectivePosture.uppercase()}", Palette.posture(l.effectivePosture), filled = true) }
                Stats("${l.present}/${l.assigned} present", "${l.securityOnShift} sec on shift", "${l.vipsPresent} VIP")
                if (l.threatIdsInArea.isNotEmpty()) { Section("THREATS IN AREA", "confirmed ones change posture (Decision 3)")
                    l.threatIdsInArea.mapNotNull { id -> snap.threats.firstOrNull { it.id == id } }.forEach { t -> Row(Modifier.clickable { store.select(Selection.ThreatSel(t.id)) }, horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                        Chip(t.severity.take(3).uppercase(), Palette.severity(t.severity), filled = true); Text(t.title, color = Palette.text, fontSize = 11.sp, modifier = Modifier.weight(1f)); if (t.id in l.confirmedThreatIds) Chip("CONFIRMED", Palette.amber) } } }
                if (isBC) { Section("SET POSTURE", "Battle Captain"); Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { listOf("normal", "elevated", "critical").forEach { p -> Mini(p.uppercase(), Palette.posture(p), !busy && p != l.posture) { store.act("setting posture") { setPosture(l.id, p) } } } } }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { Mini("DRAFT S2 ASSESSMENT", Palette.amber, !busy) { store.act("drafting") { draftAssessment("location", l.id) } }
                    if (isBC) Mini("☎ OPEN ROLL CALL", Palette.red, !busy) { store.act("opening roll call") { openRollCall(l.id, null) } } }
                val here = snap.people.filter { it.locationId == l.id }
                Section("PEOPLE HERE", "${here.size}"); here.take(40).forEach { p -> PersonLine(p) { store.select(Selection.PersonSel(p.id)) } }
            }
            is Selection.PersonSel -> snap.people.firstOrNull { it.id == sel.id }?.let { p ->
                Kicker("S1 PERSON · ${p.status.uppercase().replace('_', ' ')} · ${p.teamName}"); Title((if (p.isVip) "★ " else "") + p.name); Text(p.role, color = Palette.dim, fontSize = 11.sp)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { Chip(p.availability.uppercase().replace('_', ' '), when (p.availability) { "unreachable" -> Palette.red; "off_duty" -> Palette.dim; else -> Palette.green }); Chip(if (p.positionSource == "checkin") "CHECKED IN ${"%.0f".format(p.checkinAgeH ?: 0.0)}h ago" else "DERIVED POSITION", if (p.positionSource == "checkin") Palette.green else Palette.dim); if (p.checkinStale) Chip("STALE", Palette.amber); p.incidentStatus?.let { Chip("ROLL CALL · ${it.uppercase()}", Palette.roster(it)) } }
                p.lastCheckinNote?.let { KV("Last note", it) }; p.phone?.let { KV("Phone", it) }; p.email?.let { KV("Email", it) }
                snap.trips.firstOrNull { it.id == p.tripId }?.let { t -> KV("Trip", "${t.originName} → ${t.destName} · ${t.purpose}"); t.operation?.let { KV("Operation", "${it.title} · ${it.tasksDone}/${it.tasksTotal} tasks · ${it.status}") } }
                if (p.threatIdsInArea.isNotEmpty()) { Section("THREATS NEAR", "${p.threatIdsInArea.size}"); p.threatIdsInArea.mapNotNull { id -> snap.threats.firstOrNull { it.id == id } }.forEach { t -> Row(Modifier.clickable { store.select(Selection.ThreatSel(t.id)) }, horizontalArrangement = Arrangement.spacedBy(6.dp)) { Chip(t.severity.take(3).uppercase(), Palette.severity(t.severity), filled = true); Text(t.title, color = Palette.text, fontSize = 11.sp) } } }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { Mini("CHECK IN HERE", Palette.green, !busy) { store.act("checking in") { checkIn(p.id, p.lat, p.lon, "Checked in from Android") } } }
            }
            is Selection.ThreatSel -> snap.threats.firstOrNull { it.id == sel.id }?.let { t ->
                Kicker("S2 THREAT · ${t.source} · ${t.confidence.uppercase()} CONFIDENCE"); Title(t.title)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { Chip(t.severity.uppercase(), Palette.severity(t.severity), filled = true); Chip(if (t.synthetic) "SYNTHETIC" else "LIVE", if (t.synthetic) Palette.dim else Palette.green); t.country?.let { Chip(it, Palette.dim) }; Chip("${"%.0f".format(t.radiusKm)} km", Palette.dim) }
                Text(t.summary, color = Palette.text.copy(alpha = .9f), fontSize = 11.sp, lineHeight = 15.sp)
                KV("Observed", t.observedAt.take(16).replace('T', ' ') + "Z"); t.url?.let { KV("Source", it) }
                Section("PROXIMITY SUGGESTS", "an analyst confirms (Decision 3)")
                snap.locations.filter { t.id in it.threatIdsInArea }.forEach { l -> val conf = t.confirmedLinks.firstOrNull { it.targetType == "location" && it.targetId == l.id }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) { Dot(Palette.posture(l.effectivePosture)); Text(l.name, color = Palette.text, fontSize = 11.sp, modifier = Modifier.weight(1f))
                        if (conf != null) Mini("UNLINK", Palette.dim, !busy) { store.act("removing link") { removeLink(t.id, conf.linkId) } } else if (st.role in listOf("battle_captain", "analyst")) Mini("CONFIRM", Palette.amber, !busy) { store.act("confirming link") { confirmLink(t.id, "location", l.id) } } } }
                snap.people.filter { t.id in it.threatIdsInArea && it.status == "traveling" }.forEach { p -> val conf = t.confirmedLinks.firstOrNull { it.targetType == "person" && it.targetId == p.id }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) { Dot(Palette.blue2); Text(p.name, color = Palette.text, fontSize = 11.sp, modifier = Modifier.weight(1f))
                        if (conf != null) Mini("UNLINK", Palette.dim, !busy) { store.act("removing link") { removeLink(t.id, conf.linkId) } } else if (st.role in listOf("battle_captain", "analyst")) Mini("CONFIRM", Palette.amber, !busy) { store.act("confirming link") { confirmLink(t.id, "person", p.id) } } } }
                if (isBC) Mini("☎ OPEN ROLL CALL IN RADIUS", Palette.red, !busy) { store.act("opening roll call") { openRollCall(null, t.id) } }
            }
            is Selection.EventSel -> snap.events.firstOrNull { it.id == sel.id }?.let { e ->
                Kicker("S3 EVENT · ${e.eventType.uppercase().replace('_', ' ')} · ${if (e.status == "active") "IN PROGRESS" else "T-${e.daysUntil} DAYS"}"); Title(e.name); Text(e.venueName, color = Palette.dim, fontSize = 11.sp)
                Stats("${e.attendeeCount} attending", "${e.vipCount} VIP", "${e.securityCount} security", "${e.tripsGenerated} trips")
                KV("Window", "${e.startAt.take(10)} → ${e.endAt.take(10)}"); KV("Brief", e.description)
                e.operation?.let { KV("Operation", "${it.title} · ${it.status.uppercase()} · ${it.tasksDone}/${it.tasksTotal} tasks · ${it.resourcesOpen} S4 asks open" + (it.fromProductId?.let { f -> " · from $f" } ?: "")) }
                e.coverage?.let { KV("Coverage", "${it.assigned}/${it.required} security assigned" + (if (it.gap > 0) " · GAP ${it.gap}" else "") + " · ${it.rule}") }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { Mini("DRAFT S2 ASSESSMENT", Palette.amber, !busy) { store.act("drafting") { draftAssessment("event", e.id) } } }
            }
            is Selection.IncidentSel -> snap.incidents.firstOrNull { it.id == sel.id }?.let { i ->
                Kicker("S6 ACCOUNTABILITY · ${i.kind.uppercase()} · opened by ${i.openedBy}"); Title(i.title)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) { Text("${i.accounted}/${i.total} accounted", color = if (i.pct == 100) Palette.green else Palette.red, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                    listOf("unreachable", "assist", "injured", "unaccounted", "safe").forEach { k -> val n = i.counts[k] ?: 0; if (n > 0) Chip("${k.uppercase()} $n", Palette.roster(k)) } }
                Box(Modifier.fillMaxWidth().height(6.dp).background(Palette.line, RoundedCornerShape(3.dp))) { Box(Modifier.fillMaxWidth(i.pct / 100f).fillMaxHeight().background(if (i.pct == 100) Palette.green else Palette.red, RoundedCornerShape(3.dp))) }
                if (i.status == "open") Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { val n = (i.counts["unaccounted"] ?: 0) + (i.counts["unreachable"] ?: 0)
                    Mini("📲 REQUEST CHECK-INS ($n)", Palette.green, !busy && n > 0) { store.act("requesting check-ins") { requestCheckins(i.id) } }; if (isBC) Mini("CLOSE", Palette.dim, !busy) { store.act("closing roll call") { closeIncident(i.id) } } }
                Section("ROSTER", "unreachable and needs-assist first (Decision M)")
                i.roster.forEach { r -> Column(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) { Dot(Palette.roster(r.status)); Text((if (r.isVip) "★ " else "") + r.name, color = Palette.text, fontSize = 11.sp, modifier = Modifier.weight(1f))
                        if (r.basis == "manual") Chip("ADDED", Palette.amber); if (r.updatedBy == "rule:escalation-15m") Chip("AUTO 15m", Palette.red); Chip(r.status.uppercase(), Palette.roster(r.status)) }
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { r.phone?.let { Text(it, color = Palette.blue2, fontSize = 10.sp, fontFamily = FontFamily.Monospace) }; if (r.attempts > 0) Text("${r.attempts} attempt(s)", color = Palette.dim, fontSize = 9.5.sp)
                        r.deliveries.forEach { d -> Chip((if (d.channel == "sms") "📱" else "💬") + when (d.status) { "sent" -> "✓"; "simulated" -> "sim"; else -> "✗" }, if (d.status == "failed") Palette.red else Palette.dim) } }
                    if (i.status == "open") Row(horizontalArrangement = Arrangement.spacedBy(5.dp), modifier = Modifier.padding(top = 2.dp)) { listOf("safe" to Palette.green, "unreachable" to Palette.amber, "assist" to Palette.red, "injured" to Palette.red).forEach { (s, c) -> Mini(if (s == "unreachable") "NO ANSWER" else s.uppercase(), c, !busy) { store.act("logging contact") { updateRoster(i.id, r.personId, s) } } } }
                } }
            }
        }
    }
}

@Composable fun Kicker(t: String) = Text(t, color = Palette.dim, fontSize = 8.5.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.2.sp)
@Composable fun Title(t: String) = Text(t, color = Palette.text, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
@Composable fun Section(t: String, hint: String? = null) = Row(Modifier.padding(top = 6.dp)) { Text(t, color = Palette.dim, fontSize = 8.5.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.2.sp); hint?.let { Text("  $it", color = Palette.dim.copy(alpha = .7f), fontSize = 8.5.sp, fontFamily = FontFamily.Monospace) } }
@Composable fun KV(k: String, v: String) = Row(verticalAlignment = Alignment.Top) { Text(k, Modifier.width(70.dp), color = Palette.dim, fontSize = 10.sp, fontFamily = FontFamily.Monospace); Text(v, color = Palette.text, fontSize = 11.sp) }
@Composable fun Stats(vararg s: String) = Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) { s.forEach { Text(it, color = Palette.text, fontSize = 11.sp) } }
@Composable fun PersonLine(p: Person, onClick: () -> Unit) = Row(Modifier.fillMaxWidth().clickable { onClick() }.padding(vertical = 2.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
    Dot(if (p.isVip) Palette.amber else if (p.onShift) Palette.green else Palette.blue2); Text((if (p.isVip) "★ " else "") + p.name, color = Palette.text, fontSize = 11.sp, modifier = Modifier.weight(1f)); Text(p.role, color = Palette.dim, fontSize = 9.5.sp, maxLines = 1) }
