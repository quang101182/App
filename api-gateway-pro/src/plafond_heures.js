// plafond_heures.js v1.0.0 (01/11/2026) : plafond mensuel en heures de SubWhisper Pro, décision de Quang.
//
// Pro 15 h, essai 2 h, mois UTC : le compteur repart seul le 1er. 50 tranches pouvaient aller jusqu'à ~50 h.
// Interrupteur KV `cfg:plafond_mensuel` : absent = compte sans refuser ; `on` = actif ; `test:<cle>` = cette clé seule.
// ⛔ Ne pas allumer avant la publication des limites. Refus en 402 et non 429 : l'app réessaie 3 fois sur un 429.
// ⚠️ KV n'est pas atomique : le compteur peut sous-compter en parallèle. Garde-fou, pas une facture.

export const PLAFONDS_SEC = { pro: 15 * 3600, trial: 2 * 3600 };
export const SEUIL_ALERTE = 80;
export const ERREUR_PLAFOND = 'monthly_hours_reached';
const CLE_INTERRUPTEUR = 'cfg:plafond_mensuel';
const TTL_COMPTEUR = 40 * 86400;

const entier = (v) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : 0; };
const plafondSec = (plan) => PLAFONDS_SEC[plan] ?? PLAFONDS_SEC.pro;

export const cleMois = (proKey, maintenant = Date.now()) => `pm:${new Date(maintenant).toISOString().slice(0, 7)}:${proKey}`;

export const plafondActif = (interrupteur, proKey) => interrupteur === 'on' || interrupteur === `test:${proKey}`;

/** Panne de stockage : la transcription passe, jamais l'inverse. */
export async function lireHeures(kv, proKey, maintenant = Date.now()) {
  try {
    const [brut, interrupteur] = await Promise.all([kv.get(cleMois(proKey, maintenant)), kv.get(CLE_INTERRUPTEUR)]);
    return { sec: entier(brut), actif: plafondActif(interrupteur, proKey) };
  } catch (e) {
    console.error('[plafond-heures]', e && e.message);
    return { sec: 0, actif: false };
  }
}

/** Corps du refus (`error.message` : lu tel quel par l'app), ou null. Plafond éteint : jamais de refus. */
export function refusHeures(plan, etat) {
  if (!etat.actif || etat.sec < plafondSec(plan)) return null;
  const heures = Math.round(plafondSec(plan) / 3600);
  return { error: { code: ERREUR_PLAFOND, message: `Monthly limit of ${heures} hours reached. It resets on the 1st of the month.` }, limit_hours: heures };
}

/** Relit le compteur au dernier moment : les tranches partent en parallèle. Ne jette jamais. */
export async function ajouterHeures(kv, proKey, sec, maintenant = Date.now()) {
  try {
    const s = entier(sec);
    if (!s || !proKey) return;
    const cle = cleMois(proKey, maintenant);
    await kv.put(cle, String(Math.round(entier(await kv.get(cle)) + s)), { expirationTtl: TTL_COMPTEUR });
  } catch (e) {
    console.error('[plafond-heures]', e && e.message);
  }
}

/** Pré-alerte lue par l'app : null sous 80 % ou plafond éteint. Information seule, jamais une décision de refus. */
export function etatAffiche(plan, etat) {
  if (!etat.actif) return null;
  const pct = Math.floor((etat.sec / plafondSec(plan)) * 100);
  if (pct < SEUIL_ALERTE) return null;
  return { used_hours: Math.floor(etat.sec / 360) / 10, limit_hours: Math.round(plafondSec(plan) / 3600), pct: Math.min(pct, 100) };
}

/** Premier refus du mois pour une clé : Quang est prévenu une fois. */
export async function signalerRefus(kv, proKey, alerter, maintenant = Date.now()) {
  try {
    const cle = `${cleMois(proKey, maintenant)}:signale`;
    if (await kv.get(cle)) return;
    await kv.put(cle, '1', { expirationTtl: TTL_COMPTEUR });
    await alerter(`⚠️ SubWhisper Pro : un client a atteint son plafond mensuel (${proKey.slice(0, 6)}…). Pour tout lever : supprimer cfg:plafond_mensuel.`);
  } catch (e) {
    console.error('[plafond-heures]', e && e.message);
  }
}
