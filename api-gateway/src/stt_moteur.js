// stt_moteur.js — Interrupteur de moteur de transcription PAR APP + relais MAI-Transcribe-2 (v1.64, 03/10/2026).
//
// Calqué sur dictokey/gateway/src/stt_mai.js (en prod depuis le 03/10) mais multi-app et multi-moteur :
// le moteur choisi est une décision HUMAINE prise au dashboard (confirmation côté page), horodatée,
// jamais automatique. Panne MAI = l'app échoue proprement + compteur + alerte Telegram ≤ 1/h avec le
// lien du dashboard ; c'est Quang qui rebascule (décision D2 du 03/10, même système que DictoKey).
// Feuille de route : Repo-github/moteur-transcription-MAI/ROADMAP.md (P1).
//
// ⚠️ Dépôt PUBLIC : aucune valeur secrète ici. Les clés sont lues dans le KV (key:*) par l'appelant.
// Module PUR (KV et Telegram injectés) : banc test/test_stt_moteur.mjs.

/** Moteurs proposés au dashboard (D5). L'ordre est celui du menu. */
export const MOTEURS = {
  'mai2':            'MAI-Transcribe-2',
  'mai2-openrouter': 'MAI-Transcribe-2 via OpenRouter (secours)',
  'croise':          'Gemini 3.5 + filet Groq',
  'gemini':          'Gemini 3.5 Transcribe',
  'groq':            'Groq Whisper',
};

/**
 * Apps pilotées. `defaut` = ce qui tourne quand rien n'a été choisi au dashboard : le comportement
 * d'AVANT ce chantier (Télégramme Vidéo = croisé), pour qu'un déploiement ne change rien tout seul.
 * D3 : SubWhisper et Télégramme Vidéo partagent UN interrupteur.
 */
export const APPS_STT = {
  soustitrage: {
    nom: 'Sous-titrage (SubWhisper + Télégramme Vidéo)',
    defaut: 'croise',
    lien: 'https://dash.se7enai.com/#st',
  },
};

/** Ressource Azure Foundry (northeurope) — pas un secret ; surchargeable par cfg:mai_endpoint. */
export const MAI_ENDPOINT_DEFAUT = 'https://dictokey-stt-bench.cognitiveservices.azure.com';
export const MAI_CHEMIN = '/speechtotext/transcriptions:transcribe?api-version=2025-10-15';
/** D7 : clé dédiée au sous-titrage si elle existe, sinon celle déjà en place. */
export const MAI_CLES = ['AZURE_SPEECH_KEY_SOUSTITRES', 'AZURE_SPEECH_KEY'];

const jourIso = (decalage = 0) => new Date(Date.now() - decalage * 86400000).toISOString().slice(0, 10);

/** App demandée (`?app=`), validée ; null si inconnue. */
export function appDemandee(url, defaut = 'soustitrage') {
  const a = (url.searchParams.get('app') || defaut).trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(APPS_STT, a) ? a : null;
}

/** Moteur réellement en vigueur (valeur KV inconnue ou absente -> défaut de l'app). */
export async function moteurDe(kv, app) {
  const brut = await kv.get(`cfg:stt_engine:${app}`);
  return Object.prototype.hasOwnProperty.call(MOTEURS, brut) ? brut : APPS_STT[app].defaut;
}

/** Ce que lisent les apps (GET /api/stt-engine) : le strict nécessaire. */
export async function lireMoteur(kv, app) {
  const engine = await moteurDe(kv, app);
  const meta = await kv.get(`cfg:stt_engine_meta:${app}`, 'json');
  return { app, engine, label: MOTEURS[engine], at: (meta && meta.at) || null };
}

