/**
 * api-gateway-pro — Cloudflare Worker v1.3.0
 * Isolated gateway for paid apps (SubWhisper Pro + NoteFlowing)
 *
 * Zero dependency on api-gateway — completely independent.
 *
 * Bindings (wrangler.toml):
 *   env.PRO_KV — KV namespace for pro keys, usage, API secrets
 *
 * Secrets (wrangler secret put):
 *   ADMIN_TOKEN — Bearer token for admin routes
 *
 * KV keys:
 *   apikey:GEMINI_KEY, apikey:GROQ_KEY, apikey:ASSEMBLYAI_KEY,
 *   apikey:DEEPSEEK_KEY, apikey:AZURE_KEY
 *   cfg:azure:region
 *   pro:<key> → { email, plan, created, usage: { transcriptions, translations } }
 *
 * Routes:
 *   POST /api/verify        → Verify pro key, return plan + usage
 *   POST /api/transcribe    → Proxy to Groq/AssemblyAI (pro key required)
 *   POST /api/translate     → Proxy to Gemini/DeepSeek (pro key required)
 *   POST /api/gemini/*      → Proxy to Gemini API (pro key required)
 *   POST /api/groq          → Proxy to Groq API (pro key required)
 *   POST /api/assemblyai    → Proxy to AssemblyAI API (pro key required)
 *   POST /api/deepseek      → Proxy to DeepSeek API (pro key required)
 *   POST /api/azure         → Proxy to Azure Translator (pro key required)
 *   POST /api/subscribe       → Add email subscriber via LemonSqueezy API
 *   POST /webhook/lemonsqueezy → LemonSqueezy webhook (auto-create/revoke keys)
 *   POST /api/activate        → Activate by email (returns pro key)
 *   POST /admin/keys/set    → Set API keys in KV
 *   POST /admin/keys/list   → List API keys
 *   POST /admin/pro/create  → Create a pro user key
 *   POST /admin/pro/list    → List pro users
 *   POST /admin/pro/revoke  → Revoke a pro key
 *   GET  /health            → Health check
 */

const VERSION = '1.21.0';
// v1.15.0 (2026-08-03) — Source des visites (ADDITIF) : POST /api/visit accepte `src` et
//   incremente `stats:visits:<page>:src:<src>:total` ; GET renvoie `by_src` (via KV.list, meme
//   procede que `by_btn_all`). Ne s'ecrit QUE si `src` est fourni : dk/swp/nf/sv/ncf/tuc ne
//   l'envoient pas et gardent un comportement identique. `src` est sanitise cote worker aussi
//   ([a-z0-9.-], 24 car. max) — un parametre d'URL est saisissable par n'importe qui et ne doit
//   jamais creer de cle KV arbitraire. Motif : jusqu'ici les visites du hub se7 etaient un bloc
//   indistinct, le lien epingle TikTok (debloque le 03/08 a 1000 abonnes) n'aurait pas ete mesurable.
// v1.14.0 (2026-07-15) — Funnel analytics (ADDITIF, lecture seule) : GET /api/click renvoie désormais
//   `by_btn_all` = ventilation COMPLÈTE par bouton (via KV.list), en plus des 5 clés fixes conservées.
//   Permet au dashboard de lire le funnel du hub se7 (f:demo/f:chat/f:cta/f:waitlist + out:*). Zéro
//   changement de comportement pour les compteurs existants (dk/swp) ni pour aucune route SWP/NF/SV.
// v1.12.0 (2026-06-17) — StoryVoice monitoring (ADDITIF, lecture seule): endpoint /admin/sv/overview
//   (clés sv_ vendues, crédits restants/consommés, heures écoutées, revenu estimé, conversion démo→achat)
//   + 'sv' ajouté à l'agrégat /api/visit?page=all. Aucune logique SWP/NF/DK touchée.
// v1.10.0 (2026-06-17) — StoryVoice monetization: LS variant 1803132 (Pack Lecteur, 1M credits)
//   → webhook order_created credits the buyer's sv_ key by email (created if new). Fully isolated
//   from SWP/NF subscription flow. generateProKey supports 'sv_' prefix.
// v1.9.0 (2026-06-17) — Security hardening (additive, no behavior change for valid requests):
//   • safeApiPath(): X-Api-Path now validated on Gemini + AssemblyAI + OpenAI-SV proxies
//     → blocks upstream API-key exfiltration via "@host"/".host"/"//host" path tricks.
//   • timingSafeEqual(): constant-time compare for LS webhook signature + admin token.
//   KNOWN / DEFERRED (documented, intentionally not changed here):
//   • /api/activate returns the key by email (rate-limited 5/h) = SWP frictionless-onboarding
//     design tradeoff. For StoryVoice onboarding, prefer email-delivered key only.
//   • debitCredits() is a KV read-modify-write (non-atomic) → tiny TOCTOU overspend window,
//     bounded by prepaid balance + 10/min rate limit. Acceptable for now.
//   • CORS '*' kept (many legit origins: SWP/NoteFlowing/DictoKey/Factory).

// ── Plan limits (per calendar month) ────────────────────────────────────────
const PLAN_LIMITS = {
  pro:   { transcriptions: 50, translations: 500 },
  trial: { transcriptions: 10, translations: 100 },
};
const RATE_LIMIT_PER_MIN = 10;

// ── LemonSqueezy product dispatch ───────────────────────────────────────────
// variant_id → which app handles this product in the gateway.
// Source of truth: LS API (store 314871). Update when creating/recreating variants.
// Unhandled variants are acknowledged (200) but ignored — they belong to other services
// (e.g. VoiceBox has its own bot endpoint) or don't need a gateway key (Prompt Pack).
const LS_VARIANTS = {
  '1427150': { app: 'swp', handled: true  }, // SubWhisper Pro   €9/mo
  '1427188': { app: 'nf',  handled: true  }, // NoteFlowing Pro  €15/mo
  '1427180': { app: 'vb',  handled: false }, // VoiceBox Pro     €3/mo (handled by bot /lemon)
  '1427191': { app: 'pp',  handled: false }, // SubWhisper Prompt Pack €19 (one-time, no key)
  '1803203': { app: 'sv',  handled: true, credits: 300000  }, // StoryVoice Pack Découverte €7.90 (300k crédits voix)
  '1803132': { app: 'sv',  handled: true, credits: 1000000 }, // StoryVoice Pack Lecteur €24.90 (1M crédits voix)
  '1803204': { app: 'sv',  handled: true, credits: 3000000 }, // StoryVoice Pack Passionné €64.90 (3M crédits voix)
};

function extractVariantId(payload) {
  const a = payload?.data?.attributes || {};
  const id = a.variant_id
    || a.first_order_item?.variant_id
    || a.first_subscription_item?.variant_id
    || null;
  return id == null ? null : String(id);
}

function resolveApp(payload) {
  const variantId = extractVariantId(payload);
  const entry = variantId ? LS_VARIANTS[variantId] : null;
  return { variantId, app: entry?.app || null, handled: !!entry?.handled };
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Pro-Key, X-Api-Path, X-Azure-Region',
  'Access-Control-Max-Age': '86400',
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}

function err(msg, status = 400) {
  return json({ error: msg }, status);
}

// ── Bot/crawler filter for public visit/click counters ──────────────────────
// New domains get hammered by CT-log crawlers, scanners and social-preview bots
// that execute JS → they inflate the visit/click counters and make the funnel
// dashboard lie. Skip the increment for obvious non-human traffic so counters
// reflect real visitors. Conservative denylist (known bot tokens only).
// CRITICAL: must NOT match the TikTok in-app webview (BytedanceWebview /
// musical_ly / trill) — those are our real target users. Verified: none of the
// tokens below appear in the TikTok webview UA.
const BOT_UA_RE = /bot\b|crawl|spider|slurp|scrape|headless|phantom|puppeteer|playwright|selenium|python|curl|wget|libwww|httpclient|okhttp|go-http|java\/|axios|node-fetch|bytespider|gptbot|claudebot|ccbot|amazonbot|applebot|googlebot|bingbot|baiduspider|semrush|ahrefs|mj12|dotbot|petalbot|dataforseo|facebookexternalhit|telegrambot|whatsapp|discordbot|slackbot|embedly|skypeuripreview|censys|masscan|zgrab|expanse/i;
function isBotUA(ua) {
  if (!ua) return true;            // empty UA = scanner/bot
  return BOT_UA_RE.test(ua);
}

// ─────────────────────────────────────────────────────────────────────────────
// Pro key validation
// ─────────────────────────────────────────────────────────────────────────────

async function validateProKey(proKey, env) {
  if (!proKey) return null;
  const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
  if (!data) return null;
  if (data.revoked) return null;
  // Check expiration
  if (data.expiresAt && new Date(data.expiresAt) < new Date()) return null;
  // v1.18.0 — garde-fou par DATE, indépendant des webhooks. `endsAt` porte la fin
  // d'accès d'un abonnement résilié : si le webhook de révocation se perd (panne,
  // signature refusée, worker indisponible), l'accès s'arrête quand même à la date.
  // Un abonnement sain n'a pas d'`endsAt` — seule une résiliation en pose un.
  if (data.endsAt && new Date(data.endsAt) < new Date()) return null;
  return data;
}

// Get current month key (e.g. "2026-03")
function monthKey() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

// Check if usage limit is reached for this month
function checkUsageLimit(data, type) {
  const plan = data.plan || 'pro';
  const limits = PLAN_LIMITS[plan] || PLAN_LIMITS.pro;
  const mk = monthKey();
  const monthly = (data.monthlyUsage && data.monthlyUsage[mk]) || { transcriptions: 0, translations: 0 };
  if (type === 'transcription' && monthly.transcriptions >= limits.transcriptions) {
    return { blocked: true, reason: `Monthly transcription limit reached (${limits.transcriptions})`, usage: monthly, limits };
  }
  if (type === 'translation' && monthly.translations >= limits.translations) {
    return { blocked: true, reason: `Monthly translation limit reached (${limits.translations})`, usage: monthly, limits };
  }
  return { blocked: false, usage: monthly, limits };
}

