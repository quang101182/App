package com.videograb.app;

import android.os.Bundle;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
    }

    @Override
    public void load() {
        super.load();

        WebView webView = getBridge().getWebView();

        // Enable cookies (needed for proxy-loaded sites)
        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        // WebView settings for video sites
        WebSettings settings = webView.getSettings();
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);

        // Register native download bridge (JS ↔ Java)
        NativeDownloadBridge downloadBridge = new NativeDownloadBridge(this);
        webView.addJavascriptInterface(downloadBridge, "NativeDownload");

        // Inject VideoInterceptClient into the existing BridgeWebViewClient
        VideoInterceptClient interceptClient = new VideoInterceptClient(this, webView);
        webView.setWebViewClient(interceptClient);

        // Apply native padding for status bar / navigation bar
        View webViewParent = (View) webView.getParent();
        ViewCompat.setOnApplyWindowInsetsListener(webViewParent, (v, insets) -> {
            Insets systemBars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout()
            );
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return WindowInsetsCompat.CONSUMED;
        });
    }
}
