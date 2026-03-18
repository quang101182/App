package com.voicesnap.app.service

import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
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
import com.voicesnap.app.util.NetworkHelper
import com.voicesnap.app.util.NotificationHelper
import kotlinx.coroutines.*

class RecordingService : Service() {

    companion object {
        private const val TAG = "RecordingService"
        const val ACTION_START = "com.voicesnap.START"
        const val ACTION_STOP = "com.voicesnap.STOP"
        const val ACTION_TOGGLE = "com.voicesnap.TOGGLE"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val recorder = AudioRecorder()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val prefs by lazy { PrefsManager(this) }
    @Volatile private var isProcessing = false
    private var processingJob: Job? = null
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "onStartCommand action=${intent?.action}")

        // Only call startForeground for start/toggle actions, not STOP when already running
        val isStopAction = intent?.action == ACTION_STOP
        val isAlreadyRunning = recorder.isActive() || RecordingStateHolder.state.value != RecordingState.IDLE
        if (!(isStopAction && isAlreadyRunning)) {
            // CRITICAL: call startForeground IMMEDIATELY to avoid ANR/crash on Android 14+
            val notification = NotificationHelper.buildRecordingNotification(this, "D\u00e9marrage...")
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    startForeground(
                        Constants.NOTIF_ID_RECORDING,
                        notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
                    )
                } else {
                    startForeground(Constants.NOTIF_ID_RECORDING, notification)
                }
            } catch (e: Exception) {
                Log.e(TAG, "startForeground failed", e)
                stopSelf()
                return START_NOT_STICKY
            }
        }

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
        if (recorder.isActive()) {
            Log.d(TAG, "Already recording, ignoring start")
            return
        }

        Log.d(TAG, "Starting recording...")
        updateNotification("\u00c9coute...")
        RecordingStateHolder.update(RecordingState.RECORDING)

        // Acquire partial wake lock to keep CPU active during recording
        try {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "VoiceSnap::Recording").apply {
                acquire(Constants.MAX_RECORDING_MS + 30_000L) // max recording + processing buffer
            }
        } catch (e: Exception) {
            Log.e(TAG, "WakeLock acquire failed", e)
        }

        recorder.onSilenceDetected = {
            Log.d(TAG, "Silence detected, posting stop to main thread")
            // Must stop on main thread to avoid race conditions
            mainHandler.post { stopRecording() }
        }

        // Pass user-configured silence timeout to recorder
        val silenceTimeoutMs = prefs.getSilenceTimeoutSec() * 1000L
        recorder.setSilenceTimeout(silenceTimeoutMs)

        val started = recorder.start()
        if (!started) {
            Log.e(TAG, "Failed to start AudioRecorder")
            notifyError("Impossible de d\u00e9marrer le micro")
            cleanup()
        } else {
            Log.d(TAG, "Recording started successfully")
        }
    }

    private fun stopRecording() {
        if (isProcessing) {
            Log.d(TAG, "STOP pressed during processing — cancelling pipeline")
            processingJob?.cancel()
            cleanup()
            return
        }
        if (!recorder.isActive()) {
            Log.d(TAG, "Not recording, processing or cleaning up")
            // If we're not recording and not processing, just cleanup
            if (RecordingStateHolder.state.value == RecordingState.RECORDING) {
                cleanup()
            }
            return
        }
        isProcessing = true

        Log.d(TAG, "Stopping recording...")
        val wavData = recorder.stop()

        if (wavData.isEmpty()) {
            Log.w(TAG, "WAV data empty (too short)")
            notifyError("Enregistrement trop court (min 1.5s)")
            cleanup()
            return
        }

        Log.d(TAG, "WAV data: ${wavData.size} bytes")

        // Check network before calling API
        if (!NetworkHelper.isNetworkAvailable(this)) {
            notifyError("Pas de connexion internet")
            cleanup()
            return
        }

        updateNotification("Transcription...")
        RecordingStateHolder.update(RecordingState.TRANSCRIBING)

        processingJob = scope.launch {
            try {
                val srcLangCode = prefs.getSourceLang()
                val langObj = LANGUAGES.find { it.code == srcLangCode }
                val whisperLang = langObj?.whisperCode

                Log.d(TAG, "Calling Whisper API (lang=$whisperLang)...")
                val result = WhisperApi.transcribe(wavData, whisperLang)
                Log.d(TAG, "Whisper result: '${result.text}' (lang=${result.language})")

                if (result.text.isBlank()) {
                    notifyError("Aucune parole d\u00e9tect\u00e9e")
                    cleanup()
                    return@launch
                }

                var finalText = result.text
                var translatedText: String? = null

                // Translate if enabled
                if (prefs.isTranslateEnabled()) {
                    val detectedLang = result.language?.let { WHISPER_LANG_MAP[it.lowercase()] } ?: srcLangCode
                    val srcLang = if (srcLangCode == "auto") detectedLang else srcLangCode
                    val targetLang = prefs.getTargetLang()

                    val srcObj = LANGUAGES.find { it.code == srcLang }
                    val tgtObj = LANGUAGES.find { it.code == targetLang }

                    if (srcObj?.azureCode != null && tgtObj?.azureCode != null && srcObj.azureCode != tgtObj.azureCode) {
                        updateNotification("Traduction...")
                        RecordingStateHolder.update(RecordingState.TRANSLATING)
                        Log.d(TAG, "Translating ${srcObj.azureCode} -> ${tgtObj.azureCode}...")
                        try {
                            translatedText = AzureTranslateApi.translate(result.text, srcObj.azureCode, tgtObj.azureCode)
                            if (translatedText != null) {
                                finalText = translatedText!!
                                Log.d(TAG, "Translation: '$translatedText'")
                            } else {
                                Log.w(TAG, "Translation returned null, keeping original text")
                            }
                        } catch (e: Exception) {
                            Log.e(TAG, "Translation failed, keeping original text", e)
                            // Keep finalText = result.text (don't lose the transcription)
                        }
                    }
                }

                // Copy to clipboard
                ClipboardHelper.copyToClipboard(this@RecordingService, finalText)
                Log.d(TAG, "Copied to clipboard: '$finalText'")

                // Save to history
                val entry = HistoryEntry(
                    id = System.currentTimeMillis(),
                    text = result.text,
                    translatedText = translatedText,
                    sourceLang = srcLangCode,
                    targetLang = if (prefs.isTranslateEnabled()) prefs.getTargetLang() else null,
                    timestamp = System.currentTimeMillis()
                )
                prefs.addHistory(entry)

                // Result notification
                val notifText = if (translatedText == null && prefs.isTranslateEnabled()) {
                    "$finalText\n(traduction \u00e9chou\u00e9e)"
                } else {
                    finalText
                }
                val notifManager = getSystemService(NotificationManager::class.java)
                notifManager.notify(
                    Constants.NOTIF_ID_RESULT,
                    NotificationHelper.buildResultNotification(this@RecordingService, notifText)
                )

                // Vibrate
                vibrate()

                // Update state
                RecordingStateHolder.setResult(finalText)

            } catch (e: CancellationException) {
                Log.d(TAG, "Pipeline cancelled")
            } catch (e: Exception) {
                Log.e(TAG, "Pipeline error", e)
                notifyError(NetworkHelper.friendlyErrorMessage(e))
            } finally {
                cleanup()
            }
        }
    }

    private fun updateNotification(text: String) {
        try {
            val notifManager = getSystemService(NotificationManager::class.java)
            notifManager.notify(
                Constants.NOTIF_ID_RECORDING,
                NotificationHelper.buildRecordingNotification(this, text)
            )
        } catch (e: Exception) {
            Log.e(TAG, "updateNotification error", e)
        }
    }

    private fun notifyError(msg: String) {
        try {
            val notifManager = getSystemService(NotificationManager::class.java)
            notifManager.notify(
                Constants.NOTIF_ID_RESULT,
                NotificationHelper.buildErrorNotification(this, msg)
            )
        } catch (e: Exception) {
            Log.e(TAG, "notifyError error", e)
        }
    }

    private fun vibrate() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vm.defaultVibrator.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                val v = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                v.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Vibrate error", e)
        }
    }

    private fun cleanup() {
        Log.d(TAG, "Cleanup")
        isProcessing = false
        RecordingStateHolder.update(RecordingState.IDLE)
        NotificationHelper.releaseMediaSession()
        try {
            wakeLock?.let { if (it.isHeld) it.release() }
            wakeLock = null
        } catch (e: Exception) {
            Log.e(TAG, "WakeLock release error", e)
        }
        try {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } catch (e: Exception) {
            Log.e(TAG, "stopForeground error", e)
        }
        stopSelf()
    }

    override fun onDestroy() {
        Log.d(TAG, "onDestroy")
        scope.cancel()
        NotificationHelper.releaseMediaSession()
        if (recorder.isActive()) {
            recorder.stop()
        }
        RecordingStateHolder.update(RecordingState.IDLE)
        super.onDestroy()
    }
}
