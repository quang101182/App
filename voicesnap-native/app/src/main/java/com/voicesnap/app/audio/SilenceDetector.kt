package com.voicesnap.app.audio

import android.util.Log
import com.voicesnap.app.util.Constants
import kotlin.math.sqrt

class SilenceDetector(
    private val thresholdRms: Double = Constants.SILENCE_THRESHOLD_RMS,
    private val timeoutMs: Long = Constants.SILENCE_TIMEOUT_MS,
    private val speechForceTimeoutMs: Long = Constants.SPEECH_FORCE_TIMEOUT_MS
) {
    companion object {
        private const val TAG = "SilenceDetector"
    }

    private var silenceStartTime: Long = 0L
    private var hasSpeech: Boolean = false
    private var firstFeedTime: Long = 0L

    enum class Result {
        SPEECH,           // Voice detected
        SILENCE,          // Silence, no prior speech
        SILENCE_PENDING,  // Silence after speech, waiting
        SPEECH_END        // Silence > timeout → stop
    }

    fun feed(buffer: ShortArray, readCount: Int): Result {
        val rms = calculateRms(buffer, readCount)
        val now = System.currentTimeMillis()

        // Track first feed time for forced hasSpeech
        if (firstFeedTime == 0L) {
            firstFeedTime = now
        }

        // Force hasSpeech=true after delay even if RMS never exceeded threshold
        // This prevents infinite recording in quiet environments
        if (!hasSpeech && (now - firstFeedTime) >= speechForceTimeoutMs) {
            Log.w(TAG, "Forcing hasSpeech=true after ${speechForceTimeoutMs}ms (RMS never exceeded threshold $thresholdRms)")
            hasSpeech = true
        }

        Log.d(TAG, "RMS=%.1f threshold=%.1f hasSpeech=$hasSpeech".format(rms, thresholdRms))

        return if (rms >= thresholdRms) {
            hasSpeech = true
            silenceStartTime = 0L
            Result.SPEECH
        } else {
            if (hasSpeech) {
                if (silenceStartTime == 0L) silenceStartTime = now
                val elapsed = now - silenceStartTime
                if (elapsed >= timeoutMs) {
                    Log.i(TAG, "SPEECH_END: silence for ${elapsed}ms >= ${timeoutMs}ms")
                    Result.SPEECH_END
                } else {
                    Result.SILENCE_PENDING
                }
            } else {
                Result.SILENCE
            }
        }
    }

    private fun calculateRms(buffer: ShortArray, count: Int): Double {
        if (count <= 0) return 0.0
        var sum = 0.0
        for (i in 0 until count) {
            val v = buffer[i].toDouble()
            sum += v * v
        }
        return sqrt(sum / count)
    }

    fun reset() {
        silenceStartTime = 0L
        hasSpeech = false
        firstFeedTime = 0L
    }
}
