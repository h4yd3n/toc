package com.toc.coptoc

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression.*
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.FillLayer
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.PropertyFactory.*
import org.maplibre.android.style.layers.SymbolLayer
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.Point
import org.maplibre.geojson.Polygon
import org.maplibre.geojson.LineString

const val STYLE_URL = "https://tiles.openfreemap.org/styles/dark"

/** A ring of [lon, lat] around a centre at a radius in km — the polygon an NAI is drawn as. */
private fun ring(lat: Double, lon: Double, km: Double, n: Int = 48): List<Point> {
    val r = 6371.0; val p1 = Math.toRadians(lat); val l1 = Math.toRadians(lon); val d = km / r
    return (0..n).map { i -> val th = 2 * Math.PI * i / n
        val p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(th))
        val l2 = l1 + Math.atan2(Math.sin(th) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2))
        Point.fromLngLat(Math.toDegrees(l2), Math.toDegrees(p2)) }
}

private fun feature(lon: Double, lat: Double, vararg props: Pair<String, Any?>): Feature = Feature.fromGeometry(Point.fromLngLat(lon, lat)).also { f ->
    props.forEach { (k, v) -> when (v) { is String -> f.addStringProperty(k, v); is Number -> f.addNumberProperty(k, v); is Boolean -> f.addBooleanProperty(k, v); else -> {} } }
}

private fun hex(c: androidx.compose.ui.graphics.Color) = String.format("#%06X", 0xFFFFFF and android.graphics.Color.argb((c.alpha * 255).toInt(), (c.red * 255).toInt(), (c.green * 255).toInt(), (c.blue * 255).toInt()))

/**
 * §3.1 — the wall has one board. A section tab builds its own MapView, so the camera is kept here instead: leaving
 * S1 for S2 changes the overlay and never the view. `framed` makes the opening frame a one-time thing — a refresh
 * fifteen seconds later must not haul the map back while someone is working it.
 */
private object Board {
    var position: CameraPosition? = null
    var framed = false
    /// Where a phone that remembers nothing and cannot reach the API opens: the Bay Area.
    val bayArea: CameraPosition = CameraPosition.Builder().target(LatLng(37.72, -122.16)).zoom(8.0).build()

    private const val PREFS = "toc.map.2"   // bumped when home station replaced the fixed defaults, so a phone remembering the old one starts over
    fun load(ctx: android.content.Context) {
        if (position != null) return
        val p = ctx.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
        val lat = p.getFloat("lat", Float.NaN); val lon = p.getFloat("lon", Float.NaN); val z = p.getFloat("zoom", Float.NaN)
        if (lat.isNaN() || lon.isNaN() || z.isNaN()) return
        position = CameraPosition.Builder().target(LatLng(lat.toDouble(), lon.toDouble())).zoom(z.toDouble()).build()
        framed = true   // a remembered board is never overridden by the server's default
    }
    fun save(ctx: android.content.Context, c: CameraPosition) {
        val t = c.target ?: return
        ctx.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE).edit()
            .putFloat("lat", t.latitude.toFloat()).putFloat("lon", t.longitude.toFloat()).putFloat("zoom", c.zoom.toFloat()).apply()
    }
}

