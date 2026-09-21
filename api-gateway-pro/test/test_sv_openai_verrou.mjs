/**
 * Banc v1.25.0 — une cle sv_ (StoryVoice) ne peut faire facturer a OpenAI QUE de la voix, decomptee.
 *
 * Avant : tout X-Api-Path autre que /v1/audio/speech partait en passthrough vers OpenAI, non
 * decompte, modele au choix du client. Une cle vendue = acces gratuit a l'API de Quang.
 *
 * Appelle le VRAI worker (import de src/index.js), OpenAI simule par un faux `fetch`, KV en
 * memoire. Puis rejoue la MEME batterie contre la v1.24.1 tiree de git : elle DOIT rougir.
 *
 * ⚠️ Depot PUBLIC : cle, email et jetons ci-dessous sont FACTICES.
 *
 *   node test/test_sv_openai_verrou.mjs
 */
import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const CLE = 'sv_bancVerrouFactice00000000';
const COMMIT_AVANT = 'd63e13d';          // v1.24.1 : passthrough OpenAI ouvert

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

const makeEnv = () => ({
  ADMIN_TOKEN: 'banc-admin-factice',
  PRO_KV: makeKV({
    [`pro:${CLE}`]: JSON.stringify({ email: 'banc@test.invalid', plan: 'prepaid', app: 'sv', credits: 1000 }),
    'apikey:OPENAI_KEY': 'factice',
  }),
});

// ── Faux OpenAI : on note chaque URL reellement appelee ─────────────────────
let appels = [];
globalThis.fetch = async (url) => {
  appels.push(String(url));
  return new Response('ok', { status: 200, headers: { 'Content-Type': 'audio/mpeg' } });
};

async function appeler(worker, env, apiPath, corps) {
  const attente = [];
  const ctx = { waitUntil: (p) => attente.push(p) };
  appels = [];
  const entetes = { 'X-Pro-Key': CLE, 'Content-Type': 'application/json', 'CF-Connecting-IP': '203.0.113.9' };
  if (apiPath) entetes['X-Api-Path'] = apiPath;
  const req = new Request('https://gw.banc.invalid/api/openai', {
    method: 'POST', headers: entetes, body: JSON.stringify(corps),
  });
  let statut;
  try { statut = (await worker.fetch(req, env, ctx)).status; } catch { statut = 'exception'; }
  while (attente.length) await Promise.allSettled(attente.splice(0));
  const d = JSON.parse(env.PRO_KV.store.get(`pro:${CLE}`));
  return { statut, openai: appels.filter((u) => u.includes('openai.com')), credits: d.credits };
}

const VOIX = { model: 'gpt-4o-mini-tts', voice: 'nova', input: 'Bonjour', response_format: 'mp3',
  instructions: 'Lis en français avec un ton neutre.' };
const CAS = [
  // Le chemin legitime de l'app doit rester intact, et decompte.
  ['voix legitime (payload exact de l\'app) → 200, 7 credits debites', '/v1/audio/speech', VOIX,
    (r) => r.statut === 200 && r.openai.length === 1 && r.credits === 993],
  ['voix tts-1 (anciennes versions) → 200', '/v1/audio/speech', { ...VOIX, model: 'tts-1' },
    (r) => r.statut === 200 && r.openai.length === 1],
  // La faille elle-meme.
  ['chat gpt-5.6-sol → refuse, OpenAI jamais appele', '/v1/chat/completions',
    { model: 'gpt-5.6-sol', messages: [{ role: 'user', content: 'x' }] },
    (r) => r.statut === 403 && r.openai.length === 0],
  ['sans X-Api-Path (defaut = chat) → refuse', null,
    { model: 'gpt-4o-mini', messages: [{ role: 'user', content: 'x' }] },
    (r) => r.statut === 403 && r.openai.length === 0],
  ['/v1/responses → refuse', '/v1/responses', { model: 'gpt-6-astra', input: 'x' },
    (r) => r.statut === 403 && r.openai.length === 0],
  // La voix elle-meme ne doit pas devenir une porte.
  ['voix tts-1-hd (2x le prix) → refuse', '/v1/audio/speech', { ...VOIX, model: 'tts-1-hd' },
    (r) => r.statut === 400 && r.openai.length === 0],
  ['voix input non-texte (0 credit debite) → refuse', '/v1/audio/speech', { ...VOIX, input: ['Bonjour'] },
    (r) => r.statut === 400 && r.openai.length === 0],
  ['voix instructions geantes (facturees, jamais debitees) → refuse', '/v1/audio/speech',
    { ...VOIX, instructions: 'x'.repeat(5000) }, (r) => r.statut === 400 && r.openai.length === 0],
];

async function batterie(worker) {
  const res = [];
  for (const [nom, apiPath, corps, attendu] of CAS) {
    const r = await appeler(worker, makeEnv(), apiPath, corps);
    res.push([nom, attendu(r), JSON.stringify(r)]);
  }
  return res;
}

let echecs = 0;
console.log('v1.25.0 (src/index.js)');
const actuel = (await import('../src/index.js')).default;
for (const [nom, ok, detail] of await batterie(actuel)) {
  if (!ok) echecs++;
  console.log(`  ${ok ? 'OK   ' : 'ECHEC'} ${nom}  — ${detail}`);
}

console.log(`\nMUTATION — la meme batterie contre la v1.24.1 (${COMMIT_AVANT}) DOIT rougir`);
let dossier;
try {
  const racine = execSync('git rev-parse --show-toplevel', { cwd: ICI }).toString().trim();
  const source = execSync(`git show ${COMMIT_AVANT}:api-gateway-pro/src/index.js`, { cwd: racine, maxBuffer: 16 << 20 });
  dossier = mkdtempSync(join(tmpdir(), 'banc-sv-'));
  const fichier = join(dossier, 'index_v1241.mjs');
  writeFileSync(fichier, source);
  const ancien = (await import(pathToFileURL(fichier).href)).default;
  const res = await batterie(ancien);
  const rouges = res.filter(([, ok]) => !ok).map(([nom]) => nom);
  // Les deux cas legitimes doivent rester verts sur l'ancienne version (sinon le banc ment),
  // tous les autres doivent rougir.
  for (const [nom] of res) {
    const legitime = nom.startsWith('voix legitime') || nom.startsWith('voix tts-1 (');
    const ok = legitime ? !rouges.includes(nom) : rouges.includes(nom);
    if (!ok) echecs++;
    console.log(`  ${ok ? 'OK   ' : 'ECHEC'} ${legitime ? 'reste vert' : 'rougit'} sur la v1.24.1 : ${nom}`);
  }
} catch (e) {
  echecs++;
  console.log(`  ECHEC mutation NON jouee (${e.message}) — un banc qui ne peut pas rougir ne prouve rien`);
} finally {
  if (dossier) rmSync(dossier, { recursive: true, force: true });
}

console.log(echecs ? `\n${echecs} ECHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
