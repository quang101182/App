/**
 * Patch CapacitorWebView.java to prevent audio pause in background
 * Patch MediaSessionService.java to fix play/pause PendingIntent bug
 * Patch MediaSessionPlugin.java to auto-toggle playbackState on play/pause
 * Patch MediaSessionCallback.java to fix Bluetooth play (direct call instead of PendingIntent)
 * Run after npm install: node patch-webview.js
 */
const fs = require('fs');
const path = require('path');

// --- Patch 1: CapacitorWebView background audio ---
const webviewFile = path.join(__dirname, 'node_modules', '@capacitor', 'android', 'capacitor',
  'src', 'main', 'java', 'com', 'getcapacitor', 'CapacitorWebView.java');

let src = fs.readFileSync(webviewFile, 'utf8');
if (src.includes('onWindowVisibilityChanged')) {
  console.log('[patch] CapacitorWebView already patched.');
} else {
  src = src.replace(
    'import android.webkit.WebView;',
    'import android.view.View;\nimport android.webkit.WebView;'
  );
  src = src.replace(
    'public class CapacitorWebView extends WebView {',
    `public class CapacitorWebView extends WebView {

    // Keep WebView "visible" when app goes to background — prevents audio pause
    @Override
    protected void onWindowVisibilityChanged(int visibility) {
        if (visibility != View.GONE)
            super.onWindowVisibilityChanged(View.VISIBLE);
    }`
  );
  fs.writeFileSync(webviewFile, src, 'utf8');
  console.log('[patch] CapacitorWebView.java patched for background audio.');
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

// --- Patch 3: MediaSessionPlugin auto-toggle playbackState on play/pause action ---
const pluginFile = path.join(__dirname, 'node_modules', '@capgo', 'capacitor-media-session',
  'android', 'src', 'main', 'java', 'com', 'capgo', 'mediasession', 'MediaSessionPlugin.java');

if (fs.existsSync(pluginFile)) {
  let pl = fs.readFileSync(pluginFile, 'utf8');

  const oldActionCb = `    public void actionCallback(String action, JSObject data) {
        PluginCall handler = actionHandlers.get(action);`;
  const newActionCb = `    public void actionCallback(String action, JSObject data) {
        // Auto-update playbackState on play/pause to immediately toggle notification icon
        if ("play".equals(action)) {
            playbackState = "playing";
            updateServicePlaybackState();
        } else if ("pause".equals(action)) {
            playbackState = "paused";
            updateServicePlaybackState();
        }

        PluginCall handler = actionHandlers.get(action);`;

  if (pl.includes('Auto-update playbackState')) {
    console.log('[patch] MediaSessionPlugin already patched.');
  } else if (pl.includes(oldActionCb)) {
    pl = pl.replace(oldActionCb, newActionCb);
    fs.writeFileSync(pluginFile, pl, 'utf8');
    console.log('[patch] MediaSessionPlugin.java patched for auto play/pause toggle.');
  } else {
    console.log('[patch] MediaSessionPlugin.java — could not find target code to patch.');
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
