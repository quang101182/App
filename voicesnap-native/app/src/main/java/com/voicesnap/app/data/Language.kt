package com.voicesnap.app.data

data class Language(
    val code: String,
    val flag: String,
    val name: String,
    val whisperCode: String?,
    val azureCode: String?
)

val LANGUAGES: List<Language> = listOf(
    Language("auto", "\uD83C\uDF10", "Auto-d\u00e9tection", null, null),
    Language("fr", "\uD83C\uDDEB\uD83C\uDDF7", "Fran\u00e7ais", "fr", "fr"),
    Language("en", "\uD83C\uDDEC\uD83C\uDDE7", "English", "en", "en"),
    Language("de", "\uD83C\uDDE9\uD83C\uDDEA", "Deutsch", "de", "de"),
    Language("it", "\uD83C\uDDEE\uD83C\uDDF9", "Italiano", "it", "it"),
    Language("es", "\uD83C\uDDEA\uD83C\uDDF8", "Espa\u00f1ol", "es", "es"),
    Language("pt", "\uD83C\uDDF5\uD83C\uDDF9", "Portugu\u00eas", "pt", "pt"),
    Language("ru", "\uD83C\uDDF7\uD83C\uDDFA", "\u0420\u0443\u0441\u0441\u043A\u0438\u0439", "ru", "ru"),
    Language("zh", "\uD83C\uDDE8\uD83C\uDDF3", "\u4E2D\u6587", "zh", "zh-Hans"),
    Language("ja", "\uD83C\uDDEF\uD83C\uDDF5", "\u65E5\u672C\u8A9E", "ja", "ja")
)

// Map Whisper language codes back to our codes
val WHISPER_LANG_MAP: Map<String, String> = mapOf(
    "french" to "fr", "english" to "en", "german" to "de",
    "italian" to "it", "spanish" to "es", "portuguese" to "pt",
    "russian" to "ru", "chinese" to "zh", "japanese" to "ja"
)
