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

/** The map at the center of the wall: sites by posture, travelers, events, threat rings by severity. Tap selects. */
@Composable
fun WallMap(snap: Snapshot?, restricted: Boolean, onSelect: (Selection) -> Unit, modifier: Modifier = Modifier) {
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
            map.cameraPosition = CameraPosition.Builder().target(LatLng(32.0, -30.0)).zoom(0.9).build()
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
                applySnapshot(style, latest[0], latestRestricted[0])  // the first snapshot usually arrives before the style does
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
        mapHolder[0]?.style?.let { applySnapshot(it, snap, restricted) }
    })
}

private fun applySnapshot(style: Style, s: Snapshot?, restricted: Boolean) = try {
    applySnapshotInner(style, s, restricted)
} catch (e: Exception) { android.util.Log.e("WallMap", "applySnapshot failed", e) }

private fun applySnapshotInner(style: Style, s: Snapshot?, restricted: Boolean) {
    s ?: return
    val threats = s.threats.map { t -> feature(t.lon, t.lat, "id" to t.id, "kind" to "threat", "color" to hex(Palette.severity(t.severity)), "radius" to t.radiusKm) }
    val blue = s.locations.filter { restricted || it.sensitivity != "restricted" }.map { l -> feature(l.lon, l.lat, "id" to l.id, "kind" to "site", "label" to l.name, "color" to hex(Palette.posture(l.effectivePosture))) } +
            s.people.filter { it.status == "traveling" }.map { p -> feature(p.lon, p.lat, "id" to p.id, "kind" to "traveler", "label" to p.name.split(" ").first(), "color" to hex(if (p.isVip) Palette.amber else Palette.blue2)) } +
            s.events.map { e -> feature(e.venueLon, e.venueLat, "id" to e.id, "kind" to "event", "label" to e.name, "color" to hex(Palette.purple)) }
    (style.getSource("threats") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(threats))
    (style.getSource("blue") as? GeoJsonSource)?.setGeoJson(FeatureCollection.fromFeatures(blue))
    android.util.Log.i("WallMap", "applied ${threats.size} threats, ${blue.size} blue features; blue source present=${style.getSource("blue") != null}, layer present=${style.getLayer("blue-dots") != null}")
}
