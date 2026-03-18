package com.voicesnap.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.voicesnap.app.data.HistoryEntry
import com.voicesnap.app.data.LANGUAGES
import com.voicesnap.app.data.PrefsManager
import com.voicesnap.app.service.RecordingState
import com.voicesnap.app.service.RecordingStateHolder
import com.voicesnap.app.util.ClipboardHelper
import com.voicesnap.app.util.Constants
import java.text.SimpleDateFormat
import java.util.*

// Dark theme colors matching the VoiceSnap WebView palette
private val BgPrimary = Color(0xFF09090B)
private val BgSurface = Color(0xFF18181B)
private val BgElevated = Color(0xFF27272A)
private val TextPrimary = Color(0xFFFAFAFA)
private val TextSecondary = Color(0xFFA1A1AA)
private val TextMuted = Color(0xFF71717A)
private val AccentViolet = Color(0xFF6D28D9)
private val AccentVioletLight = Color(0xFF8B5CF6)
private val AccentCyan = Color(0xFF06B6D4)
private val SuccessGreen = Color(0xFF22C55E)
private val ErrorRed = Color(0xFFEF4444)

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request permissions
        val perms = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val needed = perms.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }

        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = AccentViolet,
                    secondary = AccentCyan,
                    background = BgPrimary,
                    surface = BgSurface,
                    surfaceVariant = BgElevated,
                    onPrimary = Color.White,
                    onBackground = TextPrimary,
                    onSurface = TextPrimary,
                    error = ErrorRed
                )
            ) {
                VoiceSnapScreen()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoiceSnapScreen() {
    val context = LocalContext.current
    val prefs = remember { PrefsManager(context) }

    var sourceLang by remember { mutableStateOf(prefs.getSourceLang()) }
    var targetLang by remember { mutableStateOf(prefs.getTargetLang()) }
    var translateEnabled by remember { mutableStateOf(prefs.isTranslateEnabled()) }
    var history by remember { mutableStateOf(prefs.getHistory()) }
    var showSourcePicker by remember { mutableStateOf(false) }
    var showTargetPicker by remember { mutableStateOf(false) }

    val recordingState by RecordingStateHolder.state.collectAsState()
    val lastResult by RecordingStateHolder.lastResult.collectAsState()

    // Refresh history when result arrives
    LaunchedEffect(lastResult) {
        history = prefs.getHistory()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("VoiceSnap", fontWeight = FontWeight.Bold, color = TextPrimary)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "v${Constants.APP_VERSION}",
                            fontSize = 12.sp,
                            color = AccentVioletLight,
                            modifier = Modifier
                                .background(AccentViolet.copy(alpha = 0.2f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgPrimary)
            )
        },
        containerColor = BgPrimary
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Status indicator
            item {
                StatusCard(recordingState)
            }

            // Settings section
            item {
                Text("R\u00e9glages", fontWeight = FontWeight.SemiBold, fontSize = 18.sp, color = TextPrimary)
            }

            // Source language
            item {
                LanguageSelector(
                    label = "Langue parl\u00e9e",
                    selectedCode = sourceLang,
                    onClick = { showSourcePicker = true }
                )
            }

            // Translate toggle
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(BgSurface, RoundedCornerShape(12.dp))
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Traduire", color = TextPrimary)
                    Switch(
                        checked = translateEnabled,
                        onCheckedChange = {
                            translateEnabled = it
                            prefs.setTranslateEnabled(it)
                        },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = AccentViolet,
                            checkedTrackColor = AccentViolet.copy(alpha = 0.3f)
                        )
                    )
                }
            }

            // Target language (visible if translate ON)
            if (translateEnabled) {
                item {
                    LanguageSelector(
                        label = "Traduire vers",
                        selectedCode = targetLang,
                        onClick = { showTargetPicker = true }
                    )
                }
            }

            // Instructions
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = AccentViolet.copy(alpha = 0.1f)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Comment utiliser", fontWeight = FontWeight.SemiBold, color = AccentVioletLight, fontSize = 14.sp)
                        Spacer(Modifier.height(8.dp))
                        Text("1. Ajoutez la tuile VoiceSnap dans vos R\u00e9glages rapides", color = TextSecondary, fontSize = 13.sp)
                        Text("2. Depuis n'importe quelle app, tirez les notifications", color = TextSecondary, fontSize = 13.sp)
                        Text("3. Appuyez sur la tuile VoiceSnap et parlez", color = TextSecondary, fontSize = 13.sp)
                        Text("4. Le texte est copi\u00e9 automatiquement dans le presse-papier", color = TextSecondary, fontSize = 13.sp)
                    }
                }
            }

            // History section
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Historique", fontWeight = FontWeight.SemiBold, fontSize = 18.sp, color = TextPrimary)
                    if (history.isNotEmpty()) {
                        TextButton(onClick = {
                            prefs.clearHistory()
                            history = emptyList()
                        }) {
                            Text("Effacer", color = TextMuted, fontSize = 12.sp)
                        }
                    }
                }
            }

            if (history.isEmpty()) {
                item {
                    Text(
                        "Aucune transcription pour le moment",
                        color = TextMuted,
                        fontSize = 14.sp,
                        modifier = Modifier.padding(vertical = 24.dp)
                    )
                }
            }

            items(history, key = { it.id }) { entry ->
                HistoryCard(entry, onCopy = {
                    val text = entry.translatedText ?: entry.text
                    ClipboardHelper.copyToClipboard(context, text)
                })
            }

            // Bottom spacer
            item { Spacer(Modifier.height(32.dp)) }
        }
    }

    // Bottom sheets for language picking
    if (showSourcePicker) {
        LanguagePickerSheet(
            includeAuto = true,
            selected = sourceLang,
            onSelect = {
                sourceLang = it.code
                prefs.setSourceLang(it.code)
                showSourcePicker = false
            },
            onDismiss = { showSourcePicker = false }
        )
    }

    if (showTargetPicker) {
        LanguagePickerSheet(
            includeAuto = false,
            selected = targetLang,
            onSelect = {
                targetLang = it.code
                prefs.setTargetLang(it.code)
                showTargetPicker = false
            },
            onDismiss = { showTargetPicker = false }
        )
    }
}

