/**
 * Banc des regles de TEMPS du SRT — extrait les vraies fonctions d'index.html et
 * les fait tourner, plutot que d'en reecrire une copie qui pourrait diverger.
 *
 * Ne que trois defauts mesures le 07/09/2026 sur les SRT reels de Quang :
 *   A. « Voila. Hein ? » affiche 594 s, parce que la deduplication fusionnait deux
 *      blocs de meme texte sans regarder l'ecart de temps entre eux ;
 *   B. 168 blocs de duree nulle sur 545, parce qu'un segment degenere de Whisper
 *      etait SCINDE au lieu d'etre supprime ;
 *   C. 67 % des blocs Gemini sous la seconde, illisibles.
 *
 * Usage :  node test_timings.js
 */
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(SRC, 'utf8');

// ── on extrait les fonctions reellement livrees ─────────────────────────────
function extraire(nom) {
  const i = html.indexOf(`function ${nom}(`);
  if (i < 0) throw new Error(`fonction introuvable dans index.html : ${nom}`);
  let prof = 0, debut = html.indexOf('{', i), j = debut;
  for (; j < html.length; j++) {
    if (html[j] === '{') prof++;
    else if (html[j] === '}') { prof--; if (prof === 0) break; }
  }
  return html.slice(i, j + 1);
}

const contexte = {};
const code = [
  'function tsToMs(ts){var m=/(\\d\\d):(\\d\\d):(\\d\\d),(\\d\\d\\d)/.exec(ts);' +
  'return m?((+m[1])*3600+(+m[2])*60+(+m[3]))*1000+(+m[4]):0;}',
  'var DEDUP_ECART_MAX_MS = ' + (/DEDUP_ECART_MAX_MS\s*=\s*(\d+)/.exec(html) || [, 'null'])[1] + ';',
  'var BLOC_DUREE_MAX_MS = '  + (/BLOC_DUREE_MAX_MS\s*=\s*(\d+)/.exec(html)  || [, 'null'])[1] + ';',
  'var BLOC_DUREE_MINI_S = '  + (/BLOC_DUREE_MINI_S\s*=\s*([\d.]+)/.exec(html)|| [, 'null'])[1] + ';',
  'var BLOC_DUREE_MAX_S = '   + (/BLOC_DUREE_MAX_S\s*=\s*([\d.]+)/.exec(html) || [, 'null'])[1] + ';',
  extraire('dedupConsecutiveBlocks'),
  extraire('motsVersBlocs'),
  'module.exports = { dedupConsecutiveBlocks, motsVersBlocs, tsToMs, ' +
  'DEDUP_ECART_MAX_MS, BLOC_DUREE_MAX_MS, BLOC_DUREE_MINI_S, BLOC_DUREE_MAX_S };',
].join('\n');

const tmp = path.join(require('os').tmpdir(), `sw_timings_${process.pid}.js`);
fs.writeFileSync(tmp, code, 'utf8');
const M = require(tmp);
fs.unlinkSync(tmp);

let echecs = 0;
function verifie(titre, condition, detail) {
  console.log(`  ${condition ? 'OK  ' : 'ECHEC'}  ${titre}${condition ? '' : '  <-- ' + detail}`);
  if (!condition) echecs++;
}

const ts = ms => {
  const h = String(Math.floor(ms / 3600000)).padStart(2, '0');
  const m = String(Math.floor(ms / 60000) % 60).padStart(2, '0');
  const s = String(Math.floor(ms / 1000) % 60).padStart(2, '0');
  return `${h}:${m}:${s},${String(ms % 1000).padStart(3, '0')}`;
};
const bloc = (id, d, f, texte) => ({ id: String(id), timestamp: `${ts(d)} --> ${ts(f)}`, text: texte });
const duree = b => {
  const p = b.timestamp.split(' --> ');
  return M.tsToMs(p[1]) - M.tsToMs(p[0]);
};