async function incrementUsage(proKey, type, env, ctx) {
  const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
  if (!data) return;
  // Legacy total usage
  if (!data.usage) data.usage = { transcriptions: 0, translations: 0 };
  if (type === 'transcription') data.usage.transcriptions++;
  if (type === 'translation') data.usage.translations++;
  // Monthly usage tracking
  const mk = monthKey();
  if (!data.monthlyUsage) data.monthlyUsage = {};
  if (!data.monthlyUsage[mk]) data.monthlyUsage[mk] = { transcriptions: 0, translations: 0 };
  if (type === 'transcription') data.monthlyUsage[mk].transcriptions++;
  if (type === 'translation') data.monthlyUsage[mk].translations++;
  // Clean old months (keep last 3)
  const months = Object.keys(data.monthlyUsage).sort();
  while (months.length > 3) { delete data.monthlyUsage[months.shift()]; }
  data.lastUsed = new Date().toISOString();
  ctx.waitUntil(env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data)));
}

// Simple rate limiter (per key, per minute) using KV
async function checkRateLimit(proKey, env) {
  const now = Math.floor(Date.now() / 60000); // minute bucket
  const rlKey = `rl:${proKey}:${now}`;
  const count = parseInt(await env.PRO_KV.get(rlKey) || '0');
  if (count >= RATE_LIMIT_PER_MIN) return false;
  await env.PRO_KV.put(rlKey, String(count + 1), { expirationTtl: 120 });
  return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// API key helpers
// ─────────────────────────────────────────────────────────────────────────────

async function getApiKey(name, env) {
  // Try KV first, fallback to wrangler secrets
  const fromKV = await env.PRO_KV.get(`apikey:${name}`);
  if (fromKV) return fromKV;
  return env[name] ?? null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Security helpers
// ─────────────────────────────────────────────────────────────────────────────

// Only allow path-style X-Api-Path values (must start with a single "/", no "..",
// no backslash, no protocol-relative "//"). Blocks "@evil.com/...", ".evil.com",
// "//evil.com" tricks that would otherwise send the upstream API key to an
// attacker-controlled host. Falls back to the safe default for anything suspicious.
function safeApiPath(raw, fallback) {
  if (typeof raw !== 'string' || !raw.startsWith('/')) return fallback;
  if (raw.startsWith('//') || raw.startsWith('/\\')) return fallback;
  if (raw.includes('..') || raw.includes('\\')) return fallback;
  return raw;
}

// Constant-time string comparison (avoids timing side-channels on secrets).
function timingSafeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Proxy helpers
// ─────────────────────────────────────────────────────────────────────────────

async function proxyGemini(request, env, apiPath) {
  const key = await getApiKey('GEMINI_KEY', env);
  if (!key) return err('Gemini API key not configured', 503);
  const path = safeApiPath(apiPath || request.headers.get('X-Api-Path'), '/v1beta/models/gemini-2.0-flash:generateContent');
  const url = `https://generativelanguage.googleapis.com${path}?key=${key}`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: request.body,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
  });
}

async function proxyGroq(request, env) {
  const key = await getApiKey('GROQ_KEY', env);
  if (!key) return err('Groq API key not configured', 503);
  const ct = request.headers.get('Content-Type') || '';
  const headers = { 'Authorization': `Bearer ${key}` };
  if (ct) headers['Content-Type'] = ct;
  const resp = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
    method: 'POST',
    headers,
    body: request.body,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
  });
}

async function proxyAssemblyAI(request, env) {
  const key = await getApiKey('ASSEMBLYAI_KEY', env);
  if (!key) return err('AssemblyAI API key not configured', 503);
  const apiPath = safeApiPath(request.headers.get('X-Api-Path'), '/v2/transcript');
  const url = `https://api.assemblyai.com${apiPath}`;
  const resp = await fetch(url, {
    method: request.method,
    headers: {
      'Authorization': key,
      'Content-Type': request.headers.get('Content-Type') || 'application/json',
    },
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
  });
}

async function proxyDeepSeek(request, env) {
  const key = await getApiKey('DEEPSEEK_KEY', env);
  if (!key) return err('DeepSeek API key not configured', 503);
  const resp = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: request.body,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
  });
}

async function proxyAzure(request, env, url) {
  const key = await getApiKey('AZURE_KEY', env);
  if (!key) return err('Azure API key not configured', 503);
  const region = request.headers.get('X-Azure-Region') || await env.PRO_KV.get('cfg:azure:region') || 'francecentral';
  const headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Ocp-Apim-Subscription-Region': region,
    'Content-Type': 'application/json',
  };
  const resp = await fetch(url.href.replace(url.origin, 'https://api.cognitive.microsofttranslator.com'), {
    method: 'POST',
    headers,
    body: request.body,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// StoryVoice — prepaid-credits path (sv_ keys). FULLY ISOLATED from SubWhisper:
// never calls checkUsageLimit / PLAN_LIMITS / incrementUsage. Additive (v1.8.0).
//   Brain (summaries/Q&A) via /api/deepseek = FREE (reuses proxyDeepSeek).
//   Voice via /api/openai + X-Api-Path:/v1/audio/speech = METERED (1 credit = 1 char).
//   Premium voice via /api/gcptts (Gemini Cloud TTS, OAuth SA) = METERED ×2 (2 credits/char).
//   plan 'unlimited' (owner/family) = never metered, just a high anti-disaster guard.
// ─────────────────────────────────────────────────────────────────────────────

// ── OAuth compte de service pour Gemini-TTS (Cloud TTS, texttospeech.googleapis.com). ──
// Clé SA (JSON) en KV PRO_KV `key:GCPTTS_SA_JSON` → JWT RS256 signé → token OAuth (caché ~55 min).
// Copié du gateway normal (v1.45) pour exposer la voix Gemini premium aux clés sv_ (v1.13.0).
let _gcpSaToken = { token: null, exp: 0 };
function _b64urlBytes(u8) { let s = ''; for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]); return btoa(s).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_'); }
function _b64urlStr(str) { return _b64urlBytes(new TextEncoder().encode(str)); }
async function _importPkcs8(pem) {
  const b64 = pem.replace(/-----BEGIN PRIVATE KEY-----/, '').replace(/-----END PRIVATE KEY-----/, '').replace(/\s+/g, '');
  const der = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  return crypto.subtle.importKey('pkcs8', der.buffer, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
}
async function getGcpSaToken(env) {
  const now = Math.floor(Date.now() / 1000);
  if (_gcpSaToken.token && _gcpSaToken.exp > now + 60) return _gcpSaToken.token;
  const raw = await env.PRO_KV.get('key:GCPTTS_SA_JSON');
  if (!raw) throw new Error('GCPTTS_SA_JSON not configured');
  const sa = JSON.parse(raw);
  const aud = sa.token_uri || 'https://oauth2.googleapis.com/token';
  const signingInput = _b64urlStr(JSON.stringify({ alg: 'RS256', typ: 'JWT' })) + '.' +
    _b64urlStr(JSON.stringify({ iss: sa.client_email, scope: 'https://www.googleapis.com/auth/cloud-platform', aud, iat: now, exp: now + 3600 }));
  const key = await _importPkcs8(sa.private_key);
  const sig = await crypto.subtle.sign({ name: 'RSASSA-PKCS1-v1_5' }, key, new TextEncoder().encode(signingInput));
  const jwt = signingInput + '.' + _b64urlBytes(new Uint8Array(sig));
  const resp = await fetch(aud, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}` });
  const j = await resp.json().catch(() => ({}));
  if (!resp.ok || !j.access_token) throw new Error('SA token failed ' + resp.status);
  _gcpSaToken = { token: j.access_token, exp: now + (j.expires_in || 3600) };
  return j.access_token;
}

async function debitCredits(proKey, chars, env) {
  const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
  if (!data) return;
  data.credits = Math.max(0, Number(data.credits || 0) - chars);
  data.ttsCharsUsed = Number(data.ttsCharsUsed || 0) + chars;
  data.lastUsed = new Date().toISOString();
  await env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data));
}

async function proxyOpenaiSV(request, env, apiPath) {
  const key = await getApiKey('OPENAI_KEY', env);
  if (!key) return err('OpenAI API key not configured', 503);
  const p = safeApiPath(apiPath, '/v1/chat/completions');
  const resp = await fetch(`https://api.openai.com${p}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': request.headers.get('Content-Type') || 'application/json' },
    body: request.body,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
  });
}

