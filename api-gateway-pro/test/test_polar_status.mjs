/**
 * Banc v1.23.0 — exactitude du statut d'abonnement Polar + comptes multiples.
 *
 * Ce que ce banc prouve, et qu'aucun test unitaire de fonction n'aurait montré :
 * l'ORDRE d'arrivée des webhooks. Le defaut du 30/08 n'etait pas une fonction
 * fausse, c'etait un evenement jete parce qu'il arrivait trop tot.
 *
 * ⚠️ Il forge ses signatures avec la derivation REELLE de Polar (chaine brute,
 * prefixe whsec_ compris) — celle qui a coute le 20/08. Un banc qui forge avec
 * l'hypothese du code valide la croyance du code, pas la realite.
 *
 *   node test/test_polar_status.mjs
 */
import worker from '../src/index.js';

const SECRET = 'whsec_bancdetest0123456789';
const BENEFIT = 'benefit-swp-123';
// Jeton propre au banc : aucun secret reel ne doit vivre dans un fichier versionne.
const ADMIN = 'banc-admin-token';

// ── KV en memoire ────────────────────────────────────────────────────────────
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

function makeEnv(seed) {
  return {
    ADMIN_TOKEN: ADMIN,
    PRO_KV: makeKV({
      'cfg:polar_webhook_secret': SECRET,
      'cfg:polar_swp_benefit_id': BENEFIT,
      'cfg:polar_api_key': 'polar_test_token',
      ...seed,
    }),
  };
}

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

