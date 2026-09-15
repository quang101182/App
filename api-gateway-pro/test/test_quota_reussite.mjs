/**
 * Banc v1.24.0 — le quota d'un client ne compte que ce qui a REUSSI chez le fournisseur.
 *
 * Avant : `incrementUsage` partait AVANT le proxy. Un 429/5xx de DeepSeek sature (14/09), une
 * coupure reseau, un refus : tout consommait le quota mensuel du client payant.
 *
 * Ce banc appelle le VRAI worker (import de src/index.js), fournisseurs simules par un faux
 * `fetch`, KV en memoire. Puis il rejoue la MEME batterie contre la v1.23.0 tiree de l'historique
 * git (`de26852`) : elle DOIT rougir. Un banc vert qui ne sait pas rougir ne prouve rien.
 *
 * ⚠️ Depot PUBLIC : cle, email et jetons ci-dessous sont FACTICES.
 *
 *   node test/test_quota_reussite.mjs
 */
import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const CLE = 'swp_bancQuotaFactice0000000';
const COMMIT_AVANT = 'de26852';          // v1.23.0 : decompte avant le proxy

function moisCourant() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

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

function makeEnv({ tx = 0, tr = 0 } = {}) {
  return {
    ADMIN_TOKEN: 'banc-admin-factice',
    PRO_KV: makeKV({
      [`pro:${CLE}`]: JSON.stringify({
        email: 'banc@test.invalid', plan: 'pro', created: '2026-09-15',
        monthlyUsage: { [moisCourant()]: { transcriptions: tx, translations: tr } },
      }),
      'apikey:GEMINI_KEY': 'factice', 'apikey:GROQ_KEY': 'factice', 'apikey:ASSEMBLYAI_KEY': 'factice',
      'apikey:DEEPSEEK_KEY': 'factice', 'apikey:AZURE_KEY': 'factice', 'cfg:azure:region': 'francecentral',
    }),
  };
}

// ── Faux fournisseurs ────────────────────────────────────────────────────────
let fournisseur = { status: 200 };
let appelsFournisseur = 0;
let ctxCourant = null;
let inscriptionsAuFournisseur = -1;
globalThis.fetch = async () => {
  appelsFournisseur++;
  // Combien de tâches `waitUntil` existent AU MOMENT où le fournisseur est appelé : si le
  // décompte n'y est pas encore, un client qui coupe pendant l'attente y échappe.
  inscriptionsAuFournisseur = ctxCourant ? ctxCourant.n : -1;
  if (fournisseur.jette) throw new TypeError('network connection lost (banc)');
  return new Response(fournisseur.corps ?? '[{"translations":[{"text":"ok","to":"fr"}]}]', {
    status: fournisseur.status, headers: { 'Content-Type': 'application/json' },
  });
};

async function appeler(worker, env, chemin, { methode = 'POST', entetes = {} } = {}) {
  // Limite de debit : 10/min par cle - le banc efface ses compteurs entre deux appels.
  for (const k of [...env.PRO_KV.store.keys()]) if (k.startsWith('rl:')) env.PRO_KV.store.delete(k);
  const attente = [];
  const ctx = { n: 0, waitUntil: (p) => { ctx.n++; attente.push(p); } };
  ctxCourant = ctx;
  inscriptionsAuFournisseur = -1;
  const req = new Request(`https://gw.banc.invalid${chemin}?to=fr`, {
    method: methode,
    headers: { 'X-Pro-Key': CLE, 'Content-Type': 'application/json', 'CF-Connecting-IP': '203.0.113.9', ...entetes },
    body: methode === 'GET' ? undefined : '{}',
  });
  let statut;
  try {
    statut = (await worker.fetch(req, env, ctx)).status;
  } catch {
    statut = 'exception';
  }
  // `incrementUsage` empile lui-meme un waitUntil (l'ecriture KV) : on vide jusqu'au calme.
  while (attente.length) await Promise.allSettled(attente.splice(0));
  const d = JSON.parse(env.PRO_KV.store.get(`pro:${CLE}`));
  const m = (d.monthlyUsage || {})[moisCourant()] || {};
  return { statut, tx: m.transcriptions || 0, tr: m.translations || 0, inscrits: inscriptionsAuFournisseur };
}

