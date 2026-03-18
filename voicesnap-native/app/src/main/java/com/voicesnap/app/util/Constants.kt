package com.voicesnap.app.util

object Constants {
    const val APP_VERSION = "1.0.2"

    // API Gateway
    const val GATEWAY_URL = "https://api-gateway.quang101182.workers.dev"
    const val WORKER_SECRET = "333a33b16f8cab5aec61eb5806eeaee332a50e1172ad1b3e3d710b3d84b9cc7b"
    const val WHISPER_PATH = "/api/groq"
    const val WHISPER_API_PATH_HEADER = "/openai/v1/audio/transcriptions"
    const val WHISPER_MODEL = "whisper-large-v3-turbo"
    const val AZURE_PATH = "/api/azure"

    // Audio
    const val SAMPLE_RATE = 16000
    const val SILENCE_TIMEOUT_MS = 5000L
    const val SILENCE_THRESHOLD_RMS = 500.0
    const val MIN_RECORDING_MS = 1500L

    // Notifications
    const val CHANNEL_RECORDING = "voicesnap_recording"
    const val CHANNEL_RESULT = "voicesnap_result"
    const val NOTIF_ID_RECORDING = 1001
    const val NOTIF_ID_RESULT = 1002
}