let seq = 0;
async function webhook(env, payload) {
  const body = JSON.stringify(payload);
  const id = `evt_${++seq}`;
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

async function overview(env) {
  const req = new Request('https://gw.test/admin/swp/overview', {
    headers: { Authorization: `Bearer ${ADMIN}` },
  });
  const res = await worker.fetch(req, env, ctx);
  await settle();
  return res.json();
}

// ── Charges utiles ───────────────────────────────────────────────────────────
const subEvent = (email, status, extra = {}) => ({
  type: 'subscription.updated',
  data: {
    customer: { email },
    status,
    product: { metadata: { app: 'swp' } },
    ...extra,
  },
});

const grantEvent = (email, licenseKeyId = 'lk-1', subscription_id = 'sub-1') => ({
  type: 'benefit_grant.created',
  data: {
    customer: { email },
    benefit_id: BENEFIT,
    subscription_id,
    properties: { license_key_id: licenseKeyId },
  },
});

// Polar ne met pas la cle en clair dans le webhook : le worker va la chercher.
globalThis.fetch = async (url) => {
  const u = String(url);
  if (u.includes('/v1/license-keys/')) {
    return new Response(JSON.stringify({ key: 'SWP-' + u.split('/').pop().toUpperCase() }), {
      headers: { 'content-type': 'application/json' },
    });
  }
  if (u.includes('/v1/subscriptions/')) {
    return new Response(JSON.stringify({
      status: 'trialing', current_period_end: '2026-09-06T00:00:00Z',
      ends_at: '2026-09-06T00:00:00Z', cancel_at_period_end: true,
      amount: 900, currency: 'eur',
    }), { headers: { 'content-type': 'application/json' } });
  }
  if (u.includes('api.resend.com')) {
    return new Response(JSON.stringify({ id: 'test' }), { headers: { 'content-type': 'application/json' } });
  }
  return new Response('{}', { headers: { 'content-type': 'application/json' } });
};

// ── Assertions ───────────────────────────────────────────────────────────────
let pass = 0, fail = 0;
function check(label, cond, detail = '') {
  if (cond) { pass++; console.log(`  ✅ ${label}`); }
  else { fail++; console.log(`  ❌ ${label}${detail ? ` — ${detail}` : ''}`); }
}
const keyOf = async (env, email) => env.PRO_KV.get(`email:swp:${email}`);
const dataOf = async (env, email) => env.PRO_KV.get(`pro:${await keyOf(env, email)}`, 'json');

// ── T1 — LE cas du 30/08 : l'abonnement arrive AVANT la cle ─────────────────
console.log('\nT1 · subscription.* arrive AVANT benefit_grant.created');
{
  const env = makeEnv();
  const r1 = await webhook(env, subEvent('early@test.com', 'trialing', {
    trial_end: '2026-09-06T00:00:00Z', current_period_end: '2026-09-06T00:00:00Z',
  }));
  check('l evenement n est plus jete', r1.json.action === 'deferred', JSON.stringify(r1.json));
  check('l etat est mis en attente',
    !!(await env.PRO_KV.get('pendingsub:swp:early@test.com', 'json')));

  await webhook(env, grantEvent('early@test.com'));
  const d = await dataOf(env, 'early@test.com');
  check('la cle nait avec le statut REEL (on_trial)', d.lsStatus === 'on_trial', JSON.stringify(d.lsStatus));
  check('elle n est PAS annoncee comme payante confirmee', d.lsStatusAssumed !== true);
  check('le plan suit le statut reel', d.plan === 'trial', d.plan);
  check('la fin d essai est posee', d.expiresAt === '2026-09-06T00:00:00Z', String(d.expiresAt));
  check('l attente est consommee',
    (await env.PRO_KV.get('pendingsub:swp:early@test.com')) === null);
}

// ── T2 — sans preuve, le defaut est ESTAMPILLE ──────────────────────────────
console.log('\nT2 · benefit_grant seul : le defaut optimiste est estampille');
{
  const env = makeEnv();
  await webhook(env, grantEvent('lonely@test.com', 'lk-2', 'sub-2'));
  const d = await dataOf(env, 'lonely@test.com');
  check('lsStatus reste active (le dashboard ne perd pas de payant)', d.lsStatus === 'active');
  check('mais il est marque comme SUPPOSE', d.lsStatusAssumed === true);

  const ov = await overview(env);
  check('overview : 0 payant confirme', ov.payers_confirmed === 0, String(ov.payers_confirmed));
  check('overview : 1 payant non confirme', ov.payers_unconfirmed === 1, String(ov.payers_unconfirmed));
}

// ── T3 — resiliation visible AVANT l echeance ───────────────────────────────
console.log('\nT3 · abonnement actif mais deja resilie');
{
  const env = makeEnv();
  await webhook(env, grantEvent('cancel@test.com', 'lk-3', 'sub-3'));
  await webhook(env, subEvent('cancel@test.com', 'active', {
    cancel_at_period_end: true, current_period_end: '2026-09-30T00:00:00Z',
    ends_at: '2026-09-30T00:00:00Z',
  }));
  const d = await dataOf(env, 'cancel@test.com');
  check('la resiliation programmee est enregistree', d.cancelAtPeriodEnd === true);
  check('le statut n est plus suppose', !d.lsStatusAssumed);
  check('l acces court jusqu a la fin de periode', d.revoked === false);

  const ov = await overview(env);
  check('overview : 1 abonnement en cours de resiliation', ov.cancelling === 1, String(ov.cancelling));
  check('overview : compte comme payant confirme jusqu au bout', ov.payers_confirmed === 1);
}

// ── T4 — resync Polar repare l historique ───────────────────────────────────
console.log('\nT4 · POST /admin/swp/sync-polar-status');
{
  const env = makeEnv();
  await webhook(env, grantEvent('resync@test.com', 'lk-4', 'sub-4'));
  check('avant : statut suppose', (await dataOf(env, 'resync@test.com')).lsStatusAssumed === true);

  const res = await worker.fetch(new Request('https://gw.test/admin/swp/sync-polar-status', {
    method: 'POST', headers: { Authorization: `Bearer ${ADMIN}` },
  }), env, ctx);
  await settle();
  const out = await res.json();
  const d = await dataOf(env, 'resync@test.com');
  check('le resync interroge Polar', out.ok === true && out.checked === 1, JSON.stringify(out).slice(0, 120));
  check('apres : statut REEL (trialing -> on_trial)', d.lsStatus === 'on_trial', String(d.lsStatus));
  check('plus rien de suppose', !d.lsStatusAssumed);
  check('resiliation + montant recuperes', d.cancelAtPeriodEnd === true && d.amountCents === 900);
}

// ── T5 — comptes multiples ──────────────────────────────────────────────────
console.log('\nT5 · detection des comptes multiples (jamais bloquante)');
{
  const env = makeEnv();
  await webhook(env, grantEvent('mauro+one@gmail.com', 'lk-5', 'sub-5'));
  await webhook(env, grantEvent('ma.uro@googlemail.com', 'lk-6', 'sub-6'));
  await webhook(env, grantEvent('autre@me.com', 'lk-7', 'sub-7'));

  // Deux cles vues depuis la meme IP (empreinte hachee posee au 1er appel).
  const k1 = await keyOf(env, 'mauro+one@gmail.com');
  const k3 = await keyOf(env, 'autre@me.com');
  for (const k of [k1, k3]) {
    await worker.fetch(new Request('https://gw.test/api/translate', {
      method: 'POST',
      headers: { 'X-Pro-Key': k, 'CF-Connecting-IP': '203.0.113.9', 'content-type': 'application/json' },
      body: '{}',
    }), env, ctx);
    await settle();
  }

  const ov = await overview(env);
  const byMail = ov.duplicate_suspects.by_normalized_email;
  const byIp = ov.duplicate_suspects.by_ip_hash;
  check('alias +tag / points / googlemail rapproches',
    byMail.length === 1 && byMail[0].value === 'mauro@gmail.com', JSON.stringify(byMail.map((g) => g.value)));
  check('deux adresses VRAIMENT distinctes rapprochees par l empreinte',
    byIp.length === 1 && byIp[0].emails.length === 2, JSON.stringify(byIp.map((g) => g.emails)));
  check('l IP en clair n est jamais stockee',
    ![...env.PRO_KV.store.values()].some((v) => String(v).includes('203.0.113.9')));
  check('aucun acces refuse par la detection',
    (await dataOf(env, 'ma.uro@googlemail.com')).revoked === false);
}

console.log(`\n${fail === 0 ? '🟢' : '🔴'} ${pass} verifications passees, ${fail} echouees\n`);
process.exit(fail === 0 ? 0 : 1);
