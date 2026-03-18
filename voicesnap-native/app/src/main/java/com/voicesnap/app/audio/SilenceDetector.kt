package com.voicesnap.app.audio

import android.util.Log
import com.voicesnap.app.util.Constants
import kotlin.math.sqrt

class SilenceDetector(
    private val baseThresholdRms: Double = Constants.SILENCE_THRESHOLD_RMS,
    private val timeoutMs: Long = Constants.SILENCE_TIMEOUT_MS,
    private val speechForceTimeoutMs: Long = Constants.SPEECH_FORCE_TIMEOUT_MS,
    private val calibrationBuffers: Int = 20 // ~0.5s at 16kHz
) {
    companion object {
        private const val TAG = "SilenceDetector"
        private const val NOISE_MULTIPLIER = 2.0
        private const val SPEECH_CONFIRM_BUFFERS = 3 // consecutive speech buffers to confirm speech
    }

    private var silenceStartTime: Long = 0L
    private var hasSpeech: Boolean = false
    private var firstFeedTime: Long = 0L

    // Adaptive calibration
    private var calibrationCount: Int = 0
    private var noiseFloorSum: Double = 0.0
    private var adaptiveThreshold: Double = baseThresholdRms
    private var calibrated: Boolean = false

    // Speech confirmation — require N consecutive above-threshold buffers
    private var consecutiveSpeechBuffers: Int = 0

    // Logging throttle
    private var totalBuffers: Int = 0

    enum class Result {
        SPEECH,           // Voice detected
        SILENCE,          // Silence, no prior speech
        SILENCE_PENDING,  // Silence after speech, waiting
        SPEECH_END        // Silence > timeout -> stop
    }

    fun feed(buffer: ShortArray, readCount: Int): Result {
        val rms = calculateRms(buffer, readCount)
        val now = System.currentTimeMillis()
        totalBuffers++

        if (firstFeedTime == 0L) {
            firstFeedTime = now
        }

        // Phase 1: Calibrate noise floor from first N buffers (ambient noise BEFORE user speaks)
        if (!calibrated) {
            noiseFloorSum += rms
            calibrationCount++
            if (calibrationCount >= calibrationBuffers) {
                val noiseFloor = noiseFloorSum / calibrationCount
                adaptiveThreshold = maxOf(noiseFloor * NOISE_MULTIPLIER, baseThresholdRms)
                calibrated = true
                Log.i(TAG, "Calibration done: noiseFloor=%.1f -> adaptiveThreshold=%.1f (base=%.1f, multiplier=%.1f)".format(
                    noiseFloor, adaptiveThreshold, baseThresholdRms, NOISE_MULTIPLIER))
            }
            return Result.SILENCE // During calibration, always silence
        }

        // Log every 50 buffers for diagnostics
        if (totalBuffers % 50 == 0) {
            Log.d(TAG, "RMS=%.1f threshold=%.1f hasSpeech=$hasSpeech consecutive=$consecutiveSpeechBuffers".format(rms, adaptiveThreshold))
        }

        // Force hasSpeech after long delay (safety net for very quiet environments)
        if (!hasSpeech && (now - firstFeedTime) >= speechForceTimeoutMs) {
            Log.w(TAG, "Forcing hasSpeech=true after ${speechForceTimeoutMs}ms (RMS never exceeded threshold %.1f)".format(adaptiveThreshold))
            hasSpeech = true
        }

        return if (rms >= adaptiveThreshold) {
            consecutiveSpeechBuffers++
            if (!hasSpeech && consecutiveSpeechBuffers >= SPEECH_CONFIRM_BUFFERS) {
                hasSpeech = true
                Log.i(TAG, "Speech confirmed after $SPEECH_CONFIRM_BUFFERS consecutive buffers (RMS=%.1f)".format(rms))
            }
            silenceStartTime = 0L
            if (hasSpeech) Result.SPEECH else Result.SILENCE
        } else {
            consecutiveSpeechBuffers = 0
            if (hasSpeech) {
                if (silenceStartTime == 0L) silenceStartTime = now
                val elapsed = now - silenceStartTime
                if (elapsed >= timeoutMs) {
                    Log.i(TAG, "SPEECH_END: silence for ${elapsed}ms >= ${timeoutMs}ms (threshold=%.1f)".format(adaptiveThreshold))
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
        calibrationCount = 0
        noiseFloorSum = 0.0
        adaptiveThreshold = baseThresholdRms
        calibrated = false
        consecutiveSpeechBuffers = 0
        totalBuffers = 0
    }
}
