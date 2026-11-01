// Banc v1.31.0 : plafond mensuel en heures de SubWhisper Pro, sans réseau. node test/test_plafond_heures.mjs
import { cleMois, plafondActif, lireHeures, refusHeures, ajouterHeures, etatAffiche, signalerRefus, PLAFONDS_SEC, ERREUR_PLAFOND } from '../src/plafond_heures.js';

let ok = 0, ko = 0;
const t = (nom, c) => { if (c) ok++; else { ko++; console.log('ROUGE :', nom); } };
const m = new Map();
const kv = { get: async (k) => (m.has(k) ? m.get(k) : null), put: async (k, v) => { m.set(k, String(v)); } };
const ON = { actif: true };

t('Pro 15 h', PLAFONDS_SEC.pro === 54000);
t('essai 2 h', PLAFONDS_SEC.trial === 7200);
t('éteint : aucun refus', refusHeures('pro', { sec: 999999, actif: false }) === null);
t('sous la limite : passe', refusHeures('pro', { sec: 53999, ...ON }) === null);
t('à la limite : refus', refusHeures('pro', { sec: 54000, ...ON })?.error?.code === ERREUR_PLAFOND);
t('essai à 2 h : refus', refusHeures('trial', { sec: 7200, ...ON })?.limit_hours === 2);
t('plan inconnu : traité en Pro', refusHeures('x', { sec: 7200, ...ON }) === null);
t('message lisible', refusHeures('pro', { sec: 54000, ...ON }).error.message.includes('15 hours'));
t('interrupteur absent', !plafondActif(null, 'k'));
t('on', plafondActif('on', 'k'));
t('test cette clé', plafondActif('test:k', 'k'));
t('test autre clé', !plafondActif('test:z', 'k'));
t('mois UTC', cleMois('k', Date.UTC(2026, 10, 30, 23, 59)) === 'pm:2026-11:k');
t('repart le 1er', cleMois('k', Date.UTC(2026, 11, 1)) === 'pm:2026-12:k');

const T = Date.UTC(2026, 10, 15);
await ajouterHeures(kv, 'k', 100, T); await ajouterHeures(kv, 'k', 100, T); await ajouterHeures(kv, 'k', 0, T);
t('tranches additionnées', m.get('pm:2026-11:k') === '200');
await ajouterHeures(kv, 'k', 5, Date.UTC(2026, 11, 1, 0, 0, 1));
t('nouveau mois à zéro', m.get('pm:2026-12:k') === '5');
await ajouterHeures(kv, null, 5, T);
t('sans clé : rien', ![...m.keys()].some((k) => k.endsWith('null')));
await ajouterHeures({ get: async () => null, put: async () => { throw new Error('x'); } }, 'k', 5, T);
const panne = await lireHeures({ get: async () => { throw new Error('x'); } }, 'k');
t('stockage en panne : pas de refus', panne.actif === false && refusHeures('pro', panne) === null);
m.set('cfg:plafond_mensuel', 'test:k');
const e = await lireHeures(kv, 'k', T);
t('lecture', e.sec === 200 && e.actif === true);

t('écran : éteint', etatAffiche('pro', { sec: 50000, actif: false }) === null);
t('écran : sous 80 %', etatAffiche('pro', { sec: 43199, ...ON }) === null);
{ const a = etatAffiche('pro', { sec: 43200, ...ON }); t('écran : 80 %', a?.pct === 80 && a?.used_hours === 12 && a?.limit_hours === 15); }
t('écran : plafonné', etatAffiche('pro', { sec: 90000, ...ON })?.pct === 100);

let n = 0;
await signalerRefus(kv, 'abcdefgh', async () => { n++; }, T); await signalerRefus(kv, 'abcdefgh', async () => { n++; }, T);
t('signalé une seule fois', n === 1);

console.log(`${ok} verts, ${ko} rouges`);
process.exit(ko ? 1 : 0);
