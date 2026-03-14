package com.videograb.app;

import android.content.Context;
import android.net.Uri;
import android.util.Log;
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
 * WebViewClient that intercepts requests to:
 * 1. Block ad/tracking domains (return empty 204 response)
 * 2. Detect video URLs (.mp4, .m3u8, .webm, etc.) and notify JS
 */
public class VideoInterceptClient extends WebViewClient {

    private static final String TAG = "VideoIntercept";
    private final Context context;
    private final WebView webView;

    // Video file extensions to detect (NO .ts — causes 100+ false positives from HLS segments)
    private static final Pattern VIDEO_PATTERN = Pattern.compile(
        "\\.(mp4|m3u8|webm|mov|mkv|mpd|m4v)(\\?|$)", Pattern.CASE_INSENSITIVE
    );

    // Thumbnail/preview/tracking patterns to skip
    private static final Pattern SKIP_PATTERN = Pattern.compile(
        "(preview|thumb|trailer|teaser|sample|poster|icon|logo|pixel|beacon|track|analytics|googlevideo\\.com/videoplayback)", Pattern.CASE_INSENSITIVE
    );

    // Dedup: track already-notified URLs (avoid 171 duplicates)
    private final Set<String> notifiedUrls = new HashSet<>();

    // Ad/tracking domains blocklist (70+ domains from api-gateway)
    private static final Set<String> AD_DOMAINS = new HashSet<>(Arrays.asList(
        "doubleclick.net", "googlesyndication.com", "googleadservices.com",
        "adnxs.com", "pubmatic.com", "openx.net", "criteo.com",
        "rubiconproject.com", "casalemedia.com", "sizmek.com", "flashtalking.com",
        "adform.net", "sovrn.com", "bidswitch.net", "bidvertiser.com",
        "contextweb.com", "conversant.com",
        "exoclick.com", "exosrv.com", "propellerads.com",
        "popads.net", "popcash.net", "popunder.net",
        "juicyads.com", "trafficjunky.net", "trafficjunky.com", "trafficfactory.biz",
        "adsterra.com", "adsterra.net", "hilltopads.com",
        "clickadu.com", "clickaine.com",
        "pushame.com", "ad-maven.com", "plugrush.com",
        "trafficstars.com", "crakrevenue.com",
        "tsyndicate.com", "realsrv.com",
        "onclkds.com", "onclickds.com", "onclickmax.com", "onclickrev.com",
        "magsrv.com", "ero-advertising.com",
        "monetag.com", "a-ads.com", "coinzilla.com", "bitmedia.io",
        "adcash.com", "richpush.net", "evadav.com",
        "notifadz.com", "mondiad.com", "galaksion.com", "clickstar.me",
        "clictune.com", "linkvertise.com", "shrinkme.io", "lootlinks.co",
        "amazon-adsystem.com", "moatads.com", "quantserve.com", "scorecardresearch.com",
        "histats.com", "statcounter.com", "hotjar.com", "mouseflow.com",
        "googletagmanager.com", "google-analytics.com", "facebook.net",
        "spotx.tv", "vungle.com", "applovin.com", "chartboost.com",
        "inmobi.com", "mintegral.com",
        "taboola.com", "outbrain.com", "mgid.com", "revcontent.com", "zergnet.com",
        "liveadsexchange.com", "betteradsexchange.com"
    ));

    // Empty response for blocked requests
    private static final WebResourceResponse BLOCKED_RESPONSE = new WebResourceResponse(
        "text/plain", "UTF-8", new ByteArrayInputStream(new byte[0])
    );

    public VideoInterceptClient(Context context, WebView webView) {
        this.context = context;
        this.webView = webView;
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        Uri uri = request.getUrl();
        String host = uri.getHost();
        String url = uri.toString();

        // 1. Block ad domains
        if (host != null && isAdDomain(host)) {
            Log.d(TAG, "BLOCKED ad: " + host);
            return BLOCKED_RESPONSE;
        }

        // 2. Detect video URLs (dedup + skip previews/tracking)
        if (VIDEO_PATTERN.matcher(url).find()) {
            if (!SKIP_PATTERN.matcher(url).find() && !notifiedUrls.contains(url)) {
                notifiedUrls.add(url);
                String extension = extractExtension(url);
                Log.d(TAG, "VIDEO detected: " + url + " (" + extension + ")");
                notifyVideoDetected(url, extension);
            }
        }

        return super.shouldInterceptRequest(view, request);
    }

    /**
     * Check if a hostname matches any ad domain (including subdomains)
     */
    private boolean isAdDomain(String host) {
        host = host.toLowerCase();
        // Direct match
        if (AD_DOMAINS.contains(host)) return true;
        // Subdomain match: split and check parent domains
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

    /**
     * Extract file extension from URL
     */
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

    /**
     * Notify JS side that a video was detected by the native interceptor
     */
    private void notifyVideoDetected(String url, String type) {
        // Must run on UI thread to call evaluateJavascript
        webView.post(() -> {
            String escaped = url.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "");
            String js = "if(typeof handleNativeVideoDetected==='function')handleNativeVideoDetected('" + escaped + "','" + type + "');";
            webView.evaluateJavascript(js, null);
        });
    }
}
