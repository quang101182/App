// stt_cout.js — Coût des transcriptions, par app et par moteur (P8, 06/10/2026).
// ⚠ Copie IDENTIQUE dans les 4 passerelles : api-gateway, api-gateway-pro, dictokey/gateway, dictokey-pc/gateway.
//   Toute modification se reporte dans les 4 (test : moteur-transcription-MAI/test_stt_cout.mjs compare les copies).
//
// POURQUOI des ÉVÉNEMENTS et pas un compteur : un compteur KV « lire + ajouter + écrire » perd des incréments
// quand deux transcriptions se terminent en même temps (SubWhisper envoie ses tranches en parallèle). Ici chaque
// transcription écrit SA clé (nom unique) -> aucune perte. Les jours clos sont consolidés en un récapitulatif
// (`cj:`) RECALCULÉ depuis les événements : idempotent, deux consolidations simultanées écrivent la même chose.
// Le dashboard lit tout l'historique en UNE liste par app (le récapitulatif vit dans les métadonnées de la clé).
//
// Jour = jour CIVIL de Paris (pas UTC) : « aujourd'hui » au dashboard = aujourd'hui pour Quang.

/** Tarifs officiels relevés le 06/10/2026. Le coût est figé à l'instant de la transcription (un changement
 *  de tarif ne réécrit pas le passé). */
export const TARIFS = {
  // Azure — offre de lancement, fin annoncée au 31/12/2026, prix normal non publié
  'mai2':            { nom: 'MAI-Transcribe-2', usdHeure: 0.10 },
  // OpenRouter renvoie lui-même usage.cost : c'est CE chiffre qui est compté (0,10 $/h constaté)
  'mai2-openrouter': { nom: 'MAI-Transcribe-2 (OpenRouter)', usdHeure: 0.10 },
  // Groq facture 10 s minimum par requête (console.groq.com/docs/speech-to-text)
  'groq-turbo':      { nom: 'Groq Whisper turbo', usdHeure: 0.04, minSec: 10 },
  'groq-v3':         { nom: 'Groq Whisper large-v3', usdHeure: 0.111, minSec: 10 },
  // Gemini 3.5 Transcribe : 2,00 $/M jetons en entrée, 12,00 $/M en sortie, 25 jetons audio par seconde
  'gemini':          { nom: 'Gemini 3.5 Transcribe', usdMEntree: 2.00, usdMSortie: 12.00, jetonsParSec: 25 },
  // OpenAI (SubWhisper, choix manuel) : 0,006 $/min whisper-1 et gpt-4o-transcribe, 0,003 $/min mini
  'openai':          { nom: 'OpenAI Whisper', usdHeure: 0.36 },
  'openai-mini':     { nom: 'OpenAI 4o-mini-transcribe', usdHeure: 0.18 },
  // autre modèle demandé à OpenRouter : seul le coût renvoyé par OpenRouter (usage.cost) est compté
  'openrouter':      { nom: 'OpenRouter (autre modèle)' },
};

const TTL_EVENEMENT = 40 * 86400;    // marge : un jour non consolidé pendant 40 jours serait perdu
const TTL_JOUR = 800 * 86400;        // ~2 ans d'historique (le dashboard en affiche 12 mois)
const FMT_PARIS = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit' });

/** Jour civil de Paris, AAAA-MM-JJ (décalé de `decalage` jours). */
export function jourParis(decalage = 0, maintenant = Date.now()) {
  return FMT_PARIS.format(new Date(maintenant - decalage * 86400000));
}

/** Moteur Groq selon le modèle demandé : seul « whisper-large-v3 » (non turbo) est au tarif large-v3. */
export function moteurGroq(modele) {
  const m = String(modele || '').toLowerCase();
  return m.includes('large-v3') && !m.includes('turbo') ? 'groq-v3' : 'groq-turbo';
}