/** The map at the center of the wall: sites by posture, travelers, events, threat rings by severity. Tap selects. */
@Composable
fun WallMap(snap: Snapshot?, restricted: Boolean, onSelect: (Selection) -> Unit, modifier: Modifier = Modifier, layer: String? = null) {
    val latestLayer = remember { arrayOfNulls<String>(1) }; latestLayer[0] = layer
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val mapView = remember { MapView(context) }
    val mapHolder = remember { arrayOfNulls<MapLibreMap>(1) }
    val latest = remember { arrayOfNulls<Snapshot>(1) }
    val latestRestricted = remember { booleanArrayOf(restricted) }
    DisposableEffect(lifecycle) {
        val obs = LifecycleEventObserver { _, e -> when (e) {
            Lifecycle.Event.ON_CREATE -> mapView.onCreate(null); Lifecycle.Event.ON_START -> mapView.onStart(); Lifecycle.Event.ON_RESUME -> mapView.onResume()
            Lifecycle.Event.ON_PAUSE -> mapView.onPause(); Lifecycle.Event.ON_STOP -> mapView.onStop(); Lifecycle.Event.ON_DESTROY -> mapView.onDestroy(); else -> {} } }
        lifecycle.addObserver(obs)
        onDispose { lifecycle.removeObserver(obs) }
    }
    AndroidView(factory = {
        mapView.onCreate(null)
        mapView.getMapAsync { map ->
            mapHolder[0] = map
            Board.load(context)
            map.cameraPosition = Board.position ?: Board.bayArea
            // The camera is shared between tabs from the first frame, but only written to disk once the board is
            // real — otherwise the placeholder we show while the first snapshot is in flight becomes permanent.
            map.addOnCameraIdleListener {
                Board.position = map.cameraPosition
                if (Board.framed) Board.save(context, map.cameraPosition)
            }
            map.uiSettings.isAttributionEnabled = true; map.uiSettings.isLogoEnabled = false
            map.setStyle(Style.Builder().fromUri(STYLE_URL)) { style ->
                // §3.4 the overlays: NAIs under everything, then movements leg by leg, then threats, then the blue force; every feature carries
                // its own alpha so a section's tab dims the others' things instead of hiding them — an overlay sits on the base, the base stays
                style.addSource(GeoJsonSource("nais", FeatureCollection.fromFeatures(emptyList())))
                style.addSource(GeoJsonSource("graphics", FeatureCollection.fromFeatures(emptyList())))
                style.addSource(GeoJsonSource("moves", FeatureCollection.fromFeatures(emptyList())))
                style.addSource(GeoJsonSource("threats", FeatureCollection.fromFeatures(emptyList())))
                style.addSource(GeoJsonSource("blue", FeatureCollection.fromFeatures(emptyList())))
                style.addLayer(FillLayer("gfx-fill", "graphics").withFilter(eq(geometryType(), literal("Polygon"))).withProperties(fillColor(get("color")), fillOpacity(get("fo"))))
                style.addLayer(LineLayer("gfx-line", "graphics").withFilter(eq(get("dash"), literal(false))).withProperties(lineColor(get("color")), lineWidth(get("lw")), lineOpacity(get("lo"))))
                style.addLayer(LineLayer("gfx-line-dashed", "graphics").withFilter(eq(get("dash"), literal(true))).withProperties(lineColor(get("color")), lineWidth(get("lw")), lineOpacity(get("lo")), lineDasharray(arrayOf(4f, 3f))))
                style.addLayer(FillLayer("nai-fill", "nais").withProperties(fillColor(get("color")), fillOpacity(get("fo"))))
                style.addLayer(LineLayer("nai-line", "nais").withProperties(lineColor(get("color")), lineWidth(get("lw")), lineOpacity(get("lo")), lineDasharray(arrayOf(4f, 3f))))
                style.addLayer(LineLayer("move-lines", "moves").withFilter(eq(get("dashed"), literal(false))).withProperties(lineColor(get("color")), lineWidth(get("lw")), lineOpacity(get("lo"))))
                style.addLayer(LineLayer("move-lines-dashed", "moves").withFilter(eq(get("dashed"), literal(true))).withProperties(lineColor(get("color")), lineWidth(get("lw")), lineOpacity(get("lo")), lineDasharray(arrayOf(3f, 3f))))
                style.addLayer(CircleLayer("threat-rings", "threats").withProperties(
                    circleRadius(interpolate(exponential(2f), zoom(), stop(0, 2f), stop(6, 12f), stop(10, 40f))),
                    circleColor(get("color")), circleOpacity(product(literal(0.12f), get("alpha"))), circleStrokeColor(get("color")), circleStrokeWidth(1.2f), circleStrokeOpacity(product(literal(0.8f), get("alpha")))))
                style.addLayer(CircleLayer("blue-dots", "blue").withProperties(
                    circleRadius(switchCase(eq(get("kind"), literal("site")), literal(7f), eq(get("kind"), literal("head")), literal(6f), eq(get("kind"), literal("graphic")), literal(3.5f), literal(5f))),
                    circleColor(get("color")), circleOpacity(get("alpha")), circleStrokeColor(literal("#0b0f14")), circleStrokeWidth(1.5f), circleStrokeOpacity(get("alpha"))))
                style.addLayer(SymbolLayer("blue-labels", "blue").withProperties(
                    textField(get("label")), textFont(arrayOf("Noto Sans Regular")), textSize(10f), textColor(literal("#dce4ee")), textOpacity(get("alpha")), textHaloColor(literal("#0b0f14")), textHaloWidth(1.2f),
                    textOffset(arrayOf(0f, 1.3f)), textAllowOverlap(false), textOptional(true)))
                applySnapshot(style, latest[0], latestRestricted[0], latestLayer[0])  // the first snapshot usually arrives before the style does
                map.addOnMapClickListener { p ->
                    val pt = map.projection.toScreenLocation(p)
                    val rect = android.graphics.RectF(pt.x - 24, pt.y - 24, pt.x + 24, pt.y + 24)
                    val hit = map.queryRenderedFeatures(rect, "blue-dots").firstOrNull() ?: map.queryRenderedFeatures(rect, "threat-rings").firstOrNull()
                    hit?.let { f ->
                        val id = f.getStringProperty("id"); when (f.getStringProperty("kind")) {
                            "site" -> onSelect(Selection.SiteSel(id)); "traveler" -> onSelect(Selection.PersonSel(id)); "event" -> onSelect(Selection.EventSel(id)); "threat" -> onSelect(Selection.ThreatSel(id)) }
                        true
                    } ?: false
                }
            }
        }
        mapView
    }, modifier = modifier, update = {
        latest[0] = snap; latestRestricted[0] = restricted
        mapHolder[0]?.let { map ->
            frameOpening(map, snap)
            map.style?.let { applySnapshot(it, snap, restricted, layer) }
        }
    })
}

