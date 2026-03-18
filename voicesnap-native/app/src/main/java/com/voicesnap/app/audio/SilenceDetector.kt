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
        private const val NOISE_MULTIPLIER = 3.0
    }

    private var silenceStartTime: Long = 0L
    private var hasSpeech: Boolean = false
    private var firstFeedTime: Long = 0L

    // Adaptive calibration
    private var calibrationCount: Int = 0
    private var noiseFloorSum: Double = 0.0
    private var adaptiveThreshold: Double = baseThresholdRms
    private var calibrated: Boolean = false

    enum class Result {
        SPEECH,           // Voice detected
        SILENCE,          // Silence, no prior speech
        SILENCE_PENDING,  // Silence after speech, waiting
        SPEECH_END        // Silence > timeout -> stop
    }

    fun feed(buffer: ShortArray, readCount: Int): Result {
        val rms = calculateRms(buffer, readCount)
        val now = System.currentTimeMillis()

        if (firstFeedTime == 0L) {
            firstFeedTime = now
        }

        // Phase 1: Calibrate noise floor from first N buffers
        if (!calibrated) {
            noiseFloorSum += rms
            calibrationCount++
            if (calibrationCount >= calibrationBuffers) {
                val noiseFloor = noiseFloorSum / calibrationCount
                adaptiveThreshold = maxOf(noiseFloor * NOISE_MULTIPLIER, baseThresholdRms)
                calibrated = true
                Log.i(TAG, "Calibration done: noiseFloor=%.1f -> adaptiveThreshold=%.1f (base=%.1f)".format(
                    noiseFloor, adaptiveThreshold, baseThresholdRms))
            }
            return Result.SILENCE // During calibration, always silence
        }

        // Force hasSpeech after long delay (safety net for very quiet environments)
        if (!hasSpeech && (now - firstFeedTime) >= speechForceTimeoutMs) {
            Log.w(TAG, "Forcing hasSpeech=true after ${speechForceTimeoutMs}ms (RMS never exceeded threshold %.1f)".format(adaptiveThreshold))
            hasSpeech = true
        }

        if (calibrationCount % 50 == 0) {
            Log.d(TAG, "RMS=%.1f threshold=%.1f hasSpeech=$hasSpeech".format(rms, adaptiveThreshold))
        }

        return if (rms >= adaptiveThreshold) {
            hasSpeech = true
            silenceStartTime = 0L
            Result.SPEECH
        } else {
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
    }
}