/** État complet affiché par le dashboard (GET /admin/stt-engine). */
export async function etatMoteur(kv, app) {
  const [brut, meta, last, eAuj, eHier] = await Promise.all([
    kv.get(`cfg:stt_engine:${app}`), kv.get(`cfg:stt_engine_meta:${app}`, 'json'),
    kv.get(`stt:last_error:${app}`, 'json'), kv.get(`stt:err:${app}:${jourIso()}`), kv.get(`stt:err:${app}:${jourIso(1)}`),
  ]);
  const engine = Object.prototype.hasOwnProperty.call(MOTEURS, brut) ? brut : APPS_STT[app].defaut;
  return {
    app, nom: APPS_STT[app].nom, engine, label: MOTEURS[engine],
    configured: brut, par_defaut: brut === null || !(brut in MOTEURS),
    changed: meta || null, last_error: last || null,
    errors_today: parseInt(eAuj || '0', 10), errors_yesterday: parseInt(eHier || '0', 10),
    moteurs: Object.entries(MOTEURS).map(([id, label]) => ({ id, label })),
  };
}

/** Bascule (POST /admin/stt-engine) — l'auth admin est faite AVANT par la gateway. */
export async function basculer(kv, app, corps) {
  const cible = corps && corps.engine;
  if (!Object.prototype.hasOwnProperty.call(MOTEURS, cible)) {
    return { status: 400, body: { ok: false, error: 'engine inconnu', moteurs: Object.keys(MOTEURS) } };
  }
  const avant = await moteurDe(kv, app);
  await kv.put(`cfg:stt_engine:${app}`, cible);
  await kv.put(`cfg:stt_engine_meta:${app}`, JSON.stringify({
    at: new Date().toISOString(), from: avant, to: cible,
    source: String((corps && corps.source) || 'dashboard').slice(0, 40),
  }));
  return { status: 200, body: { ok: true, changed_from: avant, ...(await etatMoteur(kv, app)) } };
}

/** Échec MAI : compteur du jour + dernière erreur lisible (best-effort, ne jette jamais). */
export async function noterPanne(kv, app, status, message) {
  try {
    const k = `stt:err:${app}:${jourIso()}`;
    const n = parseInt((await kv.get(k)) || '0', 10) + 1;
    await Promise.all([
      kv.put(k, String(n), { expirationTtl: 3 * 86400 }),
      kv.put(`stt:last_error:${app}`, JSON.stringify({
        ts: new Date().toISOString(), status, message: String(message || '').slice(0, 200),
      }), { expirationTtl: 30 * 86400 }),
    ]);
  } catch { /* un compteur raté ne doit jamais aggraver une panne */ }
}

/**
 * Alerte Telegram ≤ 1/heure/app. Le drapeau n'est posé QUE si Telegram a accepté — sinon une panne
 * réseau d'un instant supprimerait l'alerte de toute l'heure (même règle que DictoKey).
 * `envoyer(texte)` -> {sent:boolean}.
 */
export async function alerterPanne(kv, app, detail, envoyer) {
  const k = `alert:stt_panne:${app}:${new Date().toISOString().slice(0, 13)}`;
  try {
    if (await kv.get(k)) return { sent: false, reason: 'deja_alerte_cette_heure' };
    const texte = `🔴 Transcription MAI en panne — ${APPS_STT[app].nom}\n` +
      `Détail : ${String(detail || '').slice(0, 160)}\n` +
      `Aucune bascule automatique. Pour changer de moteur : ${APPS_STT[app].lien}`;
    const r = await envoyer(texte);
    if (r && r.sent) await kv.put(k, '1', { expirationTtl: 7200 });
    return r || { sent: false };
  } catch (e) {
    return { sent: false, reason: String(e).slice(0, 120) };
  }
}

/** Endpoint Azure et nom de la clé à utiliser (la clé elle-même est résolue par l'appelant). */
export async function cibleMai(kv) {
  const ep = ((await kv.get('cfg:mai_endpoint')) || MAI_ENDPOINT_DEFAUT).replace(/\/+$/, '');
  return ep + MAI_CHEMIN;
}