/** Frame the AO the Battle Captain declared, or the box that holds our sites. Once per process. */
private fun frameOpening(map: MapLibreMap, snap: Snapshot?) {
    if (Board.framed) return   // once per process — and never mind that the idle listener already saved the world view
    val v = snap?.view ?: return
    val lat = v.centerLat ?: return; val lon = v.centerLon ?: return
    Board.framed = true
    val r = v.radiusKm ?: 250.0
    val dLat = r / 111.0
    val dLon = r / (111.0 * Math.max(Math.cos(Math.toRadians(lat)), 0.01))
    val bounds = LatLngBounds.from(lat + dLat, lon + dLon, lat - dLat, lon - dLon)
    map.moveCamera(CameraUpdateFactory.newLatLngBounds(bounds, 48))
    Board.position = map.cameraPosition
}

private fun applySnapshot(style: Style, s: Snapshot?, restricted: Boolean, layer: String? = null) = try {
    applySnapshotInner(style, s, restricted, layer)
} catch (e: Exception) { android.util.Log.e("WallMap", "applySnapshot failed", e) }

private fun applySnapshotInner(style: Style, s: Snapshot?, restricted: Boolean, layer: String? = null) {
    s ?: return
    // §3 the map-first sections: a section's layer shows only what that section owns; S4 / S6 color every site by its health
    val showThreats = layer == null || layer == "S2"; val showTravelers = layer == null || layer == "S1" || layer == "S3"; val showEvents = layer == null || layer == "S3"
    fun siteColor(l: Site): String { val h = when (layer) { "S4" -> l.s4Status; "S6" -> l.s6Status; else -> null }; return if (h != null) hex(healthColor(h)) else hex(Palette.posture(l.effectivePosture)) }
    fun siteLabel(l: Site): String = when (layer) { "S4" -> l.s4Status?.let { "${l.name} · S4 ${it.uppercase()}" + (if (l.s4Red > 0) " (${l.s4Red})" else "") } ?: l.name
        "S6" -> l.s6Status?.let { "${l.name} · S6 ${it.uppercase()}" + (l.s6InUse?.let { n -> " · on ${n.uppercase()}" } ?: "") } ?: l.name; else -> l.name }
    // §3.4 dim, do not hide: the section's own things at full strength, the rest at a third
    val tA = if (showThreats) 1.0 else 0.3; val pA = if (showTravelers) 1.0 else 0.3; val eA = if (showEvents) 1.0 else 0.3
    val mA = if (layer == null || layer == "S3") 1.0 else if (layer == "S4") 0.6 else 0.3
    val threats = s.threats.map { t -> feature(t.lon, t.lat, "id" to t.id, "kind" to "threat", "color" to hex(Palette.severity(t.severity)), "radius" to t.radiusKm, "alpha" to tA) }
    val s2Label = { l: Site -> l.area?.let { a -> "${l.name} · rated ${a.worst.uppercase()}" } ?: l.name }
    val blue = s.locations.filter { restricted || it.sensitivity != "restricted" }.map { l -> feature(l.lon, l.lat, "id" to l.id, "kind" to "site", "label" to (if (layer == "S2") s2Label(l) else siteLabel(l)), "color" to (if (layer == "S2" && l.area != null && l.area.worst != "unknown") hex(healthColor(l.area.worst)) else siteColor(l)), "alpha" to 1.0) } +
            s.people.filter { it.status == "traveling" }.map { p -> feature(p.lon, p.lat, "id" to p.id, "kind" to "traveler", "label" to (p.shortName ?: p.name.split(" ").first()), "color" to hex(if (p.isVip) Palette.amber else Palette.blue2), "alpha" to pA) } +
            s.events.map { e -> feature(e.venueLon, e.venueLat, "id" to e.id, "kind" to "event", "label" to e.name, "color" to hex(Palette.purple), "alpha" to eA) } +
            // the head of every group movement — the unit or delegation and its count, the shipment and its ETA
            s.movements.filter { it.kind != "individual" }.mapNotNull { mv ->
                val c = if (mv.headLat != null && mv.headLon != null) mv.headLon to mv.headLat else mv.legs.firstOrNull()?.let { lg -> if (lg.fromLat != null && lg.fromLon != null) ((lg.fromLon + lg.toLon) / 2) to ((lg.fromLat + lg.toLat) / 2) else null }
                c?.let { (lon, lat) -> feature(lon, lat, "id" to (mv.personIds.firstOrNull() ?: mv.id), "kind" to (if (mv.personIds.isEmpty()) "head" else "traveler"),
                    "label" to (if (mv.kind == "shipment") "${mv.name.substringBefore(" → ")} · ETA ${Math.round(mv.hoursToEta ?: 0.0)}h" else "${mv.unit ?: mv.name.substringBefore(" · ")} · ${mv.pax} pax"),
                    "color" to hex(if (mv.kind == "shipment") (if (mv.health == "red") Palette.red else Palette.orange) else if (mv.isVip) Palette.amber else Palette.purple), "alpha" to mA) }
            }
    // §3.4 S2: every active requirement as a named area, colored by how well it is collected; only on the S2 tab
    val nais = if (layer != "S2") emptyList() else s.nais.map { n -> Feature.fromGeometry(Polygon.fromLngLats(listOf(ring(n.lat, n.lon, n.radiusKm)))).also { f ->
        f.addStringProperty("id", n.id); f.addStringProperty("color", hex(healthColor(n.health))); f.addNumberProperty("fo", if (n.priority == 1) 0.10 else 0.05); f.addNumberProperty("lo", if (n.priority == 1) 0.9 else 0.55); f.addNumberProperty("lw", if (n.priority == 1) 1.8 else 1.0) } }
    // §3.4 S3: movements leg by leg — a shipment dashed orange, a planned leg dashed, the current leg bold
    val moves = s.movements.flatMap { mv -> mv.legs.filter { it.fromLat != null && it.fromLon != null && it.kind != "lodging" }.map { lg ->
        val color = if (mv.kind == "shipment") (if (mv.health == "red") Palette.red else Palette.orange) else if (mv.isVip) Palette.amber else if (mv.status == "active") Palette.blue2 else Palette.dim
        Feature.fromGeometry(LineString.fromLngLats(listOf(Point.fromLngLat(lg.fromLon!!, lg.fromLat!!), Point.fromLngLat(lg.toLon, lg.toLat)))).also { f ->
            f.addStringProperty("id", mv.id); f.addStringProperty("color", hex(color)); f.addNumberProperty("lw", if (lg.status == "current") (if (mv.pax >= 3) 3.0 else 2.2) else 1.4)
            f.addNumberProperty("lo", (if (lg.status == "done") 0.35 else if (lg.status == "current") 0.95 else 0.7) * mA); f.addBooleanProperty("dashed", mv.kind == "shipment" || lg.status == "planned") } } }
    // §3.4 the control measures a section drew: shapes on their own source, the glyph and name as a label in the blue source
    val gfx = s.graphics.mapNotNull { g -> val a = (if (layer == null || layer == g.section) 1.0 else 0.3) * (if (g.windowFrom != null && !g.inWindow) 0.45 else 1.0); val p = g.path
        val geom = when { g.kind == "polygon" && p.size >= 3 -> Polygon.fromLngLats(listOf((p + p.first()).map { Point.fromLngLat(it.first, it.second) })); g.kind != "point" && p.size >= 2 -> LineString.fromLngLats(p.map { Point.fromLngLat(it.first, it.second) }); else -> null }
        geom?.let { Feature.fromGeometry(it).also { f -> f.addStringProperty("id", g.id); f.addStringProperty("color", g.color); f.addBooleanProperty("dash", g.dash)
            f.addNumberProperty("fo", (if (g.type == "range" && g.inWindow) 0.22 else 0.07) * a); f.addNumberProperty("lo", 0.85 * a); f.addNumberProperty("lw", if (g.type == "boundary" || g.type == "phase_line") 1.5 else 2.5) } } }
    val gfxLabels = s.graphics.mapNotNull { g -> val a = if (layer == null || layer == g.section) 1.0 else 0.3
        val at = if (g.kind == "point") g.path.firstOrNull() else g.center.takeIf { it.size == 2 }?.let { it[0] to it[1] }
        at?.let { (lon, lat) -> feature(lon, lat, "id" to g.id, "kind" to "graphic", "label" to "${g.glyph} ${g.name}", "color" to g.color, "alpha" to a) } }
    (style.getSource("graphics") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(gfx))
    (style.getSource("nais") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(nais))
    (style.getSource("moves") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(moves))
    (style.getSource("threats") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(threats))
    (style.getSource("blue") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(blue + gfxLabels))
    android.util.Log.i("WallMap", "applied ${threats.size} threats, ${blue.size} blue features; blue source present=${style.getSource("blue") != null}, layer present=${style.getLayer("blue-dots") != null}")
}
