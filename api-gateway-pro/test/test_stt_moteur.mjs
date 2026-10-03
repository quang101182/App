/**
 * Banc v1.26.0 — MAI-Transcribe-2 pour SubWhisper Pro (P7, 03/10/2026).
 *
 * VRAI worker (import de src/index.js), Azure et Telegram simulés par un faux `fetch`, KV en mémoire.
 * Vérifie : défaut = groq (le déploiement ne change rien), interrupteur admin, lecture par l'app SANS quota,
 * /api/mai = même quota/décompte que Groq (succès seulement), seule une VRAIE panne compte et alerte (≤ 1/h),
 * secondes facturées comptées. Puis des MUTATIONS de src/ doivent faire rougir le banc.
 *
 * ⚠️ Dépôt PUBLIC : clés, jetons et email ci-dessous sont FACTICES.
 *
 *   node test/test_stt_moteur.mjs
 */
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const SRC = join(ICI, '..', 'src');
const CLE = 'swp_bancMaiFactice00000000';
const ADM = 'banc-admin-factice';
const GW = 'https://gw.banc.invalid';

const mois = () => new Date().toISOString().slice(0, 7);
const jour = () => new Date().toISOString().slice(0, 10);

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
    async list({ prefix }) { return { keys: [...store.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })) }; },
  };
}

function makeEnv() {
  return {
    ADMIN_TOKEN: ADM,
    PRO_KV: makeKV({
      [`pro:${CLE}`]: JSON.stringify({ email: 'banc@test.invalid', plan: 'pro', created: '2026-09-15',
        monthlyUsage: { [mois()]: { transcriptions: 0, translations: 0 } } }),
      'apikey:AZURE_SPEECH_KEY': 'FAUSSE-CLE-AZURE', 'apikey:TELEGRAM_BOT_TOKEN': 'FAUX-TOKEN',
      'apikey:GROQ_KEY': 'factice',
    }),
  };
}

const scenario = { azure: 200, tg: 200 };
const journal = { azure: [], tg: [] };
globalThis.fetch = async (u, init = {}) => {
  u = String(u);
  if (u.includes('/speechtotext/transcriptions:transcribe')) {
    journal.azure.push({ url: u, cle: new Headers(init.headers).get('Ocp-Apim-Subscription-Key') });
    if (scenario.azure === 'throw') throw new TypeError('reseau coupe (banc)');
    const st = scenario.azure;
    return new Response(JSON.stringify(st === 200 ? { durationMilliseconds: 360000, phrases: [] } : { error: 'boom' }),
      { status: st, headers: { 'Content-Type': 'application/json' } });
  }
  if (u.includes('api.telegram.org')) { journal.tg.push(JSON.parse(init.body).text); return new Response('{}', { status: scenario.tg }); }
  return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
};

