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

const VERSION = '1.4.0';

// ── Plan limits (per calendar month) ────────────────────────────────────────
const PLAN_LIMITS = {
  pro:   { transcriptions: 50, translations: 500 },
  trial: { transcriptions: 10, translations: 100 },
};
const RATE_LIMIT_PER_MIN = 10;

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
// Proxy helpers
// ─────────────────────────────────────────────────────────────────────────────

async function proxyGemini(request, env, apiPath) {
  const key = await getApiKey('GEMINI_KEY', env);
  if (!key) return err('Gemini API key not configured', 503);
  const path = apiPath || request.headers.get('X-Api-Path') || '/v1beta/models/gemini-2.0-flash:generateContent';
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
  const apiPath = request.headers.get('X-Api-Path') || '/v2/transcript';
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
// Admin helpers
// ─────────────────────────────────────────────────────────────────────────────

function checkAdmin(request, env) {
  const auth = request.headers.get('Authorization') || '';
  const token = auth.replace('Bearer ', '');
  if (!token || token !== env.ADMIN_TOKEN) return false;
  return true;
}

function generateProKey(app = 'swp') {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  const prefix = app === 'nf' ? 'nf_' : 'swp_';
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
  return hex === signature;
}

// ─────────────────────────────────────────────────────────────────────────────
// LemonSqueezy webhook handler
// ─────────────────────────────────────────────────────────────────────────────

async function handleLemonSqueezyWebhook(request, env) {
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

  // subscription_created or order_created → create pro key
  if (event === 'subscription_created' || event === 'order_created') {
    const status = attrs.status; // 'active', 'on_trial', 'cancelled', etc.
    const plan = (status === 'on_trial') ? 'trial' : 'pro';
    const trialEndsAt = attrs.trial_ends_at || null;

    // Check if email already has a key (app-scoped first, then legacy)
    let existingKey = await env.PRO_KV.get(`email:${app}:${email.toLowerCase()}`);
    if (!existingKey) existingKey = await env.PRO_KV.get(`email:${email.toLowerCase()}`);
    if (existingKey) {
      // Reactivate if revoked
      const existingData = await env.PRO_KV.get(`pro:${existingKey}`, 'json');
      if (existingData && existingData.revoked) {
        existingData.revoked = false;
        existingData.plan = plan;
        existingData.subscriptionId = subscriptionId;
        if (trialEndsAt) existingData.expiresAt = trialEndsAt;
        else delete existingData.expiresAt;
        await env.PRO_KV.put(`pro:${existingKey}`, JSON.stringify(existingData));
      }
      return json({ ok: true, action: 'reactivated', email });
    }

    // Detect app from product (custom_data or variant name)
    const customData = payload.meta?.custom_data || {};
    const app = customData.app || 'swp';

    // Create new pro key
    const key = generateProKey(app);
    const data = {
      email: email.toLowerCase(),
      plan,
      app,
      created: new Date().toISOString(),
      subscriptionId,
      usage: { transcriptions: 0, translations: 0 },
      monthlyUsage: {},
      revoked: false,
    };
    if (trialEndsAt) data.expiresAt = trialEndsAt;

    await env.PRO_KV.put(`pro:${key}`, JSON.stringify(data));
    await env.PRO_KV.put(`email:${app}:${email.toLowerCase()}`, key);

    return json({ ok: true, action: 'created', email, plan });
  }

  // subscription_updated → update plan/status
  if (event === 'subscription_updated') {
    const proKey = await env.PRO_KV.get(`email:${email.toLowerCase()}`);
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
    data.subscriptionId = subscriptionId;
    await env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data));
    return json({ ok: true, action: 'updated', email, status });
  }

  // subscription_cancelled / subscription_expired → revoke
  if (event === 'subscription_cancelled' || event === 'subscription_expired') {
    const proKey = await env.PRO_KV.get(`email:${email.toLowerCase()}`);
    if (!proKey) return json({ ok: true, action: 'ignored' });
    const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
    if (data) {
      data.revoked = true;
      await env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data));
    }
    return json({ ok: true, action: 'revoked', email });
  }

  return json({ ok: true, action: 'ignored', event });
}

// ─────────────────────────────────────────────────────────────────────────────
// Email activation (customer enters email → gets their key)
// ─────────────────────────────────────────────────────────────────────────────

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
        const [swpT, ncfT, nfT, dkT] = await Promise.all([
          env.PRO_KV.get('stats:visits:swp:total'),
          env.PRO_KV.get('stats:visits:ncf:total'),
          env.PRO_KV.get('stats:visits:nf:total'),
          env.PRO_KV.get('stats:visits:dk:total'),
        ]);
        return json({ swp: parseInt(swpT) || 0, ncf: parseInt(ncfT) || 0, nf: parseInt(nfT) || 0, dk: parseInt(dkT) || 0 });
      }
      const prefix = `stats:visits:${page}`;
      const totalRaw = await env.PRO_KV.get(`${prefix}:total`);
      const todayRaw = await env.PRO_KV.get(`${prefix}:${today}`);
      let total = parseInt(totalRaw) || 0;
      let todayCount = parseInt(todayRaw) || 0;
      if (method === 'POST') {
        total++;
        todayCount++;
        ctx.waitUntil(Promise.all([
          env.PRO_KV.put(`${prefix}:total`, String(total)),
          env.PRO_KV.put(`${prefix}:${today}`, String(todayCount), { expirationTtl: 90 * 86400 }),
        ]));
      }
      return json({ page, total, today: todayCount });
    }

    // ── LemonSqueezy webhook ─────────────────────────────────────────────

    if (path === '/webhook/lemonsqueezy' && method === 'POST') {
      return handleLemonSqueezyWebhook(request, env);
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
        return json({ valid: true, plan: data.plan, email: data.email, usage: data.usage, monthlyUsage: monthly, limits, expiresAt: data.expiresAt || null });
      }

      // ── Newsletter subscribe (no pro key needed) ───────────────────────
      if (path === '/api/subscribe' && method === 'POST') {
        return handleSubscribe(request, env);
      }

      // All other API routes require valid pro key
      if (!proKey) return err('X-Pro-Key header required', 401);
      const proData = await validateProKey(proKey, env);
      if (!proData) return err('Invalid, expired, or revoked pro key', 403);

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
