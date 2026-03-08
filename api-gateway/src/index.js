/**
 * api-gateway — Cloudflare Worker v1.8
 *
 * Bindings required (wrangler.toml):
 *   env.GATEWAY_KV   — KV namespace for rate limiting, API keys, audit logs
 *
 * Secrets (wrangler secret put):
 *   WORKER_SECRET    — Bearer token for API routes
 *   ADMIN_TOKEN      — Bearer token for admin routes
 *
 * Keys stored in KV via /admin/keys/set:
 *   GEMINI_KEY, GROQ_KEY, OPENAI_KEY, DEEPL_KEY, ASSEMBLYAI_KEY
 *   DEEPSEEK_KEY, AZURE_KEY, CLAUDE_KEY, DEEPGRAM_KEY
 *
 * Config in KV:
 *   cfg:azure:region  — Azure Translator region (e.g. "francecentral")
 *
 * Routes:
 *   POST /api/gemini/*    → Google Generative Language API
 *   POST /api/groq        → Groq OpenAI-compatible API
 *   POST /api/openai      → OpenAI API
 *   POST /api/deepl       → DeepL Translation API
 *   POST /api/assemblyai  → AssemblyAI Transcription API
 *   POST /api/deepseek    → DeepSeek API
 *   POST /api/azure       → Azure Translator (query params forwarded)
 *   POST /api/claude      → Anthropic Claude API
 *   POST /api/deepgram/*  → Deepgram Nova-2 API (transcription + diarization)
 *   POST /admin/keys/list
 *   POST /admin/keys/set
 *   POST /admin/keys/delete
 *   POST /admin/keys/get
 *   POST /admin/keys/status
 *   GET  /health
 */

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const VERSION = '1.12';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin' : '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Path, X-Api-Variant, X-Azure-Region',
};

/** All recognised key names stored in KV */
const KNOWN_KEYS = ['GEMINI_KEY', 'GROQ_KEY', 'OPENAI_KEY', 'DEEPL_KEY', 'ASSEMBLYAI_KEY', 'DEEPSEEK_KEY', 'AZURE_KEY', 'CLAUDE_KEY', 'DEEPGRAM_KEY', 'AZURE_REGION', 'WORKER_URL', 'DIAG_FOLDER_ID', 'MCP_DRIVE_URL', 'YOUTUBE_KEYS'];

/** Rate limit: max requests per minute window */
const RL_API_MAX   = 20;
const RL_ADMIN_MAX = 10;
const RL_TTL_SEC   = 70; // KV TTL for rate-limit counters (slightly longer than 60s window)

/** Audit log TTL: 30 days in seconds */
const AUDIT_TTL_SEC = 30 * 24 * 3600;

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
      // ── Health (no auth) ──────────────────────────────────────────────────
      if (method === 'GET' && path === '/health') {
        return handleHealth();
      }

      // ── Config (auth: WORKER_SECRET) ──────────────────────────────────────
      if (method === 'GET' && path === '/config') {
        const authErr = await checkBearer(request, env.WORKER_SECRET, 'WORKER_SECRET');
        if (authErr) return authErr;
        return await handleConfig(env);
      }

      // ── API routes ────────────────────────────────────────────────────────
      if (method === 'POST' && path.startsWith('/api/')) {
        // Auth check (async — constant-time comparison)
        const authErr = await checkBearer(request, env.WORKER_SECRET, 'WORKER_SECRET');
        if (authErr) return authErr;

        // Rate limit (fire-and-forget counter update)
        const ip = request.headers.get('CF-Connecting-IP') ?? 'unknown';
        const rlErr = await checkRateLimit(env, ctx, 'api', ip, RL_API_MAX);
        if (rlErr) return rlErr;

        // Dispatch to the right upstream
        if (path.startsWith('/api/gemini'))   return await proxyGemini(request, env, path);
        if (path === '/api/groq')             return await proxyGroq(request, env);
        if (path === '/api/openai')           return await proxyOpenai(request, env);
        if (path === '/api/deepl')            return await proxyDeepl(request, env);
        if (path === '/api/assemblyai')       return await proxyAssemblyai(request, env);
        if (path === '/api/deepseek')         return await proxyDeepSeek(request, env);
        if (path === '/api/azure')            return await proxyAzure(request, env, url);
        if (path.startsWith('/api/claude'))   return await proxyClaude(request, env, path);
        if (path.startsWith('/api/deepgram')) return await proxyDeepgram(request, env, path);
        if (path === '/api/youtube-search')  return await proxyYoutubeSearch(request, env);

        return jsonResponse({ error: 'unknown api route' }, 404);
      }

      // ── Admin routes ──────────────────────────────────────────────────────
      if (method === 'POST' && path.startsWith('/admin/')) {
        const authErr = await checkBearer(request, env.ADMIN_TOKEN, 'ADMIN_TOKEN');
        if (authErr) return authErr;

        const ip = request.headers.get('CF-Connecting-IP') ?? 'unknown';
        const rlErr = await checkRateLimit(env, ctx, 'adm', ip, RL_ADMIN_MAX);
        if (rlErr) return rlErr;

        if (path === '/admin/keys/list')   return await adminKeysList(env);
        if (path === '/admin/keys/set')    return await adminKeysSet(request, env, ctx, ip);
        if (path === '/admin/keys/delete') return await adminKeysDelete(request, env, ctx, ip);
        if (path === '/admin/keys/get')    return await adminKeysGet(request, env);
        if (path === '/admin/keys/status') return await adminKeysStatus(env);

        return jsonResponse({ error: 'unknown admin route' }, 404);
      }

      // ── Web Proxy route (GET/POST) ─────────────────────────────────────
      if ((method === 'GET' || method === 'POST') && path === '/proxy') {
        return await handleProxy(request, env, ctx, url);
      }

      return jsonResponse({ error: 'not found' }, 404);

    } catch (err) {
      console.error('[gateway] unhandled error', err);
      return jsonResponse({ error: 'internal server error' }, 500);
    }
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// GET /health
// ─────────────────────────────────────────────────────────────────────────────

