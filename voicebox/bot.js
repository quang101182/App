// VoiceBox Bot v0.4.0 — Telegram voice transcription + translation + summary + payments

const express = require('express');
const crypto = require('crypto');
const { upsertUser, checkQuota, incrementUsage, logUsage, getUser, setLang, getLang, setPlan, getStats } = require('./db');

const VERSION = '0.4.0';
const LEMON_WEBHOOK_SECRET = process.env.LEMON_WEBHOOK_SECRET;
const LEMON_CHECKOUT_URL = process.env.LEMON_CHECKOUT_URL || '';
const BOT_TOKEN = process.env.BOT_TOKEN;
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;
const GATEWAY_URL = process.env.GATEWAY_URL;
const GATEWAY_KEY = process.env.GATEWAY_KEY;
const PORT = process.env.PORT || 3000;

const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;
const TELEGRAM_FILE = `https://api.telegram.org/file/bot${BOT_TOKEN}`;

// Admin IDs for /stats command
const ADMIN_IDS = new Set(
  (process.env.ADMIN_IDS || '').split(',').map(s => parseInt(s.trim())).filter(Boolean)
);

// Rate limit: Map<userId, lastRequestTimestamp>
const rateLimitMap = new Map();

// Circuit breaker for Groq API
const groqCircuit = { failures: 0, openedAt: null, THRESHOLD: 5, TIMEOUT_MS: 60000 };

// ---------------------------------------------------------------------------
// Multilingual strings FR/EN
// ---------------------------------------------------------------------------