async function batterie(worker) {
  const res = [];
  const ok = (nom, cond) => res.push([nom, !!cond]);
  const env = makeEnv();
  journal.azure = []; journal.tg = []; scenario.azure = 200; scenario.tg = 200;
  const appel = async (method, path, { auth, pro = true, body, headers = {} } = {}) => {
    for (const k of [...env.PRO_KV.store.keys()]) if (k.startsWith('rl:')) env.PRO_KV.store.delete(k);
    const attente = [];
    const ctx = { waitUntil: (p) => attente.push(p) };
    const h = { 'CF-Connecting-IP': '203.0.113.9', ...headers };
    if (pro) h['X-Pro-Key'] = CLE;
    if (auth) h.Authorization = 'Bearer ' + auth;
    const r = await worker.fetch(new Request(GW + path, { method, headers: h, body }), env, ctx);
    const texte = await r.text();
    while (attente.length) await Promise.allSettled(attente.splice(0));
    let json = null; try { json = JSON.parse(texte); } catch { /* pas du JSON */ }
    return { status: r.status, json };
  };
  const tx = () => (JSON.parse(env.PRO_KV.store.get(`pro:${CLE}`)).monthlyUsage[mois()] || {}).transcriptions || 0;
  const corps = () => { const f = new FormData(); f.append('definition', '{}'); f.append('audio', new Blob([new Uint8Array(10)]), 'a.wav'); return f; };

  // ── lecture par l'app
  let r = await appel('GET', '/api/stt-engine?app=swp');
  ok('defaut = groq (le deploiement ne change rien)', r.status === 200 && r.json.engine === 'groq');
  ok('lire le moteur ne consomme AUCUN quota', tx() === 0);
  r = await appel('GET', '/api/stt-engine?app=swp', { pro: false });
  ok('lecture sans cle Pro -> 401', r.status === 401);

  // ── interrupteur admin
  r = await appel('GET', '/admin/stt-engine?app=swp', { pro: false, auth: 'pas-le-bon' });
  ok('admin sans le bon jeton -> 401', r.status === 401);
  r = await appel('GET', '/admin/stt-engine?app=swp', { pro: false, auth: ADM });
  ok('admin GET : 2 moteurs (MAI, Groq), par defaut', r.status === 200 && r.json.moteurs.length === 2 && r.json.par_defaut === true);
  r = await appel('POST', '/admin/stt-engine?app=swp', { pro: false, auth: ADM, body: JSON.stringify({ engine: 'croise' }) });
  ok('moteur non propose a SWP refuse (400)', r.status === 400);
  r = await appel('POST', '/admin/stt-engine?app=swp', { pro: false, auth: ADM, body: JSON.stringify({ engine: 'mai2', source: 'banc' }) });
  ok('bascule groq -> mai2', r.status === 200 && r.json.engine === 'mai2' && r.json.changed_from === 'groq');
  r = await appel('GET', '/api/stt-engine?app=swp');
  ok('l app lit mai2', r.json.engine === 'mai2');

  // ── /api/mai : succes
  r = await appel('POST', '/api/mai', { body: corps() });
  ok('MAI 200 relaye, cle Azure injectee cote serveur', r.status === 200 && journal.azure.at(-1).cle === 'FAUSSE-CLE-AZURE');
  ok('succes = 1 transcription comptee (comme Groq)', tx() === 1);
  ok('succes = 360 s comptees (cout au dashboard)', env.PRO_KV.store.get(`stt:sec:swp:${mois()}`) === '360.0');
  r = await appel('POST', '/api/mai', { pro: false, body: corps() });
  ok('/api/mai sans cle Pro -> 401, Azure jamais appele', r.status === 401 && journal.azure.length === 1);

  // ── 400 = la requete, pas une panne
  scenario.azure = 400;
  r = await appel('POST', '/api/mai', { body: corps() });
  ok('400 : relaye, rien compte, ni panne ni alerte', r.status === 400 && tx() === 1
     && !env.PRO_KV.store.has(`stt:err:swp:${jour()}`) && journal.tg.length === 0);

  // ── vraie panne
  scenario.azure = 503;
  r = await appel('POST', '/api/mai', { body: corps() });
  ok('panne 503 : relayee, pas de transcription comptee', r.status === 503 && tx() === 1);
  ok('panne : compteur + 1 alerte Telegram avec le lien du dashboard',
     env.PRO_KV.store.get(`stt:err:swp:${jour()}`) === '1' && journal.tg.length === 1 && journal.tg[0].includes('dash.se7enai.com'));
  r = await appel('POST', '/api/mai', { body: corps() });
  ok('2e panne la meme heure : PAS de 2e alerte', env.PRO_KV.store.get(`stt:err:swp:${jour()}`) === '2' && journal.tg.length === 1);
  scenario.azure = 'throw';
  r = await appel('POST', '/api/mai', { body: corps() });
  ok('reseau coupe -> 502, rien compte', r.status === 502 && tx() === 1);
  r = await appel('GET', '/admin/stt-engine?app=swp', { pro: false, auth: ADM });
  ok('admin voit pannes + secondes du mois', r.json.errors_today === 3 && r.json.mai_secondes_mois === 360);

  // ── quota : un client au plafond de TRANSCRIPTIONS est refuse AVANT Azure
  scenario.azure = 200;
  const d = JSON.parse(env.PRO_KV.store.get(`pro:${CLE}`));
  d.monthlyUsage[mois()] = { transcriptions: 50, translations: 0 };
  env.PRO_KV.store.set(`pro:${CLE}`, JSON.stringify(d));
  const avantAzure = journal.azure.length;
  r = await appel('POST', '/api/mai', { body: corps() });
  ok('plafond de transcriptions atteint -> 429, Azure jamais appele', r.status === 429 && journal.azure.length === avantAzure);
  d.monthlyUsage[mois()] = { transcriptions: 1, translations: 0 };
  env.PRO_KV.store.set(`pro:${CLE}`, JSON.stringify(d));

  // ── non-regression : Groq inchange
  r = await appel('POST', '/api/groq', { body: corps() });
  ok('Groq toujours servi et compte', r.status === 200 && tx() === 2);
  return res;
}

