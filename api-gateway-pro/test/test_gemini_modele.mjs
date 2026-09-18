/**
 * Banc v1.24.1 — le relais Gemini doit envoyer à Google le modèle que l'APP demande.
 *
 * Panne constatée le 18/09/2026 en filmant SubWhisper Pro : toute traduction Gemini échouait
 * (« Translation unchanged »). L'app met le modèle dans l'URL
 * (/api/gemini/v1beta/models/gemini-3.6-flash:generateContent) mais le gateway ne lisait que
 * l'en-tête X-Api-Path, que l'app n'envoie pas -> repli sur gemini-2.0-flash, retiré par Google
 * -> 404 pour tous les clients. Le repli a masqué le défaut tant que ce modèle existait.
 *
 * Ce banc appelle le VRAI worker, Google simulé par un faux `fetch` qui note l'URL sortante.
 * Puis il rejoue la MÊME batterie contre la version d'avant (HEAD) : elle DOIT rougir.
 *
 * ⚠️ Dépôt PUBLIC : clé, email et jetons ci-dessous sont FACTICES.
 *
 *   node test/test_gemini_modele.mjs
 */
import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const CLE = 'swp_bancGeminiFactice000000';
const APP = '/api/gemini/v1beta/models/gemini-3.6-flash:generateContent';   // ce qu'envoie app.html

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
    [`pro:${CLE}`]: JSON.stringify({ email: 'banc@test.invalid', plan: 'pro', created: '2026-09-18', monthlyUsage: {} }),
    'apikey:GEMINI_KEY': 'factice',
  }),
});

let urlSortante = null;
globalThis.fetch = async (url) => {
  urlSortante = String(url);
  return new Response('{"candidates":[]}', { status: 200, headers: { 'Content-Type': 'application/json' } });
};

async function appeler(worker, chemin, entetes = {}) {
  urlSortante = null;
  const env = makeEnv();
  const attente = [];
  const ctx = { waitUntil: (p) => attente.push(p) };
  const req = new Request(`https://gw.banc.invalid${chemin}`, {
    method: 'POST',
    headers: { 'X-Pro-Key': CLE, 'Content-Type': 'application/json', 'CF-Connecting-IP': '203.0.113.9', ...entetes },
    body: '{}',
  });
  const statut = (await worker.fetch(req, env, ctx)).status;
  while (attente.length) await Promise.allSettled(attente.splice(0));
  // le chemin demandé à Google, sans la clé (?key=...) qui n'a rien à faire dans un rapport
  const vers = urlSortante ? new URL(urlSortante).pathname : null;
  return { statut, vers };
}

const MORT = 'gemini-2.0-flash';
const CAS = [
  ["l'URL de l'app, sans en-tête -> le modèle de l'app (la panne du 18/09)", APP, {},
    (r) => r.vers === '/v1beta/models/gemini-3.6-flash:generateContent'],
  ["l'en-tête X-Api-Path reste prioritaire (clients qui l'envoient)", APP,
    { 'X-Api-Path': '/v1beta/models/gemini-9-pro:generateContent' },
    (r) => r.vers === '/v1beta/models/gemini-9-pro:generateContent'],
  ["/api/gemini sans rien -> repli sur un modèle VIVANT", '/api/gemini', {},
    (r) => r.vers && !r.vers.includes(MORT) && r.vers.includes(':generateContent')],
  ["chemin qui n'est pas un appel de modèle -> repli (comportement conservé)", '/api/gemini/generate', {},
    (r) => !!r.vers && r.vers.includes('/models/') && !r.vers.includes(MORT)],
  ["tentative de sortie du chemin -> repli, jamais la cible injectée", '/api/gemini/v1beta/models/x:generateContent/../../../evil', {},
    (r) => r.vers && !r.vers.includes('evil')],
  ["domaine injecté dans le chemin -> jamais suivi", '/api/gemini//evil.example/v1beta/models/x:generateContent', {},
    (r) => r.vers && !r.vers.includes('evil')],
];

async function batterie(worker) {
  const res = [];
  for (const [nom, chemin, entetes, attendu] of CAS) {
    const r = await appeler(worker, chemin, entetes);
    res.push([nom, !!attendu(r), JSON.stringify(r)]);
  }
  // Aucun appel, quel qu'il soit, ne doit partir vers le modèle retiré.
  const tous = [];
  for (const [, chemin, entetes] of CAS) tous.push((await appeler(worker, chemin, entetes)).vers || '');
  res.push([`aucun appel vers ${MORT}`, !tous.some((v) => v.includes(MORT)), JSON.stringify(tous)]);
  return res;
}

let echecs = 0;
console.log('version courante (src/index.js)');
const actuel = (await import('../src/index.js')).default;
for (const [nom, ok, detail] of await batterie(actuel)) {
  if (!ok) echecs++;
  console.log(`  ${ok ? 'OK   ' : 'ECHEC'} ${nom}  — ${detail}`);
}

console.log('\nMUTATION — la même batterie contre la version d\'avant (HEAD) DOIT rougir');
let dossier;
try {
  const racine = execSync('git rev-parse --show-toplevel', { cwd: ICI }).toString().trim();
  const source = execSync('git show HEAD:api-gateway-pro/src/index.js', { cwd: racine, maxBuffer: 16 << 20 });
  dossier = mkdtempSync(join(tmpdir(), 'banc-gemini-'));
  const fichier = join(dossier, 'index_avant.mjs');
  writeFileSync(fichier, source);
  const ancien = (await import(pathToFileURL(fichier).href)).default;
  const rouges = (await batterie(ancien)).filter(([, ok]) => !ok).map(([nom]) => nom);
  const attendus = [CAS[0][0], CAS[2][0], `aucun appel vers ${MORT}`];
  for (const nom of attendus) {
    const rouge = rouges.includes(nom);
    if (!rouge) echecs++;
    console.log(`  ${rouge ? 'OK   ' : 'ECHEC'} rougit sur la version d'avant : ${nom}`);
  }
} catch (e) {
  echecs++;
  console.log(`  ECHEC mutation NON jouée (${e.message}) — un banc qui ne peut pas rougir ne prouve rien`);
} finally {
  if (dossier) rmSync(dossier, { recursive: true, force: true });
}

console.log(echecs ? `\n${echecs} ÉCHEC(S)` : '\nTOUT VERT (et la version d\'avant rougit bien)');
process.exit(echecs ? 1 : 0);
