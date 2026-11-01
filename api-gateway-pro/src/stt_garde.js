// stt_garde.js v1.1.0 (01/11/2026) : garde-fous de coût de la transcription.
// Copie IDENTIQUE dans 3 passerelles : dictokey/gateway, dictokey-pc/gateway, App/api-gateway-pro.
// Toute modification se reporte dans les 3 (test_stt_garde.mjs compare les copies).
//
// 1. Taille maximale côté serveur : jusqu'ici seule l'application limitait les envois.
// 2. Coupe-circuit : volume du jour anormal -> transcription arrêtée, alerte Telegram, reprise manuelle.
//    Seuil = le plus grand de 20 h ou 5 fois la moyenne des 7 jours précédents, donc il suit la croissance.
//    Aucune bascule silencieuse vers un autre moteur (règle de Quang).
//    v1.1.0 : pré-alerte Telegram à 80 % du seuil, une fois par jour : Quang est prévenu avant la coupure.
// ⚠️ Limite connue : une clé Azure volée et utilisée en direct ne passe pas par ici.
// ⚠️ KV n'est pas atomique : le compteur peut sous-compter sous forte concurrence. C'est un garde-fou, pas une facture.

export const TAILLE_MAX_OCTETS = 26 * 1024 * 1024;   // 25 Mo côté apps + enveloppe multipart
export const SEUIL_MIN_SEC = 20 * 3600;
export const FACTEUR = 5;
export const JOURS = 7;
export const PREALERTE_POURCENT = 80;
const TTL_COMPTEUR = 10 * 86400;
const CLE_COUPE = 'cc:coupe';

export const MESSAGE_TROP_GROS = 'Fichier trop volumineux : 25 Mo maximum.';
export const MESSAGE_COUPE = 'La transcription est momentanément suspendue. Réessaie un peu plus tard.';

const jour = (decalage, maintenant) => new Date(maintenant - decalage * 86400000).toISOString().slice(0, 10);
const entier = (v) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : 0; };

/** Refus AVANT de lire le corps, d'après l'en-tête. null = laisser passer (un en-tête absent se revérifie ensuite). */
export function refusTaille(octets) {
  return entier(octets) > TAILLE_MAX_OCTETS
    ? { statut: 413, corps: { error: 'fichier_trop_gros', message: MESSAGE_TROP_GROS } } : null;
}

/** Refus si le coupe-circuit est déclenché. */
export async function refusCoupe(kv) {
  return (await kv.get(CLE_COUPE))
    ? { statut: 503, corps: { error: 'stt_indisponible', message: MESSAGE_COUPE, coupe: true } } : null;
}

/** Seuil du jour, calculé une fois sur les 7 jours précédents. */
export async function seuilDuJour(kv, maintenant = Date.now()) {
  const cle = `cc:seuil:${jour(0, maintenant)}`;
  const connu = entier(await kv.get(cle));
  if (connu) return connu;
  const vals = await Promise.all(Array.from({ length: JOURS }, (_, i) => kv.get(`cc:jour:${jour(i + 1, maintenant)}`)));
  const moyenne = vals.reduce((s, v) => s + entier(v), 0) / JOURS;
  const seuil = Math.round(Math.max(SEUIL_MIN_SEC, FACTEUR * moyenne));
  await kv.put(cle, String(seuil), { expirationTtl: 2 * 86400 });
  return seuil;
}

/** Une fois par jour, dès 80 % du seuil. Le drapeau n'est posé qu'après l'envoi : une alerte ratée se retente. */
async function preAlerter(kv, j, total, base, seuil, alerter) {
  if (!alerter || (total - base) * 100 < seuil * PREALERTE_POURCENT || await kv.get(CLE_COUPE)) return;
  const cle = `cc:prealerte:${j}`;
  if (await kv.get(cle)) return;
  await alerter(`⚠️ Transcription : ${Math.round((total - base) / 360) / 10} h aujourd'hui, le coupe-circuit se déclenche à ${Math.round(seuil / 360) / 10} h. Rien n'est coupé pour l'instant.`);
  await kv.put(cle, '1', { expirationTtl: 2 * 86400 });
}

/** Après une transcription réussie : ajoute la durée, déclenche la coupure si le seuil est franchi.
 *  `alerter(texte)` envoie l'alerte. Ne jette jamais : un compteur raté ne doit pas casser une dictée. */
export async function compterVolume(kv, sec, alerter, maintenant = Date.now()) {
  try {
    const s = entier(sec);
    if (!s) return { coupe: false };
    const j = jour(0, maintenant);
    const total = entier(await kv.get(`cc:jour:${j}`)) + s;
    await kv.put(`cc:jour:${j}`, String(Math.round(total)), { expirationTtl: TTL_COMPTEUR });
    const base = entier(await kv.get(`cc:repris:${j}`));
    const seuil = await seuilDuJour(kv, maintenant);
    if (total - base < seuil) {
      await preAlerter(kv, j, total, base, seuil, alerter);
      return { coupe: false, total, seuil };
    }
    if (await kv.get(CLE_COUPE)) return { coupe: false, total, seuil };
    await kv.put(CLE_COUPE, JSON.stringify({ at: new Date(maintenant).toISOString(), heures: Math.round(total / 360) / 10, seuilHeures: Math.round(seuil / 360) / 10 }));
    if (alerter) await alerter(`🛑 Coupe-circuit transcription : ${Math.round(total / 360) / 10} h aujourd'hui, seuil ${Math.round(seuil / 360) / 10} h. Service arrêté jusqu'à ta reprise depuis le tableau de bord (onglet Moteurs).`);
    return { coupe: true, total, seuil };
  } catch (e) {
    console.error('[stt-garde]', e && e.message);
    return { coupe: false };
  }
}

/** Reprise manuelle : le volume déjà compté aujourd'hui ne redéclenche pas tout de suite. */
export async function reprendre(kv, maintenant = Date.now()) {
  const j = jour(0, maintenant);
  await kv.put(`cc:repris:${j}`, String(entier(await kv.get(`cc:jour:${j}`))), { expirationTtl: TTL_COMPTEUR });
  await kv.delete(`cc:prealerte:${j}`);
  await kv.delete(CLE_COUPE);
  return { ok: true, repris: true };
}

/** État lu par le tableau de bord. */
export async function etatGarde(kv, maintenant = Date.now()) {
  const brut = await kv.get(CLE_COUPE);
  let coupe = null;
  if (brut) { try { coupe = JSON.parse(brut); } catch { coupe = { at: null, heures: '?', seuilHeures: '?' }; } }
  return { coupe, heuresDuJour: Math.round(entier(await kv.get(`cc:jour:${jour(0, maintenant)}`)) / 360) / 10, seuilHeures: Math.round((await seuilDuJour(kv, maintenant)) / 360) / 10 };
}