const STRINGS = {
  FR: {
    start: (v) =>
      `\u{1F399} VoiceBox v${v}\n\n` +
      `Envoyez-moi un message vocal et je le transcris instantanement !\n\n` +
      `Plan gratuit : 5 vocaux/jour, max 5 min\n` +
      `Plan Pro (3€/mois) : illimite, traduction, resume\n\n` +
      `/plan — voir mon plan\n` +
      `/lang XX — langue de traduction (Pro)\n` +
      `/pro — passer en Pro\n` +
      `/help — aide`,
    plan: (planName, dailyCount, limit) =>
      `Votre plan : ${planName}\nAujourd'hui : ${dailyCount} / ${limit} vocaux`,
    plan_pro: 'Pro',
    plan_free: 'Gratuit',
    plan_unlimited: 'illimite',
    already_pro: 'Vous etes deja en plan Pro ! Profitez de la traduction et du resume.',
    pro_coming: 'Le plan Pro arrive bientot ! Restez connecte.',
    pro_cta: (url) =>
      `Plan Pro — 3€/mois\n\nTraduction + resume IA illimites\nVocaux jusqu'a 60 min\nSans limite quotidienne\n\nS'abonner : ${url}`,
    help:
      `Comment utiliser VoiceBox :\n\n` +
      `1. Envoyez un message vocal\n` +
      `2. Recevez la transcription en quelques secondes\n\n` +
      `Limites plan gratuit :\n` +
      `- 5 vocaux par jour\n` +
      `- Duree max : 5 minutes\n\n` +
      `Features Pro :\n` +
      `- Traduction automatique (/lang fr)\n` +
      `- Resume IA en bullet points\n` +
      `- Illimite, vocaux jusqu'a 60 min\n\n` +
      `Commandes :\n` +
      `/start — message d'accueil\n` +
      `/plan — voir mon plan actuel\n` +
      `/lang XX — langue de traduction (ex: /lang fr)\n` +
      `/lang off — desactiver la traduction\n` +
      `/pro — passer au plan Pro\n` +
      `/help — cette aide`,
    lang_not_pro: 'La traduction est une feature Pro. Tapez /pro pour en savoir plus.',
    lang_current: (lang) => `Langue de traduction : ${lang}\nTapez /lang off pour desactiver.`,
    lang_none: `Aucune langue de traduction definie.\nTapez /lang fr (ou en, es, de, ja, ko, zh, etc.)`,
    lang_off: 'Traduction desactivee.',
    lang_set: (lang) => `Langue de traduction : ${lang}`,
    quota_reached: (count, limit) =>
      `Quota atteint (${count}/${limit} aujourd'hui). Reessayez demain ou passez en /pro !`,
    duration_limit: (dur, maxMin) =>
      `Ce vocal dure ${dur}s — la limite de votre plan est ${maxMin} min. Passez en /pro pour des vocaux plus longs !`,
    rate_limit: (wait) => `Patientez ${wait}s entre chaque vocal.`,
    empty_transcript: "Aucun texte detecte dans ce vocal. Reessayez avec un audio plus clair.",
    translation_label: (lang) => `--- Traduction (${lang}) ---`,
    summary_label: '--- Resume ---',
    gemini_unavailable: '(Traduction/resume indisponible)',
    transcription_error: 'Erreur de transcription, reessayez.',
    circuit_open: 'Le service de transcription est temporairement indisponible. Reessayez dans 1 minute.',
    stats: (total, pro, today, all) =>
      `Stats VoiceBox v${VERSION}\n\n` +
      `Utilisateurs : ${total} (dont ${pro} Pro)\n` +
      `Transcriptions aujourd'hui : ${today}\n` +
      `Transcriptions total : ${all}`,
  },
  EN: {
    start: (v) =>
      `\u{1F399} VoiceBox v${v}\n\n` +
      `Send me a voice message and I'll transcribe it instantly!\n\n` +
      `Free plan: 5 voices/day, max 5 min\n` +
      `Pro plan (€3/mo): unlimited, translation, summary\n\n` +
      `/plan — view my plan\n` +
      `/lang XX — translation language (Pro)\n` +
      `/pro — upgrade to Pro\n` +
      `/help — help`,
    plan: (planName, dailyCount, limit) =>
      `Your plan: ${planName}\nToday: ${dailyCount} / ${limit} voices`,
    plan_pro: 'Pro',
    plan_free: 'Free',
    plan_unlimited: 'unlimited',
    already_pro: 'You are already on the Pro plan! Enjoy translation and AI summary.',
    pro_coming: 'The Pro plan is coming soon! Stay tuned.',
    pro_cta: (url) =>
      `Pro Plan — €3/mo\n\nUnlimited translation + AI summary\nVoices up to 60 min\nNo daily limit\n\nSubscribe: ${url}`,
    help:
      `How to use VoiceBox:\n\n` +
      `1. Send a voice message\n` +
      `2. Get the transcription in seconds\n\n` +
      `Free plan limits:\n` +
      `- 5 voices per day\n` +
      `- Max duration: 5 minutes\n\n` +
      `Pro features:\n` +
      `- Auto translation (/lang fr)\n` +
      `- AI summary in bullet points\n` +
      `- Unlimited, voices up to 60 min\n\n` +
      `Commands:\n` +
      `/start — welcome message\n` +
      `/plan — view my current plan\n` +
      `/lang XX — translation language (e.g. /lang fr)\n` +
      `/lang off — disable translation\n` +
      `/pro — upgrade to Pro\n` +
      `/help — this help`,
    lang_not_pro: 'Translation is a Pro feature. Type /pro to learn more.',
    lang_current: (lang) => `Translation language: ${lang}\nType /lang off to disable.`,
    lang_none: `No translation language set.\nType /lang fr (or en, es, de, ja, ko, zh, etc.)`,
    lang_off: 'Translation disabled.',
    lang_set: (lang) => `Translation language: ${lang}`,
    quota_reached: (count, limit) =>
      `Quota reached (${count}/${limit} today). Try again tomorrow or upgrade to /pro!`,
    duration_limit: (dur, maxMin) =>
      `This voice is ${dur}s — your plan limit is ${maxMin} min. Upgrade to /pro for longer voices!`,
    rate_limit: (wait) => `Please wait ${wait}s between each voice.`,
    empty_transcript: "No text detected in this voice. Try again with clearer audio.",
    translation_label: (lang) => `--- Translation (${lang}) ---`,
    summary_label: '--- Summary ---',
    gemini_unavailable: '(Translation/summary unavailable)',
    transcription_error: 'Transcription error, please try again.',
    circuit_open: 'Transcription service is temporarily unavailable. Try again in 1 minute.',
    stats: (total, pro, today, all) =>
      `VoiceBox Stats v${VERSION}\n\n` +
      `Users: ${total} (${pro} Pro)\n` +
      `Transcriptions today: ${today}\n` +
      `Total transcriptions: ${all}`,
  },
};