@Composable
fun StatusCard(state: RecordingState) {
    val (text, color) = when (state) {
        RecordingState.IDLE -> "Pr\u00eat" to SuccessGreen
        RecordingState.RECORDING -> "\u00c9coute..." to AccentCyan
        RecordingState.TRANSCRIBING -> "Transcription..." to AccentVioletLight
        RecordingState.TRANSLATING -> "Traduction..." to AccentVioletLight
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.1f)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .background(color, RoundedCornerShape(5.dp))
            )
            Spacer(Modifier.width(12.dp))
            Text(text, color = color, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
fun LanguageSelector(label: String, selectedCode: String, onClick: () -> Unit) {
    val lang = LANGUAGES.find { it.code == selectedCode }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgSurface, RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = TextSecondary)
        Text(
            "${lang?.flag ?: ""} ${lang?.name ?: selectedCode}",
            color = TextPrimary,
            fontWeight = FontWeight.Medium
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LanguagePickerSheet(
    includeAuto: Boolean,
    selected: String,
    onSelect: (com.voicesnap.app.data.Language) -> Unit,
    onDismiss: () -> Unit
) {
    val langs = if (includeAuto) LANGUAGES else LANGUAGES.filter { it.code != "auto" }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = BgSurface,
        scrimColor = Color.Black.copy(alpha = 0.5f)
    ) {
        Column(modifier = Modifier.padding(bottom = 32.dp)) {
            Text(
                "Choisir la langue",
                fontWeight = FontWeight.SemiBold,
                fontSize = 18.sp,
                color = TextPrimary,
                modifier = Modifier.padding(horizontal = 24.dp, vertical = 12.dp)
            )
            langs.forEach { lang ->
                val isSelected = lang.code == selected
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onSelect(lang) }
                        .background(if (isSelected) AccentViolet.copy(alpha = 0.15f) else Color.Transparent)
                        .padding(horizontal = 24.dp, vertical = 14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(lang.flag, fontSize = 24.sp)
                    Spacer(Modifier.width(16.dp))
                    Text(
                        lang.name,
                        color = if (isSelected) AccentVioletLight else TextPrimary,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal
                    )
                }
            }
        }
    }
}

@Composable
fun HistoryCard(entry: HistoryEntry, onCopy: () -> Unit) {
    val dateFormat = remember { SimpleDateFormat("HH:mm - dd/MM", Locale.getDefault()) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onCopy),
        colors = CardDefaults.cardColors(containerColor = BgSurface),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Source text
            Text(
                entry.text,
                color = TextPrimary,
                fontSize = 14.sp,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )

            // Translated text
            if (entry.translatedText != null) {
                Spacer(Modifier.height(6.dp))
                Text(
                    entry.translatedText,
                    color = AccentCyan,
                    fontSize = 14.sp,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Metadata
            Spacer(Modifier.height(8.dp))
            Row {
                val srcLang = LANGUAGES.find { it.code == entry.sourceLang }
                Text(
                    "${srcLang?.flag ?: ""} ${srcLang?.name ?: entry.sourceLang}",
                    color = TextMuted,
                    fontSize = 11.sp
                )
                if (entry.targetLang != null) {
                    val tgtLang = LANGUAGES.find { it.code == entry.targetLang }
                    Text(" \u2192 ${tgtLang?.flag ?: ""} ${tgtLang?.name ?: entry.targetLang}",
                        color = TextMuted, fontSize = 11.sp)
                }
                Spacer(Modifier.weight(1f))
                Text(dateFormat.format(Date(entry.timestamp)), color = TextMuted, fontSize = 11.sp)
            }
        }
    }
}
