/**
 * Patch CapacitorWebView.java to prevent JS suspension in background
 * Patch MediaSessionService.java to fix play/pause PendingIntent bug
 * Patch MediaSessionPlugin.java to auto-toggle playbackState + request AudioFocus on play
 * Patch MediaSessionCallback.java to fix Bluetooth play (direct call instead of PendingIntent)
 * Run after npm install: node patch-webview.js
 */
const fs = require('fs');
const path = require('path');

// --- Patch 1: CapacitorWebView — prevent JS suspension in background ---
// BOTH onWindowVisibilityChanged AND dispatchWindowVisibilityChanged must be overridden
// (source: jofr/capacitor-media-session#11, Capacitor#6234)
const webviewFile = path.join(__dirname, 'node_modules', '@capacitor', 'android', 'capacitor',
  'src', 'main', 'java', 'com', 'getcapacitor', 'CapacitorWebView.java');

let src = fs.readFileSync(webviewFile, 'utf8');
if (src.includes('dispatchWindowVisibilityChanged')) {
  console.log('[patch] CapacitorWebView already patched (v2).');
} else {
  // Remove old partial patch if present
  if (src.includes('onWindowVisibilityChanged')) {
    src = src.replace(/\n\s*\/\/ Keep WebView.*?\n\s*@Override\n\s*protected void onWindowVisibilityChanged\(int visibility\) \{\n\s*if \(visibility != View\.GONE\)\n\s*super\.onWindowVisibilityChanged\(View\.VISIBLE\);\n\s*\}\n?/s, '\n');
    // Also remove old import if added separately
  }
  if (!src.includes('import android.view.View;')) {
    src = src.replace(
      'import android.webkit.WebView;',
      'import android.view.View;\nimport android.webkit.WebView;'
    );
  }
  src = src.replace(
    'public class CapacitorWebView extends WebView {',
    `public class CapacitorWebView extends WebView {

    // Force WebView to stay "visible" in background — prevents JS thread suspension
    // dispatchWindowVisibilityChanged is the key method (called by the framework)
    // onWindowVisibilityChanged is the legacy fallback
    @Override
    public void dispatchWindowVisibilityChanged(int visibility) {
        super.dispatchWindowVisibilityChanged(View.VISIBLE);
    }

    @Override
    protected void onWindowVisibilityChanged(int visibility) {
        if (visibility != View.GONE)
            super.onWindowVisibilityChanged(View.VISIBLE);
    }`
  );
  fs.writeFileSync(webviewFile, src, 'utf8');
  console.log('[patch] CapacitorWebView.java patched (v2: dispatch + onWindow).');
}

// --- Patch 2: MediaSessionService play/pause PendingIntent fix ---
const msFile = path.join(__dirname, 'node_modules', '@capgo', 'capacitor-media-session',
  'android', 'src', 'main', 'java', 'com', 'capgo', 'mediasession', 'MediaSessionService.java');

if (fs.existsSync(msFile)) {
  let ms = fs.readFileSync(msFile, 'utf8');
  let changed = false;

  const oldPlayNotif = 'PlaybackStateCompat.ACTION_PLAY_PAUSE | PlaybackStateCompat.ACTION_PLAY';
  const newPlayNotif = 'PlaybackStateCompat.ACTION_PLAY';
  if (ms.includes(oldPlayNotif)) {
    ms = ms.split(oldPlayNotif).join(newPlayNotif);
    changed = true;
  }

  const oldPauseNotif = 'PlaybackStateCompat.ACTION_PLAY_PAUSE | PlaybackStateCompat.ACTION_PAUSE';
  const newPauseNotif = 'PlaybackStateCompat.ACTION_PLAY_PAUSE';
  if (ms.includes(oldPauseNotif)) {
    ms = ms.split(oldPauseNotif).join(newPauseNotif);
    changed = true;
  }

  if (changed) {
    fs.writeFileSync(msFile, ms, 'utf8');
    console.log('[patch] MediaSessionService.java patched for play/pause fix.');
  } else {
    console.log('[patch] MediaSessionService already patched.');
  }
} else {
  console.log('[patch] @capgo/capacitor-media-session not found, skipping.');
}

// --- Patch 3: MediaSessionPlugin — auto-toggle state + AudioFocus on play ---
const pluginFile = path.join(__dirname, 'node_modules', '@capgo', 'capacitor-media-session',
  'android', 'src', 'main', 'java', 'com', 'capgo', 'mediasession', 'MediaSessionPlugin.java');

