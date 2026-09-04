package com.toc.coptoc

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

val ROLES = listOf("battle_captain", "ep", "security", "analyst", "ea")

/** The wall on a phone or tablet: header strip, map in the middle, S1 left, S2 right, S3 + log below. */
@Composable
fun WallScreen(store: Store) {
    val st by store.state.collectAsStateWithLifecycle()
    val snap = st.snap
    Column(Modifier.fillMaxSize().background(Palette.bg)) {
        Header(st, store)
        FlashStrip(st, store)
        Row(Modifier.weight(1f).fillMaxWidth()) {
            val wide = androidx.compose.ui.platform.LocalConfiguration.current.screenWidthDp >= 1100
            Panel(Modifier.width(if (wide) 260.dp else 210.dp).fillMaxHeight()) { S1Panel(st, store) }
            Box(Modifier.weight(1f).fillMaxHeight()) {
                WallMap(snap, st.restricted, onSelect = store::select, modifier = Modifier.fillMaxSize())
                st.selection?.let { sel -> DetailSheet(sel, st, store, onClose = { store.select(null) }) }
                st.operation?.let { op -> OperationSheet(op, st, store, onClose = { store.openOperation(null) }) }
                st.busy?.let { Text(it.uppercase() + "…", Modifier.align(Alignment.BottomCenter).padding(8.dp).background(Palette.panel, RoundedCornerShape(4.dp)).padding(6.dp), color = Palette.blue2, fontSize = 10.sp, fontFamily = FontFamily.Monospace) }
                st.error?.let { Text(it, Modifier.align(Alignment.TopCenter).padding(8.dp).background(Palette.panel, RoundedCornerShape(4.dp)).border(1.dp, Palette.red, RoundedCornerShape(4.dp)).padding(8.dp).clickable { store.dismissError() }, color = Palette.red, fontSize = 11.sp) }
                if (snap == null && st.error == null) Text("LOADING PICTURE…", Modifier.align(Alignment.Center), color = Palette.dim, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
            }
            Panel(Modifier.width(if (wide) 300.dp else 240.dp).fillMaxHeight()) { S2Panel(st, store) }
        }
        Row(Modifier.height(118.dp).fillMaxWidth()) {
            Panel(Modifier.weight(1f).fillMaxHeight()) { S3Panel(st, store) }
            Panel(Modifier.width(300.dp).fillMaxHeight()) { LogPanel(st) }
        }
    }
}

@Composable fun Panel(modifier: Modifier, content: @Composable ColumnScope.() -> Unit) = Column(modifier.background(Palette.panel).border(0.5.dp, Palette.line), content = content)
@Composable fun Label(text: String, hint: String? = null, action: (@Composable () -> Unit)? = null) = Row(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
    Text(text, color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
    hint?.let { Text("  $it", color = Palette.dim.copy(alpha = .7f), fontSize = 9.sp, fontFamily = FontFamily.Monospace) }
    Spacer(Modifier.weight(1f)); action?.invoke()
}
@Composable fun Chip(text: String, color: Color = Palette.dim, filled: Boolean = false, onClick: (() -> Unit)? = null) = Text(text, Modifier.let { m -> if (onClick != null) m.clickable { onClick() } else m }
    .background(if (filled) color.copy(alpha = .15f) else Color.Transparent, RoundedCornerShape(3.dp)).border(1.dp, color.copy(alpha = .6f), RoundedCornerShape(3.dp)).padding(horizontal = 5.dp, vertical = 1.dp),
    color = color, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 0.8.sp, maxLines = 1, softWrap = false)
@Composable fun Mini(text: String, color: Color = Palette.blue2, enabled: Boolean = true, onClick: () -> Unit) = Text(text, Modifier.clickable(enabled = enabled) { onClick() }
    .background(color.copy(alpha = if (enabled) .12f else .05f), RoundedCornerShape(3.dp)).border(1.dp, color.copy(alpha = if (enabled) .6f else .25f), RoundedCornerShape(3.dp)).padding(horizontal = 7.dp, vertical = 3.dp),
    color = if (enabled) color else color.copy(alpha = .4f), fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 0.8.sp, maxLines = 1, softWrap = false)
@Composable fun Stat(n: String, label: String, color: Color = Palette.text) = Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(horizontal = 6.dp)) {
    Text(n, color = color, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace); Text(label, color = Palette.dim, fontSize = 7.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.sp)
}

@Composable
fun Header(st: WallState, store: Store) {
    val s = st.snap?.summary; val w = st.snap?.watch
    var roleMenu by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().height(50.dp).background(Palette.panel).border(0.5.dp, Palette.line).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Text("TOC", color = Palette.text, fontSize = 18.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
        Text("  COMMON OPERATING PICTURE", color = Palette.dim, fontSize = 8.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
        Spacer(Modifier.width(12.dp))
        s?.let { Chip("POSTURE · ${it.posture.uppercase()}", Palette.posture(it.posture), filled = true) }
        Spacer(Modifier.width(8.dp))
        w?.let { Chip("${it.name.uppercase()} WATCH ${it.battleCaptain ?: "UNASSIGNED"} · ${"%.0f".format(it.remainingH)}h left", if (it.overdue) Palette.red else if (it.inOverlap) Palette.amber else Palette.blue2, filled = true,
            onClick = if (it.battleCaptain == null && st.role == "battle_captain") ({ store.act("taking the watch") { takeWatch("Battle Captain (Android)") } }) else null) }
        Spacer(Modifier.weight(1f))
        val wide = androidx.compose.ui.platform.LocalConfiguration.current.screenWidthDp >= 1100
        s?.let { if (wide) { Stat("${it.totalPeople}", "PERSONNEL"); Stat("${it.traveling}", "TRAVELING", Palette.blue2); Stat("${it.vipsTraveling}", "VIP OUT", Palette.amber) }
                 Stat("${it.realThreats}", "LIVE THR", Palette.red); Stat("${it.confirmedLinks}", "CONFIRMED", Palette.amber); Stat("${it.unaccounted}", "UNACCTD", if (it.unaccounted > 0) Palette.red else Palette.green) }
        Spacer(Modifier.width(8.dp))
        Box { Chip(st.role.uppercase().replace('_', ' '), Palette.text, onClick = { roleMenu = true })
            DropdownMenu(roleMenu, { roleMenu = false }) { ROLES.forEach { r -> DropdownMenuItem({ Text(r, fontSize = 12.sp) }, { store.setRole(r); roleMenu = false }) } } }
    }
}

@Composable
fun ColumnScope.S1Panel(st: WallState, store: Store) {
    val snap = st.snap ?: return
    Label("S1 · PERSONNEL", "Blue Force")
    EstimateLine(snap.estimates.firstOrNull { it.section == "S1" })
    LazyColumn(Modifier.weight(1f)) {
        item { Label("LOCATIONS") }
        items(snap.locations, key = { it.id }) { l ->
            RowItem(selected = (st.selection as? Selection.SiteSel)?.id == l.id, onClick = { store.select(Selection.SiteSel(l.id)) }) {
                Dot(Palette.posture(l.effectivePosture)); Text(l.name, color = Palette.text, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                if (l.threatIdsInArea.isNotEmpty()) Text("△${l.threatIdsInArea.size} ", color = Palette.amber, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                Text("${l.present}/${l.assigned}", color = Palette.dim, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
            }
        }
        item { Label("TRAVELING", "${snap.summary.traveling}") }
        items(snap.people.filter { it.status == "traveling" }, key = { it.id }) { p ->
            RowItem(selected = (st.selection as? Selection.PersonSel)?.id == p.id, onClick = { store.select(Selection.PersonSel(p.id)) }) {
                Dot(if (p.isVip) Palette.amber else Palette.blue2); Text((if (p.isVip) "★ " else "") + p.name, color = Palette.text, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                if (p.positionSource == "checkin" && !p.checkinStale) Chip("✓${"%.0f".format(p.checkinAgeH ?: 0.0)}h", Palette.green)
                p.incidentStatus?.let { Chip(it.uppercase(), Palette.roster(it)) }
            }
        }
        val open = snap.incidents.filter { it.status == "open" }
        if (open.isNotEmpty()) { item { Label("ROLL CALLS", "${open.size} open") }
            items(open, key = { it.id }) { i -> RowItem(selected = (st.selection as? Selection.IncidentSel)?.id == i.id, onClick = { store.select(Selection.IncidentSel(i.id)) }) {
                Dot(if (i.pct == 100) Palette.green else Palette.red); Text(i.title, color = Palette.text, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f)); Text("${i.accounted}/${i.total}", color = if (i.pct == 100) Palette.green else Palette.red, fontSize = 10.sp, fontFamily = FontFamily.Monospace) } } }
    }
}

@Composable
fun ColumnScope.S2Panel(st: WallState, store: Store) {
    val snap = st.snap ?: return
    Label("S2 · INTELLIGENCE", "Sigtoc", action = { Mini("⟳ COLLECT", enabled = st.busy == null) { store.act("collecting") { refreshIntel() } } })
    EstimateLine(snap.estimates.firstOrNull { it.section == "S2" })
    LazyColumn(Modifier.weight(1f)) {
        val pending = snap.warnings.filter { it.status == "suggested" || it.status == "draft" }
        item { Label("WARNINGS", "${pending.size} awaiting release", action = { Mini("RUN RULE", enabled = st.busy == null) { store.act("running the warning rule") { runWarningRule() } } }) }
        items(pending, key = { it.id }) { w ->
            Column(Modifier.padding(horizontal = 10.dp, vertical = 4.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) { Chip(w.severity.uppercase(), if (w.severity == "critical") Palette.red else Palette.amber, filled = true); Chip(w.status.uppercase()); Text(w.shortTitle, color = Palette.text, fontSize = 11.sp, maxLines = 2, overflow = TextOverflow.Ellipsis) }
                Text("${w.suggestedBy} · ${w.subjectType} ${w.subjectName}", color = Palette.dim, fontSize = 9.5.sp, fontFamily = FontFamily.Monospace)
                Row(Modifier.padding(top = 3.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (st.role == "battle_captain") Mini("RELEASE · SMS + CHAT", Palette.red, st.busy == null) { store.act("releasing FLASH") { releaseWarning(w.id) } } else Text("Battle Captain releases", color = Palette.dim, fontSize = 9.5.sp)
                    if (st.role in listOf("battle_captain", "analyst")) Mini("CANCEL", Palette.dim, st.busy == null) { store.act("cancelling warning") { cancelWarning(w.id) } } } } }
        val reqs = st.requirements
        if (reqs.isNotEmpty()) {
            val avg = if (reqs.isEmpty()) 0 else reqs.sumOf { it.coverage.pct } / reqs.size
            item { Label("REQUIREMENTS", "${reqs.size} active · $avg% avg coverage") }
            items(reqs.sortedBy { it.priority }.take(12), key = { it.id }) { r ->
                Column(Modifier.padding(horizontal = 10.dp, vertical = 3.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        Chip("P${r.priority}", if (r.priority == 1) Palette.red else if (r.priority == 2) Palette.amber else Palette.dim, filled = true)
                        Chip(if (r.kind == "directed") "DIRECTED" else r.subjectType.uppercase())
                        Text(r.subjectName, color = Palette.text, fontSize = 10.5.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                        Text("${r.coverage.covered}/${r.coverage.total}", color = if (r.coverage.pct == 100) Palette.green else Palette.amber, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                    }
                    Box(Modifier.fillMaxWidth().height(3.dp).background(Palette.line)) { Box(Modifier.fillMaxWidth(r.coverage.pct / 100f).fillMaxHeight().background(if (r.coverage.pct == 100) Palette.green else Palette.amber)) }
                }
            }
        }
        st.intsums.firstOrNull()?.let { i -> item { Label("INTSUM", i.status.uppercase(), action = { if (i.status != "released" && st.role == "battle_captain") Mini("RELEASE", Palette.green, st.busy == null) { store.act("releasing INTSUM") { releaseIntsum(i.id) } } else if (st.role in listOf("battle_captain", "analyst")) Mini("DRAFT NOW", enabled = st.busy == null) { store.act("drafting INTSUM") { draftIntsum() } } })
            Text(i.headline, Modifier.padding(horizontal = 10.dp), color = if (i.nstr) Palette.green else Palette.text, fontSize = 10.sp, maxLines = 3, overflow = TextOverflow.Ellipsis) } }
        if (st.cases.isNotEmpty()) {
            item { Label("CASES", "${st.cases.count { it.status == "open" }} open") }
            items(st.cases, key = { it.id }) { c -> Row(Modifier.padding(horizontal = 10.dp, vertical = 3.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                Chip(c.kind.uppercase(), if (c.kind == "person") Palette.amber else Palette.dim); Text(c.title, color = Palette.text, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                if (c.pendingReview > 0) Chip("${c.pendingReview} TO REVIEW", Palette.amber) else Chip(c.status.uppercase(), if (c.status == "open") Palette.green else Palette.dim) } } }
        item { Label("THREATS", "${snap.threats.size} · ${snap.summary.realThreats} live") }
        items(snap.threats, key = { it.id }) { t ->
            RowItem(selected = (st.selection as? Selection.ThreatSel)?.id == t.id, onClick = { store.select(Selection.ThreatSel(t.id)) }) {
                Chip(t.severity.take(3).uppercase(), Palette.severity(t.severity), filled = true)
                Text(t.title, color = Palette.text, fontSize = 10.5.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                if (!t.synthetic) Chip("LIVE", Palette.green)
                if (t.confirmedLinks.isNotEmpty()) Text("▲${t.confirmedLinks.size}", color = Palette.amber, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
            }
        }
        item { Label("ASSESSMENTS", "${snap.assessments.size}") }
        items(snap.assessments, key = { it.id }) { a ->
            Column(Modifier.padding(horizontal = 10.dp, vertical = 3.dp).border(0.5.dp, Palette.line, RoundedCornerShape(4.dp)).padding(6.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) { Text(a.id, color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace); Text(a.title, color = Palette.text, fontSize = 10.5.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f)); Chip(a.status.uppercase(), if (a.status == "approved") Palette.green else if (a.status == "review") Palette.amber else Palette.dim) }
                Text("${a.likelihood} (${a.band}) · ${a.confidence} confidence", color = Palette.amber, fontSize = 9.5.sp, fontFamily = FontFamily.Monospace)
                Text(a.bluf, color = Palette.text.copy(alpha = .85f), fontSize = 10.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                if (a.status == "review" && st.role in listOf("battle_captain", "analyst")) Row(Modifier.padding(top = 4.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Mini("APPROVE", Palette.green, st.busy == null) { store.act("approving") { setAssessmentStatus(a.id, "approved") } } }
            }
        }
    }
}

@Composable
fun ColumnScope.S3Panel(st: WallState, store: Store) {
    val snap = st.snap ?: return
    Label("S3 · OPERATIONS", "Events · Travel")
    androidx.compose.foundation.lazy.LazyRow(Modifier.weight(1f), contentPadding = PaddingValues(horizontal = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        items(snap.events, key = { it.id }) { e -> Card(Palette.purple, selected = (st.selection as? Selection.EventSel)?.id == e.id, onClick = { store.select(Selection.EventSel(e.id)) }) {
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) { Chip(if (e.status == "active") "LIVE" else "T-${e.daysUntil}d", Palette.purple, filled = true); Text("★ ${e.name}", color = Palette.text, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                e.operation?.let { Chip("OP ${it.tasksDone}/${it.tasksTotal}", Palette.purple, onClick = { store.openOperation(it.id) }) }
                e.coverage?.let { Chip("COVER ${it.assigned}/${it.required}", if (it.gap > 0) Palette.red else Palette.green) } }
            Text(e.venueName, color = Palette.text.copy(alpha = .8f), fontSize = 10.sp, fontFamily = FontFamily.Monospace, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${e.attendeeCount} attending · ${e.vipCount} VIP · ${e.tripsGenerated} trips", color = Palette.dim, fontSize = 9.5.sp) } }
        items(snap.trips, key = { it.id }) { t -> Card(if (t.status == "active") Palette.blue else Palette.line, selected = (st.selection as? Selection.PersonSel)?.id == t.personId, onClick = { store.select(Selection.PersonSel(t.personId)) }) {
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) { Chip(t.status.uppercase(), if (t.status == "active") Palette.blue2 else Palette.dim, filled = true); Text((if (t.isVip) "★ " else "") + t.personName, color = Palette.text, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                t.operation?.let { Chip("OP ${it.tasksDone}/${it.tasksTotal}", Palette.purple, onClick = { store.openOperation(it.id) }) } }
            Text("${t.originName.split(" ").first()} → ${t.destName}", color = Palette.text.copy(alpha = .8f), fontSize = 10.sp, fontFamily = FontFamily.Monospace, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(t.purpose, color = Palette.dim, fontSize = 9.5.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) } }
    }
}

@Composable fun Card(color: Color, selected: Boolean, onClick: () -> Unit, content: @Composable ColumnScope.() -> Unit) =
    Column(Modifier.width(210.dp).fillMaxHeight().padding(vertical = 4.dp).background(if (selected) color.copy(alpha = .12f) else Palette.panel2, RoundedCornerShape(5.dp)).border(1.dp, color.copy(alpha = .5f), RoundedCornerShape(5.dp)).clickable { onClick() }.padding(8.dp), verticalArrangement = Arrangement.spacedBy(2.dp), content = content)

@Composable
fun ColumnScope.LogPanel(st: WallState) {
    Label("LOG · BATTLE LOG", "hash-chained")
    LazyColumn(Modifier.weight(1f)) { items(st.snap?.log ?: emptyList(), key = { it.id }) { e ->
        Row(Modifier.padding(horizontal = 8.dp, vertical = 1.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(e.type.removePrefix("cop.").removePrefix("s2.").uppercase().take(14), color = if (e.actorType == "human") Palette.blue2 else Palette.amber, fontSize = 8.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.width(78.dp))
            Text(e.summary, color = Palette.text.copy(alpha = .85f), fontSize = 9.5.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) } } }
}

@Composable fun EstimateLine(e: Estimate?) = Text(buildString { append(e?.section ?: "—"); append(" assesses: "); append(e?.assessment?.ifBlank { null } ?: "no assessment on record") },
    Modifier.padding(horizontal = 10.dp, vertical = 2.dp), color = if (e?.assessment.isNullOrBlank()) Palette.dim else Palette.text, fontSize = 9.5.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
@Composable fun Dot(color: Color) = Box(Modifier.size(7.dp).background(color, RoundedCornerShape(50)))
@Composable fun RowItem(selected: Boolean, onClick: () -> Unit, content: @Composable RowScope.() -> Unit) =
    Row(Modifier.fillMaxWidth().background(if (selected) Palette.blue.copy(alpha = .12f) else Color.Transparent).clickable { onClick() }.padding(horizontal = 10.dp, vertical = 5.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp), content = content)


/** §5.6 — released warnings under the header, with the reader's acknowledgement. */
@Composable
fun FlashStrip(st: WallState, store: Store) {
    val live = st.snap?.warnings?.filter { it.status == "released" } ?: return
    if (live.isEmpty()) return
    Column(Modifier.fillMaxWidth().background(Palette.red.copy(alpha = .14f)).border(0.5.dp, Palette.red.copy(alpha = .6f)).padding(horizontal = 12.dp, vertical = 4.dp)) {
        live.forEach { w ->
            Row(Modifier.fillMaxWidth().clickable { store.select(when (w.subjectType) { "location" -> Selection.SiteSel(w.subjectId); "person" -> Selection.PersonSel(w.subjectId); else -> Selection.EventSel(w.subjectId) }) }, horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("FLASH", Modifier.background(Palette.red, RoundedCornerShape(3.dp)).padding(horizontal = 6.dp, vertical = 1.dp), color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, fontFamily = FontFamily.Monospace, letterSpacing = 2.sp)
                Text(w.shortTitle, color = Color(0xFFFECACA), fontSize = 12.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                Text("${w.releasedBy ?: ""} · ${w.ageMin ?: 0}m", color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
                Mini("ACK", Palette.green, st.busy == null) { store.act("acknowledging") { ackProduct("warning", w.id) } }
            }
        }
    }
}

/** §5.10 #3 — the operation against its subject: tasks by section and S4 asks; tap a task to advance it. */
@Composable
fun OperationSheet(op: Operation, st: WallState, store: Store, onClose: () -> Unit) {
    Column(Modifier.padding(10.dp).width(360.dp).background(Palette.panel.copy(alpha = .97f), RoundedCornerShape(6.dp)).border(1.dp, Palette.purple.copy(alpha = .5f), RoundedCornerShape(6.dp)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { Text("S3 OPERATION · ${op.status.uppercase()}" + (op.fromProductId?.let { " · from $it" } ?: ""), color = Palette.dim, fontSize = 8.5.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.2.sp); Spacer(Modifier.weight(1f)); Text("×", Modifier.clickable { onClose() }, color = Palette.dim, fontSize = 18.sp) }
        Text(op.title, color = Palette.text, fontSize = 15.sp, fontWeight = FontWeight.SemiBold); Text(op.subjectName, color = Palette.dim, fontSize = 11.sp)
        Text("${op.tasksDone}/${op.tasksTotal} tasks", color = Palette.text, fontSize = 11.sp)
        Box(Modifier.fillMaxWidth().height(5.dp).background(Palette.line, RoundedCornerShape(3.dp))) { Box(Modifier.fillMaxWidth(op.pct / 100f).fillMaxHeight().background(if (op.pct == 100) Palette.green else Palette.purple, RoundedCornerShape(3.dp))) }
        if (op.notes.isNotBlank()) Text(op.notes, color = Palette.text.copy(alpha = .85f), fontSize = 11.sp)
        Label("TASKS", "tap to advance")
        op.tasks.forEach { t -> Row(Modifier.fillMaxWidth().clickable(enabled = st.busy == null) { store.act("updating task") { updateTask(op.id, t.id, when (t.status) { "todo" -> "doing"; "doing" -> "done"; else -> "todo" }); store.openOperation(op.id) } }.padding(vertical = 3.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Chip(t.status.uppercase(), when (t.status) { "done" -> Palette.green; "doing" -> Palette.amber; "blocked" -> Palette.red; else -> Palette.dim }, filled = true); Chip(t.section)
            Text(t.title, color = if (t.status == "done") Palette.dim else Palette.text, fontSize = 11.sp, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f)); Text(t.owner, color = Palette.dim, fontSize = 9.sp) } }
        if (op.resources.isNotEmpty()) { Label("S4 · RESOURCES"); op.resources.forEach { r -> Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) { Chip(r.status.uppercase(), when (r.status) { "issued" -> Palette.green; "approved" -> Palette.amber; "denied" -> Palette.red; else -> Palette.dim }); Text("${r.qty} × ${r.item}", color = Palette.text, fontSize = 11.sp) } } }
    }
}
