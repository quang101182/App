// VoiceBox Bot v0.2.0 — Telegram voice transcription + translation + summary

const express = require('express');
const crypto = require('crypto');
const { upsertUser, checkQuota, incrementUsage, logUsage, getUser, setLang, getLang } = require('./db');

const VERSION = '0.2.0';
const BOT_TOKEN = process.env.BOT_TOKEN;
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;
const GATEWAY_URL = process.env.GATEWAY_URL;
const GATEWAY_KEY = process.env.GATEWAY_KEY;
const PORT = process.env.PORT || 3000;

const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;
const TELEGRAM_FILE = `https://api.telegram.org/file/bot${BOT_TOKEN}`;

// Rate limit: Map<userId, lastRequestTimestamp>
const rateLimitMap = new Map();

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
// Voice transcription via gateway
// ---------------------------------------------------------------------------

async function transcribe(audioBuffer) {
  const form = new FormData();
  form.append('file', new Blob([audioBuffer], { type: 'audio/ogg' }), 'voice.ogg');
  form.append('model', 'whisper-large-v3-turbo');

  const res = await fetch(`${GATEWAY_URL}/api/groq`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${GATEWAY_KEY}`,
      'X-Api-Path': '/openai/v1/audio/transcriptions',
    },
    body: form,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gateway transcription failed: ${res.status} — ${errText}`);
  }

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Gateway returned non-JSON: ${raw.slice(0, 200)}`);
  }
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

function handleStart(chatId) {
  const text =
    `\u{1F399} VoiceBox v${VERSION}\n\n` +
    `Envoyez-moi un message vocal et je le transcris instantanément !\n\n` +
    `Plan gratuit : 5 vocaux/jour, max 5 min\n` +
    `Plan Pro (€3/mois) : illimité, traduction, résumé\n\n` +
    `/plan — voir mon plan\n` +
    `/lang XX — langue de traduction (Pro)\n` +
    `/pro — passer en Pro\n` +
    `/help — aide`;
  return sendMessage(chatId, text);
}

function handlePlan(chatId, userId) {
  const quota = checkQuota(userId);
  const planName = quota.plan === 'pro' ? 'Pro' : 'Gratuit';
  const limit = quota.plan === 'pro' ? 'illimité' : String(quota.limit);
  const text =
    `Votre plan : ${planName}\n` +
    `Aujourd'hui : ${quota.dailyCount} / ${limit} vocaux`;
  return sendMessage(chatId, text);
}

function handlePro(chatId) {
  return sendMessage(chatId, 'Bientôt disponible ! Restez connecté \u{1F680}');
}

function handleHelp(chatId) {
  const text =
    `Comment utiliser VoiceBox :\n\n` +
    `1. Envoyez un message vocal\n` +
    `2. Recevez la transcription en quelques secondes\n\n` +
    `Limites plan gratuit :\n` +
    `- 5 vocaux par jour\n` +
    `- Durée max : 5 minutes\n\n` +
    `Features Pro :\n` +
    `- Traduction automatique (/lang fr)\n` +
    `- Résumé IA en bullet points\n` +
    `- Illimité, vocaux jusqu'à 60 min\n\n` +
    `Commandes :\n` +
    `/start — message d'accueil\n` +
    `/plan — voir mon plan actuel\n` +
    `/lang XX — langue de traduction (ex: /lang fr)\n` +
    `/lang off — désactiver la traduction\n` +
    `/pro — passer au plan Pro\n` +
    `/help — cette aide`;
  return sendMessage(chatId, text);
}

function handleLang(chatId, userId, args) {
  const user = getUser(userId);
  if (!user || user.plan !== 'pro') {
    return sendMessage(chatId, 'La traduction est une feature Pro. Tapez /pro pour en savoir plus.');
  }

  const lang = (args || '').trim().toLowerCase();
  if (!lang) {
    const current = getLang(userId);
    return sendMessage(chatId, current
      ? `Langue de traduction : ${current}\nTapez /lang off pour désactiver.`
      : `Aucune langue de traduction définie.\nTapez /lang fr (ou en, es, de, ja, ko, zh, etc.)`);
  }

  if (lang === 'off' || lang === 'none') {
    setLang(userId, '');
    return sendMessage(chatId, 'Traduction désactivée.');
  }

  setLang(userId, lang);
  return sendMessage(chatId, `Langue de traduction : ${lang}`);
}

