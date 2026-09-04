package com.toc.coptoc

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import org.maplibre.android.MapLibre

class MainActivity : ComponentActivity() {
    private val store: Store by viewModels()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MapLibre.getInstance(this)  // no key: OpenFreeMap tiles are keyless
        Ui.load(applicationContext)
        setContent { TOCTheme { WallScreen(store) } }
    }
}
