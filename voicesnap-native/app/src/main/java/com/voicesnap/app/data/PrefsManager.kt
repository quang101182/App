package com.voicesnap.app.data

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

class PrefsManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("voicesnap_prefs", Context.MODE_PRIVATE)

    fun getSourceLang(): String = prefs.getString("source_lang", "fr") ?: "fr"
    fun setSourceLang(code: String) = prefs.edit().putString("source_lang", code).apply()

    fun getTargetLang(): String = prefs.getString("target_lang", "en") ?: "en"
    fun setTargetLang(code: String) = prefs.edit().putString("target_lang", code).apply()

    fun isTranslateEnabled(): Boolean = prefs.getBoolean("translate_enabled", false)
    fun setTranslateEnabled(on: Boolean) = prefs.edit().putBoolean("translate_enabled", on).apply()

    fun getSilenceTimeoutSec(): Int = prefs.getInt("silence_timeout_sec", 5)
    fun setSilenceTimeoutSec(sec: Int) = prefs.edit().putInt("silence_timeout_sec", sec).apply()

    fun getHistory(): List<HistoryEntry> {
        val json = prefs.getString("history_json", "[]") ?: "[]"
        val arr = JSONArray(json)
        val list = mutableListOf<HistoryEntry>()
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            list.add(
                HistoryEntry(
                    id = obj.getLong("id"),
                    text = obj.getString("text"),
                    translatedText = if (obj.isNull("translatedText")) null else obj.optString("translatedText"),
                    sourceLang = obj.getString("sourceLang"),
                    targetLang = if (obj.isNull("targetLang")) null else obj.optString("targetLang"),
                    timestamp = obj.getLong("timestamp")
                )
            )
        }
        return list
    }

    fun addHistory(entry: HistoryEntry) {
        val list = getHistory().toMutableList()
        list.add(0, entry)
        if (list.size > 50) list.subList(50, list.size).clear()
        val arr = JSONArray()
        for (e in list) {
            arr.put(JSONObject().apply {
                put("id", e.id)
                put("text", e.text)
                put("translatedText", e.translatedText ?: JSONObject.NULL)
                put("sourceLang", e.sourceLang)
                put("targetLang", e.targetLang ?: JSONObject.NULL)
                put("timestamp", e.timestamp)
            })
        }
        prefs.edit().putString("history_json", arr.toString()).apply()
    }

    fun clearHistory() = prefs.edit().remove("history_json").apply()

    // VAD toggle (for IME mode)
    fun isVadEnabled(): Boolean = prefs.getBoolean("vad_enabled", true)
    fun setVadEnabled(on: Boolean) = prefs.edit().putBoolean("vad_enabled", on).apply()

    // Rewrite mode
    fun isRewriteEnabled(): Boolean = prefs.getBoolean("rewrite_enabled", false)
    fun setRewriteEnabled(on: Boolean) = prefs.edit().putBoolean("rewrite_enabled", on).apply()

    fun getRewriteMode(): String = prefs.getString("rewrite_mode", "NEUTRAL") ?: "NEUTRAL"
    fun setRewriteMode(mode: String) = prefs.edit().putString("rewrite_mode", mode).apply()

    // Custom dictionary (Whisper prompt hint)
    fun getCustomDictionary(): String = prefs.getString("custom_dictionary", "") ?: ""
    fun setCustomDictionary(words: String) = prefs.edit().putString("custom_dictionary", words).apply()

    // Dismissed clipboard text (persists across IME lifecycle)
    fun getDismissedClipText(): String? = prefs.getString("dismissed_clip_text", null)
    fun setDismissedClipText(text: String?) = prefs.edit().putString("dismissed_clip_text", text).apply()
}

data class HistoryEntry(
    val id: Long,
    val text: String,
    val translatedText: String?,
    val sourceLang: String,
    val targetLang: String?,
    val timestamp: Long
)