/** Coût d'une transcription à la durée. Groq : 10 s minimum facturées. */
export function coutDuree(moteur, sec) {
  const t = TARIFS[moteur];
  if (!t || !t.usdHeure || !(sec > 0)) return 0;
  return Math.max(sec, t.minSec || 0) / 3600 * t.usdHeure;
}

/** Gemini (Interactions API) : secondes + coût depuis `usage`. null si la réponse ne contient pas d'audio. */
export function coutGemini(usage) {
  if (!usage) return null;
  const audio = (usage.input_tokens_by_modality || []).find((m) => String(m.modality).toLowerCase() === 'audio');
  if (!audio || !(audio.tokens > 0)) return null;
  const t = TARIFS.gemini;
  const entree = Number(usage.total_input_tokens) || 0;
  const sortie = (Number(usage.total_output_tokens) || 0) + (Number(usage.total_thought_tokens) || 0);
  return { sec: audio.tokens / t.jetonsParSec, usd: (entree * t.usdMEntree + sortie * t.usdMSortie) / 1e6 };
}

/** Durée d'un WAV depuis son en-tête RIFF (secours quand la réponse ne donne pas la durée). 0 si illisible. */
export function dureeWav(buf) {
  try {
    const b = new Uint8Array(buf);
    if (b.length < 44 || String.fromCharCode(...b.slice(0, 4)) !== 'RIFF' || String.fromCharCode(...b.slice(8, 12)) !== 'WAVE') return 0;
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    let p = 12, debit = 0;
    while (p + 8 <= b.length) {
      const id = String.fromCharCode(...b.slice(p, p + 4)), taille = dv.getUint32(p + 4, true);
      if (id === 'fmt ') debit = dv.getUint32(p + 16, true);
      if (id === 'data') {
        const octets = Math.min(taille, b.length - p - 8);   // flux : taille parfois 0xFFFFFFFF
        return debit > 0 ? octets / debit : 0;
      }
      p += 8 + taille + (taille % 2);
    }
  } catch { /* illisible */ }
  return 0;
}

/** Enregistre UNE transcription. `sec` = durée audio ; `usd` = coût (calculé ici si absent) ;
 *  `sec` absent ou nul -> comptée comme « non mesurée » (affichée au dashboard, jamais cachée).
 *  Best-effort : ne jette jamais (un compteur raté ne doit pas casser une transcription). */
export async function compterCout(kv, app, moteur, sec, usd, maintenant = Date.now()) {
  try {
    if (!app || !TARIFS[moteur]) return;
    const s = Number(sec) > 0 ? Number(sec) : 0;
    const u = Number(usd) >= 0 && usd !== null && usd !== undefined ? Number(usd) : coutDuree(moteur, s);
    const meta = { m: moteur, s: Math.round(s * 10) / 10, u: Math.round(u * 1e8) / 1e8 };
    if (!s) meta.nm = 1;
    const id = maintenant.toString(36) + Math.random().toString(36).slice(2, 8);
    await kv.put(`ce:${app}:${jourParis(0, maintenant)}:${id}`, '', { metadata: meta, expirationTtl: TTL_EVENEMENT });
  } catch { /* best-effort */ }
}

async function listerTout(kv, prefixe) {
  const cles = [];
  let curseur;
  do {
    const r = await kv.list({ prefix: prefixe, cursor: curseur });
    cles.push(...r.keys);
    curseur = r.list_complete ? undefined : r.cursor;
  } while (curseur);
  return cles;
}

/** Additionne des événements (ou des récapitulatifs) dans { moteur: { s, u, n, nm } }. */
export function additionner(cible, moteur, s, u, n, nm, est) {
  const c = cible[moteur] || (cible[moteur] = { s: 0, u: 0, n: 0, nm: 0 });
  c.s += s || 0; c.u += u || 0; c.n += n || 0; c.nm += nm || 0;
  if (est) c.est = 1;
  return cible;
}