function handleHealth() {
  return jsonResponse({ ok: true, version: VERSION, ts: Date.now() });
}

// ─────────────────────────────────────────────────────────────────────────────
// GET /config — returns public config for connected apps
// ─────────────────────────────────────────────────────────────────────────────

async function handleConfig(env) {
  const workerUrl = await resolveKey(env, 'WORKER_URL') || '';

  // List which API keys are configured (name only, no values)
  const apiKeys = KNOWN_KEYS.filter(k => k.endsWith('_KEY'));
  const apis = [];
  for (const key of apiKeys) {
    const val = await kvGetKey(env, key);
    if (val) apis.push(key.replace('_KEY', ''));
  }

  const diagFolder = await kvGetKey(env, 'DIAG_FOLDER_ID') || '';
  const mcpDriveUrl = await kvGetKey(env, 'MCP_DRIVE_URL') || '';

  // YouTube server keys count (for client display)
  const ytKeysRaw = await kvGetKey(env, 'YOUTUBE_KEYS');
  const ytKeysCount = ytKeysRaw ? ytKeysRaw.split(',').filter(k => k.trim()).length : 0;

  // YouTube daily usage counter
  const today = new Date().toISOString().slice(0, 10);
  const ytUsedRaw = await env.GATEWAY_KV.get(`ytusage:${today}`);
  const ytUsed = parseInt(ytUsedRaw || '0', 10);

  // YouTube quota health check — videos.list costs 1 unit (vs 100 for search.list)
  let ytQuotaOk = null;
  if (ytKeysRaw) {
    const testKeys = ytKeysRaw.split(',').map(k => k.trim()).filter(Boolean);
    // Test 2 keys from different positions (likely different projects)
    const toTest = [testKeys[0], testKeys[Math.floor(testKeys.length / 2)]].filter(Boolean);
    ytQuotaOk = false;
    for (const tk of toTest) {
      try {
        const r = await fetch(`https://www.googleapis.com/youtube/v3/videos?part=id&id=dQw4w9WgXcQ&key=${encodeURIComponent(tk)}`);
        if (r.ok) { ytQuotaOk = true; break; }
      } catch (_) {}
    }
  }

  return jsonResponse({ worker_url: workerUrl, apis, version: VERSION, diag_folder: diagFolder, mcp_drive_url: mcpDriveUrl, yt_server_keys: ytKeysCount, yt_server_used: ytUsed, yt_quota_ok: ytQuotaOk });
}

// ─────────────────────────────────────────────────────────────────────────────
// API proxy handlers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * POST /api/gemini/* → https://generativelanguage.googleapis.com
 *
 * Sub-path is extracted after /api/gemini.
 * Default path: /v1beta/models/gemini-pro:generateContent
 * Auth: ?key=GEMINI_KEY appended to upstream URL.
 */
async function proxyGemini(request, env, path) {
  const apiKey = await resolveKey(env, 'GEMINI_KEY');
  if (!apiKey) return jsonResponse({ error: 'GEMINI_KEY not configured' }, 503);

  // Extract the sub-path after /api/gemini (may be empty or e.g. /v1beta/models/gemini-2.0-flash:generateContent)
  let subPath = path.slice('/api/gemini'.length) || '/v1beta/models/gemini-1.5-flash:generateContent';
  if (!subPath.startsWith('/')) subPath = '/' + subPath;

  const upstream = `https://generativelanguage.googleapis.com${subPath}?key=${apiKey}`;
  return proxyRequest(request, upstream, {});
}

/**
 * POST /api/deepseek → https://api.deepseek.com/v1/chat/completions
 *
 * Header X-Api-Path overrides.
 * Auth: Bearer DEEPSEEK_KEY.
 */
async function proxyDeepSeek(request, env) {
  const apiKey = await resolveKey(env, 'DEEPSEEK_KEY');
  if (!apiKey) return jsonResponse({ error: 'DEEPSEEK_KEY not configured' }, 503);

  const apiPath  = safeApiPath(request, '/v1/chat/completions');
  const upstream = `https://api.deepseek.com${apiPath}`;
  return proxyRequest(request, upstream, { 'Authorization': `Bearer ${apiKey}` });
}

/**
 * POST /api/claude/* → https://api.anthropic.com
 *
 * Sub-path: /api/claude → /v1/messages (default)
 * Auth: x-api-key header (Anthropic format) + anthropic-version.
 * Header X-Api-Path overrides the upstream path.
 */
async function proxyClaude(request, env, path) {
  const apiKey = await resolveKey(env, 'CLAUDE_KEY');
  if (!apiKey) return jsonResponse({ error: 'CLAUDE_KEY not configured' }, 503);

  let subPath = path.slice('/api/claude'.length) || '/v1/messages';
  if (!subPath.startsWith('/')) subPath = '/' + subPath;

  const upstream = `https://api.anthropic.com${subPath}`;

  // Anthropic uses x-api-key + anthropic-version (not Bearer)
  const body = await request.arrayBuffer();
  const forwardHeaders = new Headers();
  const contentType = request.headers.get('Content-Type');
  if (contentType) forwardHeaders.set('Content-Type', contentType);
  forwardHeaders.set('x-api-key', apiKey);
  forwardHeaders.set('anthropic-version', request.headers.get('anthropic-version') || '2023-06-01');

  const upstreamResp = await fetch(upstream, {
    method : request.method,
    headers: forwardHeaders,
    body   : body.byteLength > 0 ? body : undefined,
  });

  const respHeaders = new Headers();
  for (const h of ['content-type', 'content-length']) {
    const val = upstreamResp.headers.get(h);
    if (val) respHeaders.set(h, val);
  }
  for (const [k, v] of Object.entries(CORS_HEADERS)) respHeaders.set(k, v);

  return new Response(upstreamResp.body, { status: upstreamResp.status, headers: respHeaders });
}

