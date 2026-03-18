package com.voicesnap.app.service

import android.content.Intent
import android.graphics.drawable.Icon
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.util.Log
import com.voicesnap.app.R
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest

class VoiceSnapTileService : TileService() {

    companion object {
        private const val TAG = "VoiceSnapTile"
    }

    private var scope: CoroutineScope? = null

    override fun onStartListening() {
        super.onStartListening()
        scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
        scope?.launch {
            RecordingStateHolder.state.collectLatest { state ->
                updateTileUI(state)
            }
        }
    }

    override fun onStopListening() {
        scope?.cancel()
        scope = null
        super.onStopListening()
    }

    override fun onClick() {
        super.onClick()
        Log.d(TAG, "Tile clicked! Current state: ${RecordingStateHolder.state.value}")

        val currentState = RecordingStateHolder.state.value

        // If currently recording → stop
        // If idle → start
        // If transcribing/translating → ignore
        val action = when (currentState) {
            RecordingState.RECORDING -> RecordingService.ACTION_STOP
            RecordingState.IDLE -> RecordingService.ACTION_START
            else -> {
                Log.d(TAG, "Busy ($currentState), ignoring tap")
                return
            }
        }

        // Launch via TrampolineActivity (guarantees foreground context)
        try {
            val intent = Intent(this, TrampolineActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION
                putExtra(TrampolineActivity.EXTRA_ACTION, action)
            }
            startActivityAndCollapse(intent)
            Log.d(TAG, "Trampoline launched with action=$action")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch trampoline", e)
        }
    }

    override fun onTileAdded() {
        super.onTileAdded()
        Log.d(TAG, "Tile added")
        qsTile?.let {
            it.state = Tile.STATE_INACTIVE
            it.label = "VoiceSnap"
            it.icon = Icon.createWithResource(this, R.drawable.ic_tile_mic)
            it.updateTile()
        }
    }

    private fun updateTileUI(state: RecordingState) {
        val tile = qsTile ?: return
        when (state) {
            RecordingState.IDLE -> {
                tile.state = Tile.STATE_INACTIVE
                tile.label = "VoiceSnap"
            }
            RecordingState.RECORDING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "\u00c9coute..."
            }
            RecordingState.TRANSCRIBING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "Transcription..."
            }
            RecordingState.TRANSLATING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "Traduction..."
            }
        }
        tile.icon = Icon.createWithResource(this, R.drawable.ic_tile_mic)
        tile.updateTile()
    }
}
