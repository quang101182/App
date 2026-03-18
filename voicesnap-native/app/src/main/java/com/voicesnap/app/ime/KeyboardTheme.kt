package com.voicesnap.app.ime

import android.graphics.Color

data class KeyboardTheme(
    val name: String,
    val icon: String,        // Unicode icon for the toggle button
    val bgKeyboard: Int,     // Main keyboard background
    val bgButton: Int,       // Regular button/key background
    val bgButtonBorder: Int, // Button border color (0 = no border)
    val bgDictate: Int,      // Dictate button background
    val bgTranslate: Int,    // Translate button background
    val bgRecording: Int,    // Recording state button background
    val bgBanner: Int,       // Clipboard banner background
    val textPrimary: Int,    // Primary text color
    val textSecondary: Int,  // Secondary/muted text color
    val textAccent: Int,     // Accent text (like "Coller" on banner)
    val accentRewrite: Int,  // Rewrite button/label color
    val vadOnColor: Int,     // VAD toggle ON color
    val vadOffColor: Int,    // VAD toggle OFF color
    val cornerRadius: Float, // Corner radius in dp for buttons
    val hasGlow: Boolean,    // Whether action buttons have glow effect
    val glowColor: Int       // Glow color (if hasGlow)
) {
    companion object {
        val THEMES = listOf(
            // 1. SOLID — Current dark theme
            KeyboardTheme(
                name = "Solid",
                icon = "\u25FC",  // ◼
                bgKeyboard = Color.parseColor("#18181B"),
                bgButton = Color.parseColor("#27272A"),
                bgButtonBorder = 0,
                bgDictate = Color.parseColor("#6D28D9"),
                bgTranslate = Color.parseColor("#0E7490"),
                bgRecording = Color.parseColor("#DC2626"),
                bgBanner = Color.parseColor("#2D2D30"),
                textPrimary = Color.parseColor("#FAFAFA"),
                textSecondary = Color.parseColor("#71717A"),
                textAccent = Color.parseColor("#8B5CF6"),
                accentRewrite = Color.parseColor("#C4B5FD"),
                vadOnColor = Color.parseColor("#22C55E"),
                vadOffColor = Color.parseColor("#EF4444"),
                cornerRadius = 12f,
                hasGlow = false,
                glowColor = 0
            ),
            // 2. GLASS — Glassmorphism, semi-transparent
            KeyboardTheme(
                name = "Glass",
                icon = "\u25C7",  // ◇
                bgKeyboard = Color.parseColor("#0D0D0F"),
                bgButton = Color.parseColor("#1A1A1F"),
                bgButtonBorder = Color.parseColor("#2A2A30"),
                bgDictate = Color.parseColor("#5B21B6"),
                bgTranslate = Color.parseColor("#0C4A6E"),
                bgRecording = Color.parseColor("#B91C1C"),
                bgBanner = Color.parseColor("#1A1A1F"),
                textPrimary = Color.parseColor("#E4E4E7"),
                textSecondary = Color.parseColor("#8B8B96"),
                textAccent = Color.parseColor("#A78BFA"),
                accentRewrite = Color.parseColor("#DDD6FE"),
                vadOnColor = Color.parseColor("#34D399"),
                vadOffColor = Color.parseColor("#F87171"),
                cornerRadius = 16f,
                hasGlow = true,
                glowColor = Color.parseColor("#6D28D9")
            ),
            // 3. MIDNIGHT — Deep blue + gold/amber accents
            KeyboardTheme(
                name = "Midnight",
                icon = "\u263E",  // ☾
                bgKeyboard = Color.parseColor("#0B1120"),
                bgButton = Color.parseColor("#131D35"),
                bgButtonBorder = Color.parseColor("#1E2D4A"),
                bgDictate = Color.parseColor("#B45309"),
                bgTranslate = Color.parseColor("#1E40AF"),
                bgRecording = Color.parseColor("#DC2626"),
                bgBanner = Color.parseColor("#131D35"),
                textPrimary = Color.parseColor("#E2E8F0"),
                textSecondary = Color.parseColor("#64748B"),
                textAccent = Color.parseColor("#F59E0B"),
                accentRewrite = Color.parseColor("#FCD34D"),
                vadOnColor = Color.parseColor("#F59E0B"),
                vadOffColor = Color.parseColor("#EF4444"),
                cornerRadius = 12f,
                hasGlow = true,
                glowColor = Color.parseColor("#B45309")
            ),
            // 4. NEON — Pure black + neon green/magenta
            KeyboardTheme(
                name = "Neon",
                icon = "\u26A1",  // ⚡
                bgKeyboard = Color.parseColor("#050505"),
                bgButton = Color.parseColor("#111111"),
                bgButtonBorder = Color.parseColor("#1A1A1A"),
                bgDictate = Color.parseColor("#059669"),
                bgTranslate = Color.parseColor("#BE185D"),
                bgRecording = Color.parseColor("#DC2626"),
                bgBanner = Color.parseColor("#111111"),
                textPrimary = Color.parseColor("#F0FDF4"),
                textSecondary = Color.parseColor("#6B7280"),
                textAccent = Color.parseColor("#10B981"),
                accentRewrite = Color.parseColor("#F0ABFC"),
                vadOnColor = Color.parseColor("#10B981"),
                vadOffColor = Color.parseColor("#F43F5E"),
                cornerRadius = 8f,
                hasGlow = true,
                glowColor = Color.parseColor("#059669")
            ),
            // 5. ARCTIC — Light theme, icy blue
            KeyboardTheme(
                name = "Arctic",
                icon = "\u2744",  // ❄
                bgKeyboard = Color.parseColor("#F1F5F9"),
                bgButton = Color.parseColor("#E2E8F0"),
                bgButtonBorder = Color.parseColor("#CBD5E1"),
                bgDictate = Color.parseColor("#2563EB"),
                bgTranslate = Color.parseColor("#0891B2"),
                bgRecording = Color.parseColor("#DC2626"),
                bgBanner = Color.parseColor("#E2E8F0"),
                textPrimary = Color.parseColor("#0F172A"),
                textSecondary = Color.parseColor("#64748B"),
                textAccent = Color.parseColor("#2563EB"),
                accentRewrite = Color.parseColor("#7C3AED"),
                vadOnColor = Color.parseColor("#059669"),
                vadOffColor = Color.parseColor("#DC2626"),
                cornerRadius = 14f,
                hasGlow = false,
                glowColor = 0
            )
        )

        fun fromName(name: String): KeyboardTheme =
            THEMES.find { it.name == name } ?: THEMES[0]

        fun next(current: KeyboardTheme): KeyboardTheme {
            val idx = THEMES.indexOf(current)
            return THEMES[(idx + 1) % THEMES.size]
        }
    }
}
