package com.toc.coptoc

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/** DISPLAY toggles, the same two as the wall: lean labels and the posture header. Both default on; persisted per device. */
object Ui {
    var userId: String = ""
    var lean by mutableStateOf(true)
    var posture by mutableStateOf(true)
    private const val FILE = "toc.ui"
    fun load(ctx: Context) { val p = ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE); lean = p.getBoolean("lean", true); posture = p.getBoolean("posture", true); userId = p.getString("user", "") ?: "" }
    fun save(ctx: Context) { ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putBoolean("lean", lean).putBoolean("posture", posture).putString("user", userId).apply() }
}


/** The collapsing dock (ported from SoriStory's NavBarChrome): scrolling DOWN folds the tab bar — labels hide, icons shrink,
 *  the capsule narrows; any upward scroll or a tab tap springs it back. Never folds near the top of a list. */
object NavBarChrome {
    var collapsed by androidx.compose.runtime.mutableStateOf(false)
        private set
    private var lastIndex = 0
    private var lastOffset = 0
    fun onScroll(firstVisibleItemIndex: Int, firstVisibleItemScrollOffset: Int) {
        val nearTop = firstVisibleItemIndex == 0 && firstVisibleItemScrollOffset < 24
        val movingDown = firstVisibleItemIndex > lastIndex || (firstVisibleItemIndex == lastIndex && firstVisibleItemScrollOffset > lastOffset + 6)
        val movingUp = firstVisibleItemIndex < lastIndex || (firstVisibleItemIndex == lastIndex && firstVisibleItemScrollOffset < lastOffset - 4)
        lastIndex = firstVisibleItemIndex; lastOffset = firstVisibleItemScrollOffset
        when { nearTop -> collapsed = false; movingDown -> collapsed = true; movingUp -> collapsed = false }
    }
    fun expand() { collapsed = false; lastIndex = 0; lastOffset = 0 }
}

/** Feed a list's scroll position to the dock. */
@androidx.compose.runtime.Composable
fun androidx.compose.foundation.lazy.LazyListState.driveDock() {
    val st = this
    androidx.compose.runtime.LaunchedEffect(st) { androidx.compose.runtime.snapshotFlow { st.firstVisibleItemIndex to st.firstVisibleItemScrollOffset }.collect { (i, o) -> NavBarChrome.onScroll(i, o) } }
}
