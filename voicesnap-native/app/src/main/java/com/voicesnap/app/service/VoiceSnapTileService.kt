package com.voicesnap.app.service

import android.app.PendingIntent
import android.content.Intent
import android.graphics.drawable.Icon
import android.os.Build
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
        scope?.cancel()
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
        val currentState = RecordingStateHolder.state.value
        Log.d(TAG, "Tile clicked! state=$currentState")

        val action = when (currentState) {
            RecordingState.RECORDING -> RecordingService.ACTION_STOP
            RecordingState.IDLE -> RecordingService.ACTION_START
            else -> {
                Log.d(TAG, "Busy ($currentState), ignoring")
                return
            }
        }

        try {
            val intent = Intent(this, TrampolineActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION
                putExtra(TrampolineActivity.EXTRA_ACTION, action)
            }

            // Android 14+ requires PendingIntent version
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                val pendingIntent = PendingIntent.getActivity(
                    this, action.hashCode(), intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                startActivityAndCollapse(pendingIntent)
                Log.d(TAG, "Launched via PendingIntent (API 34+)")
            } else {
                @Suppress("DEPRECATION")
                startActivityAndCollapse(intent)
                Log.d(TAG, "Launched via Intent (legacy)")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch trampoline", e)
            // Fallback: open MainActivity instead of direct service start (which would crash)
            try {
                val fallbackIntent = Intent(this, com.voicesnap.app.ui.MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                startActivity(fallbackIntent)
                Log.d(TAG, "Fallback: opened MainActivity")
            } catch (e2: Exception) {
                Log.e(TAG, "Fallback also failed", e2)
            }
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
            RecordingState.REWRITING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "R\u00e9\u00e9criture..."
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
