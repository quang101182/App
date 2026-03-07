// share_handler.js — n8n Code node (v2.0 — interactive)
// Commande /share : gestion interactive des liens de partage des apps

const GATEWAY_URL  = 'https://api-gateway.quang101182.workers.dev';
const ADMIN_TOKEN  = '0c99681bdec0e7af381192d4c97c4c6b820f5093edab43b642557b4dadbba02ccc8faa59a1eb902d';
const WORKER_SECRET = '333a33b16f8cab5aec61eb5806eeaee332a50e1172ad1b3e3d710b3d84b9cc7b';
const GITHUB_TREE_URL = 'https://api.github.com/repos/quang101182/App/git/trees/main';
const EXCLUDED_DIRS = ['node_modules', 'api-gateway', '.github', '.git', '.vscode', 'dist', 'build'];

const hPost = (url, body) => this.helpers.httpRequest({
  method : 'POST',
  url,
  headers: { 'Authorization': `Bearer ${ADMIN_TOKEN}`, 'Content-Type': 'application/json' },
  body   : JSON.stringify(body || {}),
});

const hGet = (url) => this.helpers.httpRequest({
  method : 'GET',
  url,
  headers: { 'User-Agent': 'n8n-bot' },
});

const cmd = ($input.first().json.cmd || '').trim();

// --- Parse command ---
let action = '';
let param  = '';

if (cmd === 'share' || cmd === '/share') {
  action = 'list';
} else if (cmd === 'addshare') {
  action = 'addshare';
} else if (cmd.startsWith('addshare:')) {
  action = 'addshare_exec';
  param  = cmd.split(':').slice(1).join(':');
} else if (cmd.startsWith('sharedel:')) {
  action = 'sharedel';
  param  = cmd.split(':').slice(1).join(':');
} else if (cmd.startsWith('sharedelconfirm:')) {
  action = 'sharedelconfirm';
  param  = cmd.split(':').slice(1).join(':');
} else {
  action = 'list';
}

let reply    = '';
let keyboard = [];

// ============================================================
// LIST — Afficher tous les liens de partage
// ============================================================
if (action === 'list') {
  const listData  = await hPost(`${GATEWAY_URL}/admin/keys/list`);
  const shareKeys = Object.keys(listData).filter(k => k.endsWith('_SHARE') && listData[k] && listData[k] !== 'not set');

  if (!shareKeys.length) {
    reply = '🔗 *Liens de partage*\n\n_Aucun lien configuré_';
  } else {
    const lines = shareKeys.map(k => {
      const appName = k.replace('_SHARE', '');
      const url = listData[k];
      return `📱 *${appName}*\n\`${url}\``;
    }).join('\n\n');
    reply = `🔗 *Liens de partage*\n\n${lines}`;

    // Un bouton delete par app
    shareKeys.forEach(k => {
      const appName = k.replace('_SHARE', '');
      keyboard.push([{ text: `🗑 ${appName}`, callback_data: `sharedel:${appName}` }]);
    });
  }

  keyboard.push([{ text: '➕ Ajouter un partage', callback_data: 'addshare' }]);
  keyboard.push([{ text: '⬅️ Menu', callback_data: 'menu' }]);
}

// ============================================================
// ADDSHARE — Lister les apps GitHub non encore partagées
// ============================================================
else if (action === 'addshare') {
  // Fetch GitHub tree
  const treeData = await hGet(GITHUB_TREE_URL);
  const allApps  = (treeData.tree || [])
    .filter(e => e.type === 'tree' && !e.path.startsWith('.') && !EXCLUDED_DIRS.includes(e.path))
    .map(e => e.path);

  // Fetch existing share keys
  const listData  = await hPost(`${GATEWAY_URL}/admin/keys/list`);
  const shareKeys = Object.keys(listData).filter(k => k.endsWith('_SHARE') && listData[k] && listData[k] !== 'not set');
  const sharedApps = shareKeys.map(k => k.replace('_SHARE', ''));

  // Filter out already shared apps (compare uppercase)
  const unshared = allApps.filter(app => {
    const keyName = app.toUpperCase().replace(/-/g, '_');
    return !sharedApps.includes(keyName);
  });

  if (!unshared.length) {
    reply = '➕ *Ajouter un partage*\n\n_Toutes les apps sont déjà partagées !_';
  } else {
    reply = '➕ *Ajouter un partage*\n\nSélectionnez une app :';
    unshared.forEach(app => {
      keyboard.push([{ text: app, callback_data: `addshare:${app}` }]);
    });
  }

  keyboard.push([{ text: '⬅️ Retour', callback_data: 'share' }]);
}

// ============================================================
// ADDSHARE:{app_name} — Générer URL et sauvegarder
// ============================================================
else if (action === 'addshare_exec') {
  const appName = param;
  const keyName = appName.toUpperCase().replace(/-/g, '_') + '_SHARE';
  const shareUrl = `https://quang101182.github.io/App/${appName}/#gwy=${WORKER_SECRET}`;

  // Save to gateway
  await hPost(`${GATEWAY_URL}/admin/keys/set`, { key: keyName, value: shareUrl });

  reply = `✅ *Partage créé*\n\n📱 *${appName.toUpperCase().replace(/-/g, '_')}*\n\`${shareUrl}\``;

  keyboard.push([{ text: '🔗 Voir tous', callback_data: 'share' }]);
  keyboard.push([{ text: '⬅️ Menu', callback_data: 'menu' }]);
}

// ============================================================
// SHAREDEL:{APPNAME} — Confirmation de suppression
// ============================================================
else if (action === 'sharedel') {
  const appName = param;

  reply = `🗑 Supprimer le partage *${appName}* ?`;

  keyboard.push([
    { text: '✅ Oui', callback_data: `sharedelconfirm:${appName}` },
    { text: '❌ Non', callback_data: 'share' },
  ]);
}

// ============================================================
// SHAREDELCONFIRM:{APPNAME} — Suppression effective
// ============================================================
else if (action === 'sharedelconfirm') {
  const appName = param;
  const keyName = `${appName}_SHARE`;

  await hPost(`${GATEWAY_URL}/admin/keys/delete`, { key: keyName });

  reply = `✅ Partage *${appName}* supprimé`;

  keyboard.push([{ text: '🔗 Voir tous', callback_data: 'share' }]);
  keyboard.push([{ text: '⬅️ Menu', callback_data: 'menu' }]);
}

return [{ json: { reply, keyboard } }];
