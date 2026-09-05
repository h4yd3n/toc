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
import org.maplibre.android.style.layers.PropertyFactory.*
import org.maplibre.android.style.layers.SymbolLayer
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.Point

const val STYLE_URL = "https://tiles.openfreemap.org/styles/dark"

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
            map.addOnCameraIdleListener { Board.position = map.cameraPosition; Board.save(context, map.cameraPosition) }
            map.uiSettings.isAttributionEnabled = true; map.uiSettings.isLogoEnabled = false
            map.setStyle(Style.Builder().fromUri(STYLE_URL)) { style ->
                style.addSource(GeoJsonSource("threats", FeatureCollection.fromFeatures(emptyList())))
                style.addSource(GeoJsonSource("blue", FeatureCollection.fromFeatures(emptyList())))
                style.addLayer(CircleLayer("threat-rings", "threats").withProperties(
                    circleRadius(interpolate(exponential(2f), zoom(), stop(0, 2f), stop(6, 12f), stop(10, 40f))),
                    circleColor(get("color")), circleOpacity(0.12f), circleStrokeColor(get("color")), circleStrokeWidth(1.2f), circleStrokeOpacity(0.8f)))
                style.addLayer(CircleLayer("blue-dots", "blue").withProperties(
                    circleRadius(switchCase(eq(get("kind"), literal("site")), literal(7f), literal(5f))),
                    circleColor(get("color")), circleStrokeColor(literal("#0b0f14")), circleStrokeWidth(1.5f)))
                style.addLayer(SymbolLayer("blue-labels", "blue").withProperties(
                    textField(get("label")), textFont(arrayOf("Noto Sans Regular")), textSize(10f), textColor(literal("#dce4ee")), textHaloColor(literal("#0b0f14")), textHaloWidth(1.2f),
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
    val threats = if (!showThreats) emptyList() else s.threats.map { t -> feature(t.lon, t.lat, "id" to t.id, "kind" to "threat", "color" to hex(Palette.severity(t.severity)), "radius" to t.radiusKm) }
    val blue = s.locations.filter { restricted || it.sensitivity != "restricted" }.map { l -> feature(l.lon, l.lat, "id" to l.id, "kind" to "site", "label" to siteLabel(l), "color" to siteColor(l)) } +
            (if (!showTravelers) emptyList() else s.people.filter { it.status == "traveling" }).map { p -> feature(p.lon, p.lat, "id" to p.id, "kind" to "traveler", "label" to (p.shortName ?: p.name.split(" ").first()), "color" to hex(if (p.isVip) Palette.amber else Palette.blue2)) } +
            (if (!showEvents) emptyList() else s.events).map { e -> feature(e.venueLon, e.venueLat, "id" to e.id, "kind" to "event", "label" to e.name, "color" to hex(Palette.purple)) }
    (style.getSource("threats") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(threats))
    (style.getSource("blue") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(blue))
    android.util.Log.i("WallMap", "applied ${threats.size} threats, ${blue.size} blue features; blue source present=${style.getSource("blue") != null}, layer present=${style.getLayer("blue-dots") != null}")
}
