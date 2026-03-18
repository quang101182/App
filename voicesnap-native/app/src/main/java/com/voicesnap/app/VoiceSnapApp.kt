package com.voicesnap.app

import android.app.Application
import com.voicesnap.app.util.NotificationHelper

class VoiceSnapApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationHelper.createChannels(this)
    }
}
