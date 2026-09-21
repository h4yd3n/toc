package com.toc.coptoc

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** §5.6b the subject of concern on the phone. The wall opens files, rates them and works the inbox; the phone reads
 *  the files and the inbox, shows on a principal who is directed at them, and files a contact from the field — the
 *  in-person door of the mailroom. It never rates a person: that is the S2 analyst's, at the wall. Everything here is
 *  empty unless the signed-in role is cleared for the files; the tally in the summary is what the floor sees. */

val SUBJECT_READERS = listOf("battle_captain", "ep", "analyst")
fun ratingColor(r: String): Color = when (r) { "green" -> Palette.green; "amber" -> Palette.amber; "red" -> Palette.red; else -> Palette.line }
fun directLabel(d: String) = when (d) { "directed" -> "DIRECTED"; "conditional" -> "CONDITIONAL"; "veiled" -> "VEILED"; else -> "NO THREAT" }
fun directColor(d: String): Color = when (d) { "directed" -> Palette.red; "conditional" -> Palette.orange; "veiled" -> Palette.amber; else -> Palette.dim }
private fun ago(d: Double?): String = if (d == null) "never assessed" else if (d < 1) "today" else "${Math.round(d)}d ago"
private fun channelLabel(c: String) = c.uppercase().replace('_', ' ')

/** The row of ratings, one block per indicator in the configured order. */
@Composable fun RatingBlocks(strip: List<String>) = Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) { strip.forEach { Box(Modifier.size(8.dp).background(ratingColor(it), RoundedCornerShape(2.dp))) } }

@Composable private fun WorstChip(unassessed: Boolean, worst: String) =
    if (unassessed) Chip("UNASSESSED", Palette.amber) else Chip(worst.uppercase(), ratingColor(worst), filled = worst == "red")

