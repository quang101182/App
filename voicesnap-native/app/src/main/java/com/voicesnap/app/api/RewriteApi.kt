package com.voicesnap.app.api

import com.voicesnap.app.util.Constants
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

enum class RewriteMode(val label: String) {
    NEUTRAL("Propre"),
    FORMAL("Formel"),
    CONCISE("Concis"),
    EXPANDED("D\u00e9velopp\u00e9")
}

object RewriteApi {

    private fun systemPrompt(mode: RewriteMode): String = when (mode) {
        RewriteMode.NEUTRAL -> """You are a text editor specialized in cleaning up voice dictation.
Transform the raw dictated text into clean written text.
Rules:
- Fix grammar and punctuation
- Remove filler words (um, uh, euh, donc voil\u00e0, en fait...)
- Fix sentence structure without changing meaning
- NEVER change who is speaking. Preserve all pronouns (I/you/he/she) exactly as in the original
- If the input is a list of tasks, keep them as separate items
- ALWAYS respond in the EXACT same language as the input
- You are NOT a coding assistant. NEVER generate code, solutions, or technical recommendations
- Output ONLY the cleaned text, nothing else"""

        RewriteMode.FORMAL -> """You are a professional writing assistant.
Rewrite the following dictated text in a formal, professional register.
Rules:
- Fix all grammar and punctuation
- Replace informal expressions with formal equivalents
- Structure sentences clearly and concisely
- STRICT: Do NOT add action items, recommendations, or task lists not in the original
- Do NOT add information that is not in the original text
- If the input is a list of tasks, keep them as separate items
- ALWAYS respond in the EXACT same language as the input. NEVER switch to another language
- Output ONLY the rewritten text, nothing else"""

        RewriteMode.CONCISE -> """You are a text summarizer specialized in voice dictation.
Rewrite the following dictated text keeping only essential information.
Rules:
- Remove all redundancy and repetition
- Condense to 30-50% of original length if possible
- Preserve all key facts and meaning
- Fix grammar and punctuation
- ALWAYS respond in the EXACT same language as the input
- Output ONLY the rewritten text. No commentary, no explanation"""

        RewriteMode.EXPANDED -> """You are a writing assistant that improves voice notes.
Rewrite the following dictated text with better structure and flow.
Rules:
- Expand abbreviations and incomplete thoughts into full sentences
- Add logical connectors between ideas
- Improve sentence variety and flow
- Fix grammar and punctuation
- STRICT: Do NOT invent facts, reasons, emotions, or details absent from the original
- STRICT: Do NOT add recommendations, consequences, or interpretations
- Only clarify what is already implied in the original text
- ALWAYS respond in the EXACT same language as the input
- Output ONLY the rewritten text. No commentary, no explanation"""
    }

    private const val EMOJI_SUFFIX = "\nEn plus, enrichis naturellement le texte avec des emojis pertinents (2-4 maximum, bien placés). Les emojis doivent renforcer le ton du message sans le surcharger."

    suspend fun rewrite(text: String, mode: RewriteMode = RewriteMode.NEUTRAL, withEmoji: Boolean = false): String =
        withContext(Dispatchers.IO) {
            val prompt = if (withEmoji) systemPrompt(mode) + EMOJI_SUFFIX else systemPrompt(mode)
            val body = JSONObject().apply {
                put("model", Constants.REWRITE_MODEL)
                put("messages", JSONArray().apply {
                    put(JSONObject().apply {
                        put("role", "system")
                        put("content", prompt)
                    })
                    put(JSONObject().apply {
                        put("role", "user")
                        put("content", text)
                    })
                })
                put("temperature", 0.3)
                put("max_tokens", 1000)
            }

            val request = Request.Builder()
                .url(Constants.GATEWAY_URL + Constants.WHISPER_PATH)
                .post(body.toString().toRequestBody("application/json".toMediaType()))
                .addHeader("Authorization", "Bearer ${Constants.WORKER_SECRET}")
                .addHeader("X-Api-Path", Constants.CHAT_API_PATH_HEADER)
                .build()

            ApiClient.client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val err = response.body?.string() ?: ""
                    throw Exception("Rewrite failed (${response.code}): ${err.take(200)}")
                }
                val json = JSONObject(response.body!!.string())
                json.getJSONArray("choices")
                    .getJSONObject(0)
                    .getJSONObject("message")
                    .getString("content")
                    .trim()
            }
        }
}