async function handleStoryVoice(request, env, ctx, path, proKey, proData) {
  // Anti-abuse rate limit (shared helper — safe, just a per-key KV counter)
  if (!await checkRateLimit(proKey, env)) {
    return err('Rate limit exceeded. Max 10 requests/minute.', 429);
  }
  const unlimited = proData.plan === 'unlimited';

  // Brain (free): summaries / Q&A / language detection via DeepSeek
  if (path === '/api/deepseek') {
    return proxyDeepSeek(request, env);
  }

  // OpenAI: TTS (metered prepaid credits) or chat (free brain)
  if (path === '/api/openai') {
    const apiPath = request.headers.get('X-Api-Path') || '/v1/chat/completions';
    if (apiPath === '/v1/audio/speech') {
      let body;
      try { body = await request.json(); } catch { return err('invalid JSON body', 400); }
      const chars = (body && typeof body.input === 'string') ? body.input.length : 0;
      const credits = Number(proData.credits || 0);
      if (!unlimited && chars > credits) {
        return json({ error: 'insufficient_credits', credits, needed: chars }, 402);
      }
      const key = await getApiKey('OPENAI_KEY', env);
      if (!key) return err('OpenAI API key not configured', 503);
      const resp = await fetch('https://api.openai.com/v1/audio/speech', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      // Debit only on success, by the chars actually sent (fire-and-forget)
      if (resp.ok && !unlimited && chars > 0) {
        ctx.waitUntil(debitCredits(proKey, chars, env));
      }
      return new Response(resp.body, {
        status: resp.status,
        headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'audio/mpeg' },
      });
    }
    return proxyOpenaiSV(request, env, apiPath);
  }

  // Gemini premium voice (Cloud TTS, OAuth SA) — METERED ×2 (Gemini ≈ 2× le coût OpenAI). Pas de cap journalier.
  if (path.startsWith('/api/gcptts')) {
    let body;
    try { body = await request.json(); } catch { return err('invalid JSON body', 400); }
    const text = (body && body.input && typeof body.input.text === 'string') ? body.input.text : '';
    const units = text.length * 2; // 2 crédits / caractère pour la voix premium Gemini
    const credits = Number(proData.credits || 0);
    if (!unlimited && units > credits) {
      return json({ error: 'insufficient_credits', credits, needed: units }, 402);
    }
    let token;
    try { token = await getGcpSaToken(env); } catch (e) { return err('GCP SA auth failed: ' + e.message, 503); }
    let subPath = path.slice('/api/gcptts'.length) || '/v1/text:synthesize';
    if (!subPath.startsWith('/')) subPath = '/' + subPath;
    subPath = safeApiPath(subPath, '/v1/text:synthesize');
    const resp = await fetch('https://texttospeech.googleapis.com' + subPath, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (resp.ok && !unlimited && units > 0) {
      ctx.waitUntil(debitCredits(proKey, units, env));
    }
    return new Response(resp.body, {
      status: resp.status,
      headers: { ...CORS_HEADERS, 'Content-Type': resp.headers.get('Content-Type') || 'application/json' },
    });
  }

  return err('Route not available for StoryVoice', 404);
}

// ─────────────────────────────────────────────────────────────────────────────
// Admin helpers
// ─────────────────────────────────────────────────────────────────────────────

function checkAdmin(request, env) {
  const auth = request.headers.get('Authorization') || '';
  const token = auth.replace('Bearer ', '');
  if (!token || !env.ADMIN_TOKEN || !timingSafeEqual(token, env.ADMIN_TOKEN)) return false;
  return true;
}

function generateProKey(app = 'swp') {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  const prefix = app === 'nf' ? 'nf_' : (app === 'sv' ? 'sv_' : 'swp_');
  let key = prefix;
  for (let i = 0; i < 24; i++) key += chars[Math.floor(Math.random() * chars.length)];
  return key;
}

// ─────────────────────────────────────────────────────────────────────────────
// Newsletter subscriber via LemonSqueezy API
// ─────────────────────────────────────────────────────────────────────────────

async function handleSubscribe(request, env) {
  const body = await request.json().catch(() => null);
  if (!body || !body.email) return err('email required', 400);

  const email = body.email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return err('Invalid email', 400);

  // Rate limit: 10 subscribes per IP per hour
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const rlKey = `rl:subscribe:${ip}`;
  const rlCount = parseInt(await env.PRO_KV.get(rlKey)) || 0;
  if (rlCount >= 10) return err('Too many attempts, try again later', 429);
  await env.PRO_KV.put(rlKey, String(rlCount + 1), { expirationTtl: 3600 });

  // Deduplicate
  const subKey = `subscriber:${email}`;
  const existing = await env.PRO_KV.get(subKey);
  if (existing) return json({ ok: true, message: 'Already subscribed' });

  // Store in KV (LemonSqueezy has no subscriber API — import manually)
  const data = { email, name: body.name || '', source: body.source || 'nocode-flow', date: new Date().toISOString() };
  await env.PRO_KV.put(subKey, JSON.stringify(data));

  // Update subscriber count
  const countRaw = await env.PRO_KV.get('subscribers:count');
  await env.PRO_KV.put('subscribers:count', String((parseInt(countRaw) || 0) + 1));

  return json({ ok: true, message: 'Subscribed!' });
}

// ─────────────────────────────────────────────────────────────────────────────
// LemonSqueezy webhook signature verification (HMAC-SHA256)
// ─────────────────────────────────────────────────────────────────────────────

async function verifyWebhookSignature(rawBody, signature, secret) {
  if (!secret || !signature) return false;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(rawBody));
  const hex = [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, '0')).join('');
  return timingSafeEqual(hex, signature);
}

// ─────────────────────────────────────────────────────────────────────────────
// Activation email delivery (Resend HTTPS API) — fire-and-forget from webhook
// ─────────────────────────────────────────────────────────────────────────────
// Direct call to Resend (HTTPS:443, works from any host incl. Railway-blocked
// SMTP environments). Email sent from noreply@sub-whisper.com (verified domain)
// with reply_to: quangapps.dev@gmail.com so customer replies land in the
// business inbox.
// Requires env.RESEND_API_KEY. Silent no-op if missing.
// Convergent recommendation from 3 LLM vote (Groq+DeepSeek+Kimi) + Railway docs
// confirming SMTP block on Hobby plan — see _incidents.md 2026-05-29.

async function sendActivationEmail({ email, key, plan, trialEndsAt, app, env }) {
  if (!env.RESEND_API_KEY) return { sent: false, reason: 'no_api_key' };
  if (app !== 'swp') return { sent: false, reason: 'unsupported_app' };

  const from = env.RESEND_FROM || 'SubWhisper Pro <noreply@sub-whisper.com>';
  const replyTo = env.RESEND_REPLY_TO || 'quangapps.dev@gmail.com';
  const trialLine = (plan === 'trial' && trialEndsAt)
    ? `Your free trial is active until ${new Date(trialEndsAt).toISOString().slice(0, 10)}. Included during the trial: 10 transcriptions + 100 translations.`
    : 'Your Pro plan is active. Included every month: 50 transcriptions + 500 translations.';
  const subject = plan === 'trial'
    ? 'Your SubWhisper Pro key — free trial active'
    : 'Your SubWhisper Pro key — Pro plan active';

  const text = `Welcome to SubWhisper Pro!

Thank you for subscribing. Here is your access key:

    ${key}

How to activate (30 seconds):
1. Go to https://sub-whisper.com
2. Click "Activate" and enter your email (${email}), OR click "Have a license key instead?" and paste the key above.
3. Done — you can start transcribing and translating right away.

${trialLine}

Any question or feedback, just reply to this email — I read every message personally.

Quang
SubWhisper Pro
https://sub-whisper.com
`;

  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#222;line-height:1.55">
<h2 style="color:#5e3bff;margin:0 0 16px">Welcome to SubWhisper Pro</h2>
<p>Thank you for subscribing. Here is your access key:</p>
<pre style="background:#f3f0ff;border:1px solid #ddd;padding:14px 16px;border-radius:8px;font-size:15px;user-select:all;word-break:break-all;margin:0">${key}</pre>
<h3 style="margin-top:24px">How to activate (30 seconds)</h3>
<ol>
<li>Go to <a href="https://sub-whisper.com/?activated=1" style="color:#5e3bff">sub-whisper.com</a></li>
<li>Click <strong>"Activate"</strong> and enter your email (<code>${email}</code>) — or click <strong>"Have a license key instead?"</strong> and paste the key above.</li>
<li>Done. Start transcribing and translating right away.</li>
</ol>
<p style="background:#f9f9f9;padding:12px 16px;border-radius:6px;border-left:3px solid #5e3bff">${trialLine}</p>
<p>Any question or feedback, just reply to this email — I read every message personally.</p>
<p style="margin-top:32px;color:#666;font-size:13px">— Quang<br>SubWhisper Pro · <a href="https://sub-whisper.com" style="color:#5e3bff">sub-whisper.com</a></p>
</body></html>`;

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ from, to: [email], reply_to: replyTo, subject, text, html }),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      console.log(`[email] Resend ${res.status}: ${errText.slice(0, 200)}`);
      return { sent: false, reason: `resend_${res.status}` };
    }
    const data = await res.json().catch(() => ({}));
    return { sent: true, id: data.id };
  } catch (e) {
    console.log(`[email] Resend exception: ${e.message}`);
    return { sent: false, reason: 'exception' };
  }
}

// StoryVoice — livraison du code prépayé par email (Resend), bilingue FR/EN.
// ISOLÉ de sendActivationEmail (SWP) : branding StoryVoice, instructions « Réglages → Code d'accès ».
// Domaine expéditeur réutilise sub-whisper.com (vérifié Resend) avec nom d'affichage StoryVoice tant que
// StoryVoice n'a pas son propre domaine vérifié. reply-to = inbox business. Silent no-op si pas de clé.
async function sendStoryVoiceKeyEmail({ email, key, credits, env }) {
  if (!env.RESEND_API_KEY) return { sent: false, reason: 'no_api_key' };
  const from = env.RESEND_SV_FROM || 'StoryVoice <noreply@storiesvoice.org>';
  const replyTo = env.RESEND_REPLY_TO || 'quangapps.dev@gmail.com';
  const url = 'https://quang101182.github.io/storyvoice/';
  const hours = Math.round((Number(credits || 0) / 90000) * 10) / 10; // 90000 crédits ≈ 1 h (SV_CPH côté app)
  const subject = 'Votre code StoryVoice · Your StoryVoice code';
  const text = `Merci pour votre achat StoryVoice !

Voici votre code d'acces :

    ${key}

Solde : ~ ${hours} h de narration vocale.

Comment l'activer (30 s) :
1. Ouvrez ${url}
2. Cliquez sur l'engrenage (Reglages) en haut a droite.
3. Collez votre code dans " Code d'acces ", puis Enregistrer.
4. C'est pret : chargez vos livres et ecoutez la narration multi-voix.

Une question ? Repondez simplement a cet email.

— Quang · StoryVoice

────────────────────────

Thank you for your StoryVoice purchase!

Here is your access code:

    ${key}

Balance: ~ ${hours} h of voice narration.

How to activate (30s):
1. Open ${url}
2. Click the gear (Settings) at the top right.
3. Paste your code into "Access code", then Save.
4. Done: load your books and enjoy the multi-voice narration.

Any question? Just reply to this email.

— Quang · StoryVoice
`;
  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#222;line-height:1.55">
<h2 style="color:#0d94b4;margin:0 0 16px">StoryVoice</h2>
<p>Merci pour votre achat ! Voici votre code d'acces :</p>
<pre style="background:#eef9fc;border:1px solid #cfe9f0;padding:14px 16px;border-radius:8px;font-size:16px;user-select:all;word-break:break-all;margin:0">${key}</pre>
<p style="color:#555;margin-top:8px">Solde : ~ <strong>${hours} h</strong> de narration vocale.</p>
<h3 style="margin-top:22px">Activation (30 s)</h3>
<ol>
<li>Ouvrez <a href="${url}" style="color:#0d94b4">StoryVoice</a></li>
<li>Cliquez sur l'engrenage <strong>&#9881; (Reglages)</strong> en haut a droite.</li>
<li>Collez votre code dans <strong>&laquo; Code d'acces &raquo;</strong>, puis Enregistrer.</li>
<li>C'est pret : chargez vos livres et ecoutez la narration multi-voix.</li>
</ol>
<hr style="border:none;border-top:1px solid #eee;margin:22px 0">
<p style="color:#666"><em>English:</em> Here is your access code (above). Open <a href="${url}" style="color:#0d94b4">StoryVoice</a> &rarr; gear &#9881; (Settings) &rarr; paste it into &quot;Access code&quot; &rarr; Save.</p>
<p>Une question ? Repondez a cet email. / Any question? Just reply.</p>
<p style="margin-top:28px;color:#666;font-size:13px">— Quang · StoryVoice</p>
</body></html>`;
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from, to: [email], reply_to: replyTo, subject, text, html }),
    });
    if (!res.ok) { const e = await res.text().catch(() => ''); console.log(`[sv-email] Resend ${res.status}: ${e.slice(0, 200)}`); return { sent: false, reason: `resend_${res.status}` }; }
    const data = await res.json().catch(() => ({}));
    return { sent: true, id: data.id };
  } catch (e) { console.log(`[sv-email] Resend exception: ${e.message}`); return { sent: false, reason: 'exception' }; }
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Trace d'envoi des mails de cle ───────────────────────────────────────────
// Les envois restent « fire-and-forget » (le webhook ne doit pas echouer parce
// que Resend est lent), mais leur RESULTAT etait jusqu'ici perdu. Domaine
// expediteur non verifie, cle revoquee, quota depasse : le client payait, le
// webhook repondait `ok`, et rien ne le signalait.
// L'issue est desormais ecrite sur la cle : un mail non parti devient visible.
async function recordEmailOutcome(env, proKey, res) {
  try {
    const d = await env.PRO_KV.get(`pro:${proKey}`, 'json');
    if (!d) return;
    d.emailSent = !!(res && res.sent);
    d.emailAt = new Date().toISOString();
    if (res && res.reason) d.emailError = res.reason; else delete d.emailError;
    await env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(d));
    if (!d.emailSent) console.log(`[email] FAILED for ${d.email} — ${d.emailError}`);
  } catch (e) { console.log('[email] outcome not recorded:', String(e)); }
}

