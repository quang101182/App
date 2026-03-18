package com.voicesnap.app.service

import android.content.Intent
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import com.voicesnap.app.R
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest

class VoiceSnapTileService : TileService() {

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

        val intent = Intent(this, RecordingService::class.java).apply {
            action = RecordingService.ACTION_TOGGLE
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun updateTileUI(state: RecordingState) {
        val tile = qsTile ?: return
        when (state) {
            RecordingState.IDLE -> {
                tile.state = Tile.STATE_INACTIVE
                tile.label = "VoiceSnap"
                tile.icon = Icon.createWithResource(this, R.drawable.ic_tile_mic)
            }
            RecordingState.RECORDING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "\u00c9coute..."
                tile.icon = Icon.createWithResource(this, R.drawable.ic_tile_mic)
            }
            RecordingState.TRANSCRIBING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "Transcription..."
                tile.icon = Icon.createWithResource(this, R.drawable.ic_tile_mic)
            }
            RecordingState.TRANSLATING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "Traduction..."
                tile.icon = Icon.createWithResource(this, R.drawable.ic_tile_mic)
            }
        }
        tile.updateTile()
    }
}