const CAS = [
  ['DeepSeek 200 → 1 traduction comptée', '/api/deepseek', { status: 200 }, {}, (r) => r.statut === 200 && r.tr === 1 && r.tx === 0],
  // Revue Codex 15/09 : 1 tâche = l'empreinte (v1.23.0), la 2ᵉ doit être le décompte, DÉJÀ inscrit.
  ['client qui coupe : décompte confié à waitUntil AVANT le fournisseur', '/api/deepseek', { status: 200 }, {},
    (r) => r.tr === 1 && r.inscrits >= 2],
  ['DeepSeek 429 → rien, et le client voit le 429', '/api/deepseek', { status: 429 }, {}, (r) => r.statut === 429 && r.tr === 0],
  ['DeepSeek 503 → rien', '/api/deepseek', { status: 503 }, {}, (r) => r.tr === 0],
  ['DeepSeek coupure réseau → rien', '/api/deepseek', { jette: true }, {}, (r) => r.tr === 0],
  ['Gemini 200 → 1', '/api/gemini/generate', { status: 200 }, {}, (r) => r.tr === 1],
  ['Gemini 500 → rien', '/api/gemini/generate', { status: 500 }, {}, (r) => r.tr === 0],
  ['Groq 200 → 1 transcription', '/api/groq', { status: 200 }, {}, (r) => r.tx === 1 && r.tr === 0],
  ['Groq 400 → rien', '/api/groq', { status: 400 }, {}, (r) => r.tx === 0],
  ['Azure 200 → 1', '/api/azure', { status: 200 }, {}, (r) => r.tr === 1],
  ['Azure 401 → rien', '/api/azure', { status: 401 }, {}, (r) => r.tr === 0],
  ['AssemblyAI création 200 → 1', '/api/assemblyai', { status: 200 },
    { methode: 'POST', entetes: { 'X-Api-Path': '/v2/transcript' } }, (r) => r.tx === 1],
  // Contournement : une query ajoutée au chemin de création ne doit PAS échapper au décompte.
  ['AssemblyAI création avec query (?x) → 1 quand même', '/api/assemblyai', { status: 200 },
    { methode: 'POST', entetes: { 'X-Api-Path': '/v2/transcript?x=1' } }, (r) => r.tx === 1],
  ['AssemblyAI envoi du fichier → rien', '/api/assemblyai', { status: 200 },
    { methode: 'POST', entetes: { 'X-Api-Path': '/v2/upload' } }, (r) => r.tx === 0],
  ['AssemblyAI suivi (GET) → rien', '/api/assemblyai', { status: 200 },
    { methode: 'GET', entetes: { 'X-Api-Path': '/v2/transcript/abc' } }, (r) => r.tx === 0],
];

async function batterie(worker) {
  const res = [];
  for (const [nom, chemin, rep, opts, attendu] of CAS) {
    fournisseur = rep;
    const r = await appeler(worker, makeEnv(), chemin, opts);
    res.push([nom, attendu(r), JSON.stringify(r)]);
  }
  // Trois succès d'affilée s'additionnent (le décompte n'est pas perdu en route).
  fournisseur = { status: 200 };
  const env = makeEnv();
  let r;
  for (let i = 0; i < 3; i++) r = await appeler(worker, env, '/api/deepseek');
  res.push(['3 succès → 3', r.tr === 3, JSON.stringify(r)]);
  // Quota atteint : refus AVANT le fournisseur, et rien de plus.
  const avant = appelsFournisseur;
  r = await appeler(worker, makeEnv({ tr: 500 }), '/api/deepseek');
  res.push(['quota atteint → 429 sans appeler le fournisseur', r.statut === 429 && r.tr === 500
    && appelsFournisseur === avant, JSON.stringify(r)]);
  return res;
}

