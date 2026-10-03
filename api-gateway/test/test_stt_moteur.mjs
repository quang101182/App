/**
 * Banc v1.64 — interrupteur de moteur de transcription par app + relais MAI (/api/mai).
 *
 * Passe par le VRAI point d'entree `fetch()` de src/index.js. Azure et Telegram simules par un faux
 * `fetch`, KV en memoire. Puis des MUTATIONS doivent rougir : un banc qui ne sait pas rougir ne prouve rien.
 * ⚠️ Depot PUBLIC : toutes les valeurs ci-dessous sont FACTICES.
 *
 *   node test/test_stt_moteur.mjs
 */
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const SRC = join(ICI, '../src');
const GW = 'https://gw.test';
const jour = () => new Date().toISOString().slice(0, 10);

function makeKV(seed = {}) {
  const store = new Map(Object.entries(seed));
  return {
    store,
    async get(k, type) {
      if (!store.has(k)) return null;
      const v = store.get(k);
      return type === 'json' ? JSON.parse(v) : v;
    },
    async put(k, v) { store.set(k, typeof v === 'string' ? v : JSON.stringify(v)); },
    async delete(k) { store.delete(k); },
    async list({ prefix }) { return { keys: [...store.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })) }; },
  };
}

/** Faux reseau : Azure repond selon `scenario.azure`, Telegram selon `scenario.tg`. */
function installerFetch(scenario, journal) {
  globalThis.fetch = async (url, init = {}) => {
    const u = String(url);
    if (u.includes('cognitiveservices.azure.com')) {
      journal.azure.push({ url: u, cle: new Headers(init.headers).get('Ocp-Apim-Subscription-Key') });
      if (scenario.azure === 'throw') throw new Error('reseau coupe');
      const st = scenario.azure;
      return new Response(JSON.stringify(st === 200 ? { durationMilliseconds: 360000, combinedPhrases: [{ text: 'ok' }] } : { error: 'boom' }),
        { status: st, headers: { 'content-type': 'application/json' } });
    }
    if (u.includes('api.telegram.org')) {
      journal.tg.push(JSON.parse(init.body).text);
      return new Response('{}', { status: scenario.tg });
    }
    throw new Error('appel reseau inattendu : ' + u);
  };
}