// ---------------------------------------------------------------------------
// Voice message handler
// ---------------------------------------------------------------------------

async function handleVoice(msg) {
  const chatId = msg.chat.id;
  const user = msg.from;
  const voice = msg.voice;

  if (!voice) return;

  const fileId = voice.file_id;
  const duration = voice.duration || 0;

  try {
    // 1. Upsert user
    upsertUser(user.id, user.username, user.first_name);

    // 2. Check quota
    const quota = checkQuota(user.id);
    if (!quota.allowed) {
      await sendMessage(
        chatId,
        `Quota atteint (${quota.dailyCount}/${quota.limit} aujourd'hui). Réessayez demain ou passez en /pro !`
      );
      return;
    }

    // 3. Duration limit
    const maxDuration = quota.plan === 'pro' ? 3600 : 300;
    if (duration > maxDuration) {
      const maxMin = Math.floor(maxDuration / 60);
      await sendMessage(
        chatId,
        `Ce vocal dure ${duration}s — la limite de votre plan est ${maxMin} min. Passez en /pro pour des vocaux plus longs !`
      );
      return;
    }

    // 4. Rate limit
    const isPro = quota.plan === 'pro';
    if (!checkRateLimit(user.id, isPro)) {
      const wait = isPro ? 5 : 10;
      await sendMessage(chatId, `Patientez ${wait}s entre chaque vocal.`);
      return;
    }

    // 5. Get file path from Telegram
    const filePath = await getFile(fileId);

    // 6. Download audio
    const audioBuffer = await downloadFile(filePath);

    // 7. Transcribe via gateway
    const text = await transcribe(audioBuffer);

    if (!text || text.trim().length === 0) {
      await sendMessage(chatId, "Aucun texte détecté dans ce vocal. Réessayez avec un audio plus clair.");
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
            reply += `\n\n--- Traduction (${lang}) ---\n${translated}`;
            logUsage(user.id, 0, 'translate', 'ok');
          }
        }
        // Summary (always for Pro)
        const summary = await summarizeText(text);
        if (summary) {
          reply += `\n\n--- Résumé ---\n${summary}`;
          logUsage(user.id, 0, 'summary', 'ok');
        }
      } catch (geminiErr) {
        console.error(`[gemini] Error for user=${user.id}:`, geminiErr.message);
        reply += '\n\n(Traduction/résumé indisponible)';
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
    await sendMessage(chatId, 'Erreur de transcription, réessayez.');
  }
}

// ---------------------------------------------------------------------------
// Webhook update router
// ---------------------------------------------------------------------------

async function handleUpdate(update) {
  const msg = update.message;
  if (!msg) return;

  const chatId = msg.chat.id;

  // Commands
  if (msg.text) {
    const parts = msg.text.split(/\s+/);
    const cmd = parts[0].replace(/@\w+$/, '').toLowerCase();
    const args = parts.slice(1).join(' ');
    console.log(`[cmd] user=${msg.from.id} cmd=${cmd}`);
    switch (cmd) {
      case '/start':
        return handleStart(chatId);
      case '/plan':
        return handlePlan(chatId, msg.from.id);
      case '/lang':
        return handleLang(chatId, msg.from.id, args);
      case '/pro':
        return handlePro(chatId);
      case '/help':
        return handleHelp(chatId);
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
app.use(express.json());

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

// POST /lemon — LemonSqueezy webhooks (Phase 3 placeholder)
app.post('/lemon', (req, res) => {
  console.log('[lemon] Received webhook:', JSON.stringify(req.body).slice(0, 200));
  res.sendStatus(200);
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
      console.log(`[purge] Supprimé ${result.changes} logs de plus de 30 jours`);
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
