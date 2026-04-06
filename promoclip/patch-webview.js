/**
 * Patch CapacitorWebView.java to prevent JS suspension in background
 * PromoClip needs this for video generation to continue if screen locks
 * Run after npm install: node patch-webview.js
 */
const fs = require('fs');
const path = require('path');

const webviewFile = path.join(__dirname, 'node_modules', '@capacitor', 'android', 'capacitor',
  'src', 'main', 'java', 'com', 'getcapacitor', 'CapacitorWebView.java');

if (!fs.existsSync(webviewFile)) {
  console.log('[patch] CapacitorWebView.java not found, skipping (run npm install first).');
  process.exit(0);
}

let src = fs.readFileSync(webviewFile, 'utf8');
if (src.includes('dispatchWindowVisibilityChanged')) {
  console.log('[patch] CapacitorWebView already patched.');
} else {
  if (!src.includes('import android.view.View;')) {
    src = src.replace(
      'import android.webkit.WebView;',
      'import android.view.View;\nimport android.webkit.WebView;'
    );
  }
  src = src.replace(
    'public class CapacitorWebView extends WebView {',
    `public class CapacitorWebView extends WebView {

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
  console.log('[patch] CapacitorWebView.java patched.');
}
