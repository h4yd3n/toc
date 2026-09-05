package com.toc.coptoc

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class WallState(
    val snap: Snapshot? = null, val requirements: List<Requirement> = emptyList(), val intsums: List<IntsumHead> = emptyList(), val cases: List<CaseHead> = emptyList(), val operation: Operation? = null,
    val users: List<UserInfo> = emptyList(), val userId: String = Ui.userId,
    val role: String = "battle_captain", val restricted: Boolean = true, val busy: String? = null, val error: String? = null,
    val selection: Selection? = null, val lastRefresh: Long = 0L,
)

/** The wall's state on the phone: one snapshot, refreshed every 15 s and after every write. */
class Store : ViewModel() {
    val api = CopClient(userId = Ui.userId)
    private val _state = MutableStateFlow(WallState())
    val state: StateFlow<WallState> = _state

    init { viewModelScope.launch { while (true) { refresh(); delay(15_000) } } }

    fun signIn(id: String, ctx: android.content.Context? = null) { api.userId = id; Ui.userId = id; ctx?.let { Ui.save(it) }; _state.update { it.copy(userId = id) }; viewModelScope.launch { refresh() } }
    suspend fun loadUsers() { runCatching { api.users() }.onSuccess { u -> _state.update { it.copy(users = u) } } }
    fun setRole(role: String) { api.role = role; _state.update { it.copy(role = role, restricted = role == "battle_captain" || role == "ep") }; viewModelScope.launch { refresh() } }
    fun select(sel: Selection?) = _state.update { it.copy(selection = sel) }
    fun openOperation(id: String?) { if (id == null) _state.update { it.copy(operation = null) } else viewModelScope.launch { runCatching { api.operation(id) }.onSuccess { op -> _state.update { it.copy(operation = op) } }.onFailure { e -> _state.update { it.copy(error = "operation: ${e.message}") } } } }
    fun dismissError() = _state.update { it.copy(error = null) }

    suspend fun refresh() {
        try {
            val s = api.snapshot(_state.value.restricted)
            val r = runCatching { api.requirements() }.getOrDefault(emptyList())
            val i = runCatching { api.intsums() }.getOrDefault(emptyList())
            val c = runCatching { api.cases() }.getOrDefault(emptyList())
            _state.update { it.copy(snap = s, requirements = r, intsums = i, cases = c, error = null, lastRefresh = System.currentTimeMillis()) }
        } catch (e: Exception) {
            _state.update { it.copy(error = "API: ${e.message ?: e::class.simpleName} (${api.baseUrl})") }
        }
    }

    /** Every write goes through here: busy label on, call, refresh, busy off — errors surface, never swallowed. */
    fun act(label: String, block: suspend CopClient.() -> Unit) {
        viewModelScope.launch {
            _state.update { it.copy(busy = label) }
            try { api.block(); refresh() } catch (e: Exception) { _state.update { it.copy(error = "${label}: ${e.message}") } }
            _state.update { it.copy(busy = null) }
        }
    }
}