console.log('\nA. deduplication — deux occurrences ELOIGNEES ne doivent pas fusionner');
{
  // le cas reel : "Voila. Hein ?" a 978,9 s puis la meme chose a 1571 s
  const r = M.dedupConsecutiveBlocks([
    bloc(1, 978900, 980200, 'Voilà. Hein ?'),
    bloc(2, 1571000, 1573100, 'Voilà. Hein ?'),
  ]);
  verifie('les deux blocs sont conserves', r.blocks.length === 2, `${r.blocks.length} bloc(s)`);
  const max = Math.max(...r.blocks.map(duree));
  verifie('aucun bloc de 594 s', max <= M.BLOC_DUREE_MAX_MS, `${(max / 1000).toFixed(1)} s`);
}

console.log('\nA-bis. deduplication — une repetition CONTIGUE doit toujours fusionner');
{
  const r = M.dedupConsecutiveBlocks([
    bloc(1, 10000, 11000, "Merci d'avoir regardé."),
    bloc(2, 11200, 12000, "Merci d'avoir regardé."),
  ]);
  verifie('les blocs contigus fusionnent', r.blocks.length === 1 && r.removed === 1,
          `${r.blocks.length} bloc(s), removed=${r.removed}`);
}

console.log('\nC. motsVersBlocs — duree minimale d affichage');
{
  const mots = [
    { start: 1.0, end: 1.2, text: 'Code' },
    { start: 1.2, end: 1.6, text: 'accepté.' },
    { start: 9.0, end: 9.3, text: 'Montez.' },   // apres une longue pause
    { start: 20.0, end: 20.4, text: 'Fin.' },
  ];
  const b = M.motsVersBlocs(mots, 360);
  // EPS : 9 + 1.2 vaut 10.199999999999999 en virgule flottante, donc la duree
  // mesuree tombe 7 millioniemes sous le seuil. C'est de l'arithmetique, pas un
  // defaut — mais le test doit le dire, pas le masquer.
  const EPS = 1e-6;
  const courts = b.filter(x => (x.end - x.start) < M.BLOC_DUREE_MINI_S - EPS && x !== b[b.length - 1]);
  verifie('aucun bloc non final sous la duree mini', courts.length === 0,
          JSON.stringify(courts));
  verifie('aucun chevauchement introduit',
          b.every((x, i) => i === b.length - 1 || x.end <= b[i + 1].start + 1e-9),
          JSON.stringify(b));
  verifie('les DEBUTS ne bougent pas (synchro intacte)',
          b[0].start === 1.0 && b[b.length - 1].start === 20.0, JSON.stringify(b.map(x => x.start)));
}

console.log('\nC-bis. motsVersBlocs — duree MAXIMALE (le texte ne reste pas a l ecran)');
{
  // un mot isole dont Gemini rend une fin aberrante, tres loin : sans plafond, le
  // sous-titre restait affiche 30 s — le symptome signale par Quang le 07/09.
  const b = M.motsVersBlocs([{ start: 5.0, end: 95.0, text: 'Voilà.' }], 360);
  const d = b[0].end - b[0].start;
  verifie('un bloc ne depasse pas la duree max', d <= M.BLOC_DUREE_MAX_S + 1e-6,
          `${d.toFixed(1)} s pour un plafond de ${M.BLOC_DUREE_MAX_S} s`);
}

console.log('\nB. blocs de duree nulle — le filtre existe dans autoFormatSRT');
{
  const a = html.indexOf('function autoFormatSRT(');
  const extrait = html.slice(a, a + 2500);
  verifie('autoFormatSRT jette les blocs fin <= debut',
          /tsToMs\(p\[1\]\)\s*>\s*tsToMs\(p\[0\]\)/.test(extrait), 'filtre absent');
}

console.log(echecs === 0
  ? '\n=> les 3 regles de temps tiennent.\n'
  : `\n=> ${echecs} ECHEC(S).\n`);
process.exit(echecs === 0 ? 0 : 1);