/**
 * Get translated string. langCode starting with "fr" → FR, else EN.
 * If value is a function, call it with extra args.
 */
function t(langCode, key, ...args) {
  const lang = (langCode || '').toLowerCase().startsWith('fr') ? 'FR' : 'EN';
  const val = STRINGS[lang][key] ?? STRINGS.EN[key] ?? key;
  return typeof val === 'function' ? val(...args) : val;
}

// ---------------------------------------------------------------------------
// Telegram helpers
// ---------------------------------------------------------------------------

async function sendMessage(chatId, text) {
  const res = await fetch(`${TELEGRAM_API}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error(`[sendMessage] Telegram error: ${res.status} ${err}`);
  }
  return res;
}

async function getFile(fileId) {
  const res = await fetch(`${TELEGRAM_API}/getFile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId }),
  });
  if (!res.ok) {
    throw new Error(`getFile failed: ${res.status}`);
  }
  const data = await res.json();
  if (!data.ok) {
    throw new Error(`getFile API error: ${JSON.stringify(data)}`);
  }
  return data.result.file_path;
}

async function downloadFile(filePath) {
  const res = await fetch(`${TELEGRAM_FILE}/${filePath}`);
  if (!res.ok) {
    throw new Error(`downloadFile failed: ${res.status}`);
  }
  return Buffer.from(await res.arrayBuffer());
}

// ---------------------------------------------------------------------------
// Circuit breaker helpers
// ---------------------------------------------------------------------------

function circuitAllowed() {
  if (groqCircuit.failures < groqCircuit.THRESHOLD) return true;
  // Circuit is open — check if timeout has elapsed
  if (groqCircuit.openedAt && Date.now() - groqCircuit.openedAt >= groqCircuit.TIMEOUT_MS) {
    // Half-open: allow one attempt
    groqCircuit.failures = 0;
    groqCircuit.openedAt = null;
    return true;
  }
  return false;
}

function circuitOnSuccess() {
  groqCircuit.failures = 0;
  groqCircuit.openedAt = null;
}

function circuitOnFailure() {
  groqCircuit.failures++;
  if (groqCircuit.failures >= groqCircuit.THRESHOLD && !groqCircuit.openedAt) {
    groqCircuit.openedAt = Date.now();
    console.warn(`[circuit] Groq circuit OPEN after ${groqCircuit.failures} failures`);
  }
}

// ---------------------------------------------------------------------------
// Voice transcription via gateway
// ---------------------------------------------------------------------------

