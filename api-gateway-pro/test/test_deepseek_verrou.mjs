/**
 * Banc v1.25.2 — /api/deepseek : une cle client ne peut faire facturer que deepseek-flash, max_tokens borne.
 *
 * Avant : le corps partait tel quel -> modele au choix (deepseek-v4-pro), max_tokens libre, gratuit pour sv_.
 * Appelle le VRAI worker, DeepSeek simule par un faux `fetch` qui note le corps REELLEMENT envoye.
 * Puis rejoue la meme batterie contre la v1.25.1 tiree de git : les cas d'abus DOIVENT rougir.
 *
 * ⚠️ Depot PUBLIC : cles, email et jetons ci-dessous sont FACTICES.
 *
 *   node test/test_deepseek_verrou.mjs
 */
import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const COMMIT_AVANT = '39189fb';          // v1.25.1 : corps DeepSeek relaye tel quel
const CLES = { sv: 'sv_bancDeepseekFactice000000', swp: 'swp_bancDeepseekFactice00000' };

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
    [`pro:${CLES.sv}`]: JSON.stringify({ email: 'banc@test.invalid', plan: 'prepaid', app: 'sv', credits: 1000 }),
    [`pro:${CLES.swp}`]: JSON.stringify({ email: 'banc2@test.invalid', plan: 'pro', active: true }),
    'apikey:DEEPSEEK_KEY': 'factice',
  }),
});

let envoyes = [];
globalThis.fetch = async (url, init) => {
  if (String(url).includes('deepseek.com')) envoyes.push(JSON.parse(typeof init.body === 'string' ? init.body : await new Response(init.body).text()));
  return new Response('{"choices":[{"message":{"content":"OK"}}]}', { status: 200, headers: { 'Content-Type': 'application/json' } });
};

async function appeler(worker, qui, corps) {
  const env = makeEnv(); const attente = []; envoyes = [];
  const req = new Request('https://gw.banc.invalid/api/deepseek', { method: 'POST',
    headers: { 'X-Pro-Key': CLES[qui], 'Content-Type': 'application/json', 'CF-Connecting-IP': '203.0.113.9' },
    body: typeof corps === 'string' ? corps : JSON.stringify(corps) });
  let statut;
  try { statut = (await worker.fetch(req, env, { waitUntil: (p) => attente.push(p) })).status; } catch (e) { statut = 'exception'; }
  while (attente.length) await Promise.allSettled(attente.splice(0));
  return { statut, envoye: envoyes[0] || null };
}

const MSG = [{ role: 'user', content: 'x' }];
const CAS = [
  ['SubWhisper Pro (payload exact de l\'app) → relaye intact', 'swp',
    { model: 'deepseek-flash', stream: true, thinking: { type: 'disabled' }, messages: MSG, max_tokens: 8192, temperature: 0 },
    (r) => r.statut === 200 && r.envoye?.model === 'deepseek-flash' && r.envoye.max_tokens === 8192 && r.envoye.stream === true, true],
  ['StoryVoice sv_ (deepseek-v4-flash) → relaye intact', 'sv',
    { model: 'deepseek-v4-flash', thinking: { type: 'disabled' }, messages: MSG, max_tokens: 2000 },
    (r) => r.statut === 200 && r.envoye?.model === 'deepseek-v4-flash' && r.envoye.max_tokens === 2000, true],
  ['sv_ demande deepseek-v4-pro → ramene a flash', 'sv', { model: 'deepseek-v4-pro', messages: MSG },
    (r) => r.statut === 200 && r.envoye?.model === 'deepseek-flash', false],
  ['swp demande deepseek-v4-pro → ramene a flash', 'swp', { model: 'deepseek-v4-pro', messages: MSG, max_tokens: 100 },
    (r) => r.statut === 200 && r.envoye?.model === 'deepseek-flash', false],
  ['max_tokens 384000 → plafonne a 8192', 'sv', { model: 'deepseek-flash', messages: MSG, max_tokens: 384000 },
    (r) => r.statut === 200 && r.envoye?.max_tokens === 8192, false],
  ['thinking enabled + reasoning_effort max → desactive', 'sv',
    { model: 'deepseek-flash', messages: MSG, thinking: { type: 'enabled' }, reasoning_effort: 'max' },
    (r) => r.statut === 200 && r.envoye?.thinking?.type === 'disabled' && !('reasoning_effort' in r.envoye), false],
  ['corps de 400 000 car. → 413, DeepSeek jamais appele', 'sv',
    { model: 'deepseek-flash', messages: [{ role: 'user', content: 'x'.repeat(400000) }] },
    (r) => r.statut === 413 && r.envoye === null, false],
  ['StoryVoice lot maximal (60 000 car.) → relaye', 'sv',
    { model: 'deepseek-v4-flash', thinking: { type: 'disabled' }, messages: [{ role: 'user', content: 'x'.repeat(62000) }], max_tokens: 6000 },
    (r) => r.statut === 200 && r.envoye?.messages[0].content.length === 62000, true],
  ['corps non-JSON → 400, DeepSeek jamais appele', 'sv', 'pas du json',
    (r) => r.statut === 400 && r.envoye === null, false],
];

async function batterie(worker) {
  const res = [];
  for (const [nom, qui, corps, attendu, legitime] of CAS) {
    const r = await appeler(worker, qui, corps);
    res.push([nom, attendu(r), JSON.stringify({ statut: r.statut, model: r.envoye?.model, max_tokens: r.envoye?.max_tokens }), legitime]);
  }
  return res;
}

let echecs = 0;
console.log('v1.25.2 (src/index.js)');
const actuel = (await import('../src/index.js')).default;
for (const [nom, ok, detail] of await batterie(actuel)) {
  if (!ok) echecs++;
  console.log(`  ${ok ? 'OK   ' : 'ECHEC'} ${nom}  — ${detail}`);
}
console.log(`\nMUTATION — la meme batterie contre la v1.25.1 (${COMMIT_AVANT}) : les abus DOIVENT rougir`);
let dossier;
try {
  const racine = execSync('git rev-parse --show-toplevel', { cwd: ICI }).toString().trim();
  const source = execSync(`git show ${COMMIT_AVANT}:api-gateway-pro/src/index.js`, { cwd: racine, maxBuffer: 16 << 20 });
  dossier = mkdtempSync(join(tmpdir(), 'banc-ds-'));
  const fichier = join(dossier, 'index_v1251.mjs');
  writeFileSync(fichier, source);
  const ancien = (await import(pathToFileURL(fichier).href)).default;
  for (const [nom, ok, , legitime] of await batterie(ancien)) {
    const bon = legitime ? ok : !ok;
    if (!bon) echecs++;
    console.log(`  ${bon ? 'OK   ' : 'ECHEC'} ${legitime ? 'reste vert' : 'rougit'} sur la v1.25.1 : ${nom}`);
  }
} catch (e) {
  echecs++;
  console.log(`  ECHEC mutation NON jouee (${e.message}) — un banc qui ne peut pas rougir ne prouve rien`);
} finally {
  if (dossier) rmSync(dossier, { recursive: true, force: true });
}
console.log(echecs ? `\n${echecs} ECHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
