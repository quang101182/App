/**
 * SubWhisper — Cloudflare Worker v7.0
 *
 * Architecture:
 *   Browser ──presigned PUT──► R2 (direct, bypasses Worker)
 *   Browser ──REST──────────► Worker (orchestration only)
 *   Worker  ──fire & forget──► Fly.io /extract
 *   Fly.io  ──PATCH /job-done► Worker (callback with SRT result)
 *
 * Bindings required (wrangler.toml):
 *   env.BUCKET  — R2 bucket  "subwhisper-uploads"
 *   env.JOB_KV  — KV namespace for job state (TTL 10 min)
 *
 * Secrets (wrangler secret put):
 *   WORKER_SECRET, FLY_SECRET, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
 *
 * Vars (wrangler.toml [vars]):
 *   R2_ACCOUNT_ID, R2_BUCKET_NAME, FLY_URL
 */

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Internal-Secret',
};

const CHUNK_SIZE_BYTES  = 100 * 1024 * 1024; // 100 MB per multipart part
const KV_TTL_SECONDS    = 3600;               // 1 hour job TTL in KV
const PRESIGN_TTL_PUT   = 3600;               // 1 hour for upload presigned URL
const PRESIGN_TTL_GET   = 7200;               // 2 hours for download presigned URL

// ─────────────────────────────────────────────────────────────────────────────
// Main fetch handler
// ─────────────────────────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    const url    = new URL(request.url);
    const method = request.method.toUpperCase();
    const path   = url.pathname;

    // CORS preflight
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    try {
      // Route dispatcher — await obligatoire pour que le catch capte les erreurs async
      if (method === 'GET'   && path === '/health')                return await handleHealth();
      if (method === 'POST'  && path === '/upload-presign')        return await handleUploadPresign(request, env);
      if (method === 'POST'  && path === '/upload-complete')       return await handleUploadComplete(request, env, ctx);
      if (method === 'POST'  && path === '/process')               return await handleProcess(request, env, ctx);
      if (method === 'GET'   && path.startsWith('/job-status/'))   return await handleJobStatus(request, env, path);
      if (method === 'PATCH' && path === '/job-done')              return await handleJobDone(request, env);
      if (method === 'DELETE'&& path.startsWith('/job/'))          return await handleJobDelete(request, env, path);

      return jsonResponse({ error: 'not found' }, 404);

    } catch (err) {
      console.error('[worker] unhandled error', err);
      return jsonResponse({ error: err.message ?? 'internal server error' }, 500);
    }
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Route handlers
// ─────────────────────────────────────────────────────────────────────────────

