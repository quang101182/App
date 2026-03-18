package com.voicesnap.app.service

import android.app.Activity
import android.app.NotificationManager
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.OpenableColumns
import android.util.Log
import android.widget.Toast
import com.voicesnap.app.api.WhisperApi
import com.voicesnap.app.data.PrefsManager
import com.voicesnap.app.data.LANGUAGES
import com.voicesnap.app.util.ClipboardHelper
import com.voicesnap.app.util.Constants
import com.voicesnap.app.util.NetworkHelper
import com.voicesnap.app.util.NotificationHelper
import kotlinx.coroutines.*

/**
 * Invisible Activity that receives shared audio files (from WhatsApp, Telegram, etc.),
 * transcribes them via Whisper, and copies the result to clipboard.
 * No UI shown — just notification + clipboard + vibration, like Tile mode.
 */
class ShareReceiverActivity : Activity() {

    companion object {
        private const val TAG = "ShareReceiver"
        private const val MAX_FILE_SIZE = 25 * 1024 * 1024 // 25 MB (Groq limit)
        private val SUPPORTED_TYPES = setOf(
            "audio/ogg", "audio/opus", "audio/mpeg", "audio/mp3", "audio/mp4",
            "audio/m4a", "audio/wav", "audio/x-wav", "audio/webm", "audio/flac",
            "audio/aac", "audio/x-m4a", "video/mp4" // some apps send voice as video/mp4
        )
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val uri = getAudioUri(intent)
        if (uri == null) {
            Log.e(TAG, "No audio URI in intent")
            Toast.makeText(this, "Format non supporté", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Read bytes IMMEDIATELY (URI permission is temporary)
        val audioData: ByteArray
        val fileName: String
        val mimeType: String
        try {
            mimeType = contentResolver.getType(uri) ?: intent.type ?: "audio/ogg"
            fileName = getFileName(uri) ?: "audio.ogg"

            if (!SUPPORTED_TYPES.contains(mimeType.lowercase()) && !mimeType.startsWith("audio/")) {
                Toast.makeText(this, "Format audio non supporté", Toast.LENGTH_SHORT).show()
                finish()
                return
            }

            audioData = contentResolver.openInputStream(uri)?.use { it.readBytes() }
                ?: throw Exception("Cannot read file")

            if (audioData.size > MAX_FILE_SIZE) {
                Toast.makeText(this, "Fichier trop volumineux (max 25 Mo)", Toast.LENGTH_SHORT).show()
                finish()
                return
            }

            Log.d(TAG, "Audio loaded: ${audioData.size} bytes, type=$mimeType, name=$fileName")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to read audio", e)
            Toast.makeText(this, "Impossible de lire le fichier audio", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Show processing notification
        NotificationHelper.createChannels(this)
        val notifManager = getSystemService(NotificationManager::class.java)
        notifManager.notify(
            Constants.NOTIF_ID_RESULT,
            NotificationHelper.buildResultNotification(this, "Transcription en cours...")
        )

        // Finish activity immediately — user stays in WhatsApp/Telegram
        finish()

        // Transcribe in background
        scope.launch {
            try {
                val prefs = PrefsManager(this@ShareReceiverActivity)
                val srcLangCode = prefs.getSourceLang()
                val langObj = LANGUAGES.find { it.code == srcLangCode }
                val whisperLang = langObj?.whisperCode

                val result = WhisperApi.transcribe(audioData, fileName, mimeType, whisperLang)
                Log.d(TAG, "Transcription: '${result.text}' (lang=${result.language})")

                if (result.text.isBlank()) {
                    notifManager.notify(
                        Constants.NOTIF_ID_RESULT,
                        NotificationHelper.buildErrorNotification(
                            this@ShareReceiverActivity, "Aucune parole détectée"
                        )
                    )
                    return@launch
                }

                // Copy to clipboard
                ClipboardHelper.copyToClipboard(this@ShareReceiverActivity, result.text)

                // Show result notification
                notifManager.notify(
                    Constants.NOTIF_ID_RESULT,
                    NotificationHelper.buildResultNotification(this@ShareReceiverActivity, result.text)
                )

                // Vibrate
                vibrate()

            } catch (e: CancellationException) {
                // Ignore
            } catch (e: Exception) {
                Log.e(TAG, "Transcription failed", e)
                notifManager.notify(
                    Constants.NOTIF_ID_RESULT,
                    NotificationHelper.buildErrorNotification(
                        this@ShareReceiverActivity, NetworkHelper.friendlyErrorMessage(e)
                    )
                )
            }
        }
    }

    private fun getAudioUri(intent: Intent?): Uri? {
        if (intent?.action != Intent.ACTION_SEND) return null
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }
    }

    private fun getFileName(uri: Uri): String? {
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx >= 0) return cursor.getString(idx)
            }
        }
        return uri.lastPathSegment
    }

    private fun vibrate() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vm.defaultVibrator.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                val v = getSystemService(VIBRATOR_SERVICE) as Vibrator
                v.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
            }
        } catch (_: Exception) {}
    }

    override fun onDestroy() {
        // Don't cancel scope here — transcription runs after activity finishes
        super.onDestroy()
    }
}
