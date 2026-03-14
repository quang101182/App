package com.videograb.app;

import android.app.DownloadManager;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Environment;
import android.util.Log;
import android.webkit.JavascriptInterface;

import java.io.File;

/**
 * JavascriptInterface bridge for native DownloadManager.
 * JS calls: NativeDownload.startDownload(url, filename, mime)
 *           NativeDownload.queryProgress(downloadId) → "progress|totalBytes|status"
 *           NativeDownload.cancelDownload(downloadId)
 */
public class NativeDownloadBridge {

    private static final String TAG = "NativeDownload";
    private static final String DOWNLOAD_SUBDIR = "VideoGrab";
    private final Context context;

    public NativeDownloadBridge(Context context) {
        this.context = context;
    }

    /**
     * Start a download using Android DownloadManager.
     * @param url     The direct URL to download
     * @param filename The desired filename
     * @param mime    MIME type (e.g., "video/mp4")
     * @return The download ID as a string (for tracking)
     */
    @JavascriptInterface
    public String startDownload(String url, String filename, String mime) {
        try {
            Log.d(TAG, "startDownload: " + url + " -> " + filename);

            // Sanitize filename
            filename = sanitizeFilename(filename);
            if (mime == null || mime.isEmpty()) mime = "video/mp4";

            // Ensure subdirectory exists
            File dir = new File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), DOWNLOAD_SUBDIR);
            if (!dir.exists()) dir.mkdirs();

            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setTitle(filename);
            request.setDescription("VideoGrab — Downloading video");
            request.setMimeType(mime);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(
                Environment.DIRECTORY_DOWNLOADS, DOWNLOAD_SUBDIR + "/" + filename);
            // Allow download over any network
            request.setAllowedOverMetered(true);
            request.setAllowedOverRoaming(true);

            DownloadManager dm = (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
            long id = dm.enqueue(request);
            Log.d(TAG, "Download enqueued: id=" + id);
            return String.valueOf(id);

        } catch (Exception e) {
            Log.e(TAG, "startDownload failed", e);
            return "-1";
        }
    }

    /**
     * Query download progress.
     * @param downloadIdStr The download ID returned by startDownload
     * @return "progress|totalBytes|status" (progress 0-100, status: running/paused/pending/success/failed)
     */
    @JavascriptInterface
    public String queryProgress(String downloadIdStr) {
        try {
            long downloadId = Long.parseLong(downloadIdStr);
            DownloadManager dm = (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
            DownloadManager.Query query = new DownloadManager.Query();
            query.setFilterById(downloadId);

            Cursor cursor = dm.query(query);
            if (cursor != null && cursor.moveToFirst()) {
                long bytesDownloaded = cursor.getLong(
                    cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR));
                long bytesTotal = cursor.getLong(
                    cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES));
                int status = cursor.getInt(
                    cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));

                cursor.close();

                int progress = bytesTotal > 0 ? (int)(bytesDownloaded * 100 / bytesTotal) : 0;
                String statusStr;
                switch (status) {
                    case DownloadManager.STATUS_RUNNING: statusStr = "running"; break;
                    case DownloadManager.STATUS_PAUSED: statusStr = "paused"; break;
                    case DownloadManager.STATUS_PENDING: statusStr = "pending"; break;
                    case DownloadManager.STATUS_SUCCESSFUL: statusStr = "success"; progress = 100; break;
                    case DownloadManager.STATUS_FAILED: statusStr = "failed"; break;
                    default: statusStr = "unknown";
                }
                return progress + "|" + bytesTotal + "|" + statusStr;
            }
            if (cursor != null) cursor.close();
        } catch (Exception e) {
            Log.e(TAG, "queryProgress failed", e);
        }
        return "0|0|unknown";
    }

    /**
     * Cancel a download.
     * @param downloadIdStr The download ID to cancel
     * @return "true" if cancelled successfully
     */
    @JavascriptInterface
    public String cancelDownload(String downloadIdStr) {
        try {
            long downloadId = Long.parseLong(downloadIdStr);
            DownloadManager dm = (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
            int removed = dm.remove(downloadId);
            Log.d(TAG, "Download cancelled: id=" + downloadId + ", removed=" + removed);
            return removed > 0 ? "true" : "false";
        } catch (Exception e) {
            Log.e(TAG, "cancelDownload failed", e);
            return "false";
        }
    }

    /**
     * Sanitize filename: remove invalid characters, limit length
     */
    private String sanitizeFilename(String name) {
        if (name == null || name.isEmpty()) return "video.mp4";
        // Remove invalid filesystem characters
        name = name.replaceAll("[\\\\/:*?\"<>|]", "_");
        // Limit length (keep extension)
        if (name.length() > 80) {
            int dot = name.lastIndexOf('.');
            if (dot > 0) {
                String ext = name.substring(dot);
                name = name.substring(0, 80 - ext.length()) + ext;
            } else {
                name = name.substring(0, 80);
            }
        }
        return name;
    }
}
