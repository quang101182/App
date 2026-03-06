// keys_handler.js — n8n Code node (v2.0)
// /keys            → liste toutes les APIs + statut clé (✅ valide / ❌ invalide / ⚪ absente)
// /keys set KEY V  → configure une clé
// /keys add KEY V  → alias set
// /keys delete KEY → supprime une clé
// /keys status     → test ping chaque API

const GATEWAY_URL = 'https://api-gateway.quang101182.workers.dev';
const ADMIN_TOKEN = typeof $env !== 'undefined' && $env.GATEWAY_ADMIN_TOKEN
  ? $env.GATEWAY_ADMIN_TOKEN
  : '0c99681bdec0e7af381192d4c97c4c6b820f5093edab43b642557b4dadbba02ccc8faa59a1eb902d';

const KNOWN_KEYS = [
  { key: 'GROQ_KEY',       label: 'Groq',        usage: 'Transcription rapide (whisper-large-v3-turbo)' },
  { key: 'OPENAI_KEY',     label: 'OpenAI',      usage: 'Transcription Whisper-1, GPT' },
  { key: 'GEMINI_KEY',     label: 'Gemini',      usage: 'Traduction & IA (gemini-2.0-flash)' },
  { key: 'DEEPSEEK_KEY',   label: 'DeepSeek',    usage: 'Traduction & IA (deepseek-chat)' },
  { key: 'AZURE_KEY',      label: 'Azure',       usage: 'Traduction Microsoft Translator' },
  { key: 'ASSEMBLYAI_KEY', label: 'AssemblyAI',  usage: 'Transcription word-level' },
  { key: 'DEEPL_KEY',      label: 'DeepL',       usage: 'Traduction de haute qualité' },
];

const text  = ($input.first().json.text || '').trim();
const parts = text.split(/\s+/);
// parts[0] = '/keys', parts[1] = subcommand ou KEY_NAME, parts[2...] = args

const sub = (parts[1] || '').toLowerCase();

const headers = {
  'Authorization': `Bearer ${ADMIN_TOKEN}`,
  'Content-Type' : 'application/json',
};

let result;

// ── /keys (sans argument) ou /keys list ────────────────────────────────────
if (!sub || sub === 'list') {
  // Appel simultané list + status pour avoir présence ET validité
  const [listRes, statusRes] = await Promise.all([
    fetch(`${GATEWAY_URL}/admin/keys/list`,   { method: 'POST', headers }),
    fetch(`${GATEWAY_URL}/admin/keys/status`, { method: 'POST', headers }),
  ]);
  const listData   = await listRes.json();
  const statusData = await statusRes.json();
  const statuses   = statusData.statuses || {};

  const lines = KNOWN_KEYS.map(({ key, label, usage }) => {
    const presence = listData[key] || 'not set';
    const hasKey   = presence !== 'not set';
    const st       = statuses[key];

    let icon;
    if (!hasKey) {
      icon = '⚪';  // pas de clé
    } else if (st?.ok) {
      icon = '✅';  // clé présente et valide
    } else {
      icon = '❌';  // clé présente mais invalide/erreur
    }

    const detail = hasKey ? presence : 'aucune clé';
    return `${icon} *${label}* \`${key}\`\n    └ ${detail}`;
  }).join('\n');

  result = `🔑 *API Gateway — Clés configurées*\n\n${lines}\n\n_/keys delete GROQ\\_KEY — pour supprimer_\n_/keys set GROQ\\_KEY gsk\\_... — pour configurer_`;

// ── /keys set KEY VALEUR ───────────────────────────────────────────────────
} else if (sub === 'set' || sub === 'add') {
  const keyName = (parts[2] || '').toUpperCase();
  // Valeur = tout ce qui suit le 3e mot (au cas où la clé contient des espaces)
  const value = parts.slice(3).join(' ');
  if (!keyName || !value) {
    result = `❌ Usage: /keys set KEY VALEUR\nEx: /keys set GROQ\\_KEY gsk\\_...`;
  } else {
    const res  = await fetch(`${GATEWAY_URL}/admin/keys/set`, {
      method: 'POST', headers, body: JSON.stringify({ key: keyName, value }),
    });
    const data = await res.json();
    result = data.ok
      ? `✅ Clé *${data.key}* configurée`
      : `❌ Erreur: ${data.error}`;
  }

// ── /keys delete KEY ───────────────────────────────────────────────────────
} else if (sub === 'delete') {
  const keyName = (parts[2] || '').toUpperCase();
  if (!keyName) {
    result = '❌ Usage: /keys delete KEY\nEx: /keys delete GROQ\\_KEY';
  } else {
    const res  = await fetch(`${GATEWAY_URL}/admin/keys/delete`, {
      method: 'POST', headers, body: JSON.stringify({ key: keyName }),
    });
    const data = await res.json();
    result = data.ok
      ? `🗑 Clé *${data.key}* supprimée`
      : `❌ Erreur: ${data.error}`;
  }

// ── /keys status ───────────────────────────────────────────────────────────
} else if (sub === 'status') {
  const res  = await fetch(`${GATEWAY_URL}/admin/keys/status`, { method: 'POST', headers });
  const data = await res.json();
  const lines = KNOWN_KEYS.map(({ key, label }) => {
    const st = (data.statuses || {})[key];
    if (!st) return `⚪ *${label}*: non configurée`;
    const icon    = st.ok ? '✅' : '❌';
    const variant = st.variant ? ` (${st.variant})` : '';
    return `${icon} *${label}*: ${st.ok ? `OK ${st.status}${variant}` : st.status}`;
  }).join('\n');
  result = `📊 *Ping APIs*\n\n${lines}`;

// ── aide ───────────────────────────────────────────────────────────────────
} else {
  result = [
    '🔑 *Gestion des clés API*',
    '',
    '/keys — liste toutes les APIs + statut',
    '/keys set KEY VALEUR — configurer une clé',
    '/keys delete KEY — supprimer une clé',
    '/keys status — tester toutes les clés (ping)',
    '',
    '*Clés disponibles:*',
    ...KNOWN_KEYS.map(({ key, label, usage }) => `• \`${key}\` — ${label}: ${usage}`),
  ].join('\n');
}

return [{ json: { reply: result } }];
