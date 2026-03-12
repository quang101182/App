# music·ai — Build APK Android

## Prérequis
1. **Android Studio** : https://developer.android.com/studio (installe aussi le SDK)
2. **Java 17+** : inclus avec Android Studio

## Build (première fois)

```bash
# 1. Ouvrir le projet Android dans Android Studio
cd music-ai-app
npx cap open android

# 2. Android Studio va télécharger Gradle et les dépendances (5-10 min)
# 3. Build > Build Bundle(s) / APK(s) > Build APK(s)
# 4. L'APK est dans : android/app/build/outputs/apk/debug/app-debug.apk
```

## Build sans Android Studio (ligne de commande)

```bash
cd android
./gradlew assembleDebug
# APK → app/build/outputs/apk/debug/app-debug.apk
```

## Installer sur téléphone

```bash
# Via USB (mode développeur activé)
adb install android/app/build/outputs/apk/debug/app-debug.apk

# Ou : copier l'APK sur le téléphone et installer manuellement
```

## Mettre à jour le contenu web

```bash
# Copier les fichiers web mis à jour
cp ../music-ai/index.html www/
cp ../music-ai/sw.js www/

# Re-sync
npx cap sync android

# Re-build
cd android && ./gradlew assembleDebug
```

## Notes
- Le background mode est activé automatiquement (plugin @anuradev/capacitor-background-mode)
- L'app affiche une notification persistante "Lecture en cours…" pendant la lecture
- L'AudioContext keepalive maintient le WebView actif en arrière-plan
- Permissions : INTERNET, FOREGROUND_SERVICE, WAKE_LOCK