// LemonSqueezy webhook handler
// ─────────────────────────────────────────────────────────────────────────────

async function handleLemonSqueezyWebhook(request, env, ctx) {
  const rawBody = await request.text();
  const signature = request.headers.get('X-Signature');
  const secret = await env.PRO_KV.get('cfg:lemonsqueezy_signing_secret');

  // Verify signature if secret is configured
  if (secret) {
    if (!await verifyWebhookSignature(rawBody, signature, secret)) {
      return err('Invalid webhook signature', 401);
    }
  }

  let payload;
  try { payload = JSON.parse(rawBody); } catch { return err('Invalid JSON', 400); }

  const event = payload.meta?.event_name;
  const attrs = payload.data?.attributes || {};
  const email = attrs.user_email;
  const subscriptionId = String(payload.data?.id || '');

  if (!email) return err('No email in webhook payload', 400);

  // Dispatch by LS variant_id. Variants not in LS_VARIANTS are acknowledged but ignored.
  const route = resolveApp(payload);
  if (!route.handled) {
    return json({ ok: true, action: 'ignored', reason: 'variant not handled by gateway', variantId: route.variantId, app: route.app });
  }
  const app = route.app;
  const emailKey = `email:${app}:${email.toLowerCase()}`;
  const emailLegacyKey = `email:${email.toLowerCase()}`;

  // ── StoryVoice (app 'sv') : achat ONE-TIME de crédits prépayés voix. ISOLÉ de SWP/NF (abonnements).
  // Seul order_created compte (pas de subscription). Crédite la clé sv_ de l'email (créée si nouvelle). ──
  if (app === 'sv') {
    if (event !== 'order_created') {
      return json({ ok: true, action: 'ignored', reason: 'sv: only order_created credits', event });
    }
    const credits = (LS_VARIANTS[route.variantId] && LS_VARIANTS[route.variantId].credits) || 0;
    let key = await env.PRO_KV.get(emailKey);
    let data = key ? await env.PRO_KV.get(`pro:${key}`, 'json') : null;
    if (!key || !data) {
      key = generateProKey('sv');
      data = { email: email.toLowerCase(), app: 'sv', plan: 'prepaid', credits: 0, created: new Date().toISOString(), revoked: false };
      await env.PRO_KV.put(emailKey, key);
    }
    data.credits = Math.max(0, Number(data.credits || 0)) + credits;
    data.lastUsed = new Date().toISOString();
    if (data.revoked) data.revoked = false; // un nouvel achat réactive
    await env.PRO_KV.put(`pro:${key}`, JSON.stringify(data));
    // Livraison du code par email (fire-and-forget, n'impacte pas la réponse webhook ni le crédit).
    let emailQueued = false;
    if (ctx && ctx.waitUntil) { ctx.waitUntil(sendStoryVoiceKeyEmail({ email, key, credits: data.credits, env }).then((r) => recordEmailOutcome(env, key, r))); emailQueued = true; }
    return json({ ok: true, action: 'sv_credited', email, app: 'sv', creditsAdded: credits, balance: data.credits, emailQueued });
  }

  // subscription_created → create pro key.
  // order_created is intentionally IGNORED here: LS fires both events for every subscription
  // purchase (order_created first, then subscription_created ~0.3s later). Handling both
  // caused a race in KV (eventually consistent) and created duplicate keys for the same email
  // (Mark 29/05, thomas_olaf 02/06). Subscriptions are the only product type the gateway handles
  // — one-time purchases (PromptPack) are routed to "ignored" via LS_VARIANTS anyway.
  if (event === 'order_created') {
    return json({ ok: true, action: 'ignored', reason: 'order_created handled by subscription_created' });
  }
  if (event === 'subscription_created') {
    const status = attrs.status; // 'active', 'on_trial', 'cancelled', etc.
    const plan = (status === 'on_trial') ? 'trial' : 'pro';
    const trialEndsAt = attrs.trial_ends_at || null;

    // Check if email already has a key (app-scoped first, then legacy)
    let existingKey = await env.PRO_KV.get(emailKey);
    if (!existingKey) existingKey = await env.PRO_KV.get(emailLegacyKey);
    if (existingKey) {
      // Reactivate if revoked
      const existingData = await env.PRO_KV.get(`pro:${existingKey}`, 'json');
      if (existingData && existingData.revoked) {
        existingData.revoked = false;
        existingData.plan = plan;
        existingData.lsStatus = status; // v1.6.0 — track real LS status
        existingData.subscriptionId = subscriptionId;
        if (trialEndsAt) existingData.expiresAt = trialEndsAt;
        else delete existingData.expiresAt;
        await env.PRO_KV.put(`pro:${existingKey}`, JSON.stringify(existingData));
      }
      if (ctx?.waitUntil) {
        ctx.waitUntil(sendActivationEmail({ email: email.toLowerCase(), key: existingKey, plan, trialEndsAt, app, env }).then((r) => recordEmailOutcome(env, existingKey, r)));
      }
      return json({ ok: true, action: 'reactivated', email });
    }

    // Create new pro key
    const key = generateProKey(app);
    const data = {
      email: email.toLowerCase(),
      plan,
      app,
      created: new Date().toISOString(),
      subscriptionId,
      lsStatus: status, // v1.6.0 — real LS status ('on_trial', 'active', ...) for honest payer counting
      usage: { transcriptions: 0, translations: 0 },
      monthlyUsage: {},
      revoked: false,
    };
    if (trialEndsAt) data.expiresAt = trialEndsAt;

    await env.PRO_KV.put(`pro:${key}`, JSON.stringify(data));
    await env.PRO_KV.put(emailKey, key);

    if (ctx?.waitUntil) {
      ctx.waitUntil(sendActivationEmail({ email: email.toLowerCase(), key, plan, trialEndsAt, app, env }).then((r) => recordEmailOutcome(env, key, r)));
    }

    return json({ ok: true, action: 'created', email, app, plan });
  }

  // subscription_updated → update plan/status
  if (event === 'subscription_updated') {
    let proKey = await env.PRO_KV.get(emailKey);
    if (!proKey) proKey = await env.PRO_KV.get(emailLegacyKey);
    if (!proKey) return json({ ok: true, action: 'ignored', reason: 'no key for email' });
    const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
    if (!data) return json({ ok: true, action: 'ignored' });

    const status = attrs.status;
    if (status === 'active') {
      data.plan = 'pro';
      data.revoked = false;
      delete data.expiresAt;
    } else if (status === 'on_trial') {
      data.plan = 'trial';
      if (attrs.trial_ends_at) data.expiresAt = attrs.trial_ends_at;
    } else if (status === 'cancelled' || status === 'expired' || status === 'unpaid') {
      data.revoked = true;
    }
    data.lsStatus = status; // v1.6.0 — always record the real LS status (incl. past_due, paused)
    data.subscriptionId = subscriptionId;
    await env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data));
    return json({ ok: true, action: 'updated', email, app, status });
  }

  // subscription_cancelled / subscription_expired → revoke
  if (event === 'subscription_cancelled' || event === 'subscription_expired') {
    let proKey = await env.PRO_KV.get(emailKey);
    if (!proKey) proKey = await env.PRO_KV.get(emailLegacyKey);
    if (!proKey) return json({ ok: true, action: 'ignored' });
    const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
    if (data) {
      data.revoked = true;
      data.lsStatus = attrs.status || (event === 'subscription_cancelled' ? 'cancelled' : 'expired'); // v1.6.0
      await env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data));
    }
    return json({ ok: true, action: 'revoked', email, app });
  }

  return json({ ok: true, action: 'ignored', event, app });
}

// ─────────────────────────────────────────────────────────────────────────────
// Email activation (customer enters email → gets their key)
// ─────────────────────────────────────────────────────────────────────────────