/** What a principal or a site carries about a file: the name, the strip, the worst of it as a word. */
@Composable fun SubjectStripRow(s: SubjectCompact, onClick: () -> Unit) =
    Row(Modifier.fillMaxWidth().clickable { onClick() }.padding(vertical = 2.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(s.name, color = Palette.text, fontSize = 11.5.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        RatingBlocks(s.strip)
        WorstChip(s.unassessed, s.worst)
        Spacer(Modifier.weight(1f))
        if (s.contactCount > 0) Text("${s.contactCount} contact" + (if (s.contactCount == 1) "" else "s"), color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
        if (s.stale) Chip("STALE", Palette.amber)
    }

/** The S2 tab section: every live file worst first, then what nobody has attributed yet. */
fun LazyListScope.subjectsSection(st: WallState, store: Store, onFile: () -> Unit) {
    val snap = st.snap ?: return
    val cleared = (snap.me?.role ?: st.role) in SUBJECT_READERS
    val live = snap.subjects.filter { it.live }; val rest = snap.subjects.filter { !it.live }
    val t = snap.summary
    item { Label("WHO IS DIRECTED AT US", "${t.subjectsOpen} open · ${t.subjectsRed} red", action = { if (cleared) Mini("+ CONTACT", Palette.blue2, st.busy == null) { onFile() } }) }
    if (!cleared) { item { Text("Subject files name private individuals. Battle Captain, Executive Protection or the S2 analyst only.", Modifier.padding(horizontal = 14.dp), color = Palette.dim, fontSize = 10.sp) }; return }
    items(live + rest, key = { "subj_" + it.id }) { s ->
        RowItem(selected = (st.selection as? Selection.SubjectSel)?.id == s.id, onClick = { store.select(Selection.SubjectSel(s.id)) }) {
            Column(Modifier.weight(1f).alpha(if (s.live) 1f else .55f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(s.name, color = Palette.text, fontSize = 11.5.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    WorstChip(s.unassessed, s.worst)
                    if (s.status != "open") Chip(s.status.uppercase(), when (s.status) { "monitoring" -> Palette.blue2; "referred" -> Palette.amber; else -> Palette.dim }) }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    RatingBlocks(s.assessment?.ratings?.map { it.rating } ?: emptyList())
                    Text(listOfNotNull(if (s.principalName.isNotEmpty()) "directed at ${s.principalName}" else (s.worstIndicator ?: "nothing rated"),
                                       if (s.contactCount > 0) "${s.contactCount} contact" + (if (s.contactCount == 1) "" else "s") else null,
                                       if (s.worstDirectness != "none") directLabel(s.worstDirectness).lowercase() else null,
                                       if (s.assessedAt == null) "never assessed" else ago(s.ageDays)).joinToString(" · "),
                         color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace, maxLines = 1, overflow = TextOverflow.Ellipsis) } } } }
    if (live.isEmpty() && rest.isEmpty()) item { Text("No file is open on anyone.", Modifier.padding(horizontal = 14.dp), color = Palette.dim, fontSize = 10.sp) }
    if (snap.subjectInbox.isNotEmpty()) {
        item { Label("INBOX", "${snap.subjectInbox.size} attributed to nobody") }
        items(snap.subjectInbox, key = { "inbox_" + it.id }) { c ->
            Column(Modifier.padding(horizontal = 14.dp, vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Chip(channelLabel(c.channel)); Text(c.fromLabel.ifEmpty { "sender not given" }, color = Palette.text, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                    Chip(directLabel(c.directness), directColor(c.directness), filled = c.directness == "directed") }
                Text(c.text, color = Palette.text.copy(alpha = .85f), fontSize = 10.5.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                Text(c.receivedAt.take(16).replace('T', ' ') + "Z · " + (if (c.principalName.isEmpty()) "names nobody we hold" else "names ${c.principalName}") + " · attributed at the wall", color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace, maxLines = 1, overflow = TextOverflow.Ellipsis)
                HorizontalDivider(thickness = 0.5.dp, color = Palette.line) } } }
}

/** The detail card for one file: who he is, the assessment as the analyst wrote it, what has arrived from him. */
@Composable fun ColumnScope.SubjectDetailBody(s: Subject, st: WallState, store: Store, onFile: () -> Unit) {
    val snap = st.snap ?: return
    Kicker("SUBJECT OF CONCERN · RESTRICTED · ${s.status.uppercase()}" + (s.assessment?.let { " · ${it.assessedBy}" } ?: ""))
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) { Title(s.name); WorstChip(s.unassessed, s.worst); if (s.stale) Chip("STALE", Palette.amber) }
    if (s.aliases.isNotEmpty()) Text("also: " + s.aliases.joinToString(" · "), color = Palette.dim, fontSize = 10.5.sp)
    if (s.summary.isNotEmpty()) Text(s.summary, color = Palette.text.copy(alpha = .9f), fontSize = 11.sp, lineHeight = 15.sp)
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        s.principalId?.let { pid -> Mini("⌖ ${s.principalName}", Palette.blue2) { store.select(Selection.PersonSel(pid)) } }
        s.locationId?.let { lid -> if (snap.locations.any { it.id == lid }) Mini("⌖ SITE", Palette.blue2) { store.select(Selection.SiteSel(lid)) } } }
    if (s.status == "referred") s.referredTo?.let { KV("Referred", it) }
    if (s.status == "closed") s.closedReason?.let { KV("Closed", it) }
    s.lastSeenPlace?.let { KV("Last seen", it + (s.lastSeenAt?.let { t -> " · " + t.take(16).replace('T', ' ') + "Z" } ?: "")) }

    Section("THE ASSESSMENT", if (s.unassessed) "none yet" else ago(s.ageDays) + " · nothing summed")
    if (s.unassessed) Text("Nobody has rated this person. That is an exception in its own right; it is not a green file. Rating is done at the wall.", color = Palette.dim, fontSize = 10.sp)
    else s.assessment?.let { a ->
        a.ratings.forEach { r -> Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Top) {
            Box(Modifier.width(3.dp).height(30.dp).background(ratingColor(r.rating)))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) { Text(r.label, color = Palette.text, fontSize = 11.5.sp, fontWeight = FontWeight.SemiBold); Chip(if (r.rating == "unknown") "—" else r.rating.uppercase(), ratingColor(r.rating)) }
                Text(r.note.ifEmpty { "no justification recorded" }, color = if (r.note.isEmpty()) Palette.dim else Palette.text.copy(alpha = .8f), fontSize = 10.5.sp, maxLines = 3, overflow = TextOverflow.Ellipsis) } } }
        if (a.summary.isNotEmpty()) Text(a.summary, color = Palette.text.copy(alpha = .85f), fontSize = 11.sp, lineHeight = 15.sp) }

    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { Section("WHAT HAS ARRIVED", "${s.contactCount}"); Spacer(Modifier.weight(1f)); if (s.live) Mini("+ CONTACT", Palette.blue2, st.busy == null) { onFile() } }
    if (s.contacts.isEmpty()) Text("Nothing has been attributed to this file.", color = Palette.dim, fontSize = 10.sp)
    s.contacts.forEach { c -> Column(Modifier.padding(vertical = 3.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Chip(channelLabel(c.channel)); Text(c.fromLabel.ifEmpty { "sender not given" }, color = Palette.text, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
            Chip(directLabel(c.directness), directColor(c.directness), filled = c.directness == "directed"); Chip("${c.reliability}/${c.credibility}") }
        Text(c.text, color = Palette.text.copy(alpha = .85f), fontSize = 10.5.sp)
        Text(c.receivedAt.take(16).replace('T', ' ') + "Z" + (if (c.principalName.isEmpty()) "" else " · names ${c.principalName}") + (c.note?.let { " · $it" } ?: ""), color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace, maxLines = 2, overflow = TextOverflow.Ellipsis) } }
    Text("Opened by ${s.openedBy} · ${s.openedAt.take(16).replace('T', ' ')}Z" + (s.caseId?.let { " · case $it" } ?: "") + ". Rated, referred and closed at the wall.", color = Palette.dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
}

/** Something arrived, or someone approached. It lands graded F/6 — an unknown sender cannot be judged — and, unless
 *  filed from a subject's own card, in the inbox: the phone never guesses whose it is. */
@Composable fun ContactDialog(st: WallState, store: Store, subjectId: String?, open: Boolean, onDone: () -> Unit) {
    if (!open) return
    val subject = st.snap?.subjects?.firstOrNull { it.id == subjectId }
    var channel by remember { mutableStateOf("in_person") }
    var from by remember { mutableStateOf("") }; var text by remember { mutableStateOf("") }; var directness by remember { mutableStateOf("none") }; var principal by remember { mutableStateOf("") }
    val me = st.snap?.me
    val channels = listOf("in_person" to "IN PERSON", "phone" to "PHONE", "letter" to "LETTER", "email" to "EMAIL", "dm" to "DM", "form" to "FORM", "other" to "OTHER")
    val vips = st.snap?.people?.filter { it.isVip } ?: emptyList()
    AlertDialog(onDismissRequest = onDone, containerColor = Palette.panel, titleContentColor = Palette.text, textContentColor = Palette.text,
        title = { Text(if (subject != null) "CONTACT · ${subject.name}" else "CONTACT · INTO THE INBOX", fontSize = 13.sp, fontFamily = FontFamily.Monospace) },
        text = { Column(verticalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.verticalScroll(rememberScrollState())) {
            Text(if (subject != null) "Onto the file. Rated at the wall." else "Attributed to nobody until an analyst says so, at the wall.", color = Palette.dim, fontSize = 9.5.sp)
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(5.dp)) { channels.forEach { (k, l) -> Chip(l, if (channel == k) Palette.blue2 else Palette.dim, filled = channel == k) { channel = k } } }
            OutlinedTextField(from, { from = it }, label = { Text(if (channel == "in_person") "Who — as they gave it, or a description" else "From — as it arrived") }, singleLine = true)
            OutlinedTextField(text, { text = it }, label = { Text("What was said or written, in the words it arrived in") }, minLines = 3)
            Text("How the threat is worded — the wording, not your view of the risk", color = Palette.dim, fontSize = 9.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) { listOf("none", "veiled", "conditional", "directed").forEach { d -> Chip(directLabel(d), if (directness == d) directColor(d) else Palette.dim, filled = directness == d) { directness = d } } }
            if (subject == null && vips.isNotEmpty()) {
                Text("Who it names, if one of ours", color = Palette.dim, fontSize = 9.sp)
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(5.dp)) { Chip("NOBODY", if (principal.isEmpty()) Palette.blue2 else Palette.dim, filled = principal.isEmpty()) { principal = "" }
                    vips.forEach { p -> Chip(p.name, if (principal == p.id) Palette.blue2 else Palette.dim, filled = principal == p.id) { principal = p.id } } } }
            Text("Filed by ${me?.name ?: store.api.actor} · graded F/6 on arrival — an unknown sender cannot be judged · time is now", color = Palette.dim, fontSize = 9.sp) } },
        confirmButton = { TextButton({
            if (text.isNotBlank()) {
                val body = buildJsonObject { put("text", text.trim()); put("channel", channel); put("from_label", from.trim()); put("directness", directness); put("received_by", me?.name ?: store.api.actor)
                    subjectId?.let { put("subject_id", it) }; if (principal.isNotEmpty()) put("principal_id", principal) }
                store.act("filing the contact") { fileContact(body) }; onDone() } }) { Text("FILE", color = Palette.blue2) } },
        dismissButton = { TextButton(onDone) { Text("CANCEL", color = Palette.dim) } })
}

