// keys_handler.js — n8n Code node (v3.0 — interactive)
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
  { key: 'WORKER_SECRET',  label: 'Worker Secret', usage: 'Secret auth apps → gateway', noPing: true },
  { key: 'DIAG_FOLDER_ID', label: 'DIAG Folder', usage: 'Google Drive folder ID pour DIAG uploads', isConfig: true },
  { key: 'MCP_DRIVE_URL',  label: 'MCP Drive',   usage: 'URL serveur MCP Drive (Render)', isConfig: true },
];

const hPost = (url, body) => this.helpers.httpRequest({
  method : 'POST',
  url,
  headers: { 'Authorization': `Bearer ${ADMIN_TOKEN}`, 'Content-Type': 'application/json' },
  body   : JSON.stringify(body || {}),
});

const text  = ($input.first().json.cmd || $input.first().json.text || '').trim();

// ── Helpers clavier ────────────────────────────────────────────────────────
const btn = (text, callback_data) => ({ text, callback_data });
const backKb = [[btn('🔑 Voir les clés', 'keys'), btn('⬅️ Menu', 'menu')]];

let reply, keyboard, forceReply = false;

// ── Route: callback keyset:{KEY} ───────────────────────────────────────────
if (text.startsWith('keyset:')) {
  const keyName = text.slice('keyset:'.length);
  const info = KNOWN_KEYS.find(k => k.key === keyName);
  const label = info ? info.label : keyName;
  reply = `✏️ Envoie la nouvelle valeur pour *${keyName}* :\n_(colle ta clé API en réponse)_`;
  forceReply = true;
  keyboard = null;

// ── Route: callback keydel:{KEY} ───────────────────────────────────────────
} else if (text.startsWith('keydel:')) {
  const keyName = text.slice('keydel:'.length);
  reply = `🗑 Supprimer *${keyName}* ?`;
  keyboard = [[btn('✅ Oui', `keydelconfirm:${keyName}`), btn('❌ Non', 'keys')]];

// ── Route: callback keydelconfirm:{KEY} ────────────────────────────────────
} else if (text.startsWith('keydelconfirm:')) {
  const keyName = text.slice('keydelconfirm:'.length);
  try {
    const data = await hPost(`${GATEWAY_URL}/admin/keys/delete`, { key: keyName });
    reply = data.ok ? `🗑 Clé *${data.key}* supprimée` : `❌ ${data.error}`;
  } catch (e) {
    reply = `❌ Erreur suppression: ${e.message}`;
  }
  keyboard = backKb;

// ── Route: callback keyadd ─────────────────────────────────────────────────
} else if (text === 'keyadd') {
  reply = `➕ Envoie la clé au format :\n\`NOM_CLE=valeur\`\nEx: \`GROQ_KEY=gsk_abc123...\``;
  forceReply = true;
  keyboard = null;

// ── Route: callback keystatus or /keys status ──────────────────────────────
} else if (text === 'keystatus' || text === 'keys status') {
  try {
    const data  = await hPost(`${GATEWAY_URL}/admin/keys/status`);
    const lines = KNOWN_KEYS.filter(k => !k.isConfig && !k.noPing).map(({ key, label }) => {
      const st = (data.statuses || {})[key];
      if (!st) return `⚪ *${label}*: non configurée`;
      const icon    = st.ok ? '✅' : '❌';
      const variant = st.variant ? ` (${st.variant})` : '';
      return `${icon} *${label}*: ${st.ok ? `OK ${st.status}${variant}` : st.status}`;
    }).join('\n');
    reply = `📊 *Ping APIs*\n\n${lines}`;
  } catch (e) {
    reply = `❌ Erreur status: ${e.message}`;
  }
  keyboard = backKb;

// ── Route: /keys or /keys list ─────────────────────────────────────────────
} else if (text === 'keys' || text === 'keys list' || text === '/keys' || text === '/keys list') {
  try {
    const [listData, statusData] = await Promise.all([
      hPost(`${GATEWAY_URL}/admin/keys/list`),
      hPost(`${GATEWAY_URL}/admin/keys/status`),
    ]);
    const statuses = statusData.statuses || {};

    const lines = KNOWN_KEYS.map(({ key, label, isConfig, noPing }) => {
      const presence = listData[key] || 'not set';
      const hasKey   = presence !== 'not set';

      if (key === 'WORKER_URL') {
        return `☁️ *Worker CF* \`WORKER_URL\` = ${hasKey ? '✔ définie' : '⚠️ non définie'}`;
      }
      if (isConfig) {
        return `    ↳ *Région*: \`${key}\` = ${hasKey ? '✔ définie' : '⚠️ non définie'}`;
      }

      const st     = statuses[key];
      const icon   = !hasKey ? '⚪' : (noPing ? '🔒' : (st?.ok ? '✅' : '❌'));
      const masked = hasKey ? `••• ${presence.length} chars` : 'aucune clé';
      return `${icon} *${label}* (\`${key}\`) ${masked}`;
    }).join('\n');

    reply = `🔑 *API Gateway — Clés*\n\n${lines}`;

    // Build inline keyboard: edit/delete buttons for each non-config key
    const keyButtons = KNOWN_KEYS
      .filter(k => !k.isConfig)
      .map(({ key, label }) => [
        btn(`✏️ ${label}`, `keyset:${key}`),
        btn(`🗑 ${label}`, `keydel:${key}`),
      ]);

    keyboard = [
      ...keyButtons,
      [btn('➕ Ajouter clé', 'keyadd'), btn('📊 Ping all', 'keystatus')],
      [btn('⬅️ Menu', 'menu')],
    ];
  } catch (e) {
    reply = `❌ Erreur chargement clés: ${e.message}`;
    keyboard = [[btn('⬅️ Menu', 'menu')]];
  }

// ── Route: /keys set KEY=VALUE ─────────────────────────────────────────────
} else if (text.match(/^(\/)?keys\s+set\b/i)) {
  const parts = text.split(/\s+/);
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
    reply = `❌ Usage:\n\`/keys set GROQ_KEY=gsk_...\`\nou\n\`/keys set GROQ_KEY gsk_...\``;
    keyboard = backKb;
  } else {
    try {
      const data = await hPost(`${GATEWAY_URL}/admin/keys/set`, { key: keyName, value });
      reply = data.ok ? `✅ Clé *${data.key}* configurée` : `❌ ${data.error}`;

      // Auto-update tous les liens *_SHARE si WORKER_SECRET change
      if (data.ok && keyName === 'WORKER_SECRET') {
        const listData = await hPost(`${GATEWAY_URL}/admin/keys/list`);
        const shareKeys = Object.keys(listData).filter(k => k.endsWith('_SHARE') && listData[k] && listData[k] !== 'not set');
        let updated = 0;
        for (const sk of shareKeys) {
          const oldUrl = listData[sk];
          const newUrl = oldUrl.replace(/#gwy=.*$/, `#gwy=${value}`);
          if (newUrl !== oldUrl) {
            await hPost(`${GATEWAY_URL}/admin/keys/set`, { key: sk, value: newUrl });
            updated++;
          }
        }
        if (updated > 0) {
          reply += `\n\n🔗 ${updated} lien(s) de partage mis à jour`;
        }
      }
    } catch (e) {
      reply = `❌ Erreur set: ${e.message}`;
    }
    keyboard = backKb;
  }

// ── Route: /keys delete KEY ────────────────────────────────────────────────
} else if (text.match(/^(\/)?keys\s+delete\b/i)) {
  const parts   = text.split(/\s+/);
  const keyName = (parts[2] || '').toUpperCase();
  if (!keyName) {
    reply = '❌ Usage: `/keys delete KEY`\nEx: `/keys delete GROQ_KEY`';
    keyboard = backKb;
  } else {
    try {
      const data = await hPost(`${GATEWAY_URL}/admin/keys/delete`, { key: keyName });
      reply = data.ok ? `🗑 Clé *${data.key}* supprimée` : `❌ ${data.error}`;
    } catch (e) {
      reply = `❌ Erreur delete: ${e.message}`;
    }
    keyboard = backKb;
  }

// ── Route: aide / fallback ─────────────────────────────────────────────────
} else {
  reply = [
    '🔑 *Gestion des clés API*', '',
    '/keys — liste toutes les APIs + statut',
    '/keys set KEY VALEUR — configurer une clé',
    '/keys delete KEY — supprimer une clé',
    '/keys status — tester toutes les clés (ping)', '',
    '*Clés disponibles:*',
    ...KNOWN_KEYS.map(({ key, label, usage, isConfig }) =>
      `${isConfig ? '  ↳' : '•'} \`${key}\` — ${label}: ${usage}`),
  ].join('\n');
  keyboard = backKb;
}

return [{ json: { reply, keyboard, forceReply } }];
