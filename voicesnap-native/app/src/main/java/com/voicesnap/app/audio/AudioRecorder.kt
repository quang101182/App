package com.voicesnap.app.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import com.voicesnap.app.util.Constants
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

class AudioRecorder {

    private var audioRecord: AudioRecord? = null
    private var recordingThread: Thread? = null
    @Volatile
    private var isRecording = false
    private val pcmOutputStream = ByteArrayOutputStream()
    private var silenceDetector = SilenceDetector()

    var onSilenceDetected: (() -> Unit)? = null
    var onAmplitude: ((Double) -> Unit)? = null

    private val sampleRate = Constants.SAMPLE_RATE
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioEncoding = AudioFormat.ENCODING_PCM_16BIT

    @SuppressLint("MissingPermission")
    fun start(): Boolean {
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioEncoding)
        if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
            Log.e("AudioRecorder", "Invalid buffer size: $bufferSize")
            return false
        }

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            channelConfig,
            audioEncoding,
            bufferSize * 2
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            Log.e("AudioRecorder", "AudioRecord failed to initialize")
            audioRecord?.release()
            audioRecord = null
            return false
        }

        pcmOutputStream.reset()
        silenceDetector.reset()
        isRecording = true
        audioRecord?.startRecording()

        recordingThread = Thread {
            val buffer = ShortArray(bufferSize / 2)
            val startTime = System.currentTimeMillis()

            while (isRecording) {
                val readCount = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (readCount <= 0) continue

                // Write PCM data
                val byteBuffer = ByteBuffer.allocate(readCount * 2).order(ByteOrder.LITTLE_ENDIAN)
                for (i in 0 until readCount) {
                    byteBuffer.putShort(buffer[i])
                }
                synchronized(pcmOutputStream) {
                    pcmOutputStream.write(byteBuffer.array(), 0, readCount * 2)
                }

                // RMS for UI feedback
                var sum = 0.0
                for (i in 0 until readCount) {
                    val v = buffer[i].toDouble()
                    sum += v * v
                }
                val rms = kotlin.math.sqrt(sum / readCount)
                onAmplitude?.invoke(rms)

                // Check max recording timeout
                val elapsed = System.currentTimeMillis() - startTime
                if (elapsed > Constants.MAX_RECORDING_MS) {
                    Log.w("AudioRecorder", "Max recording duration reached (${Constants.MAX_RECORDING_MS}ms)")
                    onSilenceDetected?.invoke()
                    break
                }

                // VAD — only check after minimum recording time
                if (elapsed > Constants.MIN_RECORDING_MS) {
                    val result = silenceDetector.feed(buffer, readCount)
                    if (result == SilenceDetector.Result.SPEECH_END) {
                        onSilenceDetected?.invoke()
                        break
                    }
                }
            }
        }
        recordingThread?.start()
        return true
    }

    fun stop(): ByteArray {
        isRecording = false
        recordingThread?.join(2000)
        recordingThread = null

        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        val pcmData: ByteArray
        synchronized(pcmOutputStream) {
            pcmData = pcmOutputStream.toByteArray()
            pcmOutputStream.reset()
        }

        // Check minimum duration
        val durationMs = (pcmData.size.toLong() * 1000L) / (sampleRate * 2)
        if (durationMs < Constants.MIN_RECORDING_MS) {
            Log.w("AudioRecorder", "Recording too short: ${durationMs}ms")
            return ByteArray(0)
        }

        return WavEncoder.encode(pcmData, sampleRate)
    }

    fun setSilenceTimeout(timeoutMs: Long) {
        silenceDetector = SilenceDetector(timeoutMs = timeoutMs)
    }

    fun isActive(): Boolean = isRecording
}
