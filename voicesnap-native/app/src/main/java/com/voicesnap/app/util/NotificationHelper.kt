package com.voicesnap.app.util

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.RemoteViews
import androidx.core.app.NotificationCompat
import com.voicesnap.app.R
import com.voicesnap.app.service.RecordingService
import com.voicesnap.app.ui.MainActivity

object NotificationHelper {

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(NotificationManager::class.java)

            // Delete old LOW importance channel if it exists, to recreate as HIGH
            try {
                manager.getNotificationChannel(Constants.CHANNEL_RECORDING)?.let {
                    if (it.importance != NotificationManager.IMPORTANCE_HIGH) {
                        manager.deleteNotificationChannel(Constants.CHANNEL_RECORDING)
                    }
                }
            } catch (_: Exception) {}

            val recordingChannel = NotificationChannel(
                Constants.CHANNEL_RECORDING,
                "Enregistrement",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notification pendant l'enregistrement vocal"
                setShowBadge(false)
                enableVibration(false)
                setSound(null, null)
            }

            val resultChannel = NotificationChannel(
                Constants.CHANNEL_RESULT,
                "Résultats",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notification du texte transcrit"
            }

            manager.createNotificationChannel(recordingChannel)
            manager.createNotificationChannel(resultChannel)
        }
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

        // Custom layout with visible STOP button (no expand needed)
        val customView = RemoteViews(context.packageName, R.layout.notification_recording)
        customView.setTextViewText(R.id.notif_state, state)
        customView.setOnClickPendingIntent(R.id.notif_stop_btn, stopPendingIntent)

        val builder = NotificationCompat.Builder(context, Constants.CHANNEL_RECORDING)
            .setSmallIcon(R.drawable.ic_tile_mic)
            .setCustomContentView(customView)
            .setCustomBigContentView(customView)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            // Keep action as fallback
            .addAction(
                android.R.drawable.ic_media_pause,
                "STOP",
                stopPendingIntent
            )

        return builder.build()
    }

    fun buildResultNotification(context: Context, text: String): Notification {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("result_text", text)
        }
        val pendingIntent = PendingIntent.getActivity(
            context, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val preview = if (text.length > 80) text.take(80) + "\u2026" else text

        return NotificationCompat.Builder(context, Constants.CHANNEL_RESULT)
            .setSmallIcon(R.drawable.ic_tile_mic)
            .setContentTitle("Texte copié")
            .setContentText(preview)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
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
