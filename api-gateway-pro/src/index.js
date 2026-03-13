/**
 * api-gateway-pro — Cloudflare Worker v1.0.0
 * Isolated gateway for SubWhisper Pro (paid users)
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
 *   POST /admin/keys/set    → Set API keys in KV
 *   POST /admin/keys/list   → List API keys
 *   POST /admin/pro/create  → Create a pro user key
 *   POST /admin/pro/list    → List pro users
 *   POST /admin/pro/revoke  → Revoke a pro key
 *   GET  /health            → Health check
 */

const VERSION = '1.0.0';

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
  return data;
}

async function incrementUsage(proKey, type, env, ctx) {
  const data = await env.PRO_KV.get(`pro:${proKey}`, 'json');
  if (!data) return;
  if (!data.usage) data.usage = { transcriptions: 0, translations: 0 };
  if (type === 'transcription') data.usage.transcriptions++;
  if (type === 'translation') data.usage.translations++;
  data.lastUsed = new Date().toISOString();
  ctx.waitUntil(env.PRO_KV.put(`pro:${proKey}`, JSON.stringify(data)));
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

function generateProKey() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  let key = 'swp_';
  for (let i = 0; i < 24; i++) key += chars[Math.floor(Math.random() * chars.length)];
  return key;
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
      return json({ apis, plan: proData.plan });
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
        const key = generateProKey();
        const data = {
          email: body.email,
          plan: body.plan || 'pro',
          created: new Date().toISOString(),
          usage: { transcriptions: 0, translations: 0 },
          revoked: false,
        };
        await env.PRO_KV.put(`pro:${key}`, JSON.stringify(data));
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
        if (!data) return err('Invalid or revoked key', 403);
        return json({ valid: true, plan: data.plan, email: data.email, usage: data.usage });
      }

      // All other API routes require valid pro key
      if (!proKey) return err('X-Pro-Key header required', 401);
      const proData = await validateProKey(proKey, env);
      if (!proData) return err('Invalid or revoked pro key', 403);

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
