package com.voicesnap.app.ime

import android.content.Intent
import android.inputmethodservice.InputMethodService
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.ExtractedTextRequest
import android.widget.ArrayAdapter
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.ListPopupWindow
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import android.graphics.drawable.GradientDrawable
import android.content.ClipboardManager
import android.content.Context
import android.widget.LinearLayout
import com.voicesnap.app.R
import com.voicesnap.app.api.AzureTranslateApi
import com.voicesnap.app.api.RewriteApi
import com.voicesnap.app.api.RewriteMode
import com.voicesnap.app.api.WhisperApi
import com.voicesnap.app.audio.AudioFocusManager
import com.voicesnap.app.audio.AudioRecorder
import com.voicesnap.app.data.HistoryEntry
import com.voicesnap.app.data.LANGUAGES
import com.voicesnap.app.data.PrefsManager
import com.voicesnap.app.data.WHISPER_LANG_MAP
import com.voicesnap.app.ui.MainActivity
import com.voicesnap.app.util.NetworkHelper
import kotlinx.coroutines.*

class VoiceSnapIME : InputMethodService() {

    companion object {
        private const val TAG = "VoiceSnapIME"
        private const val MAX_UNDO_STACK = 20
        private const val CLEAR_LONG_PRESS_MS = 800L
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val recorder = AudioRecorder()
    private val prefs by lazy { PrefsManager(this) }
    private val audioFocusManager by lazy { AudioFocusManager(this) }
    private val backspaceHandler = Handler(Looper.getMainLooper())
    private var backspaceRepeating = false

    // UI references
    private var keyboardView: View? = null
    private var tvStatus: TextView? = null
    private var tvDictateLabel: TextView? = null
    private var btnDictate: FrameLayout? = null
    private var btnTranslate: FrameLayout? = null
    private var btnToggleVad: TextView? = null
    private var tvSourceLang: TextView? = null
    private var tvTargetLang: TextView? = null
    private var progressBar: ProgressBar? = null
    private var tvUndo: TextView? = null
    private var tvRedo: TextView? = null
    private var ivRewriteIcon: ImageView? = null
    private var tvRewriteLabel: TextView? = null
    private var ledStt: View? = null
    private var ledLlm: View? = null
    private var ledTrd: View? = null
    private var bannerClipboard: LinearLayout? = null
    private var tvClipboardText: TextView? = null
    private val bannerHandler = Handler(Looper.getMainLooper())
    private var tvThemeIcon: TextView? = null
    private var ivEmojiIcon: ImageView? = null
    private var currentTheme: KeyboardTheme = KeyboardTheme.THEMES[0]
    // dismissedClipText now persisted via PrefsManager

    // State
    private var isRecording = false
    private var translateMode = false
    private var vadEnabled = true
    private var currentRewriteMode = RewriteMode.NEUTRAL
    private var emojiEnrichment = false
    private var processingJob: Job? = null
    private var currentEditorInfo: EditorInfo? = null

    // Undo/Redo stacks
    private val undoStack = ArrayDeque<String>()
    private val redoStack = ArrayDeque<String>()

    override fun onCreateInputView(): View {
        val view = layoutInflater.inflate(R.layout.keyboard_voicesnap, null)
        keyboardView = view

        // Bind UI
        tvStatus = view.findViewById(R.id.tv_status)
        tvDictateLabel = view.findViewById(R.id.tv_dictate_label)
        btnDictate = view.findViewById(R.id.btn_dictate)
        btnTranslate = view.findViewById(R.id.btn_translate)
        btnToggleVad = view.findViewById(R.id.btn_toggle_vad)
        tvSourceLang = view.findViewById(R.id.tv_source_lang)
        tvTargetLang = view.findViewById(R.id.tv_target_lang)
        progressBar = view.findViewById(R.id.progress_bar)
        tvUndo = view.findViewById(R.id.tv_undo)
        tvRedo = view.findViewById(R.id.tv_redo)
        ivRewriteIcon = view.findViewById(R.id.iv_rewrite_icon)
        tvRewriteLabel = view.findViewById(R.id.tv_rewrite_label)
        ledStt = view.findViewById(R.id.led_stt)
        ledLlm = view.findViewById(R.id.led_llm)
        ledTrd = view.findViewById(R.id.led_trd)
        bannerClipboard = view.findViewById(R.id.banner_clipboard)
        tvClipboardText = view.findViewById(R.id.tv_clipboard_text)
        tvThemeIcon = view.findViewById(R.id.tv_theme_icon)
        ivEmojiIcon = view.findViewById(R.id.iv_emoji_icon)

        // Load prefs
        vadEnabled = prefs.isVadEnabled()
        emojiEnrichment = prefs.isEmojiEnrichment()
        currentRewriteMode = try { RewriteMode.valueOf(prefs.getRewriteMode()) } catch (_: Exception) { RewriteMode.NEUTRAL }
        currentTheme = KeyboardTheme.fromName(prefs.getKeyboardTheme())
        updateTogglesUI()
        updateLanguageLabels()
        updateRewriteButtonUI()
        updateUndoRedoUI()
        updateEmojiToggleUI()

        setupListeners(view)
        applyTheme()
        return view
    }

    override fun onStartInputView(info: EditorInfo, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        currentEditorInfo = info
        updateLanguageLabels()
        // Clear undo/redo on new field
        if (!restarting) {
            undoStack.clear()
            redoStack.clear()
            updateUndoRedoUI()
        }
        // Show clipboard banner after small delay (Honor/MagicOS safe)
        bannerHandler.removeCallbacksAndMessages(null)
        bannerHandler.postDelayed({ showClipboardBanner() }, 150)
    }

    private fun setupListeners(view: View) {
        // Dictate button
        btnDictate?.setOnClickListener {
            haptic(it)
            if (isRecording) {
                stopRecordingAndProcess()
            } else {
                processingJob?.cancel()
                translateMode = false
                startRecording()
            }
        }

        // Translate button
        btnTranslate?.setOnClickListener {
            haptic(it)
            if (isRecording) {
                stopRecordingAndProcess()
            } else {
                processingJob?.cancel()
                translateMode = true
                startRecording()
            }
        }

        // VAD toggle
        btnToggleVad?.setOnClickListener {
            haptic(it)
            vadEnabled = !vadEnabled
            prefs.setVadEnabled(vadEnabled)
            updateTogglesUI()
        }

        // Language selectors — popup menus
        tvSourceLang?.setOnClickListener { haptic(it); showLanguagePopup(it, includeAuto = true, isSource = true) }
        tvTargetLang?.setOnClickListener { haptic(it); showLanguagePopup(it, includeAuto = false, isSource = false) }

        // Utility keys
        view.findViewById<TextView>(R.id.key_comma)?.setOnClickListener { haptic(it); commitChar(",") }
        view.findViewById<TextView>(R.id.key_period)?.setOnClickListener { haptic(it); commitChar(".") }
        view.findViewById<TextView>(R.id.key_question)?.setOnClickListener { haptic(it); commitChar("?") }

        // Backspace with long-press repeat
        view.findViewById<FrameLayout>(R.id.key_backspace)?.let { backspaceKey ->
            backspaceKey.setOnClickListener { haptic(it); handleBackspace() }
            backspaceKey.setOnTouchListener { v, event ->
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        backspaceRepeating = true
                        backspaceHandler.postDelayed(object : Runnable {
                            override fun run() {
                                if (backspaceRepeating) {
                                    handleBackspace()
                                    v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                                    backspaceHandler.postDelayed(this, 50)
                                }
                            }
                        }, 400)
                        false
                    }
                    MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                        backspaceRepeating = false
                        backspaceHandler.removeCallbacksAndMessages(null)
                        false
                    }
                    else -> false
                }
            }
        }

        view.findViewById<TextView>(R.id.key_space)?.setOnClickListener { haptic(it); commitChar(" ") }

        // Enter key
        view.findViewById<TextView>(R.id.key_enter)?.setOnClickListener { haptic(it); handleEnter() }

        // Undo / Redo
        view.findViewById<FrameLayout>(R.id.key_undo)?.setOnClickListener {
            haptic(it)
            if (undoStack.isNotEmpty()) performUndo()
        }
        view.findViewById<FrameLayout>(R.id.key_redo)?.setOnClickListener {
            haptic(it)
            if (redoStack.isNotEmpty()) performRedo()
        }

        // Rewrite button: tap = rewrite with current mode, long-press = mode picker popup
        view.findViewById<FrameLayout>(R.id.btn_rewrite)?.let { btn ->
            btn.setOnClickListener { haptic(it); rewriteFieldContent() }
            btn.setOnLongClickListener { haptic(it); showRewriteModePopup(it); true }
        }

        // Settings button — opens MainActivity
        view.findViewById<FrameLayout>(R.id.btn_settings)?.setOnClickListener { haptic(it); openSettings() }

        // Clear all button — long-press only, tap = tooltip
        view.findViewById<FrameLayout>(R.id.btn_clear_all)?.let { btn ->
            btn.setOnClickListener {
                haptic(it)
                Toast.makeText(this, "Restez appuy\u00e9 pour tout effacer", Toast.LENGTH_SHORT).show()
            }
            btn.setOnLongClickListener {
                haptic(it)
                clearAllFieldContent()
                true
            }
        }

        // Clipboard banner — tap text to paste, X to dismiss
        tvClipboardText?.setOnClickListener {
            haptic(it)
            pasteFromClipboard()
        }
        view.findViewById<TextView>(R.id.tv_clipboard_paste)?.setOnClickListener {
            haptic(it)
            pasteFromClipboard()
        }
        view.findViewById<FrameLayout>(R.id.btn_clipboard_dismiss)?.setOnClickListener {
            haptic(it)
            dismissClipboardBanner()
        }

        // Emoji enrichment toggle
        view.findViewById<FrameLayout>(R.id.btn_emoji_toggle)?.setOnClickListener {
            haptic(it)
            emojiEnrichment = !emojiEnrichment
            prefs.setEmojiEnrichment(emojiEnrichment)
            updateEmojiToggleUI()
        }

        // Theme toggle button
        view.findViewById<FrameLayout>(R.id.btn_theme_toggle)?.setOnClickListener {
            haptic(it)
            cycleTheme()
        }
    }

    // ---- Haptic feedback ----

    private fun haptic(view: View) {
        view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
    }

    // ---- Language popup menus ----

    private fun showLanguagePopup(anchor: View, includeAuto: Boolean, isSource: Boolean) {
        val langs = if (includeAuto) LANGUAGES else LANGUAGES.filter { it.code != "auto" }
        val labels = langs.map { "${it.flag} ${it.name}" }

        val popup = ListPopupWindow(anchor.context)
        popup.anchorView = anchor
        popup.setAdapter(ArrayAdapter(anchor.context, android.R.layout.simple_list_item_1, labels))
        popup.width = (anchor.width * 2.5).toInt().coerceAtLeast(400)
        popup.isModal = true

        popup.setOnItemClickListener { _, _, position, _ ->
            val selected = langs[position]
            if (isSource) {
                prefs.setSourceLang(selected.code)
            } else {
                prefs.setTargetLang(selected.code)
            }
            updateLanguageLabels()
            popup.dismiss()
        }
        popup.show()
    }

    // ---- Rewrite mode popup ----

    private fun showRewriteModePopup(anchor: View) {
        val modes = RewriteMode.values()
        val labels = modes.map { mode ->
            val icon = when (mode) {
                RewriteMode.NEUTRAL -> "\u2728"
                RewriteMode.FORMAL -> "\uD83D\uDC54"
                RewriteMode.CONCISE -> "\u2702\uFE0F"
                RewriteMode.EXPANDED -> "\uD83D\uDCDD"
            }
            val check = if (mode == currentRewriteMode) " \u2713" else ""
            "$icon ${mode.label}$check"
        }

        val popup = ListPopupWindow(anchor.context)
        popup.anchorView = anchor
        popup.setAdapter(ArrayAdapter(anchor.context, android.R.layout.simple_list_item_1, labels))
        popup.width = 400
        popup.isModal = true

        popup.setOnItemClickListener { _, _, position, _ ->
            currentRewriteMode = modes[position]
            prefs.setRewriteMode(currentRewriteMode.name)
            updateRewriteButtonUI()
            setStatus("Mode: ${currentRewriteMode.label}")
            popup.dismiss()
        }
        popup.show()
    }

    // ---- Enter key ----

    private fun handleEnter() {
        val info = currentEditorInfo
        val imeAction = info?.imeOptions?.and(EditorInfo.IME_MASK_ACTION) ?: EditorInfo.IME_ACTION_NONE
        val isMultiLine = (info?.inputType?.and(EditorInfo.TYPE_TEXT_FLAG_MULTI_LINE)) != 0

        if (isMultiLine || imeAction == EditorInfo.IME_ACTION_NONE || imeAction == EditorInfo.IME_ACTION_UNSPECIFIED) {
            currentInputConnection?.commitText("\n", 1)
        } else {
            sendDefaultEditorAction(true)
        }
    }

    // ---- Undo / Redo ----

    private fun saveUndoState() {
        val text = readFieldText() ?: return
        undoStack.addLast(text)
        if (undoStack.size > MAX_UNDO_STACK) undoStack.removeFirst()
        redoStack.clear()
        updateUndoRedoUI()
    }

    private fun performUndo() {
        processingJob?.cancel()
        processingJob = null
        showProgress(false)

        if (undoStack.isEmpty()) {
            setStatus("Rien \u00e0 annuler")
            return
        }
        val currentText = readFieldText()
        if (currentText != null) redoStack.addLast(currentText)

        val previousText = undoStack.removeLast()
        replaceFieldText(previousText)
        updateUndoRedoUI()
        setStatus("Annul\u00e9 \u21B6")
    }

    private fun performRedo() {
        processingJob?.cancel()
        processingJob = null
        showProgress(false)

        if (redoStack.isEmpty()) {
            setStatus("Rien \u00e0 r\u00e9tablir")
            return
        }
        val currentText = readFieldText()
        if (currentText != null) undoStack.addLast(currentText)

        val nextText = redoStack.removeLast()
        replaceFieldText(nextText)
        updateUndoRedoUI()
        setStatus("R\u00e9tabli \u21B7")
    }

    // ---- Clear all ----

    private fun clearAllFieldContent() {
        val text = readFieldText()
        if (text.isNullOrEmpty()) {
            setStatus("Champ d\u00e9j\u00e0 vide")
            return
        }
        saveUndoState()
        replaceFieldText("")
        updateUndoRedoUI()

        // Flash the clear button red
        keyboardView?.findViewById<FrameLayout>(R.id.btn_clear_all)?.let { btn ->
            btn.setBackgroundResource(R.drawable.bg_button_recording)
            Handler(Looper.getMainLooper()).postDelayed({
                btn.setBackgroundResource(R.drawable.bg_key)
            }, 300)
        }
        setStatus("Tout effac\u00e9 \u2713")
    }

    // ---- Settings ----

    private fun openSettings() {
        try {
            val intent = Intent(this, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to open settings", e)
            setStatus("Impossible d'ouvrir les param\u00e8tres")
        }
    }

    // ---- Recording ----

    private fun startRecording() {
        if (!hasRecordPermission()) {
            setStatus("Permission micro requise - ouvrez VoiceSnap")
            openSettings()
            return
        }

        hideClipboardBanner()
        audioFocusManager.requestFocus()
        Log.d(TAG, "Starting recording (translate=$translateMode, vad=$vadEnabled)")
        isRecording = true
        updateRecordingUI(true)

        // Save undo state BEFORE recording inserts text
        saveUndoState()

        if (vadEnabled) {
            recorder.onSilenceDetected = {
                Log.d(TAG, "Silence detected from IME")
                scope.launch(Dispatchers.Main) { stopRecordingAndProcess() }
            }
            val timeoutMs = prefs.getSilenceTimeoutSec() * 1000L
            recorder.setSilenceTimeout(timeoutMs)
        } else {
            recorder.onSilenceDetected = null
            recorder.setSilenceTimeout(Long.MAX_VALUE)
        }

        val started = recorder.start()
        if (!started) {
            Log.e(TAG, "Failed to start AudioRecorder")
            setStatus("Erreur micro")
            isRecording = false
            updateRecordingUI(false)
            audioFocusManager.abandonFocus()
        } else {
            setStatus(if (translateMode) "\u00c9coute... (traduction)" else "\u00c9coute...")
        }
    }

    private fun stopRecordingAndProcess() {
        if (!isRecording) return
        isRecording = false

        Log.d(TAG, "Stopping recording...")
        val wavData = recorder.stop()

        if (wavData.isEmpty()) {
            setStatus("Trop court (min 1.5s)")
            updateRecordingUI(false)
            audioFocusManager.abandonFocus()
            return
        }

        setStatus("Transcription...")
        showProgress(true)
        updateRecordingUI(false)

        processingJob = scope.launch {
            try {
                val srcLangCode = prefs.getSourceLang()
                val langObj = LANGUAGES.find { it.code == srcLangCode }
                val whisperLang = langObj?.whisperCode

                // 1. Transcribe
                val result = WhisperApi.transcribe(wavData, whisperLang)
                Log.d(TAG, "Whisper: '${result.text}' (lang=${result.language})")

                // LED: STT success
                setLed(ledStt, true)

                if (result.text.isBlank()) {
                    setStatus("Aucune parole d\u00e9tect\u00e9e")
                    showProgress(false)
                    return@launch
                }

                var finalText = result.text

                // 2. NO auto-rewrite — dictation always inserts raw text

                // 3. Translate if translate button was pressed
                var translatedText: String? = null
                if (translateMode) {
                    val detectedLang = result.language?.let { WHISPER_LANG_MAP[it.lowercase()] } ?: srcLangCode
                    val srcLang = if (srcLangCode == "auto") detectedLang else srcLangCode
                    val targetLang = prefs.getTargetLang()

                    val srcObj = LANGUAGES.find { it.code == srcLang }
                    val tgtObj = LANGUAGES.find { it.code == targetLang }

                    if (srcObj?.azureCode != null && tgtObj?.azureCode != null && srcObj.azureCode != tgtObj.azureCode) {
                        setStatus("Traduction...")
                        try {
                            translatedText = AzureTranslateApi.translate(finalText, srcObj.azureCode, tgtObj.azureCode)
                            if (translatedText != null) {
                                finalText = translatedText!!
                                Log.d(TAG, "Translation: '$translatedText'")
                                setLed(ledTrd, true)
                            } else {
                                Log.w(TAG, "Translation returned null, inserting original")
                                setLed(ledTrd, false)
                            }
                        } catch (e: Exception) {
                            Log.e(TAG, "Translation failed, inserting original text", e)
                            setLed(ledTrd, false)
                            // Keep finalText = result.text
                        }
                    }
                }

                // 4. Insert text into active field
                val inserted = commitText(finalText)

                // 5. Save to history
                val entry = HistoryEntry(
                    id = System.currentTimeMillis(),
                    text = result.text,
                    translatedText = translatedText,
                    sourceLang = srcLangCode,
                    targetLang = if (translateMode) prefs.getTargetLang() else null,
                    timestamp = System.currentTimeMillis()
                )
                prefs.addHistory(entry)

                val statusMsg = if (!inserted) {
                    "Copi\u00e9 \u2713 (tapez dans un champ)"
                } else if (translateMode && translatedText == null) {
                    "Ins\u00e9r\u00e9 \u2713 (traduction \u00e9chou\u00e9e)"
                } else {
                    "Ins\u00e9r\u00e9 \u2713"
                }
                setStatus(statusMsg)
                updateUndoRedoUI()

            } catch (e: CancellationException) {
                setStatus("Annul\u00e9")
            } catch (e: Exception) {
                Log.e(TAG, "Pipeline error", e)
                setStatus(NetworkHelper.friendlyErrorMessage(e))
                setLed(ledStt, false)
            } finally {
                showProgress(false)
                audioFocusManager.abandonFocus()
            }
        }
    }

    // ---- Rewrite existing field content ----

    private fun rewriteFieldContent() {
        val text = readFieldText()
        if (text.isNullOrBlank()) {
            setStatus("Champ vide")
            return
        }

        // Save undo state before rewrite
        saveUndoState()

        setStatus("R\u00e9\u00e9criture (${currentRewriteMode.label})...")
        showProgress(true)
        processingJob?.cancel()

        processingJob = scope.launch {
            try {
                val rewritten = RewriteApi.rewrite(text, currentRewriteMode, emojiEnrichment)
                Log.d(TAG, "Rewrite field: '$text' -> '$rewritten'")

                // LED: LLM success
                setLed(ledLlm, true)

                val ic = currentInputConnection
                if (ic != null) {
                    replaceFieldText(rewritten)
                    updateUndoRedoUI()
                    setStatus("R\u00e9\u00e9crit \u2713 (${currentRewriteMode.label})")
                } else {
                    Log.w(TAG, "InputConnection null on rewrite, fallback clipboard")
                    com.voicesnap.app.util.ClipboardHelper.copyToClipboard(this@VoiceSnapIME, rewritten)
                    setStatus("Copi\u00e9 \u2713 (tapez dans un champ)")
                }
            } catch (e: CancellationException) {
                setStatus("Annul\u00e9")
            } catch (e: Exception) {
                Log.e(TAG, "Rewrite error", e)
                setStatus(NetworkHelper.friendlyErrorMessage(e))
                setLed(ledLlm, false)
            } finally {
                showProgress(false)
            }
        }
    }

    // ---- InputConnection helpers ----

    private fun commitText(text: String): Boolean {
        val ic = currentInputConnection
        if (ic != null) {
            ic.commitText(text, 1)
            return true
        }
        // Fallback: InputConnection stale (e.g. after APK update) — copy to clipboard
        Log.w(TAG, "InputConnection null, fallback to clipboard")
        com.voicesnap.app.util.ClipboardHelper.copyToClipboard(this, text)
        return false
    }

    private fun commitChar(ch: String) {
        currentInputConnection?.commitText(ch, 1)
    }

    private fun handleBackspace() {
        val ic = currentInputConnection ?: return
        val selected = ic.getSelectedText(0)
        if (selected.isNullOrEmpty()) {
            ic.deleteSurroundingText(1, 0)
        } else {
            ic.commitText("", 1)
        }
    }

    private fun readFieldText(): String? {
        val ic = currentInputConnection ?: return null
        val req = ExtractedTextRequest().apply {
            token = 0
            hintMaxChars = 100_000
        }
        val extracted = ic.getExtractedText(req, 0)
        if (extracted?.text != null) {
            return extracted.text.toString()
        }
        val before = ic.getTextBeforeCursor(100_000, 0) ?: ""
        val after = ic.getTextAfterCursor(100_000, 0) ?: ""
        val combined = "$before$after"
        return if (combined.isBlank()) null else combined
    }

    private fun replaceFieldText(newText: String) {
        val ic = currentInputConnection ?: return
        ic.beginBatchEdit()
        try {
            val before = ic.getTextBeforeCursor(100_000, 0)?.length ?: 0
            val after = ic.getTextAfterCursor(100_000, 0)?.length ?: 0
            ic.deleteSurroundingText(before, after)
            ic.commitText(newText, 1)
        } finally {
            ic.endBatchEdit()
        }
    }

    // ---- Permission check ----

    private fun hasRecordPermission(): Boolean {
        return checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
            android.content.pm.PackageManager.PERMISSION_GRANTED
    }

    // ---- UI updates ----

    private fun setStatus(text: String) {
        tvStatus?.text = text
    }

    private fun showProgress(show: Boolean) {
        progressBar?.visibility = if (show) View.VISIBLE else View.GONE
    }

    private fun updateRecordingUI(recording: Boolean) {
        val t = currentTheme
        if (recording) {
            btnDictate?.let { applyButtonBg(it, t.bgRecording, t.cornerRadius) }
            tvDictateLabel?.text = "STOP"
            btnTranslate?.let {
                applyButtonBg(it, if (translateMode) t.bgRecording else t.bgTranslate, t.cornerRadius)
            }
        } else {
            btnDictate?.let { applyButtonBg(it, t.bgDictate, t.cornerRadius) }
            tvDictateLabel?.text = "Dicter"
            btnTranslate?.let { applyButtonBg(it, t.bgTranslate, t.cornerRadius) }
        }
    }

    private fun updateTogglesUI() {
        if (vadEnabled) {
            btnToggleVad?.text = " Auto-stop "
            btnToggleVad?.setTextColor(currentTheme.vadOnColor)
        } else {
            btnToggleVad?.text = " Auto-stop "
            btnToggleVad?.setTextColor(currentTheme.vadOffColor)
        }
    }

    private fun updateLanguageLabels() {
        val srcCode = prefs.getSourceLang()
        val tgtCode = prefs.getTargetLang()
        val srcLang = LANGUAGES.find { it.code == srcCode }
        val tgtLang = LANGUAGES.find { it.code == tgtCode }

        tvSourceLang?.text = "${srcLang?.flag ?: ""} ${srcLang?.name ?: srcCode} \u25BE"
        tvTargetLang?.text = "${tgtLang?.flag ?: ""} ${tgtLang?.name ?: tgtCode} \u25BE"
    }

    private fun updateUndoRedoUI() {
        val undoAlpha = if (undoStack.isNotEmpty()) 1.0f else 0.3f
        val redoAlpha = if (redoStack.isNotEmpty()) 1.0f else 0.3f
        tvUndo?.alpha = undoAlpha
        tvRedo?.alpha = redoAlpha
    }

    private fun updateRewriteButtonUI() {
        val iconRes = when (currentRewriteMode) {
            RewriteMode.NEUTRAL -> R.drawable.ic_rewrite_neutral
            RewriteMode.FORMAL -> R.drawable.ic_rewrite_formal
            RewriteMode.CONCISE -> R.drawable.ic_rewrite_concise
            RewriteMode.EXPANDED -> R.drawable.ic_rewrite_expanded
        }
        ivRewriteIcon?.setImageResource(iconRes)
        tvRewriteLabel?.text = currentRewriteMode.label
    }

    private fun updateEmojiToggleUI() {
        ivEmojiIcon?.alpha = if (emojiEnrichment) 1.0f else 0.3f
    }

    private fun setLed(led: View?, success: Boolean) {
        led?.setBackgroundResource(if (success) R.drawable.led_green else R.drawable.led_red)
    }

    // ---- Theme switching ----

    private fun cycleTheme() {
        currentTheme = KeyboardTheme.next(currentTheme)
        prefs.setKeyboardTheme(currentTheme.name)
        applyTheme()
        setStatus("Theme: ${currentTheme.name}")
    }

    private fun applyTheme() {
        val view = keyboardView ?: return
        val t = currentTheme

        // Keyboard background
        view.setBackgroundColor(t.bgKeyboard)

        // Theme toggle icon
        tvThemeIcon?.text = t.icon
        tvThemeIcon?.setTextColor(t.textSecondary)

        // Status text
        tvStatus?.setTextColor(t.textSecondary)

        // Language selectors
        tvSourceLang?.setTextColor(t.textPrimary)
        tvTargetLang?.setTextColor(t.textPrimary)

        // Main action buttons
        btnDictate?.let { applyButtonBg(it, if (isRecording) t.bgRecording else t.bgDictate, t.cornerRadius) }
        btnTranslate?.let { applyButtonBg(it, if (isRecording && translateMode) t.bgRecording else t.bgTranslate, t.cornerRadius) }

        // Dictate label
        tvDictateLabel?.setTextColor(t.textPrimary)

        // Utility keys — apply to all bg_key buttons
        val keyIds = intArrayOf(
            R.id.key_undo, R.id.key_redo, R.id.key_backspace,
            R.id.btn_settings, R.id.btn_clear_all, R.id.btn_theme_toggle
        )
        for (id in keyIds) {
            view.findViewById<View>(id)?.let { applyButtonBg(it, t.bgButton, t.cornerRadius) }
        }

        // Text keys
        val textKeyIds = intArrayOf(R.id.key_comma, R.id.key_period, R.id.key_question, R.id.key_space, R.id.key_enter)
        for (id in textKeyIds) {
            view.findViewById<TextView>(id)?.let { tv ->
                applyButtonBg(tv, if (id == R.id.key_enter) t.bgDictate else t.bgButton, t.cornerRadius)
                tv.setTextColor(t.textPrimary)
            }
        }

        // Undo/Redo text color
        tvUndo?.setTextColor(t.textSecondary)
        tvRedo?.setTextColor(t.textSecondary)

        // VAD toggle
        updateTogglesUI()

        // Rewrite button
        view.findViewById<FrameLayout>(R.id.btn_rewrite)?.let { applyButtonBg(it, t.bgButton, t.cornerRadius) }
        tvRewriteLabel?.setTextColor(t.accentRewrite)

        // Emoji toggle button
        view.findViewById<FrameLayout>(R.id.btn_emoji_toggle)?.let { applyButtonBg(it, t.bgButton, t.cornerRadius) }

        // Banner clipboard
        bannerClipboard?.setBackgroundColor(t.bgBanner)
        tvClipboardText?.setTextColor(t.textSecondary)
        view.findViewById<TextView>(R.id.tv_clipboard_paste)?.setTextColor(t.textAccent)

        // Language row backgrounds
        view.findViewById<TextView>(R.id.tv_source_lang)?.let { applyButtonBg(it, t.bgButton, t.cornerRadius) }
        view.findViewById<TextView>(R.id.tv_target_lang)?.let { applyButtonBg(it, t.bgButton, t.cornerRadius) }

        // Progress bar tint
        progressBar?.indeterminateTintList = android.content.res.ColorStateList.valueOf(t.bgDictate)
    }

    private fun applyButtonBg(view: View, color: Int, radius: Float) {
        val drawable = GradientDrawable().apply {
            setColor(color)
            cornerRadius = radius * view.resources.displayMetrics.density
            if (currentTheme.bgButtonBorder != 0) {
                setStroke(1, currentTheme.bgButtonBorder)
            }
        }
        view.background = drawable
    }

    // ---- Clipboard banner ----

    private fun showClipboardBanner() {
        try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
            if (!clipboard.hasPrimaryClip()) {
                bannerClipboard?.visibility = View.GONE
                return
            }
            val clip = clipboard.primaryClip ?: return
            if (clip.itemCount == 0) {
                bannerClipboard?.visibility = View.GONE
                return
            }
            val text = clip.getItemAt(0).text?.toString()
            if (text.isNullOrBlank()) {
                bannerClipboard?.visibility = View.GONE
                return
            }
            // Skip if user dismissed this exact text
            if (text == prefs.getDismissedClipText()) {
                bannerClipboard?.visibility = View.GONE
                return
            }
            // Show banner with truncated preview
            tvClipboardText?.text = text.replace('\n', ' ').trim()
            bannerClipboard?.visibility = View.VISIBLE

            // Auto-dismiss after 8 seconds
            bannerHandler.removeCallbacksAndMessages(null)
            bannerHandler.postDelayed({
                bannerClipboard?.visibility = View.GONE
            }, 8000)
        } catch (e: Exception) {
            Log.w(TAG, "Clipboard banner error", e)
            bannerClipboard?.visibility = View.GONE
        }
    }

    private fun hideClipboardBanner() {
        bannerHandler.removeCallbacksAndMessages(null)
        bannerClipboard?.visibility = View.GONE
    }

    private fun dismissClipboardBanner() {
        try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            val clip = clipboard?.primaryClip
            if (clip != null && clip.itemCount > 0) {
                prefs.setDismissedClipText(clip.getItemAt(0).text?.toString())
            }
        } catch (_: Exception) {}
        hideClipboardBanner()
    }

    private fun pasteFromClipboard() {
        try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
            val clip = clipboard.primaryClip ?: return
            if (clip.itemCount == 0) return
            val text = clip.getItemAt(0).text?.toString() ?: return
            if (text.isBlank()) return

            saveUndoState()
            commitText(text)
            updateUndoRedoUI()
            hideClipboardBanner()
            setStatus("Coll\u00e9 \u2713")
        } catch (e: Exception) {
            Log.e(TAG, "Paste error", e)
            setStatus("Erreur collage")
        }
    }

    // ---- Lifecycle ----

    override fun onDestroy() {
        Log.d(TAG, "onDestroy")
        processingJob?.cancel()
        scope.cancel()
        audioFocusManager.abandonFocus()
        backspaceHandler.removeCallbacksAndMessages(null)
        bannerHandler.removeCallbacksAndMessages(null)
        if (recorder.isActive()) {
            recorder.stop()
        }
        super.onDestroy()
    }
}
