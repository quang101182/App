package com.voicesnap.app.util

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.core.app.NotificationCompat
import androidx.media.app.NotificationCompat as MediaNotificationCompat
import com.voicesnap.app.R
import com.voicesnap.app.service.RecordingService
import com.voicesnap.app.ui.MainActivity
import com.voicesnap.app.ui.TextViewerActivity

object NotificationHelper {

    private var mediaSession: MediaSessionCompat? = null

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(NotificationManager::class.java)

            // Delete old channel if importance changed
            try {
                manager.getNotificationChannel(Constants.CHANNEL_RECORDING)?.let {
                    if (it.importance != NotificationManager.IMPORTANCE_LOW) {
                        manager.deleteNotificationChannel(Constants.CHANNEL_RECORDING)
                    }
                }
            } catch (_: Exception) {}

            val recordingChannel = NotificationChannel(
                Constants.CHANNEL_RECORDING,
                "Enregistrement",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notification pendant l'enregistrement vocal"
                setShowBadge(false)
                enableVibration(false)
                setSound(null, null)
            }

            val resultChannel = NotificationChannel(
                Constants.CHANNEL_RESULT,
                "R\u00e9sultats",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notification du texte transcrit"
            }

            manager.createNotificationChannel(recordingChannel)
            manager.createNotificationChannel(resultChannel)
        }
    }

    fun getOrCreateMediaSession(context: Context): MediaSessionCompat {
        mediaSession?.let { return it }

        val session = MediaSessionCompat(context, "VoiceSnapRecorder").apply {
            val state = PlaybackStateCompat.Builder()
                .setState(PlaybackStateCompat.STATE_PLAYING, 0L, 1f)
                .setActions(PlaybackStateCompat.ACTION_STOP or PlaybackStateCompat.ACTION_PAUSE)
                .build()
            setPlaybackState(state)

            setCallback(object : MediaSessionCompat.Callback() {
                override fun onStop() {
                    val stopIntent = Intent(context, RecordingService::class.java).apply {
                        action = RecordingService.ACTION_STOP
                    }
                    context.startService(stopIntent)
                }
                override fun onPause() {
                    onStop()
                }
            })

            isActive = true
        }
        mediaSession = session
        return session
    }

    fun releaseMediaSession() {
        mediaSession?.apply {
            isActive = false
            release()
        }
        mediaSession = null
    }

    fun buildRecordingNotification(context: Context, state: String): Notification {
        // PendingIntent to stop recording
        val stopIntent = Intent(context, RecordingService::class.java).apply {
            action = RecordingService.ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            context, 100, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val session = getOrCreateMediaSession(context)

        val builder = NotificationCompat.Builder(context, Constants.CHANNEL_RECORDING)
            .setSmallIcon(R.drawable.ic_tile_mic)
            .setContentTitle("VoiceSnap")
            .setContentText(state)
            .setOngoing(true)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            // STOP action at index 0
            .addAction(
                android.R.drawable.ic_media_pause,
                "STOP",
                stopPendingIntent
            )
            // MediaStyle with session token — forces action visible in compact view
            .setStyle(
                MediaNotificationCompat.MediaStyle()
                    .setMediaSession(session.sessionToken)
                    .setShowActionsInCompactView(0)
            )

        // Show chronometer only during active recording
        if (state.contains("coute", ignoreCase = true)) {
            builder.setUsesChronometer(true)
                .setWhen(System.currentTimeMillis())
        }

        return builder.build()
    }

    fun buildResultNotification(context: Context, text: String): Notification {
        // Tap notification → open full text viewer
        val viewIntent = Intent(context, TextViewerActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("viewer_text", text)
        }
        val viewPendingIntent = PendingIntent.getActivity(
            context, text.hashCode(), viewIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val preview = if (text.length > 80) text.take(80) + "\u2026" else text

        return NotificationCompat.Builder(context, Constants.CHANNEL_RESULT)
            .setSmallIcon(R.drawable.ic_tile_mic)
            .setContentTitle("Transcription")
            .setContentText(preview)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setContentIntent(viewPendingIntent)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
    }

    fun buildErrorNotification(context: Context, error: String): Notification {
        return NotificationCompat.Builder(context, Constants.CHANNEL_RESULT)
            .setSmallIcon(R.drawable.ic_tile_mic)
            .setContentTitle("VoiceSnap - Erreur")
            .setContentText(error)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
    }
}
