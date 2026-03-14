package com.videograb.app;

import android.graphics.Bitmap;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Message;
import android.util.Log;
import android.view.KeyEvent;
import android.webkit.ClientCertRequest;
import android.webkit.HttpAuthHandler;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.SafeBrowsingResponse;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Wraps the existing Capacitor BridgeWebViewClient.
 * Intercepts shouldInterceptRequest for ad blocking + video detection,
 * delegates EVERYTHING else to the original client (which serves local assets).
 */
public class VideoInterceptClient extends WebViewClient {

    private static final String TAG = "VideoIntercept";
    private final WebViewClient original;
    private final WebView webView;

    // Video extensions (NO .ts — HLS segments spam)
    private static final Pattern VIDEO_PATTERN = Pattern.compile(
        "\\.(mp4|m3u8|webm|mov|mkv|mpd|m4v)(\\?|$)", Pattern.CASE_INSENSITIVE
    );

    // Skip patterns (noise URLs)
    private static final Pattern SKIP_PATTERN = Pattern.compile(
        "(preview|thumb|trailer|teaser|sample|poster|icon|logo|pixel|beacon|track|analytics|sprite|loading|placeholder)", Pattern.CASE_INSENSITIVE
    );

    // Segment-like filenames: pure hex/hash strings (CDN chunks, not real videos)
    private static final Pattern SEGMENT_PATTERN = Pattern.compile(
        "/[0-9a-f]{20,}\\.(mp4|m4v)", Pattern.CASE_INSENSITIVE
    );

    // Dedup by normalized path (strip query params)
    private final Set<String> notifiedPaths = new HashSet<>();

    // Ad domains (70+)
    private static final Set<String> AD_DOMAINS = new HashSet<>(Arrays.asList(
        "doubleclick.net","googlesyndication.com","googleadservices.com",
        "adnxs.com","pubmatic.com","openx.net","criteo.com",
        "rubiconproject.com","casalemedia.com","sizmek.com","flashtalking.com",
        "adform.net","sovrn.com","bidswitch.net","bidvertiser.com",
        "contextweb.com","conversant.com",
        "exoclick.com","exosrv.com","propellerads.com",
        "popads.net","popcash.net","popunder.net",
        "juicyads.com","trafficjunky.net","trafficjunky.com","trafficfactory.biz",
        "adsterra.com","adsterra.net","hilltopads.com",
        "clickadu.com","clickaine.com",
        "pushame.com","ad-maven.com","plugrush.com",
        "trafficstars.com","crakrevenue.com",
        "tsyndicate.com","realsrv.com",
        "onclkds.com","onclickds.com","onclickmax.com","onclickrev.com",
        "magsrv.com","ero-advertising.com",
        "monetag.com","a-ads.com","coinzilla.com","bitmedia.io",
        "adcash.com","richpush.net","evadav.com",
        "notifadz.com","mondiad.com","galaksion.com","clickstar.me",
        "clictune.com","linkvertise.com","shrinkme.io","lootlinks.co",
        "amazon-adsystem.com","moatads.com","quantserve.com","scorecardresearch.com",
        "histats.com","statcounter.com","hotjar.com","mouseflow.com",
        "googletagmanager.com","google-analytics.com","facebook.net",
        "spotx.tv","vungle.com","applovin.com","chartboost.com",
        "inmobi.com","mintegral.com",
        "taboola.com","outbrain.com","mgid.com","revcontent.com","zergnet.com",
        "liveadsexchange.com","betteradsexchange.com"
    ));

    private static final WebResourceResponse BLOCKED = new WebResourceResponse(
        "text/plain", "UTF-8", new ByteArrayInputStream(new byte[0])
    );

    public VideoInterceptClient(WebViewClient original, WebView webView) {
        this.original = original;
        this.webView = webView;
    }

    // ═══ The only method we actually override with custom logic ═══

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        Uri uri = request.getUrl();
        String host = uri.getHost();
        String url = uri.toString();

        // 1. Block ads
        if (host != null && isAdDomain(host)) {
            return BLOCKED;
        }

