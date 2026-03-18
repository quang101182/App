package com.voicesnap.app.service

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.core.content.ContextCompat
import com.voicesnap.app.ui.MainActivity

/**
 * Invisible trampoline Activity that launches the RecordingService.
 * This ensures a foreground context exists when starting the service,
 * which is required on Android 14+ and Honor MagicOS.
 *
 * Flow: QS Tile click → TrampolineActivity → starts ForegroundService → finishes immediately
 */
class TrampolineActivity : Activity() {

    companion object {
        private const val TAG = "Trampoline"
        const val EXTRA_ACTION = "trampoline_action"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate action=${intent?.getStringExtra(EXTRA_ACTION)}")

        // Check permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.w(TAG, "RECORD_AUDIO not granted, redirecting to MainActivity")
            startActivity(Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                putExtra("request_permission", true)
            })
            finish()
            return
        }

        val action = intent?.getStringExtra(EXTRA_ACTION) ?: RecordingService.ACTION_TOGGLE

        try {
            val serviceIntent = Intent(this, RecordingService::class.java).apply {
                this.action = action
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
            Log.d(TAG, "Service started with action=$action")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start service", e)
            Toast.makeText(this, "VoiceSnap: impossible de démarrer le service", Toast.LENGTH_SHORT).show()
        }

        // Close immediately — no UI shown
        finish()
    }
}