if (fs.existsSync(pluginFile)) {
  let pl = fs.readFileSync(pluginFile, 'utf8');
  let plChanged = false;

  // 3a. Add AudioManager + AudioFocusRequest imports
  if (!pl.includes('import android.media.AudioManager;')) {
    pl = pl.replace(
      'import android.util.Log;',
      'import android.media.AudioAttributes;\nimport android.media.AudioFocusRequest;\nimport android.media.AudioManager;\nimport android.os.Build;\nimport android.util.Log;'
    );
    plChanged = true;
  }

  // 3b. Add audioFocusRequest field + requestAudioFocus method after the playbackState field
  if (!pl.includes('requestAudioFocusForPlay')) {
    pl = pl.replace(
      'private String playbackState = "none";',
      `private String playbackState = "none";
    private AudioFocusRequest audioFocusRequest;

    private void requestAudioFocusForPlay() {
        try {
            AudioManager am = (AudioManager) getContext().getSystemService(android.content.Context.AUDIO_SERVICE);
            if (am == null) return;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (audioFocusRequest == null) {
                    audioFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                        .setAudioAttributes(new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                            .build())
                        .setWillPauseWhenDucked(false)
                        .build();
                }
                int result = am.requestAudioFocus(audioFocusRequest);
                Log.d(TAG, "requestAudioFocus result=" + result + " (1=GRANTED)");
            }
        } catch (Exception e) {
            Log.w(TAG, "requestAudioFocus failed", e);
        }
    }`
    );
    plChanged = true;
  }

  // 3c. Patch actionCallback to auto-toggle state + request audio focus on play
  const oldActionCb = `    public void actionCallback(String action, JSObject data) {
        PluginCall handler = actionHandlers.get(action);`;
  const oldActionCbPatched = /Auto-update playbackState/.test(pl);

  if (!pl.includes('requestAudioFocusForPlay()')) {
    // Remove old patch if present
    if (oldActionCbPatched) {
      pl = pl.replace(
        /    public void actionCallback\(String action, JSObject data\) \{\n        \/\/ Auto-update playbackState.*?\n\n        PluginCall handler = actionHandlers\.get\(action\);/s,
        `    public void actionCallback(String action, JSObject data) {
        // Auto-update playbackState + request AudioFocus on play
        if ("play".equals(action)) {
            requestAudioFocusForPlay();
            playbackState = "playing";
            Log.d(TAG, "  -> set playbackState=playing + audioFocus, calling updateServicePlaybackState()");
            updateServicePlaybackState();
        } else if ("pause".equals(action)) {
            playbackState = "paused";
            Log.d(TAG, "  -> set playbackState=paused, calling updateServicePlaybackState()");
            updateServicePlaybackState();
        }

        PluginCall handler = actionHandlers.get(action);`
      );
    } else if (pl.includes(oldActionCb)) {
      pl = pl.replace(oldActionCb, `    public void actionCallback(String action, JSObject data) {
        // Auto-update playbackState + request AudioFocus on play
        if ("play".equals(action)) {
            requestAudioFocusForPlay();
            playbackState = "playing";
            Log.d(TAG, "  -> set playbackState=playing + audioFocus, calling updateServicePlaybackState()");
            updateServicePlaybackState();
        } else if ("pause".equals(action)) {
            playbackState = "paused";
            Log.d(TAG, "  -> set playbackState=paused, calling updateServicePlaybackState()");
            updateServicePlaybackState();
        }

        PluginCall handler = actionHandlers.get(action);`);
    }
    plChanged = true;
  }

  if (plChanged) {
    fs.writeFileSync(pluginFile, pl, 'utf8');
    console.log('[patch] MediaSessionPlugin.java patched (auto-toggle + AudioFocus).');
  } else {
    console.log('[patch] MediaSessionPlugin already patched (v2).');
  }
} else {
  console.log('[patch] @capgo/capacitor-media-session plugin not found, skipping.');
}

// --- Patch 4: MediaSessionCallback — direct play/pause for Bluetooth (bypass PendingIntent) ---
const callbackFile = path.join(__dirname, 'node_modules', '@capgo', 'capacitor-media-session',
  'android', 'src', 'main', 'java', 'com', 'capgo', 'mediasession', 'MediaSessionCallback.java');

if (fs.existsSync(callbackFile)) {
  let cb = fs.readFileSync(callbackFile, 'utf8');

  const oldPlayPause = `                case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                case KeyEvent.KEYCODE_HEADSETHOOK:
                    // Route through PendingIntent — same system path as notification buttons
                    plugin.dispatchPlayPauseViaIntent();
                    return true;`;
  const newPlayPause = `                case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                case KeyEvent.KEYCODE_HEADSETHOOK:
                    // Direct call — PendingIntent roundtrip fails for BT play on some devices
                    if ("playing".equals(plugin.getPlaybackState())) {
                        onPause();
                    } else {
                        onPlay();
                    }
                    return true;`;

  if (cb.includes('Direct call')) {
    console.log('[patch] MediaSessionCallback already patched.');
  } else if (cb.includes(oldPlayPause)) {
    cb = cb.replace(oldPlayPause, newPlayPause);
    fs.writeFileSync(callbackFile, cb, 'utf8');
    console.log('[patch] MediaSessionCallback.java patched for direct BT play/pause.');
  } else {
    console.log('[patch] MediaSessionCallback.java — could not find target code to patch.');
  }
} else {
  console.log('[patch] MediaSessionCallback.java not found, skipping.');
}
