package com.voicesnap.app.api

import com.voicesnap.app.util.Constants
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

data class TranscriptionResult(
    val text: String,
    val language: String?,
    val duration: Double?
)

object WhisperApi {

    suspend fun transcribe(wavData: ByteArray, languageCode: String?): TranscriptionResult =
        withContext(Dispatchers.IO) {
            val bodyBuilder = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart(
                    "file", "recording.wav",
                    wavData.toRequestBody("audio/wav".toMediaType())
                )
                .addFormDataPart("model", Constants.WHISPER_MODEL)
                .addFormDataPart("response_format", "verbose_json")
                .addFormDataPart("temperature", "0")

            if (languageCode != null) {
                bodyBuilder.addFormDataPart("language", languageCode)
            }

            val request = Request.Builder()
                .url(Constants.GATEWAY_URL + Constants.WHISPER_PATH)
                .post(bodyBuilder.build())
                .addHeader("Authorization", "Bearer ${Constants.WORKER_SECRET}")
                .addHeader("X-Api-Path", Constants.WHISPER_API_PATH_HEADER)
                .build()

            val response = ApiClient.client.newCall(request).execute()
            if (!response.isSuccessful) {
                val errBody = response.body?.string() ?: ""
                throw Exception("Transcription failed (${response.code}): ${errBody.take(200)}")
            }

            val json = JSONObject(response.body!!.string())
            TranscriptionResult(
                text = json.optString("text", "").trim(),
                language = if (json.has("language")) json.getString("language") else null,
                duration = if (json.has("duration")) json.getDouble("duration") else null
            )
        }
}