        // 2. Detect videos (filtered to avoid segment spam)
        if (VIDEO_PATTERN.matcher(url).find()) {
            String path = uri.getPath();
            String normalizedPath = path != null ? path : url;
            if (!SKIP_PATTERN.matcher(url).find()
                && !SEGMENT_PATTERN.matcher(url).find()
                && !notifiedPaths.contains(normalizedPath)) {
                notifiedPaths.add(normalizedPath);
                String ext = extractExtension(url);
                Log.d(TAG, "VIDEO: " + url.substring(0, Math.min(url.length(), 120)) + " (" + ext + ")");
                notifyVideoDetected(url, ext);
            }
        }

        // 3. Delegate to Capacitor's BridgeWebViewClient (serves local assets!)
        return original.shouldInterceptRequest(view, request);
    }

    // ═══ Delegate ALL other WebViewClient methods to original ═══

    @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return original.shouldOverrideUrlLoading(v, r); }
    @Override public void onPageStarted(WebView v, String u, Bitmap f) { original.onPageStarted(v, u, f); }
    @Override public void onPageFinished(WebView v, String u) { original.onPageFinished(v, u); }
    @Override public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) { original.onReceivedError(v, r, e); }
    @Override public void onReceivedHttpError(WebView v, WebResourceRequest r, WebResourceResponse e) { original.onReceivedHttpError(v, r, e); }
    @Override public void onReceivedSslError(WebView v, SslErrorHandler h, SslError e) { original.onReceivedSslError(v, h, e); }
    @Override public void onReceivedClientCertRequest(WebView v, ClientCertRequest r) { original.onReceivedClientCertRequest(v, r); }
    @Override public void onReceivedHttpAuthRequest(WebView v, HttpAuthHandler h, String host, String realm) { original.onReceivedHttpAuthRequest(v, h, host, realm); }
    @Override public boolean onRenderProcessGone(WebView v, RenderProcessGoneDetail d) { return original.onRenderProcessGone(v, d); }
    @Override public void onReceivedLoginRequest(WebView v, String realm, String account, String args) { original.onReceivedLoginRequest(v, realm, account, args); }
    @Override public void onFormResubmission(WebView v, Message d, Message r) { original.onFormResubmission(v, d, r); }
    @Override public void doUpdateVisitedHistory(WebView v, String u, boolean r) { original.doUpdateVisitedHistory(v, u, r); }
    @Override public void onScaleChanged(WebView v, float o, float n) { original.onScaleChanged(v, o, n); }
    @Override public boolean shouldOverrideKeyEvent(WebView v, KeyEvent e) { return original.shouldOverrideKeyEvent(v, e); }
    @Override public void onUnhandledKeyEvent(WebView v, KeyEvent e) { original.onUnhandledKeyEvent(v, e); }
    @Override public void onLoadResource(WebView v, String u) { original.onLoadResource(v, u); }
    @Override public void onPageCommitVisible(WebView v, String u) { original.onPageCommitVisible(v, u); }
    @Override public void onSafeBrowsingHit(WebView v, WebResourceRequest r, int t, SafeBrowsingResponse c) { original.onSafeBrowsingHit(v, r, t, c); }

    // ═══ Helper methods ═══

    private boolean isAdDomain(String host) {
        host = host.toLowerCase();
        if (AD_DOMAINS.contains(host)) return true;
        String[] parts = host.split("\\.");
        for (int i = 1; i < parts.length - 1; i++) {
            StringBuilder sb = new StringBuilder();
            for (int j = i; j < parts.length; j++) {
                if (j > i) sb.append(".");
                sb.append(parts[j]);
            }
            if (AD_DOMAINS.contains(sb.toString())) return true;
        }
        return false;
    }

    private String extractExtension(String url) {
        try {
            String path = Uri.parse(url).getPath();
            if (path == null) return "mp4";
            int dot = path.lastIndexOf('.');
            if (dot >= 0) {
                String ext = path.substring(dot + 1).toLowerCase();
                int q = ext.indexOf('?');
                return q >= 0 ? ext.substring(0, q) : ext;
            }
        } catch (Exception e) { /* ignore */ }
        return "mp4";
    }

    private void notifyVideoDetected(String url, String type) {
        webView.post(() -> {
            String escaped = url.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "");
            webView.evaluateJavascript(
                "if(typeof handleNativeVideoDetected==='function')handleNativeVideoDetected('" + escaped + "','" + type + "');", null);
        });
    }
}