/**
 * POST /api/azure → https://api.cognitive.microsofttranslator.com/translate
 *
 * Query params (api-version, to, from) are forwarded as-is.
 * Region: from X-Azure-Region header, or KV key cfg:azure:region.
 * Auth: Ocp-Apim-Subscription-Key + Ocp-Apim-Subscription-Region.
 */
async function proxyAzure(request, env, parsedUrl) {
  const apiKey = await resolveKey(env, 'AZURE_KEY');
  if (!apiKey) return jsonResponse({ error: 'AZURE_KEY not configured' }, 503);

  const upstream = `https://api.cognitive.microsofttranslator.com/translate${parsedUrl.search}`;

  const region = request.headers.get('X-Azure-Region')
    || await resolveKey(env, 'AZURE_REGION')
    || '';

  const authHeaders = { 'Ocp-Apim-Subscription-Key': apiKey };
  if (region) authHeaders['Ocp-Apim-Subscription-Region'] = region;

  return proxyRequest(request, upstream, authHeaders);
}

/**
 * Validate X-Api-Path header: must start with '/' and not contain '..'.
 * Returns the validated path or the default.
 */
function safeApiPath(request, defaultPath) {
  const p = request.headers.get('X-Api-Path');
  if (!p) return defaultPath;
  if (!p.startsWith('/') || p.includes('..')) return defaultPath;
  return p;
}

/**
 * POST /api/groq → https://api.groq.com/openai/v1/chat/completions
 *
 * Header X-Api-Path overrides the upstream path.
 * Auth: Bearer GROQ_KEY.
 */
async function proxyGroq(request, env) {
  const apiKey = await resolveKey(env, 'GROQ_KEY');
  if (!apiKey) return jsonResponse({ error: 'GROQ_KEY not configured' }, 503);

  const apiPath  = safeApiPath(request, '/openai/v1/chat/completions');
  const upstream = `https://api.groq.com${apiPath}`;
  return proxyRequest(request, upstream, { 'Authorization': `Bearer ${apiKey}` });
}

/**
 * POST /api/openai → https://api.openai.com/v1/chat/completions
 *
 * Header X-Api-Path overrides.
 * Auth: Bearer OPENAI_KEY.
 */
async function proxyOpenai(request, env) {
  const apiKey = await resolveKey(env, 'OPENAI_KEY');
  if (!apiKey) return jsonResponse({ error: 'OPENAI_KEY not configured' }, 503);

  const apiPath  = safeApiPath(request, '/v1/chat/completions');
  const upstream = `https://api.openai.com${apiPath}`;
  return proxyRequest(request, upstream, { 'Authorization': `Bearer ${apiKey}` });
}

/**
 * POST /api/deepl → https://api-free.deepl.com/v2/translate
 *
 * Header X-Api-Variant: pro → uses api.deepl.com instead of api-free.deepl.com.
 * Header X-Api-Path overrides the upstream path.
 * Auth: DeepL-Auth-Key DEEPL_KEY.
 */
async function proxyDeepl(request, env) {
  const apiKey = await resolveKey(env, 'DEEPL_KEY');
  if (!apiKey) return jsonResponse({ error: 'DEEPL_KEY not configured' }, 503);

  const variant  = request.headers.get('X-Api-Variant');
  const baseHost = variant === 'pro' ? 'api.deepl.com' : 'api-free.deepl.com';
  const apiPath  = safeApiPath(request, '/v2/translate');
  const upstream = `https://${baseHost}${apiPath}`;
  return proxyRequest(request, upstream, { 'DeepL-Auth-Key': apiKey });
}

/**
 * POST /api/assemblyai → https://api.assemblyai.com/v2/transcript
 *
 * Header X-Api-Path overrides.
 * Auth: Authorization header without "Bearer" prefix.
 */
async function proxyAssemblyai(request, env) {
  const apiKey = await resolveKey(env, 'ASSEMBLYAI_KEY');
  if (!apiKey) return jsonResponse({ error: 'ASSEMBLYAI_KEY not configured' }, 503);

  const apiPath  = safeApiPath(request, '/v2/transcript');
  const upstream = `https://api.assemblyai.com${apiPath}`;
  return proxyRequest(request, upstream, { 'Authorization': apiKey });
}

/**
 * POST /api/deepgram/* → https://api.deepgram.com
 *
 * Sub-path: /api/deepgram → /v1/listen (default)
 * Auth: Token DEEPGRAM_KEY.
 * STREAMS the request body directly (no buffering) to handle large files (>100MB).
 */
