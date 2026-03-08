/**
 * api-gateway — Cloudflare Worker v1.23
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

const VERSION = '1.19';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin' : '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, HEAD',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Path, X-Api-Variant, X-Azure-Region, Range, X-Proxy-Cookie, X-Requested-With',
  'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges, Content-Disposition, X-Proxy-Status',
  'Access-Control-Max-Age': '86400',
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

/**
 * Build sniffer script dynamically — needs the proxy secret for request proxying.
 * This script does 3 things:
 * 1. Proxifies ALL fetch/XHR through the Worker (fixes CORS)
 * 2. Detects video URLs and reports to parent via postMessage
 * 3. Suppresses pushState/replaceState SecurityErrors
 */
function buildSnifferScript(secret) {
  const esc = secret.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
  return `<script>(function(){
var PB=location.origin+'/proxy?s=${encodeURIComponent(esc)}&raw=1&url=';
var PP=location.origin+'/proxy?s=${encodeURIComponent(esc)}&url=';
var V=/\\.(mp4|webm|m3u8|mov|mkv|flv|avi|ts|mpd)(\\?[^"'\\s<>]*)?/i;
var VS=/\\.(m3u8|mpd)(\\?[^"'\\s<>]*)?/i;
var DT=new Set();
var _lastTitle='';
function isExt(u){return typeof u==='string'&&u.startsWith('http')&&!u.includes('/proxy?s=');}
function GT(){try{var j=document.querySelector('script[type="application/ld+json"]');if(j){var o=JSON.parse(j.textContent||'{}');if(o.name)return o.name.split('|')[0].trim()}var og=document.querySelector('meta[property="og:title"]');if(og)return og.content;return document.title||''}catch(e){return document.title||''}}
function R(u,t){if(!u||u.length<8||DT.has(u))return;DT.add(u);try{parent.postMessage({t:'vg-video',url:u,mt:t,title:GT()},'*')}catch(e){}}

/* ── 1. Proxy ALL fetch requests + block ads ── */
var OF=window.fetch;
window.fetch=function(i,o){
  var u=typeof i==='string'?i:(i&&i.url)||'';
  if(isAd(u))return Promise.resolve(new Response('',{status:200}));
  if(V.test(u)&&!isAd(u))R(u,'fetch');
  if(isExt(u)){
    var pu=PB+encodeURIComponent(u);
    if(typeof i==='string')return OF.call(this,pu,o);
    try{return OF.call(this,new Request(pu,{method:(o&&o.method)||i.method||'GET',headers:(o&&o.headers)||i.headers,body:(o&&o.body)||i.body,mode:'cors',credentials:'omit'}))}catch(e){return OF.call(this,pu,o)}
  }
  return OF.apply(this,arguments);
};

/* ── 2. Proxy ALL XHR requests + block ads ── */
var XO=XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open=function(m,u){
  if(typeof u==='string'){
    if(isAd(u)){u='data:text/plain,';return XO.call(this,m,u,true);}
    if(V.test(u)&&!isAd(u))R(u,'xhr');
    if(isExt(u))u=PB+encodeURIComponent(u);
  }
  return XO.call(this,m,u,true);
};

/* ── 3. Detect pushState/replaceState navigation + suppress SecurityError ── */
var oPS=history.pushState,oRS=history.replaceState;
var _lastNav='';
function NN(){try{var pu=new URLSearchParams(location.search).get('url');if(pu&&pu!==_lastNav){_lastNav=pu;DT.clear();parent.postMessage({t:'vg-nav',url:pu},'*')}}catch(e){}}
history.pushState=function(){try{oPS.apply(this,arguments)}catch(e){}NN()};
history.replaceState=function(){try{oRS.apply(this,arguments)}catch(e){}NN()};
window.addEventListener('popstate',NN);

/* ── 4. Mock localStorage if blocked ── */
try{localStorage.getItem('_t')}catch(e){
  var _s={};
  Object.defineProperty(window,'localStorage',{value:{getItem:function(k){return _s[k]||null},setItem:function(k,v){_s[k]=String(v)},removeItem:function(k){delete _s[k]},clear:function(){_s={}},get length(){return Object.keys(_s).length},key:function(i){return Object.keys(_s)[i]||null}},configurable:true});
}

/* ── 5. Ad domain blocklist ── */
var ADS=/(\\.|-)(magsrv|tsyndicate|exoclick|trafficjunky|juicyads|popads|adsterra|clickaine|pushame|ad-maven|hilltopads|plugrush|ero-advertising|trafficstars|crakrevenue|largeconfusion|exosrv|syndication)\\.|(doubleclick|googlesyndication)\\.com/i;
function isAd(u){return typeof u==='string'&&ADS.test(u);}

/* ── 5b. Intercept video.src / source.src setter ── */
try{
  var _vDesc=Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype,'src');
  if(_vDesc&&_vDesc.set){Object.defineProperty(HTMLMediaElement.prototype,'src',{set:function(v){if(v&&VS.test(v)&&!isAd(v))R(v,'src-set');return _vDesc.set.call(this,v)},get:_vDesc.get,configurable:true})}
  var _sDesc=Object.getOwnPropertyDescriptor(HTMLSourceElement.prototype,'src');
  if(_sDesc&&_sDesc.set){Object.defineProperty(HTMLSourceElement.prototype,'src',{set:function(v){if(v&&VS.test(v)&&!isAd(v))R(v,'source-set');return _sDesc.set.call(this,v)},get:_sDesc.get,configurable:true})}
}catch(x){}

/* ── 5c. Intercept MediaSource / HLS — catch blob URL creation ── */
try{
  var _cOU=URL.createObjectURL;
  URL.createObjectURL=function(o){var r=_cOU.apply(this,arguments);if(o&&o._vgSrc)R(o._vgSrc,'mse');return r};
  var _aS=MediaSource.prototype.addSourceBuffer;
  MediaSource.prototype.addSourceBuffer=function(){return _aS.apply(this,arguments)};
}catch(x){}

/* ── 6. Detect video URLs in DOM ── */
function S(){
  document.querySelectorAll('video,audio,source,[src],[data-src],[data-video-src]').forEach(function(e){
    var s=e.src||e.currentSrc||(e.dataset&&(e.dataset.src||e.dataset.videoSrc))||e.getAttribute('src')||'';
    /* Resolve proxied URLs back to original */
    if(s&&s.includes('/proxy?')){try{var qs=new URL(s).searchParams.get('url');if(qs)s=qs}catch(x){}}
    if(s&&V.test(s)&&!isAd(s))R(s,'dom');
    if(e.tagName==='VIDEO'&&e.currentSrc){var cs=e.currentSrc;if(cs.includes('/proxy?')){try{cs=new URL(cs).searchParams.get('url')||cs}catch(x){}}if(!isAd(cs)&&V.test(cs))R(cs,'cur')}
  });
  document.querySelectorAll('a[href]').forEach(function(a){if(V.test(a.href)&&!isAd(a.href))R(a.href,'link')});
  /* JSON-LD VideoObject detection */
  try{document.querySelectorAll('script[type="application/ld+json"]').forEach(function(s){
    try{var j=JSON.parse(s.textContent||'');var items=Array.isArray(j)?j:[j];
    items.forEach(function(o){
      if(o['@type']==='VideoObject'||o['@type']==='Video'){
        if(o.contentURL&&V.test(o.contentURL))R(o.contentURL,'jsonld');
        if(o.embedUrl&&V.test(o.embedUrl))R(o.embedUrl,'jsonld');
        if(o.url&&V.test(o.url))R(o.url,'jsonld');
        if(o.embedUrl&&!V.test(o.embedUrl))R(o.embedUrl,'embed');
      }
    })}catch(x){}
  })}catch(x){}
  /* Inline script video URL extraction */
  try{document.querySelectorAll('script:not([src])').forEach(function(s){
    var t=s.textContent||'';var re=/["'](https?:\\/\\/[^"'\\s]+\\.(?:mp4|m3u8|webm|mpd)(?:\\?[^"'\\s]*)?)["']/gi;var m;
    while((m=re.exec(t))!==null){if(!isAd(m[1]))R(m[1],'js')}})}catch(x){}
  /* Scan nested iframes (same-origin via proxy) */
  try{document.querySelectorAll('iframe').forEach(function(f){
    /* Report iframe src if it looks like a video embed */
    var fs=f.src||f.getAttribute('src')||'';
    if(fs&&fs.includes('/proxy?')){try{var iu=new URL(fs).searchParams.get('url');if(iu&&/embed|player/i.test(iu))R(iu,'iframe-embed')}catch(x){}}
    /* Scan accessible iframe content */
    try{var fd=f.contentDocument;if(fd){fd.querySelectorAll('video,source,[src]').forEach(function(e){
    var s=e.src||e.currentSrc||e.getAttribute('src')||'';
    if(s&&s.includes('/proxy?')){try{s=new URL(s).searchParams.get('url')||s}catch(x){}}
    if(s&&V.test(s)&&!isAd(s))R(s,'iframe-dom')});
    /* Also scan inline scripts in iframe */
    try{fd.querySelectorAll('script:not([src])').forEach(function(s){
      var t=s.textContent||'';var re=/["'](https?:\\/\\/[^"'\\s]+\\.(?:mp4|m3u8|webm|mpd)(?:\\?[^"'\\s]*)?)["']/gi;var m;
      while((m=re.exec(t))!==null){if(!isAd(m[1]))R(m[1],'iframe-js')}})}catch(x){}
    }}catch(x){}})}catch(x){}
}

/* ── 6b-6d: Click/History/Form interceptors moved to early-inject script in <head> ── */

/* ── 7. Report current page URL to parent ── */
try{var pu=new URLSearchParams(location.search).get('url');if(pu){_lastNav=pu;parent.postMessage({t:'vg-nav',url:pu},'*')}}catch(x){}

/* ── 8. Observe DOM changes ── */
new MutationObserver(S).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['src','data-src']});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',S);else S();
/* ── 9. Detect SPA navigation via title change ── */
_lastTitle=document.title;
setInterval(function(){
  S();
  var t=document.title;
  if(t&&t!==_lastTitle){_lastTitle=t;DT.clear();try{parent.postMessage({t:'vg-nav',url:document.URL||location.href},'*')}catch(x){}}
},3000);
})();</scrip`+`t>`;
}

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

  // Build fetch headers — realistic Chrome browser fingerprint
  const fetchHeaders = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
    'Accept': isRaw ? '*/*' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': target.origin + '/',
    'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    'Sec-Ch-Ua-Mobile': '?1',
    'Sec-Ch-Ua-Platform': '"Android"',
    'Sec-Fetch-Dest': isRaw ? 'empty' : 'document',
    'Sec-Fetch-Mode': isRaw ? 'cors' : 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1',
    'Cache-Control': 'max-age=0',
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

  // ── Fallback via Fly.io if target blocks CF datacenter IPs (403) ──
  if (resp.status === 403) {
    const flyUrl = await env.GATEWAY_KV.get('FLY_PROXY_URL'); // e.g. https://subwhisper-ffmpeg.fly.dev
    const flySecret = await env.GATEWAY_KV.get('FLY_SECRET');
    if (flyUrl && flySecret) {
      try {
        const flyResp = await fetch(`${flyUrl}/webproxy`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${flySecret}`,
          },
          body: JSON.stringify({
            url: targetUrl,
            method: request.method,
            raw: isRaw,
            headers: {
              cookie: cookie || undefined,
              range: request.headers.get('Range') || undefined,
            },
          }),
        });
        if (flyResp.ok || (flyResp.status >= 200 && flyResp.status < 500 && flyResp.status !== 403)) {
          resp = flyResp;
        }
      } catch (e) {
        // Fly.io fallback failed — use original 403 response
      }
    }
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

  // NOTE: <a href> rewriting REMOVED — dynamic click interceptor (vg-click) handles navigation
  // Static rewriting caused double navigation (iframe follows rewritten link + parent.navigate via vg-click)

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

  // Build sniffer + location polyfill
  const snifferScript = buildSnifferScript(secret);

  // Inject location polyfill at the TOP of <head> (before any other scripts)
  const locationPolyfill = `<script>(function(){
try{var u=new URLSearchParams(location.search).get('url');if(!u)return;var o=new URL(u);
Object.defineProperty(document,'URL',{get:function(){return o.href},configurable:true});
Object.defineProperty(document,'documentURI',{get:function(){return o.href},configurable:true});
try{Object.defineProperty(document,'referrer',{get:function(){return o.origin+'/'},configurable:true})}catch(e){}
try{Object.defineProperty(document,'domain',{value:o.hostname,writable:true,configurable:true})}catch(e){}
window.__vg_origUrl=o;window.__vg_origHref=o.href;
}catch(e){}})();</scrip`+`t>`;

  // Early-inject: click interceptor + History patch — MUST run before site scripts
  const earlyIntercept = `<script>(function(){
'use strict';
if(window.parent===window)return;
var OH=window.__vg_origHref;
function orig(){return OH||location.href}
/* Block History API SPA navigation — only pushState with different path triggers nav */
var _oP=history.pushState,_oR=history.replaceState;
var _curPath=(function(){try{return new URL(orig()).pathname}catch(x){return location.pathname}})();
history.pushState=function(s,t,u){if(!u)return _oP.apply(this,arguments);
  try{var a=new URL(u,orig());if(a.pathname!==_curPath){parent.postMessage({t:'vg-click',url:a.href},'*');return}
  }catch(x){}return _oP.apply(this,arguments)};
history.replaceState=function(s,t,u){return _oR.apply(this,arguments)};
/* Intercept clicks on links — capture phase on window, first handler registered */
var SK=/^(javascript:|mailto:|tel:|data:|blob:)/i;
window.addEventListener('click',function(e){
  var a=e.target.closest('a[href]');if(!a)return;
  var h=a.getAttribute('href');if(!h||SK.test(h))return;
  if(h==='#'||(h.charAt(0)==='#'&&h.indexOf('/')<0))return;
  e.preventDefault();e.stopImmediatePropagation();e.stopPropagation();
  try{var abs=new URL(h,orig()).href;
  if(abs.startsWith('http')){
    try{document.body.style.pointerEvents='none';document.body.style.opacity='0.3'}catch(x){}
    parent.postMessage({t:'vg-click',url:abs},'*')}}catch(x){}
},true);
/* Intercept form submissions */
window.addEventListener('submit',function(e){
  var f=e.target;if(!f||f.tagName!=='FORM')return;
  e.preventDefault();e.stopImmediatePropagation();
  var act=f.getAttribute('action')||'';
  try{var abs=new URL(act||orig(),orig()).href;
  parent.postMessage({t:'vg-click',url:abs},'*')}catch(x){}
},true);
})();</scrip`+`t>`;

  // Insert polyfill + early interceptor as first scripts in <head>
  if (/<head([^>]*)>/i.test(html)) {
    html = html.replace(/<head([^>]*)>/, `<head$1>${locationPolyfill}${earlyIntercept}`);
  }

  // Inject sniffer script before </body> (or at end)
  if (/<\/body>/i.test(html)) {
    html = html.replace(/<\/body>/i, snifferScript + '</body>');
  } else {
    html += snifferScript;
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
