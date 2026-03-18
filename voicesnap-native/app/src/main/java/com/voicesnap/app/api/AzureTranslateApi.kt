package com.voicesnap.app.api

import com.voicesnap.app.util.Constants
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray

object AzureTranslateApi {

    suspend fun translate(text: String, from: String, to: String): String =
        withContext(Dispatchers.IO) {
            val url = "${Constants.GATEWAY_URL}${Constants.AZURE_PATH}?api-version=3.0&from=$from&to=$to"

            val bodyJson = JSONArray().apply {
                put(org.json.JSONObject().apply { put("Text", text) })
            }

            val request = Request.Builder()
                .url(url)
                .post(bodyJson.toString().toRequestBody("application/json".toMediaType()))
                .addHeader("Authorization", "Bearer ${Constants.WORKER_SECRET}")
                .addHeader("Content-Type", "application/json")
                .build()

            ApiClient.client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errBody = response.body?.string() ?: ""
                    throw Exception("Translation failed (${response.code}): ${errBody.take(200)}")
                }

                val data = JSONArray(response.body!!.string())
                val translations = data.getJSONObject(0).getJSONArray("translations")
                translations.getJSONObject(0).getString("text")
            }
        }
}