async function batterie(worker) {
  const res = [];
  const ok = (nom, cond) => res.push([nom, !!cond]);
  const env = {
    GATEWAY_KV: makeKV({ 'key:AZURE_SPEECH_KEY': 'FAUSSE-CLE-AZURE', 'key:TELEGRAM_BOT_TOKEN': 'FAUX-TOKEN' }),
    WORKER_SECRET: 'ws-factice', ADMIN_TOKEN: 'adm-factice', DASH_STT_TOKEN: 'dash-factice',
  };
  const scenario = { azure: 200, tg: 200 };
  const journal = { azure: [], tg: [] };
  installerFetch(scenario, journal);
  const appel = async (method, path, { auth, body, headers = {} } = {}) => {
    const attente = [];
    const ctx = { waitUntil: (p) => attente.push(p) };
    const h = { ...headers };
    if (auth) h.Authorization = 'Bearer ' + auth;
    const r = await worker.fetch(new Request(GW + path, { method, headers: h, body }), env, ctx);
    const texte = await r.text();
    await Promise.all(attente);
    let json = null; try { json = JSON.parse(texte); } catch { /* pas du JSON */ }
    return { status: r.status, json, texte };
  };
  const ws = 'ws-factice', adm = 'adm-factice';

  // ── lecture par les apps
  let r = await appel('GET', '/api/stt-engine?app=soustitrage');
  ok('GET /api/stt-engine sans auth -> 401', r.status === 401);
  r = await appel('GET', '/api/stt-engine?app=soustitrage', { auth: ws });
  ok('defaut = croise (rien ne change au deploiement)', r.status === 200 && r.json.engine === 'croise' && r.json.at === null);
  r = await appel('GET', '/api/stt-engine?app=inconnue', { auth: ws });
  ok('app inconnue -> 400', r.status === 400);

  // ── interrupteur admin
  r = await appel('GET', '/admin/stt-engine?app=soustitrage', { auth: ws });
  ok('admin avec le secret des APPS -> 401', r.status === 401);
  r = await appel('GET', '/admin/stt-engine?app=soustitrage', { auth: adm });
  ok('admin GET : etat par defaut + 5 moteurs', r.status === 200 && r.json.par_defaut === true && r.json.moteurs.length === 5);
  r = await appel('POST', '/admin/stt-engine?app=soustitrage', { auth: adm, body: JSON.stringify({ engine: 'bidon' }) });
  ok('moteur inconnu refuse (400) et rien n\'est ecrit', r.status === 400 && !env.GATEWAY_KV.store.has('cfg:stt_engine:soustitrage'));
  r = await appel('POST', '/admin/stt-engine?app=soustitrage', { auth: adm, body: JSON.stringify({ engine: 'mai2', source: 'banc' }) });
  ok('bascule croise -> mai2 horodatee', r.status === 200 && r.json.changed_from === 'croise' && r.json.engine === 'mai2'
     && r.json.changed && r.json.changed.source === 'banc');
  r = await appel('GET', '/api/stt-engine?app=soustitrage', { auth: ws });
  ok('les apps lisent mai2 + date', r.json.engine === 'mai2' && typeof r.json.at === 'string');

  // ── v1.65 : jeton du dashboard = interrupteur SEULEMENT
  const dash = 'dash-factice';
  r = await appel('GET', '/admin/stt-engine?app=soustitrage', { auth: dash });
  ok('jeton dashboard : lit l interrupteur', r.status === 200 && r.json.engine === 'mai2');
  r = await appel('POST', '/admin/stt-engine?app=soustitrage', { auth: dash, body: JSON.stringify({ engine: 'croise', source: 'banc' }) });
  ok('jeton dashboard : bascule mai2 -> croise', r.status === 200 && r.json.engine === 'croise');
  r = await appel('POST', '/admin/stt-engine?app=soustitrage', { auth: dash, body: JSON.stringify({ engine: 'mai2', source: 'banc' }) });
  r = await appel('POST', '/admin/keys/get', { auth: dash, body: JSON.stringify({ name: 'AZURE_SPEECH_KEY' }) });
  ok('jeton dashboard REFUSE sur /admin/keys/get (401)', r.status === 401 && !r.texte.includes('FAUSSE-CLE-AZURE'));

  // ── relais MAI : succes
  const corps = new FormData(); corps.append('definition', '{}'); corps.append('audio', new Blob([new Uint8Array(10)]), 'a.wav');
  r = await appel('POST', '/api/mai', { auth: ws, body: corps });
  ok('MAI 200 relaye tel quel', r.status === 200 && r.json.combinedPhrases[0].text === 'ok');
  ok('cle Azure injectee cote serveur + bon chemin',
     journal.azure.at(-1).cle === 'FAUSSE-CLE-AZURE' && journal.azure.at(-1).url.includes('/speechtotext/transcriptions:transcribe?api-version=2025-10-15'));
  ok('succes = aucun compteur de panne', !env.GATEWAY_KV.store.has(`stt:err:soustitrage:${jour()}`));
  ok('succes = 360 s comptees (jour + mois)', env.GATEWAY_KV.store.get(`stt:sec:soustitrage:${jour()}`) === '360.0'
     && env.GATEWAY_KV.store.get(`stt:sec:soustitrage:${jour().slice(0, 7)}`) === '360.0');
  ok('compteur de debit PROPRE a /api/mai', [...env.GATEWAY_KV.store.keys()].some((k) => k.startsWith('rl:mai:')));

  // ── v1.66 (P5.4) : un 400 = la requete, PAS une panne -> ni compteur ni alerte
  scenario.azure = 400;
  r = await appel('POST', '/api/mai', { auth: ws, body: corps });
  ok('400 (fichier/langue/modele refuses) relaye, mais NI panne NI alerte', r.status === 400
     && !env.GATEWAY_KV.store.has(`stt:err:soustitrage:${jour()}`) && journal.tg.length === 0);

  // ── relais MAI : panne
  scenario.azure = 500;
  r = await appel('POST', '/api/mai', { auth: ws, body: corps });
  ok('panne : erreur relayee (pas de bascule)', r.status === 500 && journal.azure.length === 3);
  ok('panne : compteur 1 + derniere erreur', env.GATEWAY_KV.store.get(`stt:err:soustitrage:${jour()}`) === '1'
     && JSON.parse(env.GATEWAY_KV.store.get('stt:last_error:soustitrage')).status === 500);
  ok('panne : 1 alerte Telegram avec le lien du dashboard', journal.tg.length === 1 && journal.tg[0].includes('dash.se7enai.com'));
  r = await appel('POST', '/api/mai', { auth: ws, body: corps });
  ok('2e panne la meme heure : compteur 2, PAS de 2e alerte', env.GATEWAY_KV.store.get(`stt:err:soustitrage:${jour()}`) === '2' && journal.tg.length === 1);

  // Telegram en echec : le drapeau ne doit PAS etre pose -> la panne suivante realerte
  for (const k of [...env.GATEWAY_KV.store.keys()]) if (k.startsWith('alert:stt_panne:')) env.GATEWAY_KV.store.delete(k);
  scenario.tg = 500;
  await appel('POST', '/api/mai', { auth: ws, body: corps });
  scenario.tg = 200;
  await appel('POST', '/api/mai', { auth: ws, body: corps });
  ok('Telegram refuse -> drapeau non pose -> la panne suivante realerte', journal.tg.length === 3);

  scenario.azure = 'throw';
  r = await appel('POST', '/api/mai', { auth: ws, body: corps });
  ok('reseau coupe -> 502 stt_indisponible', r.status === 502 && r.json.error === 'stt_indisponible');

  // ── l'admin voit la panne
  r = await appel('GET', '/admin/stt-engine?app=soustitrage', { auth: adm });
  ok('admin voit les secondes MAI du mois + prix', r.json.mai_secondes_mois === 360 && r.json.mai_prix_heure === 0.1);
  ok('admin voit pannes du jour + derniere erreur', r.json.errors_today === 5 && r.json.last_error && r.json.engine === 'mai2');
  return res;
}

