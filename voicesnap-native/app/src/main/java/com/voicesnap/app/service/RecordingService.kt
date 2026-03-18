package com.voicesnap.app.service

import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import com.voicesnap.app.api.AzureTranslateApi
import com.voicesnap.app.api.WhisperApi
import com.voicesnap.app.audio.AudioRecorder
import com.voicesnap.app.data.HistoryEntry
import com.voicesnap.app.data.LANGUAGES
import com.voicesnap.app.data.PrefsManager
import com.voicesnap.app.data.WHISPER_LANG_MAP
import com.voicesnap.app.util.ClipboardHelper
import com.voicesnap.app.util.Constants
import com.voicesnap.app.util.NotificationHelper
import kotlinx.coroutines.*

class RecordingService : Service() {

    companion object {
        const val ACTION_START = "com.voicesnap.START"
        const val ACTION_STOP = "com.voicesnap.STOP"
        const val ACTION_TOGGLE = "com.voicesnap.TOGGLE"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val recorder = AudioRecorder()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startRecording()
            ACTION_STOP -> stopRecording()
            ACTION_TOGGLE -> {
                if (recorder.isActive()) stopRecording() else startRecording()
            }
            else -> startRecording()
        }
        return START_NOT_STICKY
    }

    private fun startRecording() {
        if (recorder.isActive()) return

        val notification = NotificationHelper.buildRecordingNotification(this, "\u00c9coute...")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                Constants.NOTIF_ID_RECORDING,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(Constants.NOTIF_ID_RECORDING, notification)
        }

        RecordingStateHolder.update(RecordingState.RECORDING)

        recorder.onSilenceDetected = {
            Log.d("RecordingService", "Silence detected, stopping")
            stopRecording()
        }

        val started = recorder.start()
        if (!started) {
            Log.e("RecordingService", "Failed to start recorder")
            notifyError("Impossible de d\u00e9marrer le micro")
            cleanup()
        }
    }

    private fun stopRecording() {
        if (!recorder.isActive()) return

        val wavData = recorder.stop()

        if (wavData.isEmpty()) {
            notifyError("Enregistrement trop court")
            cleanup()
            return
        }

        // Update notification
        updateNotification("Transcription...")
        RecordingStateHolder.update(RecordingState.TRANSCRIBING)

        scope.launch {
            try {
                val prefs = PrefsManager(this@RecordingService)
                val srcLangCode = prefs.getSourceLang()
                val langObj = LANGUAGES.find { it.code == srcLangCode }
                val whisperLang = langObj?.whisperCode

                // 1. Transcribe
                val result = WhisperApi.transcribe(wavData, whisperLang)

                if (result.text.isBlank()) {
                    notifyError("Aucune parole d\u00e9tect\u00e9e")
                    cleanup()
                    return@launch
                }

                var finalText = result.text
                var translatedText: String? = null

                // 2. Translate if enabled
                if (prefs.isTranslateEnabled()) {
                    val detectedLang = result.language?.let { WHISPER_LANG_MAP[it.lowercase()] } ?: srcLangCode
                    val srcLang = if (srcLangCode == "auto") detectedLang else srcLangCode
                    val targetLang = prefs.getTargetLang()

                    val srcObj = LANGUAGES.find { it.code == srcLang }
                    val tgtObj = LANGUAGES.find { it.code == targetLang }

                    if (srcObj?.azureCode != null && tgtObj?.azureCode != null && srcObj.azureCode != tgtObj.azureCode) {
                        updateNotification("Traduction...")
                        RecordingStateHolder.update(RecordingState.TRANSLATING)
                        translatedText = AzureTranslateApi.translate(result.text, srcObj.azureCode, tgtObj.azureCode)
                        finalText = translatedText
                    }
                }

                // 3. Copy to clipboard
                ClipboardHelper.copyToClipboard(this@RecordingService, finalText)

                // 4. Save to history
                val entry = HistoryEntry(
                    id = System.currentTimeMillis(),
                    text = result.text,
                    translatedText = translatedText,
                    sourceLang = srcLangCode,
                    targetLang = if (prefs.isTranslateEnabled()) prefs.getTargetLang() else null,
                    timestamp = System.currentTimeMillis()
                )
                prefs.addHistory(entry)

                // 5. Result notification
                val notifManager = getSystemService(NotificationManager::class.java)
                notifManager.notify(
                    Constants.NOTIF_ID_RESULT,
                    NotificationHelper.buildResultNotification(this@RecordingService, finalText)
                )

                // 6. Vibrate
                vibrate()

                // 7. Update state
                RecordingStateHolder.setResult(finalText)

            } catch (e: Exception) {
                Log.e("RecordingService", "Pipeline error", e)
                notifyError(e.message ?: "Erreur inconnue")
            } finally {
                cleanup()
            }
        }
    }

    private fun updateNotification(text: String) {
        val notifManager = getSystemService(NotificationManager::class.java)
        notifManager.notify(
            Constants.NOTIF_ID_RECORDING,
            NotificationHelper.buildRecordingNotification(this, text)
        )
    }

    private fun notifyError(msg: String) {
        val notifManager = getSystemService(NotificationManager::class.java)
        notifManager.notify(
            Constants.NOTIF_ID_RESULT,
            NotificationHelper.buildErrorNotification(this, msg)
        )
    }

    private fun vibrate() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vm = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vm.defaultVibrator.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            val v = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            v.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
        }
    }

    private fun cleanup() {
        RecordingStateHolder.update(RecordingState.IDLE)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        scope.cancel()
        if (recorder.isActive()) {
            recorder.stop()
        }
        RecordingStateHolder.update(RecordingState.IDLE)
        super.onDestroy()
    }
}
