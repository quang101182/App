package com.voicesnap.app.audio

import com.voicesnap.app.util.Constants
import kotlin.math.sqrt

class SilenceDetector(
    private val thresholdRms: Double = Constants.SILENCE_THRESHOLD_RMS,
    private val timeoutMs: Long = Constants.SILENCE_TIMEOUT_MS
) {
    private var silenceStartTime: Long = 0L
    private var hasSpeech: Boolean = false

    enum class Result {
        SPEECH,           // Voice detected
        SILENCE,          // Silence, no prior speech
        SILENCE_PENDING,  // Silence after speech, waiting
        SPEECH_END        // Silence > timeout → stop
    }

    fun feed(buffer: ShortArray, readCount: Int): Result {
        val rms = calculateRms(buffer, readCount)
        val now = System.currentTimeMillis()

        return if (rms >= thresholdRms) {
            hasSpeech = true
            silenceStartTime = 0L
            Result.SPEECH
        } else {
            if (hasSpeech) {
                if (silenceStartTime == 0L) silenceStartTime = now
                val elapsed = now - silenceStartTime
                if (elapsed >= timeoutMs) {
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
    }
}
