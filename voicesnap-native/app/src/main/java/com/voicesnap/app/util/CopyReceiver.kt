package com.voicesnap.app.util

import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast

/**
 * BroadcastReceiver that copies text to clipboard when notification is tapped.
 * Keeps the text accessible even if clipboard was overwritten.
 */
class CopyReceiver : BroadcastReceiver() {

    companion object {
        const val EXTRA_TEXT = "copy_text"
        const val ACTION_COPY = "com.voicesnap.COPY_TEXT"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val text = intent.getStringExtra(EXTRA_TEXT) ?: return
        ClipboardHelper.copyToClipboard(context, text)
        Toast.makeText(context, "Texte copi\u00e9", Toast.LENGTH_SHORT).show()
    }
}
