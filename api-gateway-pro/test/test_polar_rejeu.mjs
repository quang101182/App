/**
 * Banc v1.25.1 — un webhook Polar qui ECHOUE doit pouvoir etre re-essaye.
 *
 * Incident du 26/09/2026 : jeton Polar expire -> `benefit_grant.created` repond 502.
 * Polar re-essaie 7 s plus tard, avec le MEME `webhook-id`... et la passerelle le
 * jetait (« event already processed ») : la marque anti-rejeu etait posee AVANT
 * le traitement. Un vrai abonne n'a recu ni cle ni e-mail.
 *
 * Ce banc rejoue la sequence exacte : meme webhook-id, 1er envoi en panne, 2e sain.
 *
 *   node test/test_polar_rejeu.mjs
 */
import worker from '../src/index.js';

const SECRET = 'whsec_bancdetest0123456789';
const BENEFIT = 'benefit-swp-123';

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

// Meme webhook-id a chaque appel : c'est ce que fait Polar quand il re-essaie.
async function send(payload, id) {
  const body = JSON.stringify(payload);
  const ts = String(Math.floor(Date.now() / 1000));
  const req = new Request('https://gw.test/webhook/polar', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'webhook-id': id,
      'webhook-timestamp': ts,
      'webhook-signature': await sign(body, id, ts),
    },
    body,
  });
  const res = await worker.fetch(req, env, ctx);
  await settle();
  return { status: res.status, json: await res.json() };
}

let polarEnPanne = true;
globalThis.fetch = async (url) => {
  const u = String(url);
  if (u.includes('/v1/license-keys/')) {
    if (polarEnPanne) return new Response('{"error":"invalid_token"}', { status: 401 });
    return new Response(JSON.stringify({ key: 'SWP-LK-1' }), { headers: { 'content-type': 'application/json' } });
  }
  return new Response('{}', { status: 200 }); // e-mail d'activation (Resend) et autres
};

let ok = 0, ko = 0;
const check = (cond, label) => { if (cond) { ok++; console.log('  OK  ', label); } else { ko++; console.log('  FAIL', label); } };

const grant = {
  type: 'benefit_grant.created',
  data: {
    customer: { email: 'abonne@test.com' },
    benefit_id: BENEFIT,
    subscription_id: 'sub-1',
    properties: { license_key_id: 'lk-1' },
  },
};

console.log('1. Jeton Polar mort : le 1er envoi echoue');
const r1 = await send(grant, 'evt_grant_1');
check(r1.status === 502, `reponse 502 (recu ${r1.status})`);
check(!env.PRO_KV.store.has('wh:polar:evt_grant_1'), 'aucune marque anti-rejeu apres un echec');
check(!env.PRO_KV.store.has('email:swp:abonne@test.com'), 'aucune cle creee');

console.log('2. Jeton repare : le re-essai de Polar (meme webhook-id) aboutit');
polarEnPanne = false;
const r2 = await send(grant, 'evt_grant_1');
check(r2.status === 200 && r2.json.action === 'created_or_reactivated', `cle creee au re-essai (${r2.json.action || r2.json.reason})`);
check(env.PRO_KV.store.get('email:swp:abonne@test.com') === 'SWP-LK-1', 'email -> cle Polar');
check(env.PRO_KV.store.has('wh:polar:evt_grant_1'), 'marque anti-rejeu posee apres le succes');

console.log('3. Un doublon apres succes reste ignore');
const r3 = await send(grant, 'evt_grant_1');
check(r3.json.reason === 'event already processed', `doublon ignore (${r3.json.reason || r3.json.action})`);

console.log('4. Un 4xx (payload inexploitable) est marque : il ne guerirait pas au re-essai');
const r4 = await send({ type: 'benefit_grant.created', data: { benefit_id: BENEFIT, properties: { license_key_id: 'lk-2' } } }, 'evt_sans_email');
check(r4.status === 400, `400 sans email (recu ${r4.status})`);
check(env.PRO_KV.store.has('wh:polar:evt_sans_email'), 'marque posee pour un 4xx');

console.log(`\n${ok}/${ok + ko} ${ko ? 'ECHEC' : 'OK'}`);
process.exit(ko ? 1 : 0);
