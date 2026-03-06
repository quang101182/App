// keys_handler.js — n8n Code node (v2.2)
// Utilise this.helpers.httpRequest (pas fetch — n8n 2.8.3 task runner)

const GATEWAY_URL = 'https://api-gateway.quang101182.workers.dev';
const ADMIN_TOKEN = '0c99681bdec0e7af381192d4c97c4c6b820f5093edab43b642557b4dadbba02ccc8faa59a1eb902d';

const KNOWN_KEYS = [
  { key: 'GROQ_KEY',       label: 'Groq',       usage: 'Transcription (whisper-large-v3-turbo)' },
  { key: 'OPENAI_KEY',     label: 'OpenAI',     usage: 'Transcription Whisper-1, GPT' },
  { key: 'GEMINI_KEY',     label: 'Gemini',     usage: 'Traduction & IA (gemini-2.0-flash)' },
  { key: 'DEEPSEEK_KEY',   label: 'DeepSeek',   usage: 'Traduction & IA (deepseek-chat)' },
  { key: 'AZURE_KEY',      label: 'Azure',      usage: 'Traduction Microsoft Translator', paired: 'AZURE_REGION' },
  { key: 'AZURE_REGION',   label: 'Azure Région', usage: 'ex: francecentral', isConfig: true },
  { key: 'ASSEMBLYAI_KEY', label: 'AssemblyAI', usage: 'Transcription word-level' },
  { key: 'DEEPL_KEY',      label: 'DeepL',      usage: 'Traduction haute qualité' },
  { key: 'CLAUDE_KEY',     label: 'Claude',     usage: 'Anthropic Claude (claude-sonnet-4-6, etc.)' },
  { key: 'WORKER_URL',     label: 'Worker CF',  usage: 'URL Worker gros fichiers cloud', isConfig: true },
];

const hPost = (url, body) => this.helpers.httpRequest({
  method : 'POST',
  url,
  headers: { 'Authorization': `Bearer ${ADMIN_TOKEN}`, 'Content-Type': 'application/json' },
  body   : JSON.stringify(body || {}),
});

const text  = ($input.first().json.cmd || $input.first().json.text || '').trim();
const parts = text.split(/\s+/);
const sub   = (parts[1] || '').toLowerCase();

let result;

// ── /keys (sans arg) ou /keys list ────────────────────────────────────────
if (!sub || sub === 'list') {
  const [listData, statusData] = await Promise.all([
    hPost(`${GATEWAY_URL}/admin/keys/list`),
    hPost(`${GATEWAY_URL}/admin/keys/status`),
  ]);
  const statuses = statusData.statuses || {};

  const lines = KNOWN_KEYS.map(({ key, label, isConfig }) => {
    const presence = listData[key] || 'not set';
    const hasKey   = presence !== 'not set';

    if (key === 'WORKER_URL') {
      return `☁️ *Worker CF* \`WORKER_URL\` = ${hasKey ? '✔ définie' : '⚠️ non définie'}`;
    }
    if (isConfig) {
      return `    ↳ *Région*: \`${key}\` = ${hasKey ? '✔ définie' : '⚠️ non définie'}`;
    }

    const st      = statuses[key];
    const icon    = !hasKey ? '⚪' : st?.ok ? '✅' : '❌';
    const masked  = hasKey ? `••• ${presence.length} chars` : 'aucune clé';
    return `${icon} *${label}* \`${key}\`\n    └ ${masked}`;
  }).join('\n');

  result = `🔑 *API Gateway — Clés*\n\n${lines}\n\n\`/keys set GROQ_KEY=gsk_...\`\n\`/keys delete GROQ_KEY\`\n\n_Partage app:_ \`/keys set APPNAME_SHARE=https://...#gwy=...\` → \`/share\``;

// ── /keys set|add KEY VALEUR ───────────────────────────────────────────────
} else if (sub === 'set' || sub === 'add') {
  // Supporte KEY=VALUE et KEY VALEUR
  let keyName, value;
  const arg2 = parts[2] || '';
  if (arg2.includes('=')) {
    const eqIdx = arg2.indexOf('=');
    keyName = arg2.slice(0, eqIdx).toUpperCase();
    value   = arg2.slice(eqIdx + 1) + (parts.length > 3 ? ' ' + parts.slice(3).join(' ') : '');
  } else {
    keyName = arg2.toUpperCase();
    value   = parts.slice(3).join(' ');
  }
  if (!keyName || !value) {
    result = `❌ Usage:\n\`/keys set GROQ_KEY=gsk_...\`\nou\n\`/keys set GROQ_KEY gsk_...\``;
  } else {
    const data = await hPost(`${GATEWAY_URL}/admin/keys/set`, { key: keyName, value });
    result = data.ok ? `✅ Clé *${data.key}* configurée` : `❌ ${data.error}`;
  }

// ── /keys delete KEY ───────────────────────────────────────────────────────
} else if (sub === 'delete') {
  const keyName = (parts[2] || '').toUpperCase();
  if (!keyName) {
    result = '❌ Usage: `/keys delete KEY`\nEx: `/keys delete GROQ_KEY`';
  } else {
    const data = await hPost(`${GATEWAY_URL}/admin/keys/delete`, { key: keyName });
    result = data.ok ? `🗑 Clé *${data.key}* supprimée` : `❌ ${data.error}`;
  }

// ── /keys status ───────────────────────────────────────────────────────────
} else if (sub === 'status') {
  const data  = await hPost(`${GATEWAY_URL}/admin/keys/status`);
  const lines = KNOWN_KEYS.filter(k => !k.isConfig).map(({ key, label }) => {
    const st      = (data.statuses || {})[key];
    if (!st) return `⚪ *${label}*: non configurée`;
    const icon    = st.ok ? '✅' : '❌';
    const variant = st.variant ? ` (${st.variant})` : '';
    return `${icon} *${label}*: ${st.ok ? `OK ${st.status}${variant}` : st.status}`;
  }).join('\n');
  result = `📊 *Ping APIs*\n\n${lines}`;

// ── aide ───────────────────────────────────────────────────────────────────
} else {
  result = [
    '🔑 *Gestion des clés API*', '',
    '/keys — liste toutes les APIs + statut',
    '/keys set KEY VALEUR — configurer une clé',
    '/keys delete KEY — supprimer une clé',
    '/keys status — tester toutes les clés (ping)', '',
    '*Clés disponibles:*',
    ...KNOWN_KEYS.map(({ key, label, usage, isConfig }) =>
      `${isConfig ? '  ↳' : '•'} \`${key}\` — ${label}: ${usage}`),
  ].join('\n');
}

return [{ json: { reply: result } }];
