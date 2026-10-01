/**
 * Banc v1.25.3 — chaque appel à l'API Polar porte l'en-tête `Polar-Version` épinglé.
 *
 * Pourquoi : depuis le 01/10/2026, Polar versionne son API par trimestre ; sans en-tête,
 * un appel suit la version courante. Mesuré le 01/10 : une version INCONNUE rend 404.
 * La fausse API ci-dessous se comporte pareil (404 si l'en-tête manque ou diffère) :
 * un appel oublié casse donc le parcours au lieu de passer en silence.
 *
 *   node test/test_polar_version.mjs
 */
import worker from '../src/index.js';

const ATTENDUE = '2026-10';
const SECRET = 'whsec_bancdetest0123456789';
const BENEFIT = 'benefit-swp-123';
const ADMIN = 'banc-admin-token';

function makeKV(seed = {}) {
  const store = new Map(Object.entries(seed));
  return {
    store,
    async get(k, type) {
      const v = store.has(k) ? store.get(k) : null;
      if (v === null || v === undefined) return null;
      return type === 'json' ? JSON.parse(v) : v;
    },
    async put(k, v) { store.set(k, typeof v === 'string' ? v : JSON.stringify(v)); },
    async delete(k) { store.delete(k); },
    async list({ prefix }) {
      return { keys: [...store.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })) };
    },
  };
}
const env = {
  ADMIN_TOKEN: ADMIN,
  PRO_KV: makeKV({
    'cfg:polar_webhook_secret': SECRET,
    'cfg:polar_swp_benefit_id': BENEFIT,
    'cfg:polar_api_key': 'polar_test_token',
  }),
};
const pending = [];
const ctx = { waitUntil: (p) => pending.push(p) };
const settle = () => Promise.allSettled(pending.splice(0));

async function sign(body, id, ts) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${id}.${ts}.${body}`));
  return 'v1,' + btoa(String.fromCharCode(...new Uint8Array(sig)));
}

// ── Fausse API Polar : 404 si la version n'est pas exactement celle attendue ──
const appels = [];
globalThis.fetch = async (url, init = {}) => {
  const u = String(url);
  if (u.includes('api.polar.sh')) {
    const h = new Headers(init.headers || {});
    const v = h.get('Polar-Version');
    appels.push({ u, v });
    if (v !== ATTENDUE) return new Response('{"detail":"Not Found"}', { status: 404 });
    if (u.includes('/v1/license-keys/')) {
      return new Response(JSON.stringify({ key: 'SWP-LK1' }), { headers: { 'content-type': 'application/json' } });
    }
    if (u.includes('/v1/subscriptions/')) {
      return new Response(JSON.stringify({
        status: 'active', current_period_end: '2026-11-01T00:00:00Z', cancel_at_period_end: false,
        amount: 900, currency: 'eur',
      }), { headers: { 'content-type': 'application/json' } });
    }
  }
  return new Response(JSON.stringify({ id: 'test' }), { headers: { 'content-type': 'application/json' } });
};

let pass = 0, fail = 0;
function check(label, cond, detail = '') {
  if (cond) { pass++; console.log(`  ✅ ${label}`); } else { fail++; console.log(`  ❌ ${label}${detail ? ` — ${detail}` : ''}`); }
}

// 1) benefit_grant.created -> le worker va lire la clé de licence chez Polar
const body = JSON.stringify({
  type: 'benefit_grant.created',
  data: { customer: { email: 'banc@exemple.fr' }, benefit_id: BENEFIT, subscription_id: 'sub-1', properties: { license_key_id: 'lk-1' } },
});
const ts = String(Math.floor(Date.now() / 1000));
const r1 = await worker.fetch(new Request('https://gw.test/webhook/polar', {
  method: 'POST',
  headers: { 'content-type': 'application/json', 'webhook-id': 'evt_v1', 'webhook-timestamp': ts, 'webhook-signature': await sign(body, 'evt_v1', ts) },
  body,
}), env, ctx);
await settle();
const lk = appels.filter((a) => a.u.includes('/v1/license-keys/'));
check('le webhook a bien interrogé Polar pour la clé', lk.length >= 1, JSON.stringify(appels));
check('appel license-keys : Polar-Version = ' + ATTENDUE, lk.every((a) => a.v === ATTENDUE), JSON.stringify(lk));
check('la clé est créée (parcours complet passé)', r1.status < 300 && !!(await env.PRO_KV.get('email:swp:banc@exemple.fr')), String(r1.status));

// 2) synchronisation admin -> le worker relit l'abonnement chez Polar
const r2 = await worker.fetch(new Request('https://gw.test/admin/swp/sync-polar-status', {
  method: 'POST', headers: { Authorization: `Bearer ${ADMIN}` },
}), env, ctx);
await settle();
const sub = appels.filter((a) => a.u.includes('/v1/subscriptions/'));
check('la synchro a bien interrogé Polar pour l\'abonnement', sub.length >= 1, JSON.stringify(appels));
check('appel subscriptions : Polar-Version = ' + ATTENDUE, sub.every((a) => a.v === ATTENDUE), JSON.stringify(sub));
const cle = await env.PRO_KV.get('email:swp:banc@exemple.fr');
const d = cle ? await env.PRO_KV.get(`pro:${cle}`, 'json') : null;
check('le statut réel est lu (active), pas « not_found »', r2.status === 200 && d && d.lsStatus === 'active', `${r2.status} ${d ? d.lsStatus : 'fiche absente'}`);

check('AUCUN appel Polar sans la bonne version', appels.length > 0 && appels.every((a) => a.v === ATTENDUE), JSON.stringify(appels));
console.log(`\n${pass}/${pass + fail} ${fail ? '❌' : '✅'}`);
process.exit(fail ? 1 : 0);