async function transcribe(audioBuffer) {
  if (!circuitAllowed()) {
    throw new Error('CIRCUIT_OPEN');
  }

  const form = new FormData();
  form.append('file', new Blob([audioBuffer], { type: 'audio/ogg' }), 'voice.ogg');
  form.append('model', 'whisper-large-v3-turbo');

  let res;
  try {
    res = await fetch(`${GATEWAY_URL}/api/groq`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${GATEWAY_KEY}`,
        'X-Api-Path': '/openai/v1/audio/transcriptions',
      },
      body: form,
    });
  } catch (fetchErr) {
    circuitOnFailure();
    throw fetchErr;
  }

  if (!res.ok) {
    const errText = await res.text();
    circuitOnFailure();
    throw new Error(`Gateway transcription failed: ${res.status} — ${errText}`);
  }

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    circuitOnFailure();
    throw new Error(`Gateway returned non-JSON: ${raw.slice(0, 200)}`);
  }

  circuitOnSuccess();
  return data.text || data.transcript || '';
}

// ---------------------------------------------------------------------------
// Gemini AI via gateway (translation + summary)
// ---------------------------------------------------------------------------

async function callGemini(prompt) {
  const res = await fetch(`${GATEWAY_URL}/api/gemini/v1beta/models/gemini-2.0-flash:generateContent`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${GATEWAY_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini failed: ${res.status} — ${errText}`);
  }

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Gemini non-JSON: ${raw.slice(0, 200)}`);
  }

  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
  return text.trim();
}

async function translateText(text, targetLang) {
  const prompt = `Translate the following text to ${targetLang}. Return ONLY the translation, nothing else.\n\n${text}`;
  return callGemini(prompt);
}

async function summarizeText(text) {
  const prompt = `Summarize the following transcription in 2-3 concise bullet points. Use the same language as the text. Return ONLY the bullet points.\n\n${text}`;
  return callGemini(prompt);
}

// ---------------------------------------------------------------------------
// Rate limiting
// ---------------------------------------------------------------------------

function checkRateLimit(userId, isPro) {
  const cooldown = isPro ? 5000 : 10000; // ms
  const last = rateLimitMap.get(userId);
  if (last && Date.now() - last < cooldown) {
    return false; // too fast
  }
  rateLimitMap.set(userId, Date.now());
  return true;
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

function handleStart(chatId, langCode) {
  return sendMessage(chatId, t(langCode, 'start', VERSION));
}

function handlePlan(chatId, userId, langCode) {
  const quota = checkQuota(userId);
  const planName = quota.plan === 'pro' ? t(langCode, 'plan_pro') : t(langCode, 'plan_free');
  const limit = quota.plan === 'pro' ? t(langCode, 'plan_unlimited') : String(quota.limit);
  return sendMessage(chatId, t(langCode, 'plan', planName, quota.dailyCount, limit));
}

function handlePro(chatId, userId, langCode) {
  const user = getUser(userId);
  if (user && user.plan === 'pro') {
    return sendMessage(chatId, t(langCode, 'already_pro'));
  }
  if (!LEMON_CHECKOUT_URL) {
    return sendMessage(chatId, t(langCode, 'pro_coming'));
  }
  const url = `${LEMON_CHECKOUT_URL}?checkout[custom][telegram_id]=${userId}`;
  return sendMessage(chatId, t(langCode, 'pro_cta', url));
}

function handleHelp(chatId, langCode) {
  return sendMessage(chatId, t(langCode, 'help'));
}

function handleLang(chatId, userId, args, langCode) {
  const user = getUser(userId);
  if (!user || user.plan !== 'pro') {
    return sendMessage(chatId, t(langCode, 'lang_not_pro'));
  }

  const lang = (args || '').trim().toLowerCase();
  if (!lang) {
    const current = getLang(userId);
    return sendMessage(chatId, current
      ? t(langCode, 'lang_current', current)
      : t(langCode, 'lang_none'));
  }

  if (lang === 'off' || lang === 'none') {
    setLang(userId, '');
    return sendMessage(chatId, t(langCode, 'lang_off'));
  }

  setLang(userId, lang);
  return sendMessage(chatId, t(langCode, 'lang_set', lang));
}

function handleStats(chatId, userId) {
  if (!ADMIN_IDS.has(userId)) return; // silent ignore
  const s = getStats();
  return sendMessage(chatId, t('fr', 'stats', s.totalUsers, s.proUsers, s.todayTranscriptions, s.totalTranscriptions));
}

// ---------------------------------------------------------------------------
// Voice message handler
// ---------------------------------------------------------------------------

async function handleVoice(msg) {
  const chatId = msg.chat.id;
  const user = msg.from;
  const voice = msg.voice;
  const langCode = user.language_code || 'en';

  if (!voice) return;

  const fileId = voice.file_id;
  const duration = voice.duration || 0;

  try {
    // 1. Upsert user
    upsertUser(user.id, user.username, user.first_name);

    // 2. Check quota
    const quota = checkQuota(user.id);
    if (!quota.allowed) {
      await sendMessage(chatId, t(langCode, 'quota_reached', quota.dailyCount, quota.limit));
      return;
    }

    // 3. Duration limit
    const maxDuration = quota.plan === 'pro' ? 3600 : 300;
    if (duration > maxDuration) {
      const maxMin = Math.floor(maxDuration / 60);
      await sendMessage(chatId, t(langCode, 'duration_limit', duration, maxMin));
      return;
    }

    // 4. Rate limit
    const isPro = quota.plan === 'pro';
    if (!checkRateLimit(user.id, isPro)) {
      const wait = isPro ? 5 : 10;
      await sendMessage(chatId, t(langCode, 'rate_limit', wait));
      return;
    }

    // 5. Get file path from Telegram
    const filePath = await getFile(fileId);

    // 6. Download audio
    const audioBuffer = await downloadFile(filePath);

    // 7. Transcribe via gateway (with circuit breaker)
    let text;
    try {
      text = await transcribe(audioBuffer);
    } catch (transcribeErr) {
      if (transcribeErr.message === 'CIRCUIT_OPEN') {
        await sendMessage(chatId, t(langCode, 'circuit_open'));
        logUsage(user.id, duration, 'transcribe', 'circuit_open');
        return;
      }
      throw transcribeErr;
    }

    if (!text || text.trim().length === 0) {
      await sendMessage(chatId, t(langCode, 'empty_transcript'));
      logUsage(user.id, duration, 'transcribe', 'empty');
      return;
    }

    // 8. Reply with transcription
    let reply = text;

    // 9. Pro features: translation + summary
    if (isPro) {
      const lang = getLang(user.id);
      try {
        // Translation (if lang set)
        if (lang) {
          const translated = await translateText(text, lang);
          if (translated) {
            reply += `\n\n${t(langCode, 'translation_label', lang)}\n${translated}`;
            logUsage(user.id, 0, 'translate', 'ok');
          }
        }
        // Summary (always for Pro)
        const summary = await summarizeText(text);
        if (summary) {
          reply += `\n\n${t(langCode, 'summary_label')}\n${summary}`;
          logUsage(user.id, 0, 'summary', 'ok');
        }
      } catch (geminiErr) {
        console.error(`[gemini] Error for user=${user.id}:`, geminiErr.message);
        reply += `\n\n${t(langCode, 'gemini_unavailable')}`;
      }
    }

    await sendMessage(chatId, reply);

    // 10. Increment usage & log
    incrementUsage(user.id);
    logUsage(user.id, duration, 'transcribe', 'ok');

    console.log(`[voice] user=${user.id} duration=${duration}s len=${text.length} pro=${isPro}`);
  } catch (err) {
    console.error(`[voice] Error for user=${user.id}:`, err);
    logUsage(user.id, duration, 'transcribe', 'error');
    await sendMessage(chatId, t(langCode, 'transcription_error'));
  }
}

// ---------------------------------------------------------------------------
// Webhook update router
// ---------------------------------------------------------------------------

async function handleUpdate(update) {
  const msg = update.message;
  if (!msg) return;

  const chatId = msg.chat.id;
  const langCode = msg.from?.language_code || 'en';

  // Commands
  if (msg.text) {
    const parts = msg.text.split(/\s+/);
    const cmd = parts[0].replace(/@\w+$/, '').toLowerCase();
    const args = parts.slice(1).join(' ');
    console.log(`[cmd] user=${msg.from.id} cmd=${cmd}`);
    switch (cmd) {
      case '/start':
        return handleStart(chatId, langCode);
      case '/plan':
        return handlePlan(chatId, msg.from.id, langCode);
      case '/lang':
        return handleLang(chatId, msg.from.id, args, langCode);
      case '/pro':
        return handlePro(chatId, msg.from.id, langCode);
      case '/help':
        return handleHelp(chatId, langCode);
      case '/stats':
        return handleStats(chatId, msg.from.id);
    }
  }

  // Voice messages
  if (msg.voice) {
    return handleVoice(msg);
  }
}

// ---------------------------------------------------------------------------
// Express server
// ---------------------------------------------------------------------------

const app = express();

// Capture raw body for ALL requests (needed for HMAC verification on /lemon)
app.use((req, _res, next) => {
  const chunks = [];
  req.on('data', chunk => chunks.push(chunk));
  req.on('end', () => {
    req.rawBody = Buffer.concat(chunks);
    // Try to parse JSON body manually
    if (req.headers['content-type']?.includes('application/json') && req.rawBody.length > 0) {
      try {
        req.body = JSON.parse(req.rawBody.toString());
      } catch (e) {
        // Not valid JSON — leave body empty
      }
    }
    next();
  });
});

// GET / — Landing page
app.get('/', (_req, res) => {
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VoiceBox — Telegram Voice Transcription Bot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh}
.container{text-align:center;max-width:480px;padding:2rem}
h1{font-size:2.5rem;margin-bottom:.5rem;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.version{font-size:.85rem;color:#64748b;margin-bottom:1.5rem}
p{font-size:1.1rem;line-height:1.6;color:#94a3b8;margin-bottom:2rem}
.btn{display:inline-block;padding:.85rem 2rem;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;text-decoration:none;border-radius:12px;font-size:1.1rem;font-weight:600;transition:transform .15s,box-shadow .15s}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(59,130,246,.35)}
.features{margin-top:2.5rem;font-size:.95rem;color:#64748b;line-height:1.8}
</style>
</head>
<body>
<div class="container">
<h1>VoiceBox</h1>
<p class="version">v${VERSION}</p>
<p>Send a voice message on Telegram — get an instant transcription powered by AI. Translation and summary included with Pro.</p>
<a class="btn" href="https://t.me/VoiceBoxBot">Open in Telegram</a>
<div class="features">Free: 5 voices/day &bull; Pro: unlimited + translation + summary</div>
</div>
</body>
</html>`);
});