async function proxyDeepgram(request, env, path) {
  const apiKey = await resolveKey(env, 'DEEPGRAM_KEY');
  if (!apiKey) return jsonResponse({ error: 'DEEPGRAM_KEY not configured' }, 503);

  let subPath = path.slice('/api/deepgram'.length) || '/v1/listen';
  if (!subPath.startsWith('/')) subPath = '/' + subPath;

  const url = new URL(request.url);
  const qs = url.search || '';
  const upstream = `https://api.deepgram.com${subPath}${qs}`;

  const forwardHeaders = new Headers();
  const contentType = request.headers.get('Content-Type');
  if (contentType) forwardHeaders.set('Content-Type', contentType);
  forwardHeaders.set('Authorization', `Token ${apiKey}`);
  // Forward content-length for progress tracking
  const contentLength = request.headers.get('Content-Length');
  if (contentLength) forwardHeaders.set('Content-Length', contentLength);

  // Stream body directly — no arrayBuffer() buffering — handles large files
  const upstreamResp = await fetch(upstream, {
    method : request.method,
    headers: forwardHeaders,
    body   : request.body,
  });

  const respHeaders = new Headers();
  for (const h of ['content-type', 'content-length']) {
    const val = upstreamResp.headers.get(h);
    if (val) respHeaders.set(h, val);
  }
  for (const [k, v] of Object.entries(CORS_HEADERS)) respHeaders.set(k, v);

  return new Response(upstreamResp.body, { status: upstreamResp.status, headers: respHeaders });
}

// ─────────────────────────────────────────────────────────────────────────────
// Web Proxy — GET/POST /proxy?url=...&s=WORKER_SECRET[&raw=1]
// ─────────────────────────────────────────────────────────────────────────────

/** Video sniffer script injected into proxied HTML pages */
const SNIFFER_SCRIPT = `<script>(function(){
var D=new Set(),V=/\\.(mp4|webm|m3u8|mov|mkv|flv|avi|ts|mpd)(\\?[^"'\\s<>]*)?/i;
var M=/video\\//i;
function R(u,t){if(!u||u.length<8||D.has(u))return;D.add(u);try{parent.postMessage({t:'vg-video',url:u,mt:t},'*')}catch(e){}}
function S(){document.querySelectorAll('video,audio,source,[src],[data-src],[data-video-src]').forEach(function(e){
var s=e.src||e.currentSrc||(e.dataset&&(e.dataset.src||e.dataset.videoSrc))||e.getAttribute('src')||'';
if(s&&(V.test(s)||M.test(e.type||'')))R(s,'dom');
if(e.tagName==='VIDEO'){if(e.currentSrc)R(e.currentSrc,'cur');
try{for(var i=0;i<e.children.length;i++){var c=e.children[i];if(c.src)R(c.src,'src')}}catch(x){}}
});
document.querySelectorAll('a[href]').forEach(function(a){if(V.test(a.href))R(a.href,'link')});
document.querySelectorAll('[style]').forEach(function(e){var m=e.getAttribute('style').match(/url\\(["']?([^"')]+\\.mp4[^"')]*)/i);if(m)R(m[1],'css')});
try{document.querySelectorAll('script:not([src])').forEach(function(s){
var t=s.textContent||'';var re=/["'](https?:\\/\\/[^"'\\s]+\\.(?:mp4|m3u8|webm)(?:\\?[^"'\\s]*)?)["']/gi;var m;
while((m=re.exec(t))!==null)R(m[1],'js')})}catch(x){}}
var XO=XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open=function(m,u){if(typeof u==='string'){if(V.test(u))R(u,'xhr');if(u.indexOf('.m3u8')>-1||u.indexOf('.mpd')>-1||u.indexOf('/manifest')>-1)R(u,'manifest')}return XO.apply(this,arguments)};
var FO=window.fetch;window.fetch=function(i,o){var u=typeof i==='string'?i:(i&&i.url)||'';if(V.test(u))R(u,'fetch');if(u.indexOf('.m3u8')>-1||u.indexOf('.mpd')>-1)R(u,'manifest');return FO.apply(this,arguments)};
var CE=document.createElement;document.createElement=function(t){var el=CE.apply(this,arguments);if(t==='video'||t==='source'){var origSet=Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype,'src')||Object.getOwnPropertyDescriptor(Element.prototype,'src');
if(origSet&&origSet.set){var oSet=origSet.set;Object.defineProperty(el,'src',{set:function(v){if(V.test(v))R(v,'create');return oSet.call(this,v)},get:origSet.get,configurable:true})}}return el};
try{var params=new URLSearchParams(location.search);var pu=params.get('url');if(pu)parent.postMessage({t:'vg-nav',url:pu},'*')}catch(x){}
var obs=new MutationObserver(S);obs.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['src','data-src']});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',S);else S();
setInterval(S,2500);
})();</scrip`+`t>`;