let echecs = 0;
const afficher = (lignes) => lignes.forEach(([nom, okv]) => { if (!okv) echecs++; console.log(`  ${okv ? 'OK   ' : 'ECHEC'} ${nom}`); });

console.log('BATTERIE sur le vrai src/index.js');
const actuel = (await import(pathToFileURL(join(SRC, 'index.js')).href)).default;
afficher(await batterie(actuel));

/** Rejoue la batterie sur une copie sabotee ; `attendu` = le test qui DOIT rougir. */
async function mutation(titre, fichierSrc, cible, remplacement, attendu) {
  console.log(`\nMUTATION — ${titre} DOIT rougir`);
  let dossier;
  try {
    dossier = mkdtempSync(join(tmpdir(), 'banc-stt-'));
    for (const f of ['index.js', 'stt_moteur.js']) copyFileSync(join(SRC, f), join(dossier, f));
    const src = readFileSync(join(SRC, fichierSrc), 'utf8');
    if (!src.includes(cible)) throw new Error('cible introuvable');
    writeFileSync(join(dossier, fichierSrc), src.replace(cible, remplacement));
    const mute = (await import(pathToFileURL(join(dossier, 'index.js')).href + '?m=' + Math.random())).default;
    const rouges = (await batterie(mute)).filter(([, o]) => !o).map(([n]) => n);
    const ok = rouges.includes(attendu);
    if (!ok) echecs++;
    console.log(`  ${ok ? 'OK   ' : 'ECHEC'} rougit : ${attendu}${ok ? '' : ' (rouges : ' + rouges.join(' | ') + ')'}`);
  } catch (e) {
    echecs++;
    console.log(`  ECHEC mutation NON jouee (${e.message})`);
  } finally {
    if (dossier) rmSync(dossier, { recursive: true, force: true });
  }
}

await mutation('drapeau d\'alerte pose meme si Telegram refuse', 'stt_moteur.js',
  'if (r && r.sent) await kv.put(k', 'await kv.put(k', 'Telegram refuse -> drapeau non pose -> la panne suivante realerte');
await mutation('moteur non valide a la bascule', 'stt_moteur.js',
  'if (!Object.prototype.hasOwnProperty.call(MOTEURS, cible)) {', 'if (false) {', 'moteur inconnu refuse (400) et rien n\'est ecrit');
await mutation('/api/mai sur le compteur commun', 'index.js',
  "mai ? 'mai' : (manga ? 'mgs' : 'api')", "(manga ? 'mgs' : 'api')", 'compteur de debit PROPRE a /api/mai');
await mutation('jeton du dashboard accepte sur tout /admin/', 'index.js',
  "const authErr = await checkBearer(request, env.ADMIN_TOKEN, 'ADMIN_TOKEN');",
  "const authErr = await checkBearer(request, [env.ADMIN_TOKEN, env.DASH_STT_TOKEN], 'ADMIN_TOKEN');",
  'jeton dashboard REFUSE sur /admin/keys/get (401)');
await mutation('jeton du dashboard refuse sur l interrupteur', 'index.js',
  '[env.ADMIN_TOKEN, env.DASH_STT_TOKEN]', 'env.ADMIN_TOKEN', 'jeton dashboard : lit l interrupteur');
await mutation('un 400 compte comme panne', 'stt_moteur.js',
  'return status >= 500 ||', 'return status >= 400 ||', '400 (fichier/langue/modele refuses) relaye, mais NI panne NI alerte');
await mutation('secondes non comptees', 'index.js',
  "compterSecondes(env.GATEWAY_KV, app, j && j.durationMilliseconds)", "null", 'succes = 360 s comptees (jour + mois)');
await mutation('defaut force a mai2 (le deploiement changerait le moteur tout seul)', 'stt_moteur.js',
  "defaut: 'croise',", "defaut: 'mai2',", 'defaut = croise (rien ne change au deploiement)');

console.log(echecs ? `\n${echecs} ECHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
