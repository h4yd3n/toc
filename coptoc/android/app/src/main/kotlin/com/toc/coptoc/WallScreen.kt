package com.toc.coptoc

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import kotlinx.coroutines.launch
import androidx.compose.animation.animateContentSize
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.Icons
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

/** Entry: a phone gets the tabbed layout (map, S1, S2, S3) like iOS; a wide screen (tablet) gets the wall. */
@Composable
fun WallScreen(store: Store) {
    val st by store.state.collectAsStateWithLifecycle()
    if (androidx.compose.ui.platform.LocalConfiguration.current.screenWidthDp >= 840) TabletWall(st, store) else PhoneScreen(st, store)
}

/** The wall on a tablet: header strip, map in the middle, S1 left, S2 right, S3 + log below. */
@Composable
fun TabletWall(st: WallState, store: Store) {
    val snap = st.snap
    Column(Modifier.fillMaxSize().background(Palette.bg).safeDrawingPadding()) {  // stay clear of the cutout and the system bars on a real phone
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
@Composable fun Label(text: String, hint: String? = null, action: (@Composable () -> Unit)? = null) = Row(Modifier.fillMaxWidth().padding(start = 14.dp, end = 14.dp, top = 16.dp, bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
    Text(text, color = Palette.dim, fontSize = 10.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.8.sp)
    if (!Ui.lean || (hint != null && hint.any { it.isDigit() })) hint?.let { Text("  $it", color = Palette.dim.copy(alpha = .7f), fontSize = 9.sp, fontFamily = FontFamily.Monospace) }  // lean keeps counts, drops words
    Spacer(Modifier.weight(1f)); action?.invoke()
}
@Composable fun Chip(text: String, color: Color = Palette.dim, filled: Boolean = false, onClick: (() -> Unit)? = null) = Text(text, Modifier.let { m -> if (onClick != null) m.clickable { onClick() } else m }
    .background(if (filled) color.copy(alpha = .15f) else Color.Transparent, RoundedCornerShape(3.dp)).border(1.dp, color.copy(alpha = .6f), RoundedCornerShape(3.dp)).padding(horizontal = 5.dp, vertical = 1.dp),
    color = color, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 0.8.sp, maxLines = 1, softWrap = false)
@Composable fun Mini(text: String, color: Color = Palette.blue2, enabled: Boolean = true, onClick: () -> Unit) = Text(text, Modifier.clickable(enabled = enabled) { onClick() }
    .background(color.copy(alpha = if (enabled) .16f else .06f), RoundedCornerShape(6.dp)).padding(horizontal = 9.dp, vertical = 5.dp),
    color = if (enabled) color else color.copy(alpha = .4f), fontSize = 9.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, letterSpacing = 0.8.sp, maxLines = 1, softWrap = false)
@Composable fun Stat(n: String, label: String, color: Color = Palette.text) = Column(horizontalAlignment = Alignment.Start, verticalArrangement = Arrangement.spacedBy(2.dp)) {
    Text(n, color = color, fontSize = 18.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace); Text(label, color = Palette.dim, fontSize = 8.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.2.sp)
}

@Composable
fun Header(st: WallState, store: Store) {
    val s = st.snap?.summary; val w = st.snap?.watch
    var roleMenu by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().height(50.dp).background(Palette.panel).border(0.5.dp, Palette.line).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Text("TOC", color = Palette.text, fontSize = 18.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
        Text("  COMMON OPERATING PICTURE", color = Palette.dim, fontSize = 8.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
        Spacer(Modifier.width(12.dp))
        var defconMenu by remember { mutableStateOf(false) }
        s?.let { Box {
            if (Ui.posture) Text("DEFCON ${it.defcon}", Modifier.clickable { defconMenu = true }.border(2.dp, Palette.posture(it.posture).copy(alpha = .8f), RoundedCornerShape(4.dp)).padding(horizontal = 12.dp, vertical = 5.dp), color = Palette.posture(it.posture), fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, fontFamily = FontFamily.Monospace, letterSpacing = 2.sp)
            else Chip("DEFCON ${it.defcon}", Palette.posture(it.posture), filled = true, onClick = { defconMenu = true })
            DropdownMenu(defconMenu, { defconMenu = false }) {
                it.defconLevels.sortedByDescending { l -> l.defcon }.forEach { l -> DropdownMenuItem({ Column { Text((if (l.defcon == it.defcon) "● " else "○ ") + "DEFCON ${l.defcon} · ${l.posture.uppercase()}" + (if (l.sites > 0) "  (${l.sites})" else ""), color = Palette.posture(l.posture), fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = if (l.defcon == it.defcon) FontWeight.Bold else FontWeight.Normal); Text(l.meaning, color = Palette.dim, fontSize = 10.sp) } }, { defconMenu = false }) }
                DropdownMenuItem({ Text("The wall reads the worst site. Set a site's level from its card.", color = Palette.dim, fontSize = 10.sp) }, { defconMenu = false }) } } }
        Spacer(Modifier.width(8.dp))
        w?.let { Chip("${it.name.uppercase()} WATCH ${it.battleCaptain ?: "UNASSIGNED"} · " + (if (it.overdue) "OVERDUE ${"%.0f".format(-it.remainingH)}h" else "${"%.0f".format(it.remainingH)}h left"), if (it.overdue) Palette.red else if (it.inOverlap) Palette.amber else Palette.blue2, filled = true,
            onClick = if (it.battleCaptain == null && st.role == "battle_captain") ({ store.act("taking the watch") { takeWatch("Battle Captain (Android)") } }) else null) }
        Spacer(Modifier.weight(1f))
        val wide = androidx.compose.ui.platform.LocalConfiguration.current.screenWidthDp >= 1100
        s?.let { if (wide || !Ui.posture) { Stat("${it.totalPeople}", "PERSONNEL"); Stat("${it.traveling}", "TRAVELING", Palette.blue2); Stat("${it.vipsTraveling}", "VIP OUT", Palette.amber) }
                 Stat("${it.realThreats}", "LIVE THR", Palette.red); Stat("${it.confirmedLinks}", "CONFIRMED", Palette.amber)
                 if (it.unaccounted > 0 || !Ui.posture) Stat("${it.unaccounted}", "UNACCTD", if (it.unaccounted > 0) Palette.red else Palette.green)
                 if (it.flash > 0) Stat("${it.flash}", "FLASH", Palette.red)
                 if (!Ui.posture) { Stat("${it.present}", "PRESENT"); Stat("${it.securityOnShift}", "SEC ON", Palette.green); Stat("${it.openPirs}", "PIRS", Palette.amber) } }
        Spacer(Modifier.width(8.dp))
        var dispMenu by remember { mutableStateOf(false) }
        val ctx = androidx.compose.ui.platform.LocalContext.current
        Box { Chip("DISPLAY ▾", Palette.dim, onClick = { dispMenu = true })
            DropdownMenu(dispMenu, { dispMenu = false }) {
                DropdownMenuItem({ Text((if (Ui.lean) "✓ " else "   ") + "Lean labels", fontSize = 12.sp) }, { Ui.lean = !Ui.lean; Ui.save(ctx) })
                DropdownMenuItem({ Text((if (Ui.posture) "✓ " else "   ") + "Posture header", fontSize = 12.sp) }, { Ui.posture = !Ui.posture; Ui.save(ctx) }) } }
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
    LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(bottom = 96.dp)) {  // room for the floating tab bar
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
    LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(bottom = 96.dp)) {
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

@Composable fun EstimateLine(e: Estimate?) { if (Ui.lean && e?.assessment.isNullOrBlank()) return; Text(buildString { append(e?.section ?: "—"); append(" assesses: "); append(e?.assessment?.ifBlank { null } ?: "no assessment on record") },
    Modifier.padding(horizontal = 10.dp, vertical = 2.dp), color = if (e?.assessment.isNullOrBlank()) Palette.dim else Palette.text, fontSize = 9.5.sp, maxLines = 2, overflow = TextOverflow.Ellipsis) }
@Composable fun Dot(color: Color) = Box(Modifier.size(7.dp).background(color, RoundedCornerShape(50)))
@Composable fun RowItem(selected: Boolean, onClick: () -> Unit, content: @Composable RowScope.() -> Unit) = Column {
    Row(Modifier.fillMaxWidth().background(if (selected) Palette.blue.copy(alpha = .12f) else Color.Transparent).clickable { onClick() }.padding(horizontal = 14.dp, vertical = 9.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), content = content)
    HorizontalDivider(Modifier.padding(start = 14.dp), thickness = 0.5.dp, color = Palette.line)
}


/** §5.6 — released warnings under the header, with the reader's acknowledgement. */
@Composable
fun FlashStrip(st: WallState, store: Store) {
    val live = st.snap?.warnings?.filter { it.status == "released" } ?: return
    if (live.isEmpty()) return
    Column(Modifier.fillMaxWidth().background(Palette.red.copy(alpha = .14f)).padding(horizontal = 12.dp, vertical = 6.dp)) {
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
    Column(Modifier.padding(10.dp).widthIn(max = 420.dp).fillMaxWidth().background(Palette.panel.copy(alpha = .97f), RoundedCornerShape(6.dp)).border(1.dp, Palette.purple.copy(alpha = .5f), RoundedCornerShape(6.dp)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
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


// ---------------------------------------------------------------- the phone: four tabs, like iOS

enum class Tab(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) { COP("COP", Icons.Filled.Place), S1("S1", Icons.Filled.Person), S2("S2", Icons.Filled.Search), S3("S3", Icons.Filled.DateRange) }

@Composable
fun PhoneScreen(st: WallState, store: Store) {
    var tab by remember { mutableStateOf(Tab.COP) }
    val snap = st.snap
    Box(Modifier.fillMaxSize().background(Palette.bg)) {
        Column(Modifier.fillMaxSize()) {
            PhoneHeader(st, store)
            FlashStrip(st, store)
            Box(Modifier.weight(1f).fillMaxWidth()) {
                when (tab) {
                    Tab.COP -> {
                        WallMap(snap, st.restricted, onSelect = store::select, modifier = Modifier.fillMaxSize())
                        if (snap == null && st.error == null) Text("LOADING PICTURE…", Modifier.align(Alignment.Center), color = Palette.dim, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                    }
                    Tab.S1 -> Column(Modifier.fillMaxSize()) { S1Panel(st, store) }
                    Tab.S2 -> Column(Modifier.fillMaxSize()) { S2Panel(st, store) }
                    Tab.S3 -> Column(Modifier.fillMaxSize()) { S3Phone(st, store) }
                }
                st.selection?.let { sel -> DetailSheet(sel, st, store, onClose = { store.select(null) }) }
                st.operation?.let { op -> OperationSheet(op, st, store, onClose = { store.openOperation(null) }) }
                st.busy?.let { Text(it.uppercase() + "…", Modifier.align(Alignment.BottomCenter).padding(bottom = 96.dp).background(Palette.panel, RoundedCornerShape(6.dp)).padding(8.dp), color = Palette.blue2, fontSize = 10.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp) }
                st.error?.let { Text(it, Modifier.align(Alignment.BottomCenter).padding(bottom = 96.dp).padding(horizontal = 12.dp).background(Palette.red.copy(alpha = .9f), RoundedCornerShape(6.dp)).padding(8.dp).clickable { store.dismissError() }, color = Color.White, fontSize = 11.sp, fontFamily = FontFamily.Monospace, maxLines = 2) }
            }
        }
        // the tab bar: a floating capsule over the content, like the iOS tab bar
        Row(Modifier.align(Alignment.BottomCenter).navigationBarsPadding().padding(horizontal = 24.dp, vertical = 10.dp).fillMaxWidth()
            .background(Palette.panel.copy(alpha = .94f), RoundedCornerShape(50)).border(0.5.dp, Palette.line, RoundedCornerShape(50)).padding(4.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
            Tab.values().forEach { t ->
                val on = t == tab
                val badge = when (t) { Tab.S1 -> snap?.incidents?.count { it.status == "open" } ?: 0; Tab.S2 -> snap?.summary?.warningsPending ?: 0; else -> 0 }
                Column(Modifier.weight(1f).clip(RoundedCornerShape(50)).background(if (on) Palette.panel2 else Color.Transparent).clickable { tab = t; store.select(null) }.padding(vertical = 7.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Box { Icon(t.icon, contentDescription = t.label, tint = if (on) Palette.blue2 else Palette.dim, modifier = Modifier.size(22.dp))
                        if (badge > 0) Text("$badge", Modifier.offset(x = 14.dp, y = (-6).dp).background(Palette.red, RoundedCornerShape(8.dp)).padding(horizontal = 4.dp), color = Color.White, fontSize = 9.sp) }
                    Text(t.label, color = if (on) Palette.blue2 else Palette.dim, fontSize = 10.sp, fontWeight = if (on) FontWeight.SemiBold else FontWeight.Normal)
                }
            }
        }
    }
}

/** The iOS posture bar, on Android: TOC · DEFCON · clock; the watch line; the counters. Drawn under the status bar. */
@Composable
fun PhoneHeader(st: WallState, store: Store) {
    val s = st.snap?.summary; val w = st.snap?.watch
    var roleMenu by remember { mutableStateOf(false) }
    var defconMenu by remember { mutableStateOf(false) }
    var dispMenu by remember { mutableStateOf(false) }
    val ctx = androidx.compose.ui.platform.LocalContext.current
    var now by remember { mutableStateOf(System.currentTimeMillis()) }
    androidx.compose.runtime.LaunchedEffect(Unit) { while (true) { now = System.currentTimeMillis(); kotlinx.coroutines.delay(1000) } }
    val clock = java.text.SimpleDateFormat("HH:mm:ss'Z'", java.util.Locale.US).apply { timeZone = java.util.TimeZone.getTimeZone("UTC") }.format(java.util.Date(now))
    Column(Modifier.fillMaxWidth().background(Palette.panel).statusBarsPadding().padding(start = 14.dp, end = 14.dp, top = 6.dp, bottom = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("TOC", color = Palette.text, fontSize = 18.sp, fontWeight = FontWeight.Black, fontFamily = FontFamily.Monospace, letterSpacing = 3.sp)
            s?.let { Box {
                if (Ui.posture) Text("DEFCON ${it.defcon}", Modifier.clickable { defconMenu = true }.border(2.dp, Palette.posture(it.posture), RoundedCornerShape(4.dp)).padding(horizontal = 12.dp, vertical = 6.dp), color = Palette.posture(it.posture), fontSize = 14.sp, fontWeight = FontWeight.Black, fontFamily = FontFamily.Monospace, letterSpacing = 2.5.sp)
                else Chip("DEFCON ${it.defcon}", Palette.posture(it.posture), onClick = { defconMenu = true })
                DropdownMenu(defconMenu, { defconMenu = false }) { it.defconLevels.sortedByDescending { l -> l.defcon }.forEach { l -> DropdownMenuItem({ Column { Text((if (l.defcon == it.defcon) "● " else "○ ") + "DEFCON ${l.defcon} · ${l.posture.uppercase()}", color = Palette.posture(l.posture), fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = if (l.defcon == it.defcon) FontWeight.Bold else FontWeight.Normal); Text(l.meaning, color = Palette.dim, fontSize = 10.sp) } }, { defconMenu = false }) } } } }
            Spacer(Modifier.weight(1f))
            Box { Text("DISPLAY ▾", Modifier.clickable { dispMenu = true }.border(1.dp, Palette.line, RoundedCornerShape(3.dp)).padding(horizontal = 6.dp, vertical = 4.dp), color = Palette.dim, fontSize = 9.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
                DropdownMenu(dispMenu, { dispMenu = false }) {
                    DropdownMenuItem({ Text((if (Ui.lean) "✓ " else "   ") + "Lean labels", fontSize = 12.sp) }, { Ui.lean = !Ui.lean; Ui.save(ctx) })
                    DropdownMenuItem({ Text((if (Ui.posture) "✓ " else "   ") + "Posture header", fontSize = 12.sp) }, { Ui.posture = !Ui.posture; Ui.save(ctx) })
                    HorizontalDivider()
                    ROLES.forEach { r -> DropdownMenuItem({ Text((if (st.role == r) "✓ " else "   ") + "role: " + r.replace('_', ' '), fontSize = 12.sp) }, { store.setRole(r); dispMenu = false }) } } }
            Text(clock, color = Palette.dim, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
        }
        w?.let { Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("${it.name.uppercase()} WATCH", color = Palette.blue2, fontSize = 10.sp, fontWeight = FontWeight.Black, fontFamily = FontFamily.Monospace)
            Text(it.battleCaptain?.let { bc -> "BC $bc" } ?: "UNASSIGNED", color = Palette.text, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
            Spacer(Modifier.weight(1f))
            Text(if (it.status == "pending_ack") "HANDOVER PENDING" else if (it.overdue) "OVERDUE" else "→ ${it.nextWatch.split(" ").first()} in ${"%.0f".format(it.remainingH)}h", color = if (it.status == "pending_ack" || it.overdue) Palette.red else if (it.inOverlap) Palette.amber else Palette.dim, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
            if (it.battleCaptain == null && st.role == "battle_captain") Mini("TAKE", enabled = st.busy == null) { store.act("taking the watch") { takeWatch("Battle Captain (Android)") } } } }
        s?.let { Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Stat("${it.totalPeople}", "PERSONNEL"); Stat("${it.traveling}", "TRAVELING", Palette.blue2); Stat("${it.vipsTraveling}", "VIP OUT", Palette.amber)
            Stat("${it.realThreats}", "THREATS", Palette.red); Stat("${it.confirmedLinks}", "CONFIRMED", Palette.red)
            if (it.flash > 0) Stat("${it.flash}", "FLASH", Palette.red); if (it.unaccounted > 0) Stat("${it.unaccounted}", "UNACCOUNTED", Palette.red)
            if (!Ui.posture) { Stat("${it.present}", "PRESENT"); Stat("${it.checkedInFresh}", "CHECKED IN", Palette.green); Stat("${it.securityOnShift}", "SEC ON SHIFT", Palette.green); Stat("${it.openPirs}", "OPEN PIRS", Palette.amber); Stat("${it.upcomingEvents}", "EVENTS") } } }
    }
    HorizontalDivider(thickness = 0.5.dp, color = Palette.line)
}

/** S3 on the phone: an agenda by day — events and standalone trips under their date, a gap line when days go by
 * with nothing — and the battle log beneath. */
sealed class AgendaRow { data class Day(val day: java.time.LocalDate, val daysAway: Long) : AgendaRow(); data class Gap(val days: Long) : AgendaRow(); data class Ev(val e: CopEvent) : AgendaRow(); data class Tr(val t: Trip) : AgendaRow() }

fun agendaRows(snap: Snapshot): List<AgendaRow> {
    val today = java.time.LocalDate.now()
    fun dayOf(iso: String) = runCatching { java.time.Instant.parse(iso).atZone(java.time.ZoneId.systemDefault()).toLocalDate() }.getOrDefault(today)
    val byDay = sortedMapOf<java.time.LocalDate, MutableList<AgendaRow>>()
    snap.events.forEach { e -> byDay.getOrPut(dayOf(e.startAt)) { mutableListOf() }.add(AgendaRow.Ev(e)) }
    snap.trips.filter { it.eventId == null }.forEach { t -> byDay.getOrPut(maxOf(dayOf(t.departAt), today)) { mutableListOf() }.add(AgendaRow.Tr(t)) }
    val out = mutableListOf<AgendaRow>(); var prev: java.time.LocalDate? = null
    byDay.forEach { (d, rows) ->
        prev?.let { p -> val gap = java.time.temporal.ChronoUnit.DAYS.between(p, d); if (gap > 1) out.add(AgendaRow.Gap(gap - 1)) }
        out.add(AgendaRow.Day(d, java.time.temporal.ChronoUnit.DAYS.between(today, d))); out.addAll(rows); prev = d
    }
    return out
}

@Composable
fun ColumnScope.S3Phone(st: WallState, store: Store) {
    val snap = st.snap ?: return
    val today = java.time.LocalDate.now()
    val rows = remember(snap) { agendaRows(snap) }
    val listState = androidx.compose.foundation.lazy.rememberLazyListState()
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    var expanded by remember { mutableStateOf(false) }
    var month by remember { mutableStateOf<java.time.LocalDate?>(null) }
    // the day at the top of the list is the cursor the strip follows
    val cursor by remember { androidx.compose.runtime.derivedStateOf { val i = listState.firstVisibleItemIndex - 1; rows.take(maxOf(i + 1, 0)).asReversed().firstNotNullOfOrNull { r -> (r as? AgendaRow.Day)?.day ?: dayOfRow(r) } ?: today } }
    androidx.compose.runtime.LaunchedEffect(listState.firstVisibleItemIndex) { if (listState.firstVisibleItemIndex > 1) expanded = false }
    val markedDays = remember(rows) { rows.filterIsInstance<AgendaRow.Day>().map { it.day }.toSet() }
    val eventDays = remember(snap) { snap.events.flatMap { e -> val a = runCatching { java.time.Instant.parse(e.startAt).atZone(java.time.ZoneId.systemDefault()).toLocalDate() }.getOrNull(); val b = runCatching { java.time.Instant.parse(e.endAt).atZone(java.time.ZoneId.systemDefault()).toLocalDate() }.getOrNull()
        if (a == null || b == null) emptyList() else generateSequence(a) { it.plusDays(1) }.takeWhile { !it.isAfter(b) }.toList() }.toSet() }
    CalendarStrip(cursor = cursor, today = today, marked = markedDays, eventDays = eventDays, expanded = expanded, month = month,
        onToggle = { expanded = !expanded; month = null }, onMonth = { m -> month = m },
        onPick = { d -> val idx = rows.indexOfFirst { r -> r is AgendaRow.Day && !r.day.isBefore(d) }; if (idx >= 0) { expanded = false; scope.launch { listState.animateScrollToItem(idx + 1) } } })
    LazyColumn(Modifier.weight(1f), state = listState, contentPadding = PaddingValues(bottom = 96.dp)) {
        item { Label("S3 · OPERATIONS", "Agenda"); EstimateLine(snap.estimates.firstOrNull { it.section == "S3" }) }
        items(rows.size, key = { i -> when (val r = rows[i]) { is AgendaRow.Day -> "d${r.day}"; is AgendaRow.Gap -> "g$i"; is AgendaRow.Ev -> r.e.id; is AgendaRow.Tr -> r.t.id } }) { i ->
            when (val r = rows[i]) {
                is AgendaRow.Day -> Row(Modifier.padding(start = 14.dp, end = 14.dp, top = 14.dp, bottom = 4.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(r.day.format(java.time.format.DateTimeFormatter.ofPattern("EEE d MMM", java.util.Locale.US)).uppercase(), color = if (r.daysAway == 0L) Palette.red else Palette.text, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
                    Text(when { r.daysAway == 0L -> "TODAY"; r.daysAway == 1L -> "TOMORROW"; r.daysAway < 0 -> "STARTED"; else -> "IN ${r.daysAway} DAYS" }, color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace) }
                is AgendaRow.Gap -> Text("— nothing for ${r.days} day${if (r.days == 1L) "" else "s"} —", Modifier.fillMaxWidth().padding(vertical = 10.dp), color = Palette.dim, fontSize = 10.sp, fontFamily = FontFamily.Monospace, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                is AgendaRow.Ev -> { val e = r.e; RowItem(selected = (st.selection as? Selection.EventSel)?.id == e.id, onClick = { store.select(Selection.EventSel(e.id)) }) { Column(Modifier.weight(1f)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) { Chip(if (e.status == "active") "LIVE" else "T-${e.daysUntil}d", Palette.purple, filled = true); Text("★ ${e.name}", color = Palette.text, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                        e.operation?.let { Chip("OP ${it.tasksDone}/${it.tasksTotal}", Palette.purple, onClick = { store.openOperation(it.id) }) }; e.coverage?.let { Chip("COVER ${it.assigned}/${it.required}", if (it.gap > 0) Palette.red else Palette.green) } }
                    Text(e.venueName, color = Palette.text.copy(alpha = .8f), fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text("${e.startAt.take(10)} → ${e.endAt.take(10)} · ${e.attendeeCount} attending · ${e.vipCount} VIP · ${e.tripsGenerated} trips", color = Palette.dim, fontSize = 10.sp) } } }
                is AgendaRow.Tr -> { val t = r.t; RowItem(selected = (st.selection as? Selection.PersonSel)?.id == t.personId, onClick = { store.select(Selection.PersonSel(t.personId)) }) { Column(Modifier.weight(1f)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) { Chip(t.status.uppercase(), if (t.status == "active") Palette.blue2 else Palette.dim, filled = true); Text((if (t.isVip) "★ " else "") + t.personName, color = Palette.text, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f)); t.operation?.let { Chip("OP ${it.tasksDone}/${it.tasksTotal}", Palette.purple, onClick = { store.openOperation(it.id) }) } }
                    Text("${t.originName.split(" ").first()} → ${t.destName.split(",").first()} · ret ${t.returnAt.take(10)}", color = Palette.text.copy(alpha = .8f), fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    Text(t.purpose, color = Palette.dim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) } } }
            }
        }
        if (rows.isEmpty()) item { Text("Nothing planned.", Modifier.padding(14.dp), color = Palette.dim, fontSize = 12.sp) }
        item { Label("LOG · BATTLE LOG", "hash-chained") }
        items(snap.log, key = { it.id }) { e -> Row(Modifier.padding(horizontal = 14.dp, vertical = 3.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(e.type.removePrefix("cop.").removePrefix("s2.").uppercase().take(14), color = if (e.actorType == "human") Palette.blue2 else Palette.amber, fontSize = 8.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.width(78.dp))
            Text(e.summary, color = Palette.text.copy(alpha = .85f), fontSize = 10.sp, maxLines = 2, overflow = TextOverflow.Ellipsis) } }
    }
}

/** The calendar strip: a continuous ribbon of days that keeps the agenda's day in the middle; tap the month name and it unfolds into the month. */
@Composable
fun CalendarStrip(cursor: java.time.LocalDate, today: java.time.LocalDate, marked: Set<java.time.LocalDate>, eventDays: Set<java.time.LocalDate>, expanded: Boolean, month: java.time.LocalDate?,
                  onToggle: () -> Unit, onMonth: (java.time.LocalDate) -> Unit, onPick: (java.time.LocalDate) -> Unit) {
    val shown = (if (expanded) month else null) ?: cursor.withDayOfMonth(1)
    // two months back to four past the last marked day — enough tape in both directions
    val ribbon = remember(today, marked) { val last = maxOf(marked.maxOrNull() ?: today, today); val start = today.minusDays(60); val n = java.time.temporal.ChronoUnit.DAYS.between(start, last.plusDays(120)).toInt(); List(n) { start.plusDays(it.toLong()) } }
    val cursorIdx = ribbon.indexOf(cursor).coerceAtLeast(0)
    val rowState = androidx.compose.foundation.lazy.rememberLazyListState(initialFirstVisibleItemIndex = (cursorIdx - 3).coerceAtLeast(0))
    androidx.compose.runtime.LaunchedEffect(cursor, expanded) { if (!expanded) rowState.animateScrollToItem((cursorIdx - 3).coerceAtLeast(0)) }
    Column(Modifier.fillMaxWidth().background(Palette.panel).padding(horizontal = 10.dp, vertical = 6.dp).animateContentSize(), verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(Modifier.padding(horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(shown.format(java.time.format.DateTimeFormatter.ofPattern("MMMM yyyy", java.util.Locale.US)).uppercase() + (if (expanded) "  ▴" else "  ▾"), Modifier.clickable { onToggle() }, color = Palette.text, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, letterSpacing = 1.8.sp)
            Spacer(Modifier.weight(1f))
            if (expanded) { Text("‹", Modifier.clickable { onMonth(shown.minusMonths(1)) }.padding(horizontal = 8.dp), color = Palette.dim, fontSize = 16.sp); Text("›", Modifier.clickable { onMonth(shown.plusMonths(1)) }.padding(horizontal = 8.dp), color = Palette.dim, fontSize = 16.sp) }
            else Text(if (cursor == today) "TODAY" else "${java.time.temporal.ChronoUnit.DAYS.between(today, cursor)} DAYS OUT", color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
        }
        @Composable fun cell(d: java.time.LocalDate, weekday: Boolean) {
            val isToday = d == today; val isCursor = d == cursor
            val bg by androidx.compose.animation.animateColorAsState(if (isCursor) Palette.blue else Color.Transparent, label = "cursor")
            Column(Modifier.clickable { onPick(d) }.padding(vertical = 2.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
                if (weekday) Text(d.dayOfWeek.getDisplayName(java.time.format.TextStyle.NARROW, java.util.Locale.US), color = if (isCursor) Palette.blue else Palette.dim, fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                Box(Modifier.size(26.dp).background(bg, RoundedCornerShape(50)).border(if (isToday) 1.5.dp else 0.dp, if (isToday) Palette.red else Color.Transparent, RoundedCornerShape(50)), contentAlignment = Alignment.Center) {
                    Text("${d.dayOfMonth}", color = if (isCursor) Color.Black else if (d.isBefore(today)) Palette.dim else Palette.text, fontSize = 12.sp, fontWeight = if (isToday || isCursor) FontWeight.Bold else FontWeight.Normal, fontFamily = FontFamily.Monospace) }
                Box(Modifier.size(5.dp).background(if (d in eventDays) Palette.purple else if (d in marked) Palette.blue2 else Color.Transparent, RoundedCornerShape(50))) }
        }
        if (expanded) {
            Row { listOf("M", "T", "W", "T", "F", "S", "S").forEach { d -> Text(d, Modifier.weight(1f), color = Palette.dim, fontSize = 8.sp, fontFamily = FontFamily.Monospace, textAlign = androidx.compose.ui.text.style.TextAlign.Center) } }
            val offset = (shown.dayOfWeek.value + 6) % 7; val count = shown.lengthOfMonth(); val rowsN = (offset + count + 6) / 7
            for (r in 0 until rowsN) Row { for (c in 0 until 7) { val i = r * 7 + c - offset; Box(Modifier.weight(1f)) { if (i in 0 until count) cell(shown.plusDays(i.toLong()), weekday = false) } } }
        } else {
            androidx.compose.foundation.layout.BoxWithConstraints(Modifier.fillMaxWidth()) {
                val cw = maxWidth / 7
                androidx.compose.foundation.lazy.LazyRow(state = rowState, flingBehavior = androidx.compose.foundation.gestures.snapping.rememberSnapFlingBehavior(rowState)) {
                    items(ribbon.size, key = { ribbon[it].toEpochDay() }) { i -> Box(Modifier.width(cw)) { cell(ribbon[i], weekday = true) } }
                }
            }
        }
    }
    HorizontalDivider(thickness = 0.5.dp, color = Palette.line)
}

fun dayOfRow(r: AgendaRow): java.time.LocalDate? {
    val today = java.time.LocalDate.now()
    fun dayOf(iso: String) = runCatching { java.time.Instant.parse(iso).atZone(java.time.ZoneId.systemDefault()).toLocalDate() }.getOrDefault(today)
    return when (r) { is AgendaRow.Ev -> dayOf(r.e.startAt); is AgendaRow.Tr -> maxOf(dayOf(r.t.departAt), today); else -> null }
}
