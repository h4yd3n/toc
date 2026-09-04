package com.toc.coptoc

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// The wall's palette (coptoc/web/src/index.css): near-black ground, panels a shade up, blue for blue force,
// amber for elevated, red for critical, green for good.
object Palette {
    val bg = Color(0xFF0B0F14); val panel = Color(0xFF111821); val panel2 = Color(0xFF17202B); val line = Color(0xFF223041)
    val text = Color(0xFFDCE4EE); val dim = Color(0xFF7B8AA0)
    val blue = Color(0xFF3B82F6); val blue2 = Color(0xFF60A5FA); val amber = Color(0xFFF59E0B); val red = Color(0xFFEF4444); val green = Color(0xFF22C55E); val purple = Color(0xFFC084FC)
    fun posture(p: String) = when (p) { "critical" -> red; "elevated" -> amber; else -> green }
    fun severity(s: String) = when (s) { "critical" -> red; "elevated" -> amber; "moderate" -> Color(0xFFFBBF24); else -> dim }
    fun roster(s: String) = when (s) { "safe", "contacted" -> green; "unreachable" -> amber; "assist", "injured" -> red; else -> dim }
}

@Composable
fun TOCTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = darkColorScheme(primary = Palette.blue, background = Palette.bg, surface = Palette.panel, onBackground = Palette.text, onSurface = Palette.text, secondary = Palette.amber, error = Palette.red), content = content)
}
