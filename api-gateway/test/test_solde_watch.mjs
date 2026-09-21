/**
 * Banc v1.59 — runSoldeWatch : la depense des fournisseurs RECHARGEABLES deduite de la baisse du solde.
 *
 * Appelle le VRAI point d'entree `scheduled()` de src/index.js. Fournisseurs et Telegram simules
 * par un faux `fetch`, KV en memoire. Puis une MUTATION (une recharge comptee comme une baisse
 * negative -> plus aucune protection) doit rougir : un banc qui ne sait pas rougir ne prouve rien.
 *
 * ⚠️ Depot PUBLIC : toutes les cles ci-dessous sont FACTICES.
 *
 *   node test/test_solde_watch.mjs
 */
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const JOUR = 86400000;
const iso = (decalage) => new Date(Date.now() + decalage * JOUR).toISOString().slice(0, 10);

function makeKV(seed = {}) {
  const store = new Map(Object.entries(seed));
  return {
    store,
    async get(k) { return store.has(k) ? store.get(k) : null; },
    async put(k, v) { store.set(k, typeof v === 'string' ? v : JSON.stringify(v)); },
    async delete(k) { store.delete(k); },
    async list({ prefix }) { return { keys: [...store.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })) }; },
  };
}

// Soldes « du jour » renvoyes par les faux fournisseurs, et messages Telegram captes.
let soldes = {};
let telegrams = [];
globalThis.fetch = async (url, init = {}) => {
  const u = String(url);
  const rep = (corps, status = 200) => new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } });
  if (u.includes('api.telegram.org')) { telegrams.push(JSON.parse(init.body).text); return rep({ ok: true }); }
  if (u.includes('deepseek.com/user/balance')) {
    return rep({ is_available: true, balance_infos: [{ currency: 'USD', total_balance: String(soldes.deepseek) }] });
  }
  if (u.includes('moonshot.ai/v1/users/me/balance')) return rep({ code: 0, data: { available_balance: soldes.moonshot } });
  if (u.includes('runpod.io/graphql')) return rep({ data: { myself: { clientBalance: soldes.runpod, currentSpendPerHr: 0 } } });
  if (u.includes('piapi.ai/account/info')) {
    return soldes.piapi === 'casse' ? rep({ message: 'not found' }, 404) : rep({ code: 200, data: { equivalent_in_usd: soldes.piapi } });
  }
  return rep({}, 404);
};

// Historique. deepseek baisse de 0,20 $/j. moonshot : 3 RECHARGES (+10 $) sur 6 jours, 0,10 $/j sinon —
// si une recharge etait comptee comme une baisse negative, la mediane passerait sous zero et
// aveuglerait la detection d'anomalie : c'est ce que la mutation doit prouver.
function makeEnv() {
  const hist = {
    deepseek: { [iso(-5)]: 20.0, [iso(-4)]: 19.8, [iso(-3)]: 19.6, [iso(-2)]: 19.4, [iso(-1)]: 19.2 },
    moonshot: { [iso(-7)]: 5.0, [iso(-6)]: 4.9, [iso(-5)]: 14.9, [iso(-4)]: 14.8, [iso(-3)]: 24.8, [iso(-2)]: 24.7, [iso(-1)]: 34.7 },
    runpod:   { [iso(-1)]: 40.0 },
    piapi:    { [iso(-1)]: 3.0 },
  };
  return { GATEWAY_KV: makeKV({ 'soldewatch:hist': JSON.stringify(hist), 'key:DEEPSEEK_KEY': 'f', 'key:MOONSHOT_KEY': 'f',
                                 'key:RUNPOD_KEY': 'f', 'key:PIAPI_KEY': 'f', 'key:TELEGRAM_BOT_TOKEN': 'f' }) };
}

async function passage(worker, soldesDuJour) {
  soldes = soldesDuJour; telegrams = [];
  const env = makeEnv();
  const attente = [];
  await worker.scheduled({}, env, { waitUntil: (p) => attente.push(p) });
  await Promise.allSettled(attente);
  const last = JSON.parse(env.GATEWAY_KV.store.get('soldewatch:last') || '{}');
  return { alertes: last.alerts || [], telegrams, env, last };
}