async function handleProxy(request, env, ctx, parsedUrl) {
  // Auth via query param 's'
  const secret = parsedUrl.searchParams.get('s') || '';
  if (!env.WORKER_SECRET || !(await timingSafeEqual(secret, env.WORKER_SECRET))) {
    return new Response('Unauthorized', { status: 401, headers: CORS_HEADERS });
  }

  const targetUrl = parsedUrl.searchParams.get('url');
  if (!targetUrl) return jsonResponse({ error: 'missing url parameter' }, 400);

  // Validate URL
  let target;
  try { target = new URL(targetUrl); } catch { return jsonResponse({ error: 'invalid url' }, 400); }

  // Block obvious dangerous schemes
  if (!['http:', 'https:'].includes(target.protocol)) {
    return jsonResponse({ error: 'only http/https allowed' }, 400);
  }

  // Rate limit: 120 req/min for proxy (generous for browsing)
  const ip = request.headers.get('CF-Connecting-IP') ?? 'unknown';
  const rlErr = await checkRateLimit(env, ctx, 'prx', ip, 120);
  if (rlErr) return rlErr;

  const isRaw = parsedUrl.searchParams.has('raw');

  // Build fetch headers — mobile User-Agent
  const fetchHeaders = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Accept': isRaw ? '*/*' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip',
    'Referer': target.origin + '/',
  };

  // Forward Range header (video seeking)
  const range = request.headers.get('Range');
  if (range) fetchHeaders['Range'] = range;

  // Forward cookies if provided
  const cookie = request.headers.get('X-Proxy-Cookie');
  if (cookie) fetchHeaders['Cookie'] = cookie;

  // For POST requests, forward the body
  let fetchBody = undefined;
  if (request.method === 'POST') {
    fetchBody = request.body;
    const ct = request.headers.get('Content-Type');
    if (ct) fetchHeaders['Content-Type'] = ct;
  }

  let resp;
  try {
    resp = await fetch(targetUrl, {
      method: request.method,
      headers: fetchHeaders,
      body: fetchBody,
      redirect: 'follow',
    });
  } catch (err) {
    return jsonResponse({ error: 'fetch failed: ' + err.message }, 502);
  }

  const contentType = resp.headers.get('content-type') || '';

  // ── Raw mode or non-HTML → stream directly ──
  if (isRaw || !contentType.includes('text/html')) {
    const headers = new Headers();
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    headers.set('Access-Control-Allow-Headers', 'Range, X-Proxy-Cookie');
    headers.set('Access-Control-Expose-Headers', 'Content-Range, Content-Length, Accept-Ranges, Content-Disposition');
    if (contentType) headers.set('Content-Type', contentType);
    for (const h of ['content-length', 'accept-ranges', 'content-range', 'content-disposition', 'last-modified', 'etag']) {
      const v = resp.headers.get(h);
      if (v) headers.set(h, v);
    }
    return new Response(resp.body, { status: resp.status, headers });
  }

  // ── HTML mode → rewrite for iframe navigation ──
  let html = await resp.text();
  const finalUrl = resp.url || targetUrl;
  const base = new URL(finalUrl);
  const basePath = base.origin + base.pathname.replace(/[^/]*$/, '');
  const proxyPrefix = `/proxy?s=${encodeURIComponent(secret)}&url=`;

  // Remove existing <base> tags
  html = html.replace(/<base\s[^>]*>/gi, '');

  // Insert <base> tag for resource resolution (images, css, js load directly from origin)
  if (/<head/i.test(html)) {
    html = html.replace(/<head([^>]*)>/i, `<head$1><base href="${basePath}" target="_self">`);
  } else {
    html = `<base href="${basePath}" target="_self">` + html;
  }

  // Rewrite <a href> and <area href> for navigation within proxy
  html = html.replace(/(<(?:a|area)\s[^>]*href\s*=\s*["'])([^"']*)(["'])/gi, (m, pre, href, post) => {
    if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('data:') || href.startsWith('mailto:') || href.startsWith('tel:')) return m;
    try {
      const abs = new URL(href, finalUrl).href;
      return `${pre}${proxyPrefix}${encodeURIComponent(abs)}${post}`;
    } catch { return m; }
  });

  // Rewrite <form action>
  html = html.replace(/(<form\s[^>]*action\s*=\s*["'])([^"']*)(["'])/gi, (m, pre, action, post) => {
    if (!action || action.startsWith('javascript:')) return m;
    try {
      const abs = new URL(action || finalUrl, finalUrl).href;
      return `${pre}${proxyPrefix}${encodeURIComponent(abs)}${post}`;
    } catch { return m; }
  });

  // Rewrite <iframe src> so nested iframes also go through proxy
  html = html.replace(/(<iframe\s[^>]*src\s*=\s*["'])([^"']*)(["'])/gi, (m, pre, src, post) => {
    if (!src || src.startsWith('about:') || src.startsWith('javascript:') || src.startsWith('data:')) return m;
    try {
      const abs = new URL(src, finalUrl).href;
      return `${pre}${proxyPrefix}${encodeURIComponent(abs)}${post}`;
    } catch { return m; }
  });

  // Remove CSP meta tags
  html = html.replace(/<meta\s[^>]*http-equiv\s*=\s*["']Content-Security-Policy["'][^>]*>/gi, '');

  // Inject sniffer script before </body> (or at end)
  if (/<\/body>/i.test(html)) {
    html = html.replace(/<\/body>/i, SNIFFER_SCRIPT + '</body>');
  } else {
    html += SNIFFER_SCRIPT;
  }

  // Return clean HTML — NO X-Frame-Options, NO CSP
  return new Response(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-store',
    },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Core proxy helper
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Forward the incoming request body (as-is) to `upstreamUrl`.
 * Injects `authHeaders` into the upstream request.
 * Strips the client-side Authorization and X-Api-* headers from the forwarded request.
 * Returns the upstream response with CORS headers appended.
 */
// ─────────────────────────────────────────────────────────────────────────────
// POST /api/youtube-search — YouTube Data API v3 with multi-key rotation + KV cache
// Body: { q: "search query" }
// Returns: { videoId, title, cached } or { error }
// ─────────────────────────────────────────────────────────────────────────────

const YT_CACHE_TTL = 7 * 24 * 3600; // 7 days

async function proxyYoutubeSearch(request, env) {
  let body;
  try { body = await request.json(); } catch { return jsonResponse({ error: 'invalid JSON body' }, 400); }
  const query = (body.q || '').trim();
  if (!query) return jsonResponse({ error: 'missing q parameter' }, 400);

  // 1. Check KV cache first (before counting — cached = free)
  const cacheKey = `ytcache:${query.toLowerCase().replace(/\s+/g, ' ')}`;
  const cached = await env.GATEWAY_KV.get(cacheKey);
  if (cached) {
    try {
      const data = JSON.parse(cached);
      return jsonResponse({ videoId: data.videoId, title: data.title || '', cached: true });
    } catch { /* cache corrupted, continue to search */ }
  }

  // 0. Increment daily usage counter (only for real API calls, not cached)
  const today = new Date().toISOString().slice(0, 10);
  const usageKey = `ytusage:${today}`;
  env.GATEWAY_KV.get(usageKey).then(raw => {
    const count = parseInt(raw || '0', 10) + 1;
    env.GATEWAY_KV.put(usageKey, String(count), { expirationTtl: 172800 }).catch(() => {});
  }).catch(() => {});

  // 2. Load YOUTUBE_KEYS from KV (comma-separated string)
  const keysRaw = await resolveKey(env, 'YOUTUBE_KEYS');
  if (!keysRaw) return jsonResponse({ error: 'YOUTUBE_KEYS not configured' }, 503);
  const keys = keysRaw.split(',').map(k => k.trim()).filter(Boolean);
  if (!keys.length) return jsonResponse({ error: 'YOUTUBE_KEYS is empty' }, 503);

  // 3. Try each key with rotation — shuffle to spread load across projects
  const shuffled = keys.slice().sort(() => Math.random() - 0.5);
  let lastError = null;
  let quotaHits = 0;
  for (const apiKey of shuffled) {
    // After 3 consecutive 403s, all projects are likely exhausted — stop wasting API calls
    if (quotaHits >= 3) break;
    try {
      // Search top 8 results (more candidates for duration filter)
      const ytUrl = `https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=8&q=${encodeURIComponent(query)}&key=${encodeURIComponent(apiKey)}`;
      const resp = await fetch(ytUrl);
      if (resp.status === 403) {
        lastError = 'quota exceeded';
        quotaHits++;
        continue;
      }
      if (!resp.ok) {
        lastError = `YouTube API error ${resp.status}`;
        continue;
      }
      const data = await resp.json();
      const items = data.items || [];
      if (!items.length) return jsonResponse({ videoId: null, title: null, cached: false });

      const ids = items.map(i => i.id?.videoId).filter(Boolean);
      // Duration filter: 90s–300s (same as client-side ytSearchLocal)
      let bestId = ids[0], bestTitle = items[0].snippet?.title || '';
      if (ids.length > 0) {
        try {
          const vUrl = `https://www.googleapis.com/youtube/v3/videos?part=contentDetails,snippet&id=${ids.join(',')}&key=${encodeURIComponent(apiKey)}`;
          const vResp = await fetch(vUrl);
          if (vResp.ok) {
            const vData = await vResp.json();
            // Sort: prefer audio/lyric/topic, deprioritize music video/MV (fewer ads)
            const sorted = (vData.items || []).sort((a, b) => {
              const tA = (a.snippet?.title || '').toLowerCase();
              const tB = (b.snippet?.title || '').toLowerCase();
              const scoreA = (tA.includes('audio') || tA.includes('lyric') || tA.includes('topic') ? 2 : 0)
                           - (tA.includes('music video') || tA.includes('official video') || / mv[\s\]|\)]/i.test(tA) ? 2 : 0);
              const scoreB = (tB.includes('audio') || tB.includes('lyric') || tB.includes('topic') ? 2 : 0)
                           - (tB.includes('music video') || tB.includes('official video') || / mv[\s\]|\)]/i.test(tB) ? 2 : 0);
              return scoreB - scoreA;
            });
            const valid = sorted.find(v => {
              const dur = v.contentDetails?.duration || '';
              const m = dur.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
              if (!m) return false;
              const secs = (parseInt(m[1]||0)*3600) + (parseInt(m[2]||0)*60) + parseInt(m[3]||0);
              return secs >= 90 && secs <= 300;
            });
            if (valid) { bestId = valid.id; bestTitle = valid.snippet?.title || bestTitle; }
            else if (sorted.length) { bestId = sorted[0].id; bestTitle = sorted[0].snippet?.title || bestTitle; }
          }
        } catch (_) { /* duration check failed, use first result */ }
      }

      // 4. Cache result in KV (fire-and-forget)
      if (bestId) {
        env.GATEWAY_KV.put(cacheKey, JSON.stringify({ videoId: bestId, title: bestTitle }), { expirationTtl: YT_CACHE_TTL }).catch(() => {});
      }

      return jsonResponse({ videoId: bestId, title: bestTitle, cached: false });
    } catch (err) {
      lastError = err.message;
      continue;
    }
  }

  // All keys exhausted
  return jsonResponse({ error: 'all YouTube keys exhausted', detail: lastError }, 429);
}