/** GET /health */
function handleHealth() {
  return jsonResponse({ ok: true });
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * POST /upload-presign
 * Body: { filename, filesize, mimeType, multipart: boolean }
 *
 * Single-part:    returns { jobId, r2Key, presignedUrl, multipart: false }
 * Multipart:      returns { jobId, r2Key, uploadId, chunkPresignedUrls, multipart: true }
 */
async function handleUploadPresign(request, env) {
  const body = await request.json().catch(() => null);
  if (!body || !body.filename || !body.filesize) {
    return jsonResponse({ error: 'missing required fields: filename, filesize' }, 400);
  }

  const { filename, filesize, mimeType = 'application/octet-stream', multipart = false } = body;

  const jobId  = crypto.randomUUID();
  const r2Key  = `jobs/${jobId}/${sanitizeFilename(filename)}`;

  // Initial KV record
  const jobRecord = {
    status : 'pending',
    r2Key,
    jobId,
    filename,
    filesize,
    mimeType,
    ts     : Date.now(),
  };
  await kvPut(env, jobId, jobRecord, KV_TTL_SECONDS);

  const s3Config = getS3Config(env);

  if (!multipart) {
    // ── Single presigned PUT ──────────────────────────────────────────────────
    const presignedUrl = await presignPut(s3Config, r2Key, mimeType, PRESIGN_TTL_PUT);
    return jsonResponse({
      jobId,
      r2Key,
      presignedUrl,
      multipart: false,
    });
  }

  // ── Multipart upload ─────────────────────────────────────────────────────
  // Create multipart upload in R2
  const mpu = await env.BUCKET.createMultipartUpload(r2Key, {
    httpMetadata: { contentType: mimeType },
  });
  const uploadId = mpu.uploadId;

  // Calculate part count
  const partCount = Math.ceil(filesize / CHUNK_SIZE_BYTES);
  if (partCount < 1 || partCount > 10000) {
    return jsonResponse({ error: `invalid part count: ${partCount}` }, 400);
  }

  // Generate one presigned URL per part
  const chunkPresignedUrls = [];
  for (let partNumber = 1; partNumber <= partCount; partNumber++) {
    const partUrl = await presignUploadPart(s3Config, r2Key, uploadId, partNumber, PRESIGN_TTL_PUT);
    chunkPresignedUrls.push({ partNumber, url: partUrl });
  }

  // Update KV with uploadId
  await kvPut(env, jobId, { ...jobRecord, uploadId }, KV_TTL_SECONDS);

  return jsonResponse({
    jobId,
    r2Key,
    uploadId,
    chunkPresignedUrls,
    partCount,
    multipart: true,
  });
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * POST /upload-complete
 * Body: { uploadId, r2Key, jobId, parts: [{ ETag, PartNumber }] }
 *
 * Completes a multipart upload, updates KV, dispatches to Fly.io in background.
 */
async function handleUploadComplete(request, env, ctx) {
  const body = await request.json().catch(() => null);
  if (!body || !body.uploadId || !body.r2Key || !body.jobId || !Array.isArray(body.parts)) {
    return jsonResponse({ error: 'missing required fields: uploadId, r2Key, jobId, parts' }, 400);
  }

  const { uploadId, r2Key, jobId, parts, groqKey = null } = body;

  // Validate parts
  if (parts.length === 0) {
    return jsonResponse({ error: 'parts array must not be empty' }, 400);
  }
  for (const p of parts) {
    if (!p.ETag || typeof p.PartNumber !== 'number') {
      return jsonResponse({ error: 'each part must have ETag (string) and PartNumber (number)' }, 400);
    }
  }

  // Complete the multipart upload in R2
  const mpu = env.BUCKET.resumeMultipartUpload(r2Key, uploadId);
  await mpu.complete(parts.map(p => ({ partNumber: p.PartNumber, etag: p.ETag })));

  // Update KV
  const existing = await kvGet(env, jobId);
  const updated  = { ...(existing ?? {}), status: 'uploaded', jobId, r2Key, ts: Date.now() };
  await kvPut(env, jobId, updated, KV_TTL_SECONDS);

  // Fire-and-forget dispatch to Fly.io /extract
  ctx.waitUntil(dispatchToFly(env, jobId, r2Key, existing?.srcLang ?? null, groqKey, buildCallbackUrl(request.url)));

  return jsonResponse({ status: 'processing', jobId });
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * POST /process
 * Body: { jobId, r2Key, srcLang }
 *
 * Generates a presigned GET URL, updates KV, fires request to Fly.io.
 */
async function handleProcess(request, env, ctx) {
  const body = await request.json().catch(() => null);
  if (!body || !body.jobId || !body.r2Key) {
    return jsonResponse({ error: 'missing required fields: jobId, r2Key' }, 400);
  }

  const { jobId, r2Key, srcLang = null, groqKey = null } = body;

  // Verify job exists
  const existing = await kvGet(env, jobId);
  if (!existing) {
    return jsonResponse({ error: 'job not found' }, 404);
  }

  // Generate presigned GET URL for Fly.io to download the file from R2
  const s3Config         = getS3Config(env);
  const presignedDownload = await presignGet(s3Config, r2Key, PRESIGN_TTL_GET);

  // Update KV: mark as processing, store srcLang
  const updated = { ...existing, status: 'processing', srcLang, ts: Date.now() };
  await kvPut(env, jobId, updated, KV_TTL_SECONDS);

  // Worker public URL (used as callback)
  const workerCallbackUrl = buildCallbackUrl(request.url);

  // Fire-and-forget POST to Fly.io /extract
  ctx.waitUntil(
    fetch(`${env.FLY_URL}/extract`, {
      method : 'POST',
      headers: {
        'Content-Type' : 'application/json',
        'Authorization': `Bearer ${env.FLY_SECRET}`,
      },
      body: JSON.stringify({
        jobId,
        r2Key,
        presignedDownload,
        srcLang,
        workerCallbackUrl,
        workerSecret: env.WORKER_SECRET,
        groqKey,
      }),
    }).catch(err => console.error('[worker] fly dispatch error', err))
  );

  return jsonResponse({ status: 'processing', jobId });
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * GET /job-status/:jobId
 */
async function handleJobStatus(request, env, path) {
  const jobId = path.replace('/job-status/', '').split('/')[0];
  if (!jobId) return jsonResponse({ error: 'missing jobId' }, 400);

  const record = await kvGet(env, jobId);
  if (!record) return jsonResponse({ error: 'job not found' }, 404);

  return jsonResponse(record);
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * PATCH /job-done
 * Body: { jobId, srt, detectedLang, progress?, log?, error? }
 * Header: X-Internal-Secret
 *
 * Called by Fly.io when extraction/transcription is complete.
 */
async function handleJobDone(request, env) {
  // Auth
  const secret = request.headers.get('X-Internal-Secret');
  if (!secret || secret !== env.WORKER_SECRET) {
    return jsonResponse({ error: 'unauthorized' }, 401);
  }

  const body = await request.json().catch(() => null);
  if (!body || !body.jobId) {
    return jsonResponse({ error: 'missing required field: jobId' }, 400);
  }

  const { jobId, srt, detectedLang, progress, log, error: jobError } = body;

  // Fetch existing record to get r2Key
  const existing = await kvGet(env, jobId);
  if (!existing) {
    return jsonResponse({ error: 'job not found' }, 404);
  }

  const status  = jobError ? 'error' : 'done';
  const updated = {
    ...existing,
    status,
    ts    : Date.now(),
    ...(srt          != null && { srt }),
    ...(detectedLang != null && { detectedLang }),
    ...(progress     != null && { progress }),
    ...(log          != null && { log }),
    ...(jobError     != null && { error: jobError }),
  };

  // Store with same TTL (reset from now)
  await kvPut(env, jobId, updated, KV_TTL_SECONDS);

  // If successful, clean up R2 (schedule in background — no await from client POV)
  if (status === 'done' && existing.r2Key) {
    // Not using waitUntil here since we already returned — use plain .catch()
    env.BUCKET.delete(existing.r2Key).catch(err =>
      console.error('[worker] r2 delete error', existing.r2Key, err)
    );
  }

  return jsonResponse({ ok: true });
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * DELETE /job/:jobId
 */
async function handleJobDelete(request, env, path) {
  const jobId = path.replace('/job/', '').split('/')[0];
  if (!jobId) return jsonResponse({ error: 'missing jobId' }, 400);

  const record = await kvGet(env, jobId);
  if (!record) {
    // Already deleted or never existed — return success anyway
    return jsonResponse({ deleted: true });
  }

  // Delete R2 object
  if (record.r2Key) {
    await env.BUCKET.delete(record.r2Key).catch(err =>
      console.error('[worker] r2 delete error on job delete', record.r2Key, err)
    );
  }

  // Delete KV record
  await env.JOB_KV.delete(jobId);

  return jsonResponse({ deleted: true });
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper: dispatch to Fly.io (used by /upload-complete for non-process flow)
// ─────────────────────────────────────────────────────────────────────────────

async function dispatchToFly(env, jobId, r2Key, srcLang, groqKey = null, workerCallbackUrl = null) {
  try {
    const s3Config         = getS3Config(env);
    const presignedDownload = await presignGet(s3Config, r2Key, PRESIGN_TTL_GET);

    await fetch(`${env.FLY_URL}/extract`, {
      method : 'POST',
      headers: {
        'Content-Type' : 'application/json',
        'Authorization': `Bearer ${env.FLY_SECRET}`,
      },
      body: JSON.stringify({
        jobId,
        r2Key,
        presignedDownload,
        srcLang,
        workerCallbackUrl,
        workerSecret: env.WORKER_SECRET,
        groqKey,
      }),
    });
  } catch (err) {
    console.error('[worker] dispatchToFly error', err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// S3 Signature V4 — pure Web Crypto (no Node.js, no external libs)
// Compatible with Cloudflare Workers V8 isolate environment.
// ─────────────────────────────────────────────────────────────────────────────

/** Build S3 config object from env vars */
function getS3Config(env) {
  return {
    accessKeyId    : env.R2_ACCESS_KEY_ID,
    secretAccessKey: env.R2_SECRET_ACCESS_KEY,
    accountId      : env.R2_ACCOUNT_ID,
    bucketName     : env.R2_BUCKET_NAME,
    // R2 S3-compatible endpoint
    endpoint       : `https://${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    region         : 'auto',
  };
}

/** Generate a presigned PUT URL (single-part upload) */
async function presignPut(cfg, key, contentType, ttlSeconds) {
  // Content-Type envoyé comme header HTTP par le client (non signé)
  return presignS3Request(cfg, {
    method      : 'PUT',
    key,
    ttlSeconds,
    queryParams : {},
  });
}

/** Generate a presigned GET URL (download) */
async function presignGet(cfg, key, ttlSeconds) {
  return presignS3Request(cfg, {
    method    : 'GET',
    key,
    ttlSeconds,
    queryParams: {},
  });
}

/** Generate a presigned URL for a single multipart part upload */
async function presignUploadPart(cfg, key, uploadId, partNumber, ttlSeconds) {
  return presignS3Request(cfg, {
    method    : 'PUT',
    key,
    ttlSeconds,
    queryParams: {
      uploadId   : uploadId,
      partNumber : String(partNumber),
    },
  });
}

/**
 * Core S3 Signature V4 presigned URL generator.
 * Reference: https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-query-string-auth.html
 */
async function presignS3Request(cfg, { method, key, ttlSeconds, queryParams = {} }) {
  const { accessKeyId, secretAccessKey, endpoint, region, bucketName } = cfg;

  const host        = new URL(`${endpoint}/${bucketName}`).host;
  const service     = 's3';
  const now         = new Date();
  const amzDate     = formatAmzDate(now);        // YYYYMMDDTHHMMSSZ
  const dateStamp   = amzDate.slice(0, 8);       // YYYYMMDD
  const credScope   = `${dateStamp}/${region}/${service}/aws4_request`;

  // Canonical query string (must be sorted)
  const signedHeaders = 'host';
  const allQueryParams = {
    'X-Amz-Algorithm'    : 'AWS4-HMAC-SHA256',
    'X-Amz-Credential'   : `${accessKeyId}/${credScope}`,
    'X-Amz-Date'         : amzDate,
    'X-Amz-Expires'      : String(ttlSeconds),
    'X-Amz-SignedHeaders': signedHeaders,
    ...queryParams,
  };

  const canonicalQueryString = Object.keys(allQueryParams)
    .sort()
    .map(k => `${uriEncode(k)}=${uriEncode(allQueryParams[k])}`)
    .join('&');

  // Canonical URI — doit inclure /<bucket>/<key> (path-style R2)
  const canonicalUri = '/' + [bucketName, ...key.split('/')].map(segment => uriEncode(segment)).join('/');

  // Canonical headers
  const canonicalHeaders = `host:${host}\n`;

  // Canonical request
  const payloadHash      = 'UNSIGNED-PAYLOAD';
  const canonicalRequest = [
    method,
    canonicalUri,
    canonicalQueryString,
    canonicalHeaders,
    signedHeaders,
    payloadHash,
  ].join('\n');

  // String to sign
  const canonicalRequestHash = await sha256Hex(canonicalRequest);
  const stringToSign         = [
    'AWS4-HMAC-SHA256',
    amzDate,
    credScope,
    canonicalRequestHash,
  ].join('\n');

  // Signing key
  const signingKey = await deriveSigningKey(secretAccessKey, dateStamp, region, service);
  const signature  = await hmacHex(signingKey, stringToSign);

  // Final presigned URL
  const url = `${endpoint}/${bucketName}/${key.split('/').map(s => uriEncode(s)).join('/')}?${canonicalQueryString}&X-Amz-Signature=${signature}`;
  return url;
}

// ─────────────────────────────────────────────────────────────────────────────
// Crypto helpers (Web Crypto API — V8 isolate compatible)
// ─────────────────────────────────────────────────────────────────────────────

async function sha256Hex(message) {
  const msgBuffer  = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  return bufToHex(hashBuffer);
}

async function hmacRaw(keyMaterial, message) {
  let keyData;
  if (typeof keyMaterial === 'string') {
    keyData = new TextEncoder().encode(keyMaterial);
  } else {
    keyData = keyMaterial;
  }

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const msgBuffer = typeof message === 'string' ? new TextEncoder().encode(message) : message;
  return crypto.subtle.sign('HMAC', cryptoKey, msgBuffer);
}

async function hmacHex(keyMaterial, message) {
  const raw = await hmacRaw(keyMaterial, message);
  return bufToHex(raw);
}

async function deriveSigningKey(secret, dateStamp, region, service) {
  const kSecret  = new TextEncoder().encode(`AWS4${secret}`);
  const kDate    = await hmacRaw(kSecret, dateStamp);
  const kRegion  = await hmacRaw(kDate, region);
  const kService = await hmacRaw(kRegion, service);
  const kSigning = await hmacRaw(kService, 'aws4_request');
  return kSigning;
}

function bufToHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/** RFC 3986 percent-encoding (stricter than encodeURIComponent) */
function uriEncode(str) {
  return encodeURIComponent(String(str))
    .replace(/[!'()*]/g, c => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
}

function formatAmzDate(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
}

// ─────────────────────────────────────────────────────────────────────────────
// KV helpers
// ─────────────────────────────────────────────────────────────────────────────

async function kvPut(env, key, value, ttlSeconds) {
  return env.JOB_KV.put(key, JSON.stringify(value), { expirationTtl: ttlSeconds });
}

async function kvGet(env, key) {
  const raw = await env.JOB_KV.get(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Misc helpers
// ─────────────────────────────────────────────────────────────────────────────

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

/** Remove path traversal and problematic characters from filename */
function sanitizeFilename(name) {
  return name
    .replace(/\.\./g, '')
    .replace(/[^a-zA-Z0-9._\-]/g, '_')
    .slice(0, 255);
}

/**
 * Derive the Worker's own public URL from the incoming request URL.
 * Used to build the callback URL for Fly.io.
 */
function buildCallbackUrl(requestUrl) {
  const u = new URL(requestUrl);
  return `${u.protocol}//${u.host}/job-done`;
}
