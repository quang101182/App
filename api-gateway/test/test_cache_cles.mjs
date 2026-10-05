/**
 * Banc v1.74 — cache memoire des cles d'API (60 s par isolat) + trace des lectures KV lentes.
 *
 * Contexte (05/10/2026) : au datacenter CDG, `key:GROQ_KEY` se lisait en 5,08 s a CHAQUE appel. Le cache
 * doit ramener ce cout a une lecture par minute et par isolat, sans jamais servir une cle perimee apres
 * un set/delete par l'admin. Passe par le VRAI point d'entree `fetch()` ; KV simule avec compteur de
 * lectures et latence reglable. Puis des MUTATIONS doivent rougir.
 * ⚠️ Depot PUBLIC : toutes les valeurs ci-dessous sont FACTICES.
 *
 *   node test/test_cache_cles.mjs
 */
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ICI = dirname(fileURLToPath(import.meta.url));
const SRC = join(ICI, '../src');
const GW = 'https://gw.test';
const reel = Date.now;

function makeKV(seed, lectures, lenteur) {
  const store = new Map(Object.entries(seed));
  return {
    store,
    async get(k, type) {
      lectures.push(k);
      if (lenteur.ms) Date.now = ((avance) => () => reel() + avance)(lenteur.ms);   // horloge avancee = lecture « lente »
      const v = store.has(k) ? store.get(k) : null;
      return v && type === 'json' ? JSON.parse(v) : v;
    },
    async put(k, v) { store.set(k, typeof v === 'string' ? v : JSON.stringify(v)); },
    async delete(k) { store.delete(k); },
    async list({ prefix }) { return { keys: [...store.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })) }; },
  };
}

async function batterie(worker) {
  const res = [];
  const ok = (nom, cond) => res.push([nom, !!cond]);
  const lectures = [], points = [], lenteur = { ms: 0 };
  const env = {
    GATEWAY_KV: makeKV({ 'key:STUDIO_SECRET': 'VALEUR-1' }, lectures, lenteur),
    GATEWAY_LOG: { writeDataPoint: (p) => points.push(p) },
    WORKER_SECRET: 'ws-factice', ADMIN_TOKEN: 'adm-factice',
  };
  const ctx = { waitUntil: () => {} };
  const appel = async (methode, chemin, jeton, corps) => {
    const r = await worker.fetch(new Request(GW + chemin, { method: methode,
      headers: { Authorization: 'Bearer ' + jeton, 'Content-Type': 'application/json' }, body: corps ? JSON.stringify(corps) : undefined }), env, ctx);
    return { status: r.status, json: await r.json().catch(() => null) };
  };
  const secret = () => appel('GET', '/api/studio-secret', 'ws-factice');
  const nLect = () => lectures.filter((k) => k === 'key:STUDIO_SECRET').length;

  let r = await secret();
  ok('1re lecture : valeur servie depuis le KV', r.json && r.json.secret === 'VALEUR-1' && nLect() === 1);
  r = await secret();
  ok('2e lecture < 60 s : servie par le cache, AUCUNE lecture KV', r.json.secret === 'VALEUR-1' && nLect() === 1);

  r = await appel('POST', '/admin/keys/set', 'adm-factice', { key: 'STUDIO_SECRET', value: 'VALEUR-2' });
  r = await secret();
  ok('apres un set admin : la NOUVELLE valeur, jamais la perimee', r.json.secret === 'VALEUR-2' && nLect() === 2);

  r = await appel('POST', '/admin/keys/delete', 'adm-factice', { key: 'STUDIO_SECRET' });
  r = await secret();
  ok('apres un delete admin : plus de valeur', r.json.secret === '' && nLect() === 3);

  env.GATEWAY_KV.store.set('key:STUDIO_SECRET', 'VALEUR-3');   // ecrit AILLEURS (autre isolat, dashboard)
  Date.now = () => reel() + 61 * 1000;
  r = await secret();
  Date.now = reel;
  ok('ecrit ailleurs : pris en compte apres 60 s', r.json.secret === 'VALEUR-3' && nLect() === 4);

  Date.now = () => reel() + 200 * 1000; lenteur.ms = 200 * 1000 + 5080;   // lecture de 5,08 s
  r = await secret();
  Date.now = reel; lenteur.ms = 0;
  const p = points.find((x) => x.blobs && x.blobs[0] === '#kv-lent');
  ok('lecture KV de 5 s : tracee dans Analytics Engine (#kv-lent, nom, ms)', p && p.blobs[1] === 'STUDIO_SECRET' && p.doubles[0] >= 5000);
  return res;
}

let echecs = 0;
const afficher = (lignes) => lignes.forEach(([nom, okv]) => { if (!okv) echecs++; console.log(`  ${okv ? 'OK   ' : 'ECHEC'} ${nom}`); });
console.log('BATTERIE sur le vrai src/index.js');
afficher(await batterie((await import(pathToFileURL(join(SRC, 'index.js')).href)).default));

async function mutation(titre, cible, remplacement, attendu) {
  console.log(`\nMUTATION — ${titre} DOIT rougir`);
  let dossier;
  try {
    dossier = mkdtempSync(join(tmpdir(), 'banc-cache-'));
    for (const f of ['index.js', 'stt_moteur.js']) copyFileSync(join(SRC, f), join(dossier, f));
    const src = readFileSync(join(SRC, 'index.js'), 'utf8').split('\r\n').join('\n');   // source en CRLF
    if (!src.includes(cible)) throw new Error('cible introuvable');
    writeFileSync(join(dossier, 'index.js'), src.replace(cible, remplacement));
    const mute = (await import(pathToFileURL(join(dossier, 'index.js')).href + '?m=' + Math.random())).default;
    const rouges = (await batterie(mute)).filter(([, o]) => !o).map(([n]) => n);
    const bon = rouges.includes(attendu);
    if (!bon) echecs++;
    console.log(`  ${bon ? 'OK   ' : 'ECHEC'} rougit : ${attendu}${bon ? '' : ' (rouges : ' + rouges.join(' | ') + ')'}`);
  } catch (e) {
    echecs++;
    console.log(`  ECHEC mutation NON jouee (${e.message})`);
  } finally {
    Date.now = reel;
    if (dossier) rmSync(dossier, { recursive: true, force: true });
  }
}

await mutation('pas de cache', 'if (c && Date.now() - c.t < CACHE_CLES_MS) return c.v;', '',
  '2e lecture < 60 s : servie par le cache, AUCUNE lecture KV');
await mutation('set admin sans invalidation', "  _cacheCles.delete(name);\n  return env.GATEWAY_KV.put(", '  return env.GATEWAY_KV.put(',
  'apres un set admin : la NOUVELLE valeur, jamais la perimee');
await mutation('cache eternel', 'Date.now() - c.t < CACHE_CLES_MS', 'true', 'ecrit ailleurs : pris en compte apres 60 s');
await mutation('lecture lente non tracee', "if (ms > 1000 && env.GATEWAY_LOG)", 'if (false)',
  'lecture KV de 5 s : tracee dans Analytics Engine (#kv-lent, nom, ms)');

console.log(echecs ? `\n${echecs} ECHEC(S)` : '\nVERT');
process.exit(echecs ? 1 : 0);
