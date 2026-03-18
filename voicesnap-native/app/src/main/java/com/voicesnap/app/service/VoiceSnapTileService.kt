package com.voicesnap.app.service

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.util.Log
import androidx.core.content.ContextCompat
import com.voicesnap.app.R
import com.voicesnap.app.ui.MainActivity
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
        Log.d(TAG, "Tile clicked!")

        // Check RECORD_AUDIO permission first
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.w(TAG, "RECORD_AUDIO not granted, opening MainActivity")
            val intent = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                putExtra("request_permission", true)
            }
            startActivityAndCollapse(intent)
            return
        }

        // If currently recording, stop it
        if (RecordingStateHolder.state.value == RecordingState.RECORDING) {
            Log.d(TAG, "Stopping recording")
            val intent = Intent(this, RecordingService::class.java).apply {
                action = RecordingService.ACTION_STOP
            }
            startService(intent)
            return
        }

        // If not idle (transcribing/translating), ignore
        if (RecordingStateHolder.state.value != RecordingState.IDLE) {
            Log.d(TAG, "Not idle, ignoring: ${RecordingStateHolder.state.value}")
            return
        }

        // Start recording - handle locked screen
        Log.d(TAG, "Starting recording service")
        try {
            val intent = Intent(this, RecordingService::class.java).apply {
                action = RecordingService.ACTION_START
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start service", e)
            // Fallback: open app
            val intent = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            startActivityAndCollapse(intent)
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
