package com.voicesnap.app.service

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class RecordingState {
    IDLE, RECORDING, STOPPING, TRANSCRIBING, REWRITING, TRANSLATING
}

object RecordingStateHolder {
    private val _state = MutableStateFlow(RecordingState.IDLE)
    val state: StateFlow<RecordingState> = _state.asStateFlow()

    private val _lastResult = MutableStateFlow<String?>(null)
    val lastResult: StateFlow<String?> = _lastResult.asStateFlow()

    fun update(newState: RecordingState) {
        _state.value = newState
    }

    fun setResult(text: String?) {
        _lastResult.value = text
    }
}
