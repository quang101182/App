package com.voicesnap.app.util

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.voicesnap.app.R
import com.voicesnap.app.ui.MainActivity

object NotificationHelper {

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(NotificationManager::class.java)

            val recordingChannel = NotificationChannel(
                Constants.CHANNEL_RECORDING,
                "Enregistrement",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notification pendant l'enregistrement vocal"
                setShowBadge(false)
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

    fun buildRecordingNotification(context: Context, state: String): Notification {
        return NotificationCompat.Builder(context, Constants.CHANNEL_RECORDING)
            .setSmallIcon(R.drawable.ic_tile_mic)
            .setContentTitle("VoiceSnap")
            .setContentText(state)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
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
            .setContentTitle("Texte copi\u00e9")
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
