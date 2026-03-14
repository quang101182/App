/**
 * Patch 1: CapacitorWebView.java — prevent JS suspension in background
 * (keeps WebView "visible" so JS thread doesn't get suspended)
 * Run after npm install: node patch-webview.js
 */
const fs = require('fs');
const path = require('path');

// --- Patch 1: CapacitorWebView — prevent JS suspension in background ---
const webviewFile = path.join(__dirname, 'node_modules', '@capacitor', 'android', 'capacitor',
  'src', 'main', 'java', 'com', 'getcapacitor', 'CapacitorWebView.java');

let src = fs.readFileSync(webviewFile, 'utf8');
if (src.includes('dispatchWindowVisibilityChanged')) {
  console.log('[patch] CapacitorWebView already patched.');
} else {
  if (src.includes('onWindowVisibilityChanged')) {
    src = src.replace(/\n\s*\/\/ Keep WebView.*?\n\s*@Override\n\s*protected void onWindowVisibilityChanged\(int visibility\) \{\n\s*if \(visibility != View\.GONE\)\n\s*super\.onWindowVisibilityChanged\(View\.VISIBLE\);\n\s*\}\n?/s, '\n');
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
