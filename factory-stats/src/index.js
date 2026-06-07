/**
 * factory-stats — Ebook Funnel Factory monitoring backend (read-only)
 * ──────────────────────────────────────────────────────────────────────────
 *   GET /overview  → { accounts: { <id>: {sales,revenue,currency,subs} }, generatedAt }
 *   GET /health    → liveness
 *
 * Agrège :
 *   - Ventes + revenu LemonSqueezy par produit (store 314871, orders status=paid)
 *   - Abonnés MailerLite par groupe (active_count, sommé sur les groupes du compte)
 *
 * Worker ISOLÉ du gateway api-gateway-pro (zéro risque régression revenue prod).
 * Bindings : PRO_KV (cfg:lemonsqueezy_api_key) + TUC_KV (cfg:mailerlite_api_token).
 * Auth : Bearer ADMIN_TOKEN (secret). CORS *.
 */

const VERSION = '1.0.0';
const STORE_ID = '314871';

// Config comptes (miroir server-side de FACTORY_ACCOUNTS du dashboard).
// Ajouter un compte = 1 entrée (id = clé renvoyée au dashboard).
const ACCOUNTS = [
  { id: 'tuc', lemonProductId: '1079445', mailerliteGroups: ['188196310320416300', '188196324324148652'] }, // TUC = tripwire "The Starter Field Kit" 6,99€
  { id: 'aea', lemonProductId: '1124161', mailerliteGroups: ['189630922714252838'] }
];

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type'
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...CORS }
  });
}

// Paginer /v1/orders du store, agréger par product_id (status=paid uniquement).
async function fetchOrdersByProduct(lemonKey) {
  const byProduct = {}; // productId -> { sales, revenueCents, currency }
  let url = `https://api.lemonsqueezy.com/v1/orders?filter[store_id]=${STORE_ID}&page[size]=100`;
  let guard = 0;
  while (url && guard < 25) {
    guard++;
    const r = await fetch(url, {
      headers: { 'Accept': 'application/vnd.api+json', 'Authorization': 'Bearer ' + lemonKey }
    });
    if (!r.ok) throw new Error('lemonsqueezy_orders_' + r.status);
    const data = await r.json();
    (data.data || []).forEach((o) => {
      const a = o.attributes || {};
      if (a.status !== 'paid') return; // ignore refunded / pending / void
      const foi = a.first_order_item || {};
      const pid = String(foi.product_id || '');
      if (!pid) return;
      if (!byProduct[pid]) byProduct[pid] = { sales: 0, revenueCents: 0, currency: a.currency || 'EUR' };
      byProduct[pid].sales += 1;
      byProduct[pid].revenueCents += (a.total || 0); // total en cents
      if (a.currency) byProduct[pid].currency = a.currency;
    });
    url = (data.links && data.links.next) ? data.links.next : null;
  }
  return byProduct;
}

// Nombre d'abonnés actifs d'un groupe MailerLite (API connect.mailerlite.com).
async function fetchGroupCount(mlToken, groupId) {
  const r = await fetch('https://connect.mailerlite.com/api/groups/' + groupId, {
    headers: { 'Authorization': 'Bearer ' + mlToken, 'Accept': 'application/json' }
  });
  if (!r.ok) return null;
  const j = await r.json();
  const d = j.data || {};
  if (typeof d.active_count === 'number') return d.active_count;
  return null;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
    if (url.pathname === '/health') return json({ ok: true, worker: 'factory-stats', version: VERSION });
    if (url.pathname !== '/overview') return json({ error: 'not_found' }, 404);

    // Auth
    const tok = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '').trim();
    if (!env.ADMIN_TOKEN || tok !== env.ADMIN_TOKEN) return json({ error: 'unauthorized' }, 401);

    const lemonKey = await env.PRO_KV.get('cfg:lemonsqueezy_api_key');
    const mlToken = await env.TUC_KV.get('cfg:mailerlite_api_token');

    let byProduct = {};
    let lemonErr = null;
    if (lemonKey) {
      try { byProduct = await fetchOrdersByProduct(lemonKey); }
      catch (e) { lemonErr = String(e && e.message || e); }
    } else {
      lemonErr = 'lemonsqueezy_key_missing';
    }

    const accounts = {};
    let mlErr = null;
    for (const acc of ACCOUNTS) {
      const out = {};
      if (acc.lemonProductId) {
        const p = byProduct[acc.lemonProductId];
        if (p) { out.sales = p.sales; out.revenue = Math.round(p.revenueCents) / 100; out.currency = p.currency; }
        else if (!lemonErr) { out.sales = 0; out.revenue = 0; out.currency = 'EUR'; }
      }
      if (mlToken && acc.mailerliteGroups && acc.mailerliteGroups.length) {
        let total = 0, ok = false;
        for (const g of acc.mailerliteGroups) {
          const c = await fetchGroupCount(mlToken, g);
          if (c !== null) { total += c; ok = true; }
        }
        if (ok) out.subs = total; else mlErr = 'mailerlite_group_fetch_failed';
      } else if (!mlToken) {
        mlErr = 'mailerlite_token_missing';
      }
      accounts[acc.id] = out;
    }

    return json({ accounts, generatedAt: Date.now(), lemonErr, mlErr });
  }
};