// POST /webhook — Telegram updates
app.post('/webhook', async (req, res) => {
  // Verify secret token
  const secret = req.headers['x-telegram-bot-api-secret-token'] || '';
  if (!WEBHOOK_SECRET || !secret || !crypto.timingSafeEqual(Buffer.from(secret), Buffer.from(WEBHOOK_SECRET))) {
    console.warn(`[webhook] Invalid secret token from ${req.ip}`);
    return res.sendStatus(403);
  }

  // Process update async, respond 200 immediately to Telegram
  res.sendStatus(200);

  try {
    await handleUpdate(req.body);
  } catch (err) {
    console.error('[webhook] Unhandled error:', err);
  }
});

// POST /lemon — LemonSqueezy webhooks (HMAC-SHA256 verified)
app.post('/lemon', async (req, res) => {
  // 1. Verify HMAC signature
  if (!LEMON_WEBHOOK_SECRET) {
    console.warn('[lemon] LEMON_WEBHOOK_SECRET not configured');
    return res.sendStatus(500);
  }

  const signature = req.headers['x-signature'] || '';
  if (!signature || !req.rawBody) {
    console.warn('[lemon] Missing signature or body');
    return res.sendStatus(400);
  }

  const hmac = crypto.createHmac('sha256', LEMON_WEBHOOK_SECRET);
  hmac.update(req.rawBody);
  const digest = hmac.digest('hex');

  try {
    if (!crypto.timingSafeEqual(Buffer.from(digest), Buffer.from(signature))) {
      console.warn('[lemon] Invalid HMAC signature');
      return res.sendStatus(403);
    }
  } catch (e) {
    console.warn('[lemon] Signature comparison failed:', e.message);
    return res.sendStatus(403);
  }

  // 2. Process event (messages LemonSqueezy restent en FR — pas de langue dispo)
  res.sendStatus(200);

  try {
    const event = req.body?.meta?.event_name;
    const data = req.body?.data?.attributes;
    const customData = req.body?.meta?.custom_data || data?.first_order_item?.custom_data || {};
    const telegramId = parseInt(customData.telegram_id || '0');
    const customerId = String(data?.customer_id || '');
    const subscriptionId = String(req.body?.data?.id || '');

    console.log(`[lemon] event=${event} telegram_id=${telegramId} customer=${customerId} sub=${subscriptionId}`);

    if (!telegramId) {
      console.warn('[lemon] No telegram_id in custom data');
      return;
    }

    switch (event) {
      case 'subscription_created':
      case 'subscription_resumed':
      case 'subscription_unpaused': {
        setPlan(telegramId, 'pro', customerId, subscriptionId);
        console.log(`[lemon] Activated Pro for telegram_id=${telegramId}`);
        await sendMessage(telegramId, 'Votre plan Pro est active ! Profitez de la traduction et du resume IA.\n\nTapez /lang fr pour activer la traduction.');
        break;
      }

      case 'subscription_expired':
      case 'subscription_cancelled':
      case 'subscription_paused': {
        setPlan(telegramId, 'free', customerId, subscriptionId);
        console.log(`[lemon] Deactivated Pro for telegram_id=${telegramId}`);
        await sendMessage(telegramId, 'Votre abonnement Pro a expire. Vous repassez au plan gratuit (5 vocaux/jour).\n\nTapez /pro pour vous reabonner.');
        break;
      }

      case 'subscription_updated':
      case 'subscription_payment_success': {
        // Refresh plan status — ensure Pro is active
        const currentUser = getUser(telegramId);
        if (currentUser && currentUser.plan !== 'pro') {
          setPlan(telegramId, 'pro', customerId, subscriptionId);
          console.log(`[lemon] Re-activated Pro via ${event} for telegram_id=${telegramId}`);
          await sendMessage(telegramId, 'Votre plan Pro est active ! Profitez de la traduction et du resume IA.\n\nTapez /lang fr pour activer la traduction.');
        } else {
          console.log(`[lemon] ${event} for telegram_id=${telegramId} — already Pro`);
        }
        break;
      }

      case 'subscription_payment_failed': {
        console.log(`[lemon] Payment failed for telegram_id=${telegramId}`);
        await sendMessage(telegramId, 'Echec de paiement pour votre plan Pro. Mettez a jour votre moyen de paiement pour eviter la desactivation.');
        break;
      }

      default:
        console.log(`[lemon] Unhandled event: ${event}`);
    }
  } catch (err) {
    console.error('[lemon] Error processing webhook:', err);
  }
});

// GET /health
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', version: VERSION });
});

// ---------------------------------------------------------------------------
// Purge old usage logs (keep 30 days) — runs daily
// ---------------------------------------------------------------------------

function purgeOldLogs() {
  try {
    const { db } = require('./db');
    const result = db.prepare(
      "DELETE FROM usage_logs WHERE timestamp < datetime('now', '-30 days')"
    ).run();
    if (result.changes > 0) {
      console.log(`[purge] Supprime ${result.changes} logs de plus de 30 jours`);
    }
  } catch (e) {
    console.error('[purge] Erreur:', e.message);
  }
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

app.listen(PORT, () => {
  console.log(`[VoiceBox] v${VERSION} — listening on port ${PORT}`);
  purgeOldLogs();
  setInterval(purgeOldLogs, 24 * 60 * 60 * 1000); // toutes les 24h
});
