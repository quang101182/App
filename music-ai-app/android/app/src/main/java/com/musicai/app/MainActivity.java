package com.musicai.app;

import android.os.Bundle;
import android.os.PowerManager;
import android.view.View;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private PowerManager.WakeLock wakeLock;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Acquire partial wake lock — keeps CPU alive for background audio
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "musicai::audio");
        wakeLock.setReferenceCounted(false);
        wakeLock.acquire(7200000); // 2 hours max
    }

    @Override
    public void load() {
        super.load();

        // Apply native padding on WebView's parent to avoid status bar overlap
        // This avoids conflicting with Capacitor 8 SystemBars insets listener
        View webViewParent = (View) getBridge().getWebView().getParent();
        ViewCompat.setOnApplyWindowInsetsListener(webViewParent, (v, insets) -> {
            Insets systemBars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout()
            );
            Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());
            int bottomPadding = Math.max(systemBars.bottom, ime.bottom);
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, bottomPadding);
            return WindowInsetsCompat.CONSUMED;
        });
    }
}