async function proxyRequest(request, upstreamUrl, authHeaders) {
  // Read body as raw bytes to forward regardless of content-type
  const body = await request.arrayBuffer();

  // Build clean headers for upstream (forward Content-Type, strip client auth/meta)
  const forwardHeaders = new Headers();
  const contentType = request.headers.get('Content-Type');
  if (contentType) forwardHeaders.set('Content-Type', contentType);

  // Inject upstream auth headers
  for (const [k, v] of Object.entries(authHeaders)) {
    forwardHeaders.set(k, v);
  }

  const upstreamResp = await fetch(upstreamUrl, {
    method : request.method,
    headers: forwardHeaders,
    body   : body.byteLength > 0 ? body : undefined,
  });

  // Build response — whitelist safe headers only, append CORS
  const respHeaders = new Headers();
  for (const h of ['content-type', 'content-length']) {
    const val = upstreamResp.headers.get(h);
    if (val) respHeaders.set(h, val);
  }
  for (const [k, v] of Object.entries(CORS_HEADERS)) {
    respHeaders.set(k, v);
  }

  return new Response(upstreamResp.body, {
    status : upstreamResp.status,
    headers: respHeaders,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Admin route handlers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * POST /admin/keys/list
 * Returns each known key as "set (N chars)" or "not set".
 */
async function adminKeysList(env) {
  const result = {};
  // KNOWN_KEYS toujours présents (avec statut)
  for (const name of KNOWN_KEYS) {
    const val = await kvGetKey(env, name);
    result[name] = val ? val : 'not set';
  }
  // Clés custom (ex: *_SHARE) via KV.list
  const listed = await env.GATEWAY_KV.list({ prefix: 'key:' });
  for (const item of listed.keys) {
    const name = item.name.replace(/^key:/, '');
    if (!KNOWN_KEYS.includes(name)) {
      const val = await kvGetKey(env, name);
      result[name] = val ? val : 'not set';
    }
  }
  return jsonResponse(result);
}

/**
 * POST /admin/keys/set
 * Body: { key: "GEMINI_KEY", value: "AIza..." }
 */
async function adminKeysSet(request, env, ctx, ip) {
  const body = await request.json().catch(() => null);
  if (!body || !body.key || !body.value) {
    return jsonResponse({ error: 'missing required fields: key, value' }, 400);
  }
  if (!/^[A-Z][A-Z0-9_]{1,63}$/.test(body.key)) {
    return jsonResponse({ error: `invalid key name "${body.key}". Use uppercase letters, digits, underscores.` }, 400);
  }

  await kvSetKey(env, body.key, body.value);

  // Async audit log
  ctx.waitUntil(writeAuditLog(env, { action: 'set', key_name: body.key, ip }));

  return jsonResponse({ ok: true, key: body.key });
}

/**
 * POST /admin/keys/delete
 * Body: { key: "GEMINI_KEY" }
 */
async function adminKeysDelete(request, env, ctx, ip) {
  const body = await request.json().catch(() => null);
  if (!body || !body.key) {
    return jsonResponse({ error: 'missing required field: key' }, 400);
  }
  if (!/^[A-Z][A-Z0-9_]{1,63}$/.test(body.key)) {
    return jsonResponse({ error: `invalid key name "${body.key}". Use uppercase letters, digits, underscores.` }, 400);
  }

  await kvDeleteKey(env, body.key);

  ctx.waitUntil(writeAuditLog(env, { action: 'delete', key_name: body.key, ip }));

  return jsonResponse({ ok: true, key: body.key });
}

/**
 * POST /admin/keys/get
 * Body: { key: "GEMINI_KEY" }
 * Returns the raw value stored in KV for the given key name.
 */
async function adminKeysGet(request, env) {
  const body = await request.json().catch(() => null);
  if (!body || !body.key) {
    return jsonResponse({ error: 'missing required field: key' }, 400);
  }
  if (!/^[A-Z][A-Z0-9_]{1,63}$/.test(body.key)) {
    return jsonResponse({ error: `invalid key name "${body.key}". Use uppercase letters, digits, underscores.` }, 400);
  }

  const value = await kvGetKey(env, body.key);
  if (value === null) {
    return jsonResponse({ ok: false, error: 'not found' }, 404);
  }
  return jsonResponse({ ok: true, key: body.key, value });
}

/**
 * POST /admin/keys/status
 * Pings each configured upstream API with a minimal authenticated request.
 * Returns { statuses: { GEMINI_KEY: { ok, status }, ... } }
 */
async function adminKeysStatus(env) {
  const checks = {
    GEMINI_KEY    : pingGemini,
    GROQ_KEY      : pingGroq,
    OPENAI_KEY    : pingOpenai,
    DEEPL_KEY     : pingDeepl,
    ASSEMBLYAI_KEY: pingAssemblyai,
    DEEPSEEK_KEY  : pingDeepSeek,
    AZURE_KEY     : pingAzure,
    CLAUDE_KEY    : pingClaude,
    DEEPGRAM_KEY  : pingDeepgram,
    // AZURE_REGION, WORKER_URL are config values — skip ping
  };

  const statuses = {};

  await Promise.all(
    KNOWN_KEYS.map(async (name) => {
      const apiKey = await resolveKey(env, name);
      if (!apiKey) {
        statuses[name] = { ok: false, status: 'not configured' };
        return;
      }
      try {
        const result = await checks[name](apiKey);
        statuses[name] = result;
      } catch (err) {
        statuses[name] = { ok: false, status: `error: ${err.message}` };
      }
    })
  );

  return jsonResponse({ statuses });
}

// ─────────────────────────────────────────────────────────────────────────────
// Ping helpers (minimal API health checks)
// ─────────────────────────────────────────────────────────────────────────────

async function pingGemini(apiKey) {
  const resp = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`,
    { method: 'GET' }
  );
  return { ok: resp.ok, status: resp.status };
}

async function pingGroq(apiKey) {
  const resp = await fetch('https://api.groq.com/openai/v1/models', {
    method : 'GET',
    headers: { 'Authorization': `Bearer ${apiKey}` },
  });
  return { ok: resp.ok, status: resp.status };
}

async function pingOpenai(apiKey) {
  const resp = await fetch('https://api.openai.com/v1/models', {
    method : 'GET',
    headers: { 'Authorization': `Bearer ${apiKey}` },
  });
  return { ok: resp.ok, status: resp.status };
}

async function pingDeepl(apiKey) {
  // Try free tier first; detect pro vs free by attempting both if needed
  // The variant is unknown at this level so we try free-tier endpoint
  const resp = await fetch('https://api-free.deepl.com/v2/usage', {
    method : 'GET',
    headers: { 'DeepL-Auth-Key': apiKey },
  });
  // A 403 on free tier with a pro key is common — try pro variant
  if (resp.status === 403) {
    const respPro = await fetch('https://api.deepl.com/v2/usage', {
      method : 'GET',
      headers: { 'DeepL-Auth-Key': apiKey },
    });
    return { ok: respPro.ok, status: respPro.status, variant: 'pro' };
  }
  return { ok: resp.ok, status: resp.status, variant: 'free' };
}

async function pingDeepSeek(apiKey) {
  const resp = await fetch('https://api.deepseek.com/v1/models', {
    method : 'GET',
    headers: { 'Authorization': `Bearer ${apiKey}` },
  });
  return { ok: resp.ok, status: resp.status };
}

async function pingAzure(apiKey) {
  const resp = await fetch('https://api.cognitive.microsofttranslator.com/languages?api-version=3.0', {
    method : 'GET',
    headers: { 'Ocp-Apim-Subscription-Key': apiKey },
  });
  return { ok: resp.ok, status: resp.status };
}

async function pingAssemblyai(apiKey) {
  const resp = await fetch('https://api.assemblyai.com/v2/account', {
    method : 'GET',
    headers: { 'Authorization': apiKey },
  });
  return { ok: resp.ok, status: resp.status };
}

async function pingClaude(apiKey) {
  const resp = await fetch('https://api.anthropic.com/v1/models', {
    method : 'GET',
    headers: { 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
  });
  return { ok: resp.ok, status: resp.status };
}

async function pingDeepgram(apiKey) {
  const resp = await fetch('https://api.deepgram.com/v1/projects', {
    method : 'GET',
    headers: { 'Authorization': `Token ${apiKey}` },
  });
  return { ok: resp.ok, status: resp.status };
}

// ─────────────────────────────────────────────────────────────────────────────
// Rate limiting (KV-based, sliding 1-minute window)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Check and increment rate-limit counter for `type` (api|adm) and `ip`.
 * Uses fire-and-forget (ctx.waitUntil) for the KV increment to avoid latency.
 * Returns a 429 Response if limit exceeded, otherwise null.
 */
async function checkRateLimit(env, ctx, type, ip, maxPerMin) {
  const window = Math.floor(Date.now() / 60000);
  const kvKey  = `rl:${type}:${ip}:${window}`;

  // Read current count synchronously (needed to decide whether to reject)
  const raw   = await env.GATEWAY_KV.get(kvKey);
  const count = raw ? parseInt(raw, 10) : 0;

  if (count >= maxPerMin) {
    return jsonResponse(
      { error: 'rate limit exceeded', retry_after: 60 },
      429,
      { 'Retry-After': '60' }
    );
  }

  // Increment counter fire-and-forget
  ctx.waitUntil(
    env.GATEWAY_KV.put(kvKey, String(count + 1), { expirationTtl: RL_TTL_SEC })
      .catch(err => console.error('[gateway] rl increment error', err))
  );

  return null; // allowed
}

// ─────────────────────────────────────────────────────────────────────────────
// KV helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Read a named API key: first from KV (managed), fallback to env secret. */
async function resolveKey(env, name) {
  const fromKV = await kvGetKey(env, name);
  if (fromKV) return fromKV;
  // Fallback to env secret (set via `wrangler secret put`)
  return env[name] ?? null;
}

async function kvGetKey(env, name) {
  return env.GATEWAY_KV.get(`key:${name}`);
}

async function kvSetKey(env, name, value) {
  return env.GATEWAY_KV.put(`key:${name}`, value);
}

async function kvDeleteKey(env, name) {
  return env.GATEWAY_KV.delete(`key:${name}`);
}

async function writeAuditLog(env, { action, key_name, ip }) {
  const entry = JSON.stringify({
    action,
    key_name,
    ip,
    timestamp: new Date().toISOString(),
  });
  const kvKey = `audit:${Date.now()}:${crypto.randomUUID().slice(0, 8)}`;
  return env.GATEWAY_KV.put(kvKey, entry, { expirationTtl: AUDIT_TTL_SEC });
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Constant-time comparison via HMAC to prevent timing attacks.
 */
async function timingSafeEqual(a, b) {
  const enc  = new TextEncoder();
  const key  = await crypto.subtle.generateKey({ name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const [sa, sb] = await Promise.all([
    crypto.subtle.sign('HMAC', key, enc.encode(a)),
    crypto.subtle.sign('HMAC', key, enc.encode(b)),
  ]);
  const va = new Uint8Array(sa), vb = new Uint8Array(sb);
  let diff = 0;
  for (let i = 0; i < va.length; i++) diff |= va[i] ^ vb[i];
  return diff === 0;
}

/**
 * Validate "Authorization: Bearer <token>" header against the expected secret.
 * Uses constant-time comparison to prevent timing attacks.
 * Returns null if valid, or a 401/503 Response if invalid/missing.
 */
async function checkBearer(request, expectedSecret, secretName) {
  if (!expectedSecret) {
    return jsonResponse({ error: `server misconfiguration: ${secretName} not set` }, 503);
  }
  const auth     = request.headers.get('Authorization') ?? '';
  const spaceIdx = auth.indexOf(' ');
  const scheme   = spaceIdx > -1 ? auth.slice(0, spaceIdx) : auth;
  const token    = spaceIdx > -1 ? auth.slice(spaceIdx + 1) : '';
  if (scheme !== 'Bearer' || !(await timingSafeEqual(token, expectedSecret))) {
    return jsonResponse({ error: 'unauthorized' }, 401);
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Response helper
// ─────────────────────────────────────────────────────────────────────────────

function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
      ...extraHeaders,
    },
  });
}