// ═══════════════════════════════════════════════════════════════════════════
// Webhook Polar (Standard Webhooks) — adaptateur SubWhisper Pro + StoryVoice
// ═══════════════════════════════════════════════════════════════════════════
// Pourquoi un ADAPTATEUR et pas un second webhook copié-collé : Polar a son
// propre vocabulaire de statuts. Le reste du gateway (et le dashboard de
// monitoring) raisonne sur `lsStatus` avec le vocabulaire LemonSqueezy, et des
// clés issues de LS vivent encore dans ce KV. On traduit donc ICI, à la
// frontière, et rien en aval ne change.
//
// ⚠️ Le dashboard compte un payant sur `lsStatus === 'active'` STRICT. Écrire
// un statut Polar brut ('trialing', 'canceled') ferait disparaître des abonnés
// des compteurs sans que personne ne s'en aperçoive.
const POLAR_STATUS_TO_INTERNAL = {
  active: 'active',
  trialing: 'on_trial',
  canceled: 'cancelled',
  past_due: 'past_due',
  unpaid: 'unpaid',
  paused: 'paused',
  incomplete: 'unpaid',
  incomplete_expired: 'expired',
};

function polarB64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function polarConstantEquals(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// Standard Webhooks : contenu signé = `${id}.${timestamp}.${body}`, secret en
// base64 derrière `whsec_`, en-tête pouvant porter plusieurs `v1,<sig>`.
async function verifyPolarSignature(body, request, rawSecret) {
  const id = request.headers.get('webhook-id');
  const ts = request.headers.get('webhook-timestamp');
  const header = request.headers.get('webhook-signature');
  if (!id || !ts || !header) return false;

  // Polar horodate le contenu signé (LemonSqueezy ne le faisait pas) : un rejeu
  // tardif est refusé d'emblée, pas seulement détecté après coup.
  const ageS = Math.abs(Date.now() / 1000 - Number(ts));
  if (!Number.isFinite(ageS) || ageS > 300) return false;

  // ⚠️ PIEGE PAYE LE 20/08 : Polar S'ECARTE de la spec Standard Webhooks.
  // La spec signe avec le secret DECODE depuis sa base64 (prefixe `whsec_` retire).
  // Polar signe avec la CHAINE BRUTE, prefixe COMPRIS, en UTF-8. Suivre la spec
  // renvoyait 401 sur CHAQUE livraison reelle — invisible au banc maison, qui
  // forgeait ses signatures avec la meme hypothese que le code : il validait la
  // croyance, pas la realite. Seul un achat reel l'a revele.
  // Les deux derivations sont essayees, pour survivre a un futur alignement.
  const candidates = [
    new TextEncoder().encode(rawSecret),                                                  // Polar (reel)
    polarB64ToBytes(rawSecret.startsWith('whsec_') ? rawSecret.slice(6) : rawSecret),      // spec
  ];
  const received = header.split(' ').map((s) => s.split(',')[1] || '').filter(Boolean);

  for (const material of candidates) {
    let key;
    try {
      key = await crypto.subtle.importKey('raw', material, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    } catch { continue; }
    const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${id}.${ts}.${body}`));
    const expected = btoa(String.fromCharCode(...new Uint8Array(sig)));
    if (received.some((s) => polarConstantEquals(s, expected))) return true;
  }
  return false;
}

// La clé complète n'est jamais dans le webhook (seulement un `display_key`
// masqué). On la lit via l'API avec le jeton rangé dans le KV.
async function fetchPolarLicenseKey(env, licenseKeyId) {
  const token = await env.PRO_KV.get('cfg:polar_api_key');
  if (!token) { console.log('[polar] cfg:polar_api_key absent'); return null; }
  const res = await fetch(`https://api.polar.sh/v1/license-keys/${licenseKeyId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) { console.log(`[polar] license-keys ${res.status}`); return null; }
  const b = await res.json().catch(() => null);
  return b?.key || null;
}

async function handlePolarWebhook(request, env, ctx) {
  const rawBody = await request.text();
  const secret = await env.PRO_KV.get('cfg:polar_webhook_secret');

  // Pas de secret = endpoint ouvert. On refuse : cet endpoint crée des licences.
  if (!secret) return err('webhook not configured (cfg:polar_webhook_secret missing)', 503);
  if (!await verifyPolarSignature(rawBody, request, secret)) return err('Invalid webhook signature', 401);

  const eventId = request.headers.get('webhook-id');
  const replayKey = `wh:polar:${eventId}`;
  if (await env.PRO_KV.get(replayKey)) {
    return json({ ok: true, action: 'ignored', reason: 'event already processed' });
  }
  ctx.waitUntil(env.PRO_KV.put(replayKey, '1', { expirationTtl: 2592000 }));

  let payload;
  try { payload = JSON.parse(rawBody); } catch { return err('Invalid JSON', 400); }

  const type = payload.type;
  const data = payload.data || {};
  const email = String(data.customer?.email || '').toLowerCase();

  // ── StoryVoice : crédits prépayés, achat unique. Le nombre de crédits vient
  // des MÉTADONNÉES du produit — plus de table d'identifiants codée en dur
  // comme l'était `LS_VARIANTS`. Changer un pack ne demandera plus de déploiement.
  if (type === 'order.paid') {
    const meta = data.product?.metadata || {};
    if (meta.app !== 'sv') {
      return json({ ok: true, action: 'ignored', reason: 'order for a non-sv product', app: meta.app || null });
    }
    const credits = Number(meta.credits || 0);
    if (!Number.isFinite(credits) || credits <= 0) {
      return json({ ok: true, action: 'ignored', reason: 'product has no credits metadata' });
    }
    if (!email) return err('No email in webhook payload', 400);

    const emailKey = `email:sv:${email}`;
    let key = await env.PRO_KV.get(emailKey);
    let d = key ? await env.PRO_KV.get(`pro:${key}`, 'json') : null;
    if (!key || !d) {
      key = generateProKey('sv');
      d = { email, app: 'sv', plan: 'prepaid', credits: 0, created: new Date().toISOString(), revoked: false };
      await env.PRO_KV.put(emailKey, key);
    }
    d.credits = Math.max(0, Number(d.credits || 0)) + credits;
    d.lastUsed = new Date().toISOString();
    d.source = 'polar';
    if (d.revoked) d.revoked = false; // un nouvel achat réactive
    await env.PRO_KV.put(`pro:${key}`, JSON.stringify(d));

    let emailQueued = false;
    if (ctx?.waitUntil) { ctx.waitUntil(sendStoryVoiceKeyEmail({ email, key, credits: d.credits, env }).then((r) => recordEmailOutcome(env, key, r))); emailQueued = true; }
    return json({ ok: true, action: 'sv_credited', email, creditsAdded: credits, balance: d.credits, emailQueued });
  }

  // ── SubWhisper Pro : la clé est CELLE DE POLAR (activations limitées,
  // révocation automatique à l'annulation — ce que LemonSqueezy ne faisait pas).
  // `handleActivate` retrouve la clé par email et n'impose aucun format : rien
  // à changer côté client.
  if (type === 'benefit_grant.created') {
    const expectedBenefit = await env.PRO_KV.get('cfg:polar_swp_benefit_id');
    if (!expectedBenefit) return json({ ok: true, action: 'ignored', reason: 'cfg:polar_swp_benefit_id not set' });
    if (String(data.benefit_id || '') !== expectedBenefit) {
      return json({ ok: true, action: 'ignored', reason: 'benefit of another product' });
    }
    if (!email) return err('No email in webhook payload', 400);

    const licenseKeyId = data.properties?.license_key_id;
    if (!licenseKeyId) return json({ ok: true, action: 'ignored', reason: 'no license_key_id' });
    const key = await fetchPolarLicenseKey(env, licenseKeyId);
    if (!key) return err('license key unreadable', 502);

    // 🪤 Un email qui a DÉJÀ une clé n'en reçoit jamais une seconde (doublons
    // Mark 29/05, thomas_olaf 02/06). On réutilise l'enregistrement existant.
    const emailKey = `email:swp:${email}`;
    const previous = (await env.PRO_KV.get(emailKey)) || (await env.PRO_KV.get(`email:${email}`));
    const d = (previous ? await env.PRO_KV.get(`pro:${previous}`, 'json') : null) || {
      email, app: 'swp', created: new Date().toISOString(),
      usage: { transcriptions: 0, translations: 0 }, monthlyUsage: {},
    };
    d.app = 'swp';
    d.plan = d.plan === 'trial' ? 'trial' : (d.plan || 'pro');
    // Meme ordre d'evenements que cote DictoKey PC : `subscription.active` peut
    // arriver avant que la cle existe, donc `lsStatus` resterait vide. Ici
    // `validateProKey` ne s'en sert pas (l'acces ne serait pas coupe), mais le
    // dashboard compte les payants sur `lsStatus === 'active'` STRICT : sans ca,
    // un vrai payant serait invisible dans les compteurs.
    if (!d.lsStatus) d.lsStatus = 'active';
    d.revoked = false;
    d.source = 'polar';
    d.polarLicenseKeyId = licenseKeyId;
    d.subscriptionId = String(data.subscription_id || d.subscriptionId || '');

    await env.PRO_KV.put(emailKey, key);
    await env.PRO_KV.put(`pro:${key}`, JSON.stringify(d));
    if (previous && previous !== key) ctx.waitUntil(env.PRO_KV.delete(`pro:${previous}`));
    if (ctx?.waitUntil) {
      ctx.waitUntil(sendActivationEmail({ email, key, plan: d.plan, trialEndsAt: d.expiresAt || null, app: 'swp', env }).then((r) => recordEmailOutcome(env, key, r)));
    }
    return json({ ok: true, action: 'created_or_reactivated', email, app: 'swp' });
  }

  // ── Suivi d'abonnement : on met à jour l'état, on ne crée jamais de clé ici.
  if (type.startsWith('subscription.')) {
    const app = data.product?.metadata?.app;
    if (app && app !== 'swp') {
      return json({ ok: true, action: 'ignored', reason: 'subscription of another app', app });
    }
    if (!email) return err('No email in webhook payload', 400);

    let key = await env.PRO_KV.get(`email:swp:${email}`);
    if (!key) key = await env.PRO_KV.get(`email:${email}`);
    if (!key) return json({ ok: true, action: 'ignored', reason: 'no key for this email' });
    const d = await env.PRO_KV.get(`pro:${key}`, 'json');
    if (!d) return json({ ok: true, action: 'ignored', reason: 'key without data' });

    const raw = String(data.status || '');
    const internal = POLAR_STATUS_TO_INTERNAL[raw];
    // Un statut que Polar ajouterait demain ne doit pas être écrit tel quel :
    // il ferait mentir les compteurs. On conserve l'ancien et on le signale.
    if (!internal) {
      console.log(`[polar] unknown subscription status "${raw}" — state kept`);
      return json({ ok: true, action: 'ignored', reason: 'unknown status', status: raw });
    }

    d.lsStatus = internal;
    d.source = 'polar';
    d.plan = internal === 'on_trial' ? 'trial' : 'pro';
    if (data.trial_end) d.expiresAt = data.trial_end; else if (internal !== 'on_trial') delete d.expiresAt;
    d.renewsAt = data.current_period_end ?? d.renewsAt ?? null;
    d.endsAt = data.ends_at ?? d.endsAt ?? null;

    // ── Coupure. Deux temps, et il faut les DEUX :
    //  • `subscription.canceled` = « ne se renouvellera pas ». L'accès COURT jusqu'à
    //    la fin de la période déjà payée — on ne révoque pas, on note `endsAt`.
    //  • `subscription.revoked`  = « l'accès est terminé » (Polar l'émet à échéance).
    //    Là on révoque pour de bon.
    // `unpaid` et `incomplete_expired` coupent aussi : plus personne ne paie.
    // ⚠️ L'ancien code LemonSqueezy révoquait dès `cancelled`, ce qui coupait un
    // client encore dans son mois payé. Le comportement retenu est celui décidé le
    // 17/08 pour DictoKey PC (et pour l'Android) : on va au bout du mois payé.
    if (type === 'subscription.revoked' || internal === 'unpaid' || internal === 'expired') {
      d.revoked = true;
    } else if (internal === 'active' || internal === 'on_trial') {
      d.revoked = false;
    }

    await env.PRO_KV.put(`pro:${key}`, JSON.stringify(d));
    return json({ ok: true, action: 'updated', type, status: internal, revoked: !!d.revoked });
  }

  // Révocation explicite (remboursement, litige) — là, on coupe.
  if (type === 'benefit_grant.revoked' || type === 'order.refunded') {
    if (!email) return json({ ok: true, action: 'ignored', reason: 'no email' });
    for (const scope of ['swp', 'sv']) {
      const key = await env.PRO_KV.get(`email:${scope}:${email}`);
      if (!key) continue;
      const d = await env.PRO_KV.get(`pro:${key}`, 'json');
      if (!d) continue;
      d.revoked = true;
      d.lastUsed = new Date().toISOString();
      await env.PRO_KV.put(`pro:${key}`, JSON.stringify(d));
      return json({ ok: true, action: 'revoked', email, app: scope });
    }
    return json({ ok: true, action: 'ignored', reason: 'no key for this email' });
  }

  return json({ ok: true, action: 'ignored', type });
}

async function handleActivate(request, env) {
  const body = await request.json().catch(() => null);
  if (!body?.email) return err('email required', 400);
  const email = body.email.trim().toLowerCase();
  const app = body.app || 'swp';

  // Rate limit: 5 attempts per email per hour
  const rlKey = `rl:activate:${email}:${Math.floor(Date.now() / 3600000)}`;
  const attempts = parseInt(await env.PRO_KV.get(rlKey) || '0');
  if (attempts >= 5) return err('Too many activation attempts. Try again in 1 hour.', 429);
  await env.PRO_KV.put(rlKey, String(attempts + 1), { expirationTtl: 3600 });

  // Look up key by email (try app-scoped first, then legacy)
  let proKey = await env.PRO_KV.get(`email:${app}:${email}`);
  if (!proKey) proKey = await env.PRO_KV.get(`email:${email}`);
  if (!proKey) return err('No subscription found for this email. Please check your email or complete checkout first.', 404);

  // Validate key is active
  const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
  if (!data) return err('Key data missing', 500);
  if (data.revoked) return err('Subscription cancelled or expired. Please renew.', 403);
  if (data.expiresAt && new Date(data.expiresAt) < new Date()) return err('Trial expired. Please subscribe to continue.', 403);

  return json({ ok: true, key: proKey, plan: data.plan, email: data.email });
}

// ─────────────────────────────────────────────────────────────────────────────
// Main handler
// ─────────────────────────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // CORS preflight
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // Health
    if (method === 'GET' && path === '/health') {
      return json({ status: 'ok', version: VERSION, service: 'api-gateway-pro' });
    }

    // ── Visit counter (multi-page: swp, ncf) ─────────────────────────
    if (path === '/api/visit') {
      const page = url.searchParams.get('page') || 'swp';
      const today = new Date().toISOString().slice(0, 10);
      // If page=all, return all counters
      if (page === 'all') {
        const [swpT, ncfT, nfT, dkT, tucT, svT, se7T] = await Promise.all([
          env.PRO_KV.get('stats:visits:swp:total'),
          env.PRO_KV.get('stats:visits:ncf:total'),
          env.PRO_KV.get('stats:visits:nf:total'),
          env.PRO_KV.get('stats:visits:dk:total'),
          env.PRO_KV.get('stats:visits:tuc:total'),
          env.PRO_KV.get('stats:visits:sv:total'),
          env.PRO_KV.get('stats:visits:se7:total'),
        ]);
        return json({ swp: parseInt(swpT) || 0, ncf: parseInt(ncfT) || 0, nf: parseInt(nfT) || 0, dk: parseInt(dkT) || 0, tuc: parseInt(tucT) || 0, sv: parseInt(svT) || 0, se7: parseInt(se7T) || 0 });
      }
      const prefix = `stats:visits:${page}`;
      // v1.15.0 — ventilation par SOURCE. `src` est fourni par le site (?src=tiktok sur le lien
      // épinglé du profil TikTok, débloqué le 03/08 au passage des 1000 abonnés ; sinon domaine
      // du referrer, sinon 'direct'). Sanitisé ICI AUSSI et pas seulement côté client : un
      // paramètre d'URL est saisissable par n'importe qui, il ne doit jamais créer de clé KV
      // arbitraire. Absent ⇒ on n'écrit rien : les pages qui n'envoient pas `src` (dk/swp/nf/sv)
      // gardent exactement le comportement d'avant.
      const srcRaw = (url.searchParams.get('src') || '').toLowerCase();
      const src = srcRaw.replace(/[^a-z0-9.-]/g, '').slice(0, 24);
      const totalRaw = await env.PRO_KV.get(`${prefix}:total`);
      const todayRaw = await env.PRO_KV.get(`${prefix}:${today}`);
      let total = parseInt(totalRaw) || 0;
      let todayCount = parseInt(todayRaw) || 0;
      // Only count real (non-bot) sessions — see isBotUA().
      if (method === 'POST' && !isBotUA(request.headers.get('user-agent') || '')) {
        total++;
        todayCount++;
        const writes = [
          env.PRO_KV.put(`${prefix}:total`, String(total)),
          env.PRO_KV.put(`${prefix}:${today}`, String(todayCount), { expirationTtl: 90 * 86400 }),
        ];
        if (src) {
          const srcKey = `${prefix}:src:${src}:total`;
          const srcRawVal = await env.PRO_KV.get(srcKey);
          writes.push(env.PRO_KV.put(srcKey, String((parseInt(srcRawVal) || 0) + 1)));
        }
        ctx.waitUntil(Promise.all(writes));
      }
      // GET : ventilation complète par source (même procédé que `by_btn_all` de /api/click).
      let by_src = {};
      if (method !== 'POST') {
        try {
          const listed = await env.PRO_KV.list({ prefix: `${prefix}:src:` });
          const vals = await Promise.all(listed.keys.map((k) => env.PRO_KV.get(k.name)));
          listed.keys.forEach((k, i) => {
            const m = k.name.match(/:src:(.+):total$/);
            if (m) by_src[m[1]] = parseInt(vals[i]) || 0;
          });
        } catch (e) { by_src = {}; }
      }
      return json({ page, total, today: todayCount, by_src });
    }

    // ── Click counter (Play Store CTA tracking) ────────────────────────
    if (path === '/api/click') {
      const page = url.searchParams.get('page') || 'dk';
      // v1.16.0 (17/08) — `btn` s'ecrivait BRUT dans une cle KV. C'est un parametre d'URL :
      // n'importe qui pouvait creer `stats:clicks:se7:btn:<ce qu'il veut>:total`, le voir
      // apparaitre dans le dashboard (`by_btn_all` liste tout le prefixe) et faire grossir le KV
      // a volonte. `src` avait deja ete sanitise ici meme pour cette raison exacte (l.921-928) —
      // le meme raisonnement n'avait simplement jamais ete applique a `btn`.
      // Alphabet volontairement large : les cles LEGITIMES portent des ':' (`f:dl_view:win`) et
      // des espaces (`out:SubWhisper Pro`). Toutes passent ce filtre — verifie sur les 14 cles
      // reellement en base le 17/08. Ce qui ne passe pas retombe sur 'unknown' plutot que d'etre
      // tronque en une cle voisine plausible : un compteur faux est pire qu'un compteur nomme.
      const btnRawParam = url.searchParams.get('btn') || 'unknown';
      const btn = /^[A-Za-z0-9 :._-]{1,32}$/.test(btnRawParam) ? btnRawParam : 'unknown';
      const today = new Date().toISOString().slice(0, 10);
      const prefix = `stats:clicks:${page}`;
      if (method === 'POST') {
        const totalRaw = await env.PRO_KV.get(`${prefix}:total`);
        const todayRaw = await env.PRO_KV.get(`${prefix}:${today}`);
        const btnRaw = await env.PRO_KV.get(`${prefix}:btn:${btn}:total`);
        let total = parseInt(totalRaw) || 0;
        let todayCount = parseInt(todayRaw) || 0;
        let btnTotal = parseInt(btnRaw) || 0;
        // Only count real (non-bot) clicks — see isBotUA().
        if (!isBotUA(request.headers.get('user-agent') || '')) {
          total++;
          todayCount++;
          btnTotal++;
          ctx.waitUntil(Promise.all([
            env.PRO_KV.put(`${prefix}:total`, String(total)),
            env.PRO_KV.put(`${prefix}:${today}`, String(todayCount), { expirationTtl: 90 * 86400 }),
            env.PRO_KV.put(`${prefix}:btn:${btn}:total`, String(btnTotal)),
          ]));
        }
        return json({ page, btn, total, today: todayCount });
      }
      // GET: return all click stats
      const [totalRaw, todayRaw, heroRaw, pricingRaw, navRaw, ctaRaw, stickyRaw] = await Promise.all([
        env.PRO_KV.get(`${prefix}:total`),
        env.PRO_KV.get(`${prefix}:${today}`),
        env.PRO_KV.get(`${prefix}:btn:hero:total`),
        env.PRO_KV.get(`${prefix}:btn:pricing:total`),
        env.PRO_KV.get(`${prefix}:btn:nav:total`),
        env.PRO_KV.get(`${prefix}:btn:cta:total`),
        env.PRO_KV.get(`${prefix}:btn:sticky:total`),
      ]);
      // v1.14.0 ADDITIF : ventilation COMPLÈTE par bouton via KV.list (funnel dashboards, ex se7).
      // Les 5 clés fixes ci-dessus sont conservées pour compat. Non bloquant si la list échoue.
      // Le btn peut contenir des ':' (ex 'f:demo', 'out:DictoKey') → on retire le préfixe et le suffixe ':total'.
      const by_btn_all = {};
      try {
        const listPrefix = `${prefix}:btn:`;
        let cursor;
        do {
          const res = await env.PRO_KV.list({ prefix: listPrefix, cursor });
          await Promise.all(res.keys.map(async (k) => {
            const name = k.name.slice(listPrefix.length).replace(/:total$/, '');
            if (name) by_btn_all[name] = parseInt(await env.PRO_KV.get(k.name)) || 0;
          }));
          cursor = res.list_complete ? null : res.cursor;
        } while (cursor);
      } catch (e) { /* non-fatal — by_btn_all reste partiel/vide */ }
      return json({
        page, total: parseInt(totalRaw) || 0, today: parseInt(todayRaw) || 0,
        by_btn: {
          hero: parseInt(heroRaw) || 0,
          pricing: parseInt(pricingRaw) || 0,
          nav: parseInt(navRaw) || 0,
          cta: parseInt(ctaRaw) || 0,
          sticky: parseInt(stickyRaw) || 0,
        },
        by_btn_all,
      });
    }

    // ── LemonSqueezy webhook ─────────────────────────────────────────────

    if (path === '/webhook/lemonsqueezy' && method === 'POST') {
      return handleLemonSqueezyWebhook(request, env, ctx);
    }
    if (path === '/webhook/polar' && method === 'POST') {
      return handlePolarWebhook(request, env, ctx);
    }

    // ── Email activation ──────────────────────────────────────────────────

    if (path === '/api/activate' && method === 'POST') {
      return handleActivate(request, env);
    }

    // ── /config — validates pro key and returns available APIs ────────────

    if (path === '/config') {
      const proKey = request.headers.get('X-Pro-Key') || request.headers.get('Authorization')?.replace('Bearer ', '');
      if (!proKey) return err('X-Pro-Key required', 401);
      const proData = await validateProKey(proKey, env);
      if (!proData) return err('Invalid key', 403);
      // Check which API keys are configured
      const apiNames = ['GEMINI', 'GROQ', 'ASSEMBLYAI', 'DEEPSEEK', 'AZURE'];
      const apis = [];
      for (const name of apiNames) {
        const key = await getApiKey(name + '_KEY', env);
        if (key) apis.push(name);
      }
      const mk = monthKey();
      const monthly = (proData.monthlyUsage && proData.monthlyUsage[mk]) || { transcriptions: 0, translations: 0 };
      const limits = PLAN_LIMITS[proData.plan] || PLAN_LIMITS.pro;
      return json({ apis, plan: proData.plan, monthlyUsage: monthly, limits });
    }

    // ── Admin routes ──────────────────────────────────────────────────────

    if (path.startsWith('/admin/')) {
      if (!checkAdmin(request, env)) return err('Unauthorized', 401);

      // Set API key
      if (path === '/admin/keys/set' && method === 'POST') {
        const body = await request.json();
        if (!body.name || !body.value) return err('name and value required');
        await env.PRO_KV.put(`apikey:${body.name}`, body.value);
        return json({ ok: true, key: body.name });
      }

      // List API keys
      if (path === '/admin/keys/list') {
        const keys = ['GEMINI_KEY', 'GROQ_KEY', 'ASSEMBLYAI_KEY', 'DEEPSEEK_KEY', 'AZURE_KEY'];
        const result = {};
        for (const k of keys) {
          const v = await env.PRO_KV.get(`apikey:${k}`);
          result[k] = v ? '***' + v.slice(-4) : null;
        }
        return json(result);
      }

      // Create pro user
      if (path === '/admin/pro/create' && method === 'POST') {
        const body = await request.json();
        if (!body.email) return err('email required');
        const app = body.app || 'swp';
        const key = generateProKey(app);
        const data = {
          email: body.email,
          app,
          plan: body.plan || 'pro',
          created: new Date().toISOString(),
          usage: { transcriptions: 0, translations: 0 },
          monthlyUsage: {},
          revoked: false,
        };
        // Optional expiration (e.g. for trial keys): body.expiresIn (days) or body.expiresAt (ISO)
        if (body.expiresAt) data.expiresAt = body.expiresAt;
        else if (body.expiresIn) {
          const exp = new Date();
          exp.setDate(exp.getDate() + body.expiresIn);
          data.expiresAt = exp.toISOString();
        }
        await env.PRO_KV.put(`pro:${key}`, JSON.stringify(data));
        await env.PRO_KV.put(`email:${app}:${body.email.toLowerCase()}`, key);
        return json({ ok: true, key, ...data });
      }

      // List pro users
      if (path === '/admin/pro/list') {
        const list = await env.PRO_KV.list({ prefix: 'pro:' });
        const users = [];
        for (const k of list.keys) {
          const data = await env.PRO_KV.get(k.name, 'json');
          users.push({ key: k.name.replace('pro:', ''), ...data });
        }
        return json({ users, count: users.length });
      }

      // Reset/set monthly usage for a pro key (geste commercial, debug)
      if (path === '/admin/pro/reset-usage' && method === 'POST') {
        const body = await request.json();
        if (!body.key) return err('key required');
        const data = await env.PRO_KV.get(`pro:${body.key}`, 'json');
        if (!data) return err('Key not found', 404);
        const mk = body.month || monthKey();
        const transcriptions = Number.isFinite(body.transcriptions) ? body.transcriptions : 0;
        const translations = Number.isFinite(body.translations) ? body.translations : 0;
        data.monthlyUsage = data.monthlyUsage || {};
        const previous = data.monthlyUsage[mk] || { transcriptions: 0, translations: 0 };
        data.monthlyUsage[mk] = { transcriptions, translations };
        await env.PRO_KV.put(`pro:${body.key}`, JSON.stringify(data));
        return json({ ok: true, key: body.key, month: mk, previous, current: data.monthlyUsage[mk] });
      }

      // Revoke pro key
      if (path === '/admin/pro/revoke' && method === 'POST') {
        const body = await request.json();
        if (!body.key) return err('key required');
        const data = await env.PRO_KV.get(`pro:${body.key}`, 'json');
        if (!data) return err('Key not found', 404);
        data.revoked = true;
        await env.PRO_KV.put(`pro:${body.key}`, JSON.stringify(data));
        return json({ ok: true, revoked: body.key });
      }

      // Reconcile lsStatus from LemonSqueezy (backfill + on-demand resync).
      // For each SWP pro key with a numeric subscriptionId, query the LS API and
      // store the real subscription status. Lets the dashboard tell a genuine
      // active payer from a past_due (failed payment) or an orphan key whose
      // subscriptionId isn't a real subscription (e.g. an order_id → 404).
      if (path === '/admin/swp/sync-ls-status' && method === 'POST') {
        const lsToken = await env.PRO_KV.get('cfg:lemonsqueezy_api_key');
        if (!lsToken) return err('cfg:lemonsqueezy_api_key not set in KV', 500);
        const list = await env.PRO_KV.list({ prefix: 'pro:' });
        const results = [];
        for (const k of list.keys) {
          const data = await env.PRO_KV.get(k.name, 'json');
          if (!data) continue;
          const keyName = k.name.replace('pro:', '');
          const isSwp = data.app === 'swp' || (!data.app && keyName.startsWith('swp_'));
          if (!isSwp || data.plan !== 'pro') continue;
          const subId = data.subscriptionId;
          if (!subId || !/^\d+$/.test(String(subId))) {
            results.push({ key: keyName, email: data.email, subscriptionId: subId || null, action: 'skipped_no_numeric_sub', lsStatus: data.lsStatus || null });
            continue;
          }
          let lsStatus = null, http = null;
          try {
            const res = await fetch(`https://api.lemonsqueezy.com/v1/subscriptions/${subId}`, {
              headers: { 'Authorization': `Bearer ${lsToken}`, 'Accept': 'application/vnd.api+json' },
            });
            http = res.status;
            if (res.status === 404) {
              lsStatus = 'not_found'; // subscriptionId is not a real LS subscription (orphan / order_id)
            } else if (res.ok) {
              const b = await res.json().catch(() => ({}));
              lsStatus = (b && b.data && b.data.attributes && b.data.attributes.status) || 'unknown';
            } else {
              results.push({ key: keyName, email: data.email, subscriptionId: subId, action: 'ls_http_error', http });
              continue;
            }
          } catch (e) {
            results.push({ key: keyName, email: data.email, subscriptionId: subId, action: 'exception', error: e.message });
            continue;
          }
          const previous = data.lsStatus || null;
          data.lsStatus = lsStatus;
          data.lsStatusCheckedAt = new Date().toISOString();
          await env.PRO_KV.put(k.name, JSON.stringify(data));
          results.push({ key: keyName, email: data.email, subscriptionId: subId, previous, lsStatus, http });
        }
        return json({ ok: true, checked: results.length, results });
      }

      // Test activation email delivery — bypasses LS webhook signature, calls
      // sendActivationEmail directly so we can validate the real subscription_created
      // path end-to-end without creating a real LS sub. Admin only.
      if (path === '/admin/test-activation-email' && method === 'POST') {
        const body = await request.json();
        if (!body.email) return err('email required');
        const result = await sendActivationEmail({
          email: body.email,
          key: body.key || 'swp_TEST_ADMIN_DELIVERY_KEY',
          plan: body.plan || 'trial',
          trialEndsAt: body.trialEndsAt || new Date(Date.now() + 14 * 24 * 3600 * 1000).toISOString(),
          app: body.app || 'swp',
          env,
        });
        return json({ ok: true, result });
      }

      // SWP-only overview (monitoring dashboard)
      if (path === '/admin/swp/overview' && method === 'GET') {
        const list = await env.PRO_KV.list({ prefix: 'pro:' });
        const mk = monthKey();
        const today = new Date().toISOString().slice(0, 10);
        let total = 0, trial = 0, pro = 0, revoked = 0;
        // v1.5.5 — usage_this_month now counts ALL keys (revoked included) so the real
        // monthly API consumption / cost is visible even after a key is revoked (abuse, churn).
        // usage_this_month_active keeps the non-revoked-only view for "current active load".
        let mTranscriptions = 0, mTranslations = 0;
        let mTranscriptionsActive = 0, mTranslationsActive = 0;
        const customers = [];
        for (const k of list.keys) {
          const data = await env.PRO_KV.get(k.name, 'json');
          if (!data) continue;
          const keyName = k.name.replace('pro:', '');
          const isSwp = data.app === 'swp' || (!data.app && keyName.startsWith('swp_'));
          if (!isSwp) continue;
          total++;
          if (data.revoked) revoked++;
          else if (data.plan === 'trial') trial++;
          else if (data.plan === 'pro') pro++;
          const monthly = (data.monthlyUsage && data.monthlyUsage[mk]) || { transcriptions: 0, translations: 0 };
          mTranscriptions += monthly.transcriptions || 0;
          mTranslations += monthly.translations || 0;
          if (!data.revoked) {
            mTranscriptionsActive += monthly.transcriptions || 0;
            mTranslationsActive += monthly.translations || 0;
          }
          customers.push({
            key: keyName,
            email: data.email,
            plan: data.plan,
            revoked: !!data.revoked,
            created: data.created || null,
            expiresAt: data.expiresAt || null,
            lastUsed: data.lastUsed || null,
            subscriptionId: data.subscriptionId || null,
            lsStatus: data.lsStatus || null, // v1.6.0 — real LS status for honest payer/MRR classification
            lsStatusCheckedAt: data.lsStatusCheckedAt || null,
            usageMonth: monthly,
            usageTotal: data.usage || { transcriptions: 0, translations: 0 },
          });
        }
        customers.sort((a, b) => {
          const ka = a.lastUsed || a.created || '';
          const kb = b.lastUsed || b.created || '';
          return kb.localeCompare(ka);
        });
        const [visitsTotalRaw, visitsTodayRaw] = await Promise.all([
          env.PRO_KV.get('stats:visits:swp:total'),
          env.PRO_KV.get(`stats:visits:swp:${today}`),
        ]);
        return json({
          generatedAt: new Date().toISOString(),
          month: mk,
          customers: { total, trial, pro, revoked },
          usage_this_month: { transcriptions: mTranscriptions, translations: mTranslations },
          usage_this_month_active: { transcriptions: mTranscriptionsActive, translations: mTranslationsActive },
          limits_per_plan: PLAN_LIMITS,
          site_visits: {
            total: parseInt(visitsTotalRaw) || 0,
            today: parseInt(visitsTodayRaw) || 0,
          },
          customers_list: customers,
        });
      }

      // StoryVoice-only overview (monitoring dashboard) — read-only, isolé des clés SWP/NF.
      // v1.12.0 : crédits prépayés (1 crédit = 1 caractère TTS). granted = remaining + used.
      if (path === '/admin/sv/overview' && method === 'GET') {
        const list = await env.PRO_KV.list({ prefix: 'pro:' });
        const today = new Date().toISOString().slice(0, 10);
        // Tarifs packs LemonSqueezy (desc) — pour estimer le revenu à partir des crédits accordés
        const PACKS = [
          { credits: 3000000, eur: 64.90 },
          { credits: 1000000, eur: 24.90 },
          { credits: 300000, eur: 7.90 },
        ];
        let totalCust = 0, active = 0, revoked = 0;
        let creditsRemaining = 0, creditsUsed = 0, revenueEst = 0;
        const customers = [];
        for (const k of list.keys) {
          const data = await env.PRO_KV.get(k.name, 'json');
          if (!data) continue;
          const keyName = k.name.replace('pro:', '');
          const isSv = data.app === 'sv' || (!data.app && keyName.startsWith('sv_'));
          if (!isSv) continue;
          totalCust++;
          if (data.revoked) revoked++; else active++;
          const rem = Math.max(0, Number(data.credits || 0));
          const used = Math.max(0, Number(data.ttsCharsUsed || 0));
          const granted = rem + used;
          creditsRemaining += rem; creditsUsed += used;
          // Estimation revenu : décompose les crédits accordés en packs (greedy desc)
          let g = granted, eur = 0;
          for (const p of PACKS) { while (g >= p.credits) { g -= p.credits; eur += p.eur; } }
          if (g > 0) eur += (g / PACKS[PACKS.length - 1].credits) * PACKS[PACKS.length - 1].eur;
          revenueEst += eur;
          customers.push({
            key: keyName, email: data.email || null, plan: data.plan || 'prepaid',
            revoked: !!data.revoked, created: data.created || null, lastUsed: data.lastUsed || null,
            creditsRemaining: rem, creditsUsed: used, creditsGranted: granted,
          });
        }
        customers.sort((a, b) => String(b.lastUsed || b.created || '').localeCompare(String(a.lastUsed || a.created || '')));
        const [visTotalRaw, visTodayRaw] = await Promise.all([
          env.PRO_KV.get('stats:visits:sv:total'),
          env.PRO_KV.get(`stats:visits:sv:${today}`),
        ]);
        const visits = parseInt(visTotalRaw) || 0;
        return json({
          generatedAt: new Date().toISOString(),
          customers: { total: totalCust, active, revoked },
          credits: { remaining: creditsRemaining, used: creditsUsed, granted: creditsRemaining + creditsUsed },
          hours_listened: Math.round((creditsUsed / 90000) * 10) / 10,
          revenue_eur_est: Math.round(revenueEst * 100) / 100,
          site_visits: { total: visits, today: parseInt(visTodayRaw) || 0 },
          conversion_pct: visits > 0 ? Math.round((totalCust / visits) * 1000) / 10 : null,
          customers_list: customers,
        });
      }

      // List newsletter subscribers
      if (path === '/admin/subscribers' && method === 'GET') {
        const list = await env.PRO_KV.list({ prefix: 'subscriber:' });
        const subs = [];
        for (const key of list.keys) {
          const val = await env.PRO_KV.get(key.name, 'json');
          if (val) subs.push(val);
        }
        const count = await env.PRO_KV.get('subscribers:count');
        return json({ count: parseInt(count) || subs.length, subscribers: subs });
      }

      return err('Unknown admin route', 404);
    }

    // ── Pro API routes (require pro key) ──────────────────────────────────

    if (path.startsWith('/api/')) {
      // Extract pro key from header
      const proKey = request.headers.get('X-Pro-Key') || request.headers.get('Authorization')?.replace('Bearer ', '');

      // Verify endpoint (no key needed — used to check key validity)
      if (path === '/api/verify') {
        if (!proKey) return err('X-Pro-Key header required', 401);
        const data = await validateProKey(proKey, env);
        if (!data) return err('Invalid, expired, or revoked key', 403);
        const mk = monthKey();
        const monthly = (data.monthlyUsage && data.monthlyUsage[mk]) || { transcriptions: 0, translations: 0 };
        const limits = PLAN_LIMITS[data.plan] || PLAN_LIMITS.pro;
        return json({ valid: true, plan: data.plan, email: data.email, usage: data.usage, monthlyUsage: monthly, limits, credits: data.credits, expiresAt: data.expiresAt || null });
      }

      // ── Newsletter subscribe (no pro key needed) ───────────────────────
      if (path === '/api/subscribe' && method === 'POST') {
        return handleSubscribe(request, env);
      }

      // All other API routes require valid pro key
      if (!proKey) return err('X-Pro-Key header required', 401);
      const proData = await validateProKey(proKey, env);
      if (!proData) return err('Invalid, expired, or revoked pro key', 403);

      // ── StoryVoice (sv_ keys): fully isolated prepaid-credits path. Returns BEFORE
      // any SubWhisper usage logic runs (checkUsageLimit / PLAN_LIMITS / incrementUsage). ──
      if (proKey.startsWith('sv_')) {
        return handleStoryVoice(request, env, ctx, path, proKey, proData);
      }

      // Rate limit check
      if (!await checkRateLimit(proKey, env)) {
        return err('Rate limit exceeded. Max 10 requests/minute.', 429);
      }

      // Determine usage type for this route
      const usageType = (path === '/api/groq' || path === '/api/assemblyai' || path.startsWith('/api/assemblyai/'))
        ? 'transcription' : 'translation';

      // Check monthly usage limit
      const limitCheck = checkUsageLimit(proData, usageType);
      if (limitCheck.blocked) {
        return json({ error: limitCheck.reason, usage: limitCheck.usage, limits: limitCheck.limits }, 429);
      }

      // Gemini proxy
      if (path.startsWith('/api/gemini')) {
        ctx.waitUntil(incrementUsage(proKey, 'translation', env, ctx));
        const apiPath = request.headers.get('X-Api-Path');
        return proxyGemini(request, env, apiPath);
      }

      // Groq proxy
      if (path === '/api/groq') {
        ctx.waitUntil(incrementUsage(proKey, 'transcription', env, ctx));
        return proxyGroq(request, env);
      }

      // AssemblyAI proxy
      if (path === '/api/assemblyai' || path.startsWith('/api/assemblyai/')) {
        ctx.waitUntil(incrementUsage(proKey, 'transcription', env, ctx));
        return proxyAssemblyAI(request, env);
      }

      // DeepSeek proxy
      if (path === '/api/deepseek') {
        ctx.waitUntil(incrementUsage(proKey, 'translation', env, ctx));
        return proxyDeepSeek(request, env);
      }

      // Azure Translator proxy
      if (path === '/api/azure') {
        ctx.waitUntil(incrementUsage(proKey, 'translation', env, ctx));
        return proxyAzure(request, env, url);
      }

      return err('Unknown API route', 404);
    }

    return err('Not found', 404);
  },
};
