package com.toc.coptoc

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/** DISPLAY toggles, the same two as the wall: lean labels and the posture header. Both default on; persisted per device. */
object Ui {
    var lean by mutableStateOf(true)
    var posture by mutableStateOf(true)
    private const val FILE = "toc.ui"
    fun load(ctx: Context) { val p = ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE); lean = p.getBoolean("lean", true); posture = p.getBoolean("posture", true) }
    fun save(ctx: Context) { ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putBoolean("lean", lean).putBoolean("posture", posture).apply() }
}