/** Consolide les jours clos qui ont des événements. Idempotent : le récapitulatif est RECALCULÉ depuis les
 *  événements, jamais incrémenté, et les événements ne sont JAMAIS supprimés (ils expirent seuls) — deux
 *  consolidations simultanées écrivent donc la même chose. Un jour est définitif quand son récapitulatif a été
 *  calculé au moins 2 h après la fin du jour (marge de cohérence de KV.list, ≤ 60 s). Une part reconstituée
 *  depuis d'anciens compteurs (`b`, backfill) est conservée et ajoutée (ses événements n'existent pas). */
async function consolider(kv, app, recaps, evenements, maintenant) {
  const aujourdhui = jourParis(0, maintenant);
  const parJour = {};
  for (const k of evenements) {
    const j = k.name.split(':')[2];
    if (j < aujourdhui) (parJour[j] || (parJour[j] = [])).push(k);
  }
  for (const [j, cles] of Object.entries(parJour)) {
    const existant = recaps[j];
    if (existant && existant.t && jourParis(0, existant.t - 2 * 3600000) > j) continue;   // déjà définitif
    const recap = {};
    for (const k of cles) { const m = k.metadata || {}; if (m.m) additionner(recap, m.m, m.s, m.u, 1, m.nm ? 1 : 0); }
    const ancien = existant && existant.b;
    if (ancien) for (const [m, v] of Object.entries(ancien)) additionner(recap, m, v.s, v.u, v.n, v.nm, 1);
    const meta = { r: arrondir(recap), t: maintenant, ...(ancien ? { b: ancien } : {}) };
    recaps[j] = meta;   // affiché même si l'écriture échoue : elle sera retentée à la lecture suivante
    try { await kv.put(`cj:${app}:${j}`, '', { metadata: meta, expirationTtl: TTL_JOUR }); } catch { /* best-effort */ }
  }
}

function arrondir(r) {
  const o = {};
  for (const [m, v] of Object.entries(r)) {
    o[m] = { s: Math.round(v.s * 10) / 10, u: Math.round(v.u * 1e8) / 1e8, n: v.n };
    if (v.nm) o[m].nm = v.nm;
    if (v.est) o[m].est = 1;
  }
  return o;
}

/** GET /admin/stt-cout : historique par jour (Paris) de chaque app de CETTE passerelle.
 *  { ok, aujourdhui, tarifs, apps: { <app>: { depuis, jours: { AAAA-MM-JJ: { moteur: {s,u,n,nm?,est?} } } } } } */
export async function lireCouts(kv, apps, maintenant = Date.now()) {
  const sortie = { ok: true, version: 1, fuseau: 'Europe/Paris', aujourdhui: jourParis(0, maintenant), tarifs: TARIFS, apps: {} };
  await Promise.all(apps.map(async (app) => {
    const [cj, evenements, depuis] = await Promise.all([
      listerTout(kv, `cj:${app}:`), listerTout(kv, `ce:${app}:`), kv.get(`cout:depuis:${app}`),
    ]);
    const recaps = {};
    for (const k of cj) recaps[k.name.split(':')[2]] = k.metadata || {};
    await consolider(kv, app, recaps, evenements, maintenant);
    const jours = {};
    for (const [j, m] of Object.entries(recaps)) if (m.r && Object.keys(m.r).length) jours[j] = m.r;
    // le jour en cours se lit toujours en direct depuis ses événements (+ sa part reconstituée s'il en a une)
    const auj = {}, partB = recaps[sortie.aujourdhui] && recaps[sortie.aujourdhui].b;
    if (partB) for (const [m, v] of Object.entries(partB)) additionner(auj, m, v.s, v.u, v.n, v.nm, 1);
    for (const k of evenements) {
      const m = k.metadata || {};
      if (m.m && k.name.split(':')[2] === sortie.aujourdhui) additionner(auj, m.m, m.s, m.u, 1, m.nm ? 1 : 0);
    }
    if (Object.keys(auj).length) jours[sortie.aujourdhui] = arrondir(auj);
    sortie.apps[app] = { depuis: depuis || null, jours };
  }));
  return sortie;
}
