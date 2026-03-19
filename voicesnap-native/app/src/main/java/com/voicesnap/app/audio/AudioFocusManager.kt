package com.voicesnap.app.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.util.Log

class AudioFocusManager(context: Context) {

    companion object {
        private const val TAG = "AudioFocusManager"
    }

    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var focusRequest: AudioFocusRequest? = null
    private var hasFocus = false

    private val focusChangeListener = AudioManager.OnAudioFocusChangeListener { change ->
        when (change) {
            AudioManager.AUDIOFOCUS_LOSS -> {
                hasFocus = false
                Log.d(TAG, "Audio focus lost permanently")
            }
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> {
                Log.d(TAG, "Audio focus lost transiently")
            }
            AudioManager.AUDIOFOCUS_GAIN -> {
                hasFocus = true
                Log.d(TAG, "Audio focus gained")
            }
        }
    }

    fun requestFocus(): Boolean {
        if (hasFocus) return true
        val attributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANT)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()

        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(attributes)
            .setOnAudioFocusChangeListener(focusChangeListener)
            .setAcceptsDelayedFocusGain(false)
            .build()

        focusRequest = request
        val result = audioManager.requestAudioFocus(request)
        hasFocus = (result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED)
        Log.d(TAG, "requestFocus: ${if (hasFocus) "GRANTED" else "DENIED"}")
        return hasFocus
    }

    fun abandonFocus() {
        focusRequest?.let {
            audioManager.abandonAudioFocusRequest(it)
            hasFocus = false
            focusRequest = null
            Log.d(TAG, "Audio focus abandoned")
        }
    }
}