let echecs = 0;
console.log('v1.24.0 (src/index.js)');
const actuel = (await import('../src/index.js')).default;
for (const [nom, ok, detail] of await batterie(actuel)) {
  if (!ok) echecs++;
  console.log(`  ${ok ? 'OK   ' : 'ECHEC'} ${nom}  — ${detail}`);
}

console.log(`\nMUTATION — la même batterie contre la v1.23.0 (${COMMIT_AVANT}) DOIT rougir`);
let dossier;
try {
  const racine = execSync('git rev-parse --show-toplevel', { cwd: ICI }).toString().trim();
  const source = execSync(`git show ${COMMIT_AVANT}:api-gateway-pro/src/index.js`, { cwd: racine, maxBuffer: 16 << 20 });
  dossier = mkdtempSync(join(tmpdir(), 'banc-quota-'));
  const fichier = join(dossier, 'index_v1230.mjs');
  writeFileSync(fichier, source);
  const ancien = (await import(pathToFileURL(fichier).href)).default;
  const rouges = (await batterie(ancien)).filter(([, ok]) => !ok).map(([nom]) => nom);
  const attendus = ['DeepSeek 429 → rien, et le client voit le 429', 'DeepSeek coupure réseau → rien',
    'Groq 400 → rien', 'AssemblyAI suivi (GET) → rien'];
  for (const nom of attendus) {
    const rouge = rouges.includes(nom);
    if (!rouge) echecs++;
    console.log(`  ${rouge ? 'OK   ' : 'ECHEC'} rougit sur la v1.23.0 : ${nom}`);
  }
} catch (e) {
  echecs++;
  console.log(`  ECHEC mutation NON jouée (${e.message}) — un banc qui ne peut pas rougir ne prouve rien`);
} finally {
  if (dossier) rmSync(dossier, { recursive: true, force: true });
}

console.log('\nMUTATION 2 — « attendre le fournisseur PUIS inscrire le décompte » (1re version) DOIT rougir');
let dossier2;
try {
  const { readFileSync } = await import('node:fs');
  const source = readFileSync(join(ICI, '../src/index.js'), 'utf8');
  const debut = source.indexOf('function relayerEtCompter(');
  const fin = source.indexOf('\n}\n', debut);
  if (debut < 0 || fin < 0) throw new Error('relayerEtCompter introuvable');
  const sabote = source.slice(0, debut)
    + 'async function relayerEtCompter(promesseReponse, proKey, type, env, ctx) {\n'
    + '  const rep = await promesseReponse;\n'
    + '  if (rep && rep.ok) ctx.waitUntil(incrementUsage(proKey, type, env, ctx));\n'
    + '  return rep;'
    + source.slice(fin);
  dossier2 = mkdtempSync(join(tmpdir(), 'banc-quota2-'));
  const fichier = join(dossier2, 'index_attendre_puis_compter.mjs');
  writeFileSync(fichier, sabote);
  const mute = (await import(pathToFileURL(fichier).href)).default;
  const rouges = (await batterie(mute)).filter(([, ok]) => !ok).map(([nom]) => nom);
  const nom = 'client qui coupe : décompte confié à waitUntil AVANT le fournisseur';
  const rouge = rouges.includes(nom);
  if (!rouge) echecs++;
  console.log(`  ${rouge ? 'OK   ' : 'ECHEC'} rougit : ${nom}` + (rouges.length > 1 ? ` (autres rouges : ${rouges.length - 1})` : ''));
} catch (e) {
  echecs++;
  console.log(`  ECHEC mutation 2 NON jouée (${e.message})`);
} finally {
  if (dossier2) rmSync(dossier2, { recursive: true, force: true });
}

console.log(echecs ? `\n${echecs} ÉCHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