let echecs = 0;
const worker = (await import(pathToFileURL(join(SRC, 'index.js')).href)).default;
console.log('BATTERIE — worker v1.26.0');
for (const [nom, o] of await batterie(worker)) { if (!o) echecs++; console.log(`  ${o ? 'OK   ' : 'ECHEC'} ${nom}`); }

async function mutation(titre, fichierSrc, cible, remplacement, attendu) {
  console.log(`\nMUTATION — ${titre} DOIT rougir`);
  let dossier;
  try {
    dossier = mkdtempSync(join(tmpdir(), 'banc-pro-stt-'));
    for (const f of ['index.js', 'stt_moteur.js']) copyFileSync(join(SRC, f), join(dossier, f));
    const src = readFileSync(join(SRC, fichierSrc), 'utf8');
    if (!src.includes(cible)) throw new Error('cible introuvable');
    writeFileSync(join(dossier, fichierSrc), src.replace(cible, remplacement));
    const mute = (await import(pathToFileURL(join(dossier, 'index.js')).href + '?m=' + Math.random())).default;
    const rouges = (await batterie(mute)).filter(([, o]) => !o).map(([n]) => n);
    const bon = rouges.includes(attendu);
    if (!bon) echecs++;
    console.log(`  ${bon ? 'OK   ' : 'ECHEC'} rougit : ${attendu}${bon ? '' : ' (rouges : ' + rouges.join(' | ') + ')'}`);
  } catch (e) { echecs++; console.log(`  ECHEC mutation NON jouee (${e.message})`); }
  finally { if (dossier) rmSync(dossier, { recursive: true, force: true }); }
}

await mutation('defaut force a mai2 (le deploiement basculerait les clients payants)', 'stt_moteur.js',
  "defaut: 'groq',", "defaut: 'mai2',", 'defaut = groq (le deploiement ne change rien)');
await mutation('/api/mai soumis au quota des TRADUCTIONS', 'index.js',
  "path === '/api/groq' || path === '/api/mai' ||", "path === '/api/groq' ||", 'plafond de transcriptions atteint -> 429, Azure jamais appele');
await mutation('/api/mai sans decompte sur succes', 'index.js',
  "return relayerEtCompter(proxyMai(request, env, ctx), proKey, 'transcription', env, ctx);", 'return proxyMai(request, env, ctx);',
  'succes = 1 transcription comptee (comme Groq)');
await mutation('un 400 compte comme panne', 'stt_moteur.js',
  'return status >= 500 ||', 'return status >= 400 ||', '400 : relaye, rien compte, ni panne ni alerte');
await mutation('lecture du moteur soumise au quota (placee apres le rate limit)', 'index.js',
  "if (path === '/api/stt-engine' && method === 'GET') {", "if (false) {", 'defaut = groq (le deploiement ne change rien)');

console.log(echecs ? `\n${echecs} ECHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