const NORMAL = { deepseek: 19.0, moonshot: 34.6, runpod: 38.0, piapi: 2.9 };
const CAS = [
  ['journee normale partout -> aucune alerte, aucun Telegram', NORMAL,
    (r) => r.alertes.length === 0 && r.telegrams.length === 0],
  ['deepseek brule 3 $ (15x sa mediane de 0,20) -> [anomalie] deepseek', { ...NORMAL, deepseek: 16.2 },
    (r) => r.alertes.some((a) => a.startsWith('[anomalie] deepseek')) && r.telegrams.length === 1],
  ['deepseek brule 8 $ -> [seuil] deepseek', { ...NORMAL, deepseek: 11.2 },
    (r) => r.alertes.some((a) => a.startsWith('[seuil] deepseek'))],
  ['recharges de moonshot : la hausse ne cree NI alerte NI fausse mediane', NORMAL,
    (r) => !r.alertes.some((a) => a.includes('moonshot')) && r.last.soldes.moonshot.baisse24h === 0.1],
  ['moonshot brule 2 $ (20x) malgre 3 recharges passees -> [anomalie] moonshot', { ...NORMAL, moonshot: 32.7 },
    (r) => r.alertes.some((a) => a.startsWith('[anomalie] moonshot'))],
  ['runpod brule 20 $ (pod oublie) -> [seuil] runpod (seuil 15)', { ...NORMAL, runpod: 20.0 },
    (r) => r.alertes.some((a) => a.startsWith('[seuil] runpod'))],
  ['piapi a 0,50 $ -> [solde-bas] piapi', { ...NORMAL, piapi: 0.5 },
    (r) => r.alertes.some((a) => a.startsWith('[solde-bas] piapi'))],
  ['piapi repond 404 -> [casse] piapi, les 3 autres releves quand meme', { ...NORMAL, piapi: 'casse' },
    (r) => r.alertes.some((a) => a.startsWith('[casse] piapi')) && r.last.soldes.deepseek.solde === 19.0],
  ['la garde : un 2e passage le meme jour ne resonde rien', NORMAL, null],
];

async function batterie(worker) {
  const res = [];
  for (const [nom, sd, attendu] of CAS) {
    if (!attendu) {
      soldes = sd; telegrams = [];
      const env = makeEnv();
      const w = []; await worker.scheduled({}, env, { waitUntil: (p) => w.push(p) }); await Promise.allSettled(w);
      const avant = env.GATEWAY_KV.store.get('soldewatch:last');
      soldes = { ...sd, deepseek: 1.0 };   // si ca resondait, deepseek crierait
      const w2 = []; await worker.scheduled({}, env, { waitUntil: (p) => w2.push(p) }); await Promise.allSettled(w2);
      res.push([nom, env.GATEWAY_KV.store.get('soldewatch:last') === avant, '']);
      continue;
    }
    const r = await passage(worker, sd);
    res.push([nom, attendu(r), JSON.stringify(r.alertes)]);
  }
  return res;
}

let echecs = 0;
console.log('v1.59 (src/index.js)');
const actuel = (await import('../src/index.js')).default;
for (const [nom, ok, detail] of await batterie(actuel)) {
  if (!ok) echecs++;
  console.log(`  ${ok ? 'OK   ' : 'ECHEC'} ${nom}  ${ok ? '' : '— ' + detail}`);
}

console.log('\nMUTATION — une recharge comptee comme une baisse (garde « baisse >= 0 » retiree) DOIT rougir');
let dossier;
try {
  const source = readFileSync(join(ICI, '../src/index.js'), 'utf8');
  const cible = '    if (baisse >= 0) out[ap] = Math.round(baisse * 1e6) / 1e6;';
  if (!source.includes(cible)) throw new Error('garde introuvable');
  dossier = mkdtempSync(join(tmpdir(), 'banc-solde-'));
  const fichier = join(dossier, 'index_mute.mjs');
  writeFileSync(fichier, source.replace(cible, '    out[ap] = Math.round(baisse * 1e6) / 1e6;'));
  const mute = (await import(pathToFileURL(fichier).href)).default;
  const rouges = (await batterie(mute)).filter(([, ok]) => !ok).map(([nom]) => nom);
  const attendu = 'moonshot brule 2 $ (20x) malgre 3 recharges passees -> [anomalie] moonshot';
  const ok = rouges.includes(attendu);
  if (!ok) echecs++;
  console.log(`  ${ok ? 'OK   ' : 'ECHEC'} rougit : ${attendu}`);
} catch (e) {
  echecs++;
  console.log(`  ECHEC mutation NON jouee (${e.message})`);
} finally {
  if (dossier) rmSync(dossier, { recursive: true, force: true });
}

console.log(echecs ? `\n${echecs} ECHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
