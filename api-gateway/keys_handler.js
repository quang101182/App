// keys_handler.js — n8n Code node (v1.0)
// Commandes Telegram: /keys list|set|add|delete|status
// Auth: Authorization: Bearer ADMIN_TOKEN vers api-gateway
// IMPORTANT: définir GATEWAY_URL et ADMIN_TOKEN dans les variables n8n

const GATEWAY_URL = 'https://api-gateway.quang101182.workers.dev';
const ADMIN_TOKEN = $env.GATEWAY_ADMIN_TOKEN || '';

const text  = ($input.first().json.text || '').trim();
const parts = text.split(/\s+/);
// parts[0] = '/keys', parts[1] = subcommand, parts[2] = KEY, parts[3] = VALUE

const cmd = (parts[1] || '').toLowerCase();

const headers = {
  'Authorization': `Bearer ${ADMIN_TOKEN}`,
  'Content-Type' : 'application/json',
};

let result;

if (cmd === 'list') {
  const res  = await fetch(`${GATEWAY_URL}/admin/keys/list`, { method: 'POST', headers });
  const data = await res.json();
  const lines = Object.entries(data).map(([k, v]) => `• *${k}*: ${v}`).join('\n');
  result = `🔑 *Clés API*\n\n${lines || '(aucune clé configurée)'}`;

} else if (cmd === 'set' || cmd === 'add') {
  const keyName = (parts[2] || '').toUpperCase();
  const value   = parts[3];
  if (!keyName || !value) {
    result = `❌ Usage: /keys ${cmd} KEY VALEUR\nEx: /keys set GEMINI AIza...`;
  } else {
    const res  = await fetch(`${GATEWAY_URL}/admin/keys/set`, {
      method: 'POST', headers, body: JSON.stringify({ key: keyName, value }),
    });
    const data = await res.json();
    result = data.ok
      ? `✅ Clé *${data.key}* configurée`
      : `❌ Erreur: ${data.error}`;
  }

} else if (cmd === 'delete') {
  const keyName = (parts[2] || '').toUpperCase();
  if (!keyName) {
    result = '❌ Usage: /keys delete KEY\nEx: /keys delete GROQ';
  } else {
    const res  = await fetch(`${GATEWAY_URL}/admin/keys/delete`, {
      method: 'POST', headers, body: JSON.stringify({ key: keyName }),
    });
    const data = await res.json();
    result = data.ok
      ? `✅ Clé *${data.key}* supprimée`
      : `❌ Erreur: ${data.error}`;
  }

} else if (cmd === 'status') {
  const res  = await fetch(`${GATEWAY_URL}/admin/keys/status`, { method: 'POST', headers });
  const data = await res.json();
  const lines = Object.entries(data.statuses || {}).map(([k, v]) => {
    const icon    = v.ok ? '✅' : '❌';
    const variant = v.variant ? ` (${v.variant})` : '';
    return `${icon} *${k}*: ${v.ok ? `OK ${v.status}${variant}` : v.status}`;
  }).join('\n');
  result = `📊 *Status des APIs*\n\n${lines || '(aucune clé configurée)'}`;

} else {
  result = [
    '🔑 *Commandes /keys*',
    '',
    '/keys list — liste toutes les clés',
    '/keys set KEY VALEUR — configurer une clé',
    '/keys add KEY VALEUR — alias de set',
    '/keys delete KEY — supprimer une clé',
    '/keys status — tester toutes les clés',
    '',
    'Clés valides: GEMINI\\_KEY, GROQ\\_KEY, OPENAI\\_KEY, DEEPL\\_KEY, ASSEMBLYAI\\_KEY',
  ].join('\n');
}

return [{ json: { reply: result } }];
