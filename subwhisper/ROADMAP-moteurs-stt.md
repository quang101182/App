# ROADMAP — Choix du moteur STT dans SubWhisper (perso)

> Ouverte le **07/09/2026**. Mandat Quang : *« carte blanche pour faire tout le nécessaire […]
> la plus grosse partie sur le SubWhisper perso. Si il y a un dysfonctionnement sur la version
> pro, corriger simplement ce qui dysfonctionne […] tu traces bien une feuille de route. »*
>
> **Autosuffisante par construction** : tout ce qui est nécessaire pour reprendre ce chantier
> est ici, sans renvoyer à une mémoire externe.

## Pourquoi ce chantier — les mesures qui le justifient

Google a sorti le **26/08/2026** `gemini-3.5-transcribe`, un modèle STT dédié. Campagne de
mesure du 07/09 (4 régimes d'audio, corpus FLEURS / AMI / VoxPopuli + 40 extraits de la
bibliothèque réelle de Quang) :

| Régime | Groq turbo (actuel) | Gemini `smart` | Gemini `verbatim` |
|---|---|---|---|
| FLEURS studio, 6 langues (médiane) | 4,5 % | — | **0-2 %** |
| VoxPopuli FR (oratoire spontané) | 5,2 % | **2,9 %** | 3,5 % |
| AMI (réunions EN, bruit, chevauchements) | 22,2 % | 28,1 % ⛔ | **14,7 %** ✅ |
| Bibliothèque perso JP/ZH (40 extraits) | **muet 0/40** | muet 25/40 ⛔ | muet 9/40 |

**Bout en bout** (audio → sous-titres FR), écart au plafond d'une transcription parfaite,
avec **DeepSeek** comme traducteur — celui que Quang active réellement :

| Langue | via Groq | via Gemini |
|---|---|---|
| japonais | +2,2 pt | **−0,2 pt** (= indiscernable d'une transcription parfaite) |
| chinois | **+10,3 pt** | **+2,9 pt** |

⇒ **Le gain est réel et large dans l'usage réel de Quang.** Il ne l'était PAS avec un
traducteur Gemini (qui répare les erreurs de STT tout seul) : c'est bien parce que DeepSeek
propage les erreurs que la qualité du STT compte.

### Les trois faits qui cadrent la conception

1. ⛔ **Le mode `smart` est à proscrire** : muet 62 % du temps sur le corpus perso, et **pire
   que Groq** sur du dialogue bruité. Il « nettoie » jusqu'à supprimer, et il **reformule**
   (il reconstruit du plausible). Pour un sous-titre, c'est disqualifiant. **`verbatim` toujours.**
2. ✅ **Groq n'est JAMAIS muet** (0/40) là où Gemini l'est 9/40. C'est son seul avantage, mais
   il est décisif sur l'audio à faible parole articulée → **Groq reste le filet**, jamais retiré.
3. 🔴 **Gemini hallucine**, rarement mais **en silence** : sur 60 phrases FLEURS, une a produit
   un monument américain absent de l'audio (CER 140 % = du texte AJOUTÉ). Détectable par
   croisement (voir P4).

## État des lieux du code — ce qui existe et ce qui est cassé

- Dispatcher : `transcribe()` **`index.html:1937-1995`**, cascade en dur commentée
  « Priorité : Groq > Gateway > OpenAI > AAI » (l.1941-1943).
- ⚠️ **Un seul chemin est réellement atteignable** : tous les getters de clés renvoient `''`
  en dur (`index.html:1730-1750`) → seul `API_DOTS['GWY'] === 'ok'` peut être vrai, donc
  **toujours Groq via gateway**. Les branches OpenAI et AssemblyAI sont mortes.
- ⛔ **Deux fonctions de l'UI ne font RIEN** (conséquence du point précédent) :
  - la case **« Détection des locuteurs »** (`index.html:1217`) n'est lue qu'à **une** ligne,
    `index.html:1972`, dans la branche AssemblyAI inatteignable ;
  - la **vue RICH** (mot à mot cliquable) : bouton `disabled` tant que `wordData` est vide
    (`index.html:~3208`), et `wordData` n'est rempli que par AssemblyAI.
- 🐛 `transcribeOpenAI()` étiquette ses DIAG `'assemblyai'` (`index.html:2174`).
- Chunking : `MAX_BYTES = 24 Mo` (~13 min) — `index.html:2067` et `2219`.
- Post-traitement (switch auto, **toujours actif chez Quang**) : `autoFormatSRT()`
  `index.html:4782`, règles `MAX_LINE=42 · MAX_LINES=2 · MAX_CPS=25 · MAX_CHARS=84`.

## Contraintes d'API mesurées le 07/09 — ne pas les redécouvrir

| Fait | Conséquence de conception |
|---|---|
| `/api/gemini/*` proxifie déjà n'importe quel sous-chemin (`App/api-gateway/src/index.js:422`) | Aucune clé ni secret côté client. Rien à changer côté gateway. |
| Le gateway ne fait **aucun WebSocket** | La variante `-live` est hors de portée. Sans objet ici (fichiers). |
| `custom_vocabulary` vit **uniquement** sur `/v1beta/interactions`, pas sur `generateContent` | On passe par l'Interactions API. |
| `custom_vocabulary` est **incompatible** avec diarisation ET timestamps | **Choisir le calage** : pas de vocabulaire personnalisé pour SubWhisper. |
| `timestamp_granularities:["segment"]` ne rend **AUCUN** timestamp | C'est **le mot ou rien** → il faut **fabriquer les blocs** (P3). |
| L'audio se passe en `data` + `mime_type` **à plat** (`inline_data` → 400) | Format du corps à respecter tel quel. |
| Réponse dans `steps[].content[].text` ; mots dans `annotations[]` `type:"word_info"`, offsets `"2.200s"` | Parsing à écrire. |
| Diarisation plafonnée à **3 locuteurs** | Suffisant pour l'usage, à afficher comme limite. |
| Coût **$0,30/h** contre $0,04/h (×7,5) ; péage fixe ~2,8 s **amorti** sur un chunk de 13 min | Négligeable en perso. **Pas sur Pro** (facturé) → voir P0. |

---

# Les étapes

## P0 — Correctif Pro : le modèle de traduction est MORT ✅ *(fait, non poussé)*

`gemini-2.0-flash` répond **404** (« no longer available […] use models/gemini-3.6-flash »).
Il était codé en dur comme traducteur par défaut dans **les deux** versions
(`subwhisper-pro/app.html:3039-3040`, `App/subwhisper/index.html:2751-2752`).
⇒ **Toute traduction en mode Gemini échouait**, y compris pour les clients de SubWhisper
**Pro** (payant). Invisible pour Quang, qui active DeepSeek.

- [x] Remplacé par `gemini-3.6-flash` dans les deux fichiers (+ `.bak-2026-09-07-gemini2flash`).
- [ ] **Pousser sur `subwhisper-pro`** — ⚠️ le dépôt est **public** et sert `sub-whisper.com` :
      un push **déploie en production**. Accord de Quang requis.

📌 **Décision Quang (07/09) — dette assumée** : Pro ne reçoit **que** les correctifs, aucune
amélioration, *« car ça ne rapporte pas beaucoup »* et Gemini y coûterait ×7,5.
⚠️ Contre-indication signalée et acceptée : la divergence PRO/APP s'aggrave (74 vs 16 langues,
deux gateways). À rouvrir seulement si Pro redevient un axe de revenu.

## P1 — Réparer le garde-fou : `model_watch.py` est aveugle aux modèles Gemini

**Cause racine de P0.** `llm-cli/model_watch.py:293` :
`UNTESTABLE_PREFIXES = ("gemini-", "claude-", "anthracite-org/", "fal-ai/", "gpt-5.")`.
Les modèles Gemini sont déclarés **non testables** : le watcher les repère dans les fichiers
surveillés (les deux fichiers SubWhisper y sont, l.324 et l.326) mais **ne les appelle jamais**.

✅ Or ils **sont** testables — vérifié : `gemini-2.0-flash` → **404 net**, `gemini-3.6-flash`
→ **200**, `gemini-2.5-flash` → **200**, via un `generateContent` de 16 tokens.

- [ ] Retirer `"gemini-"` de `UNTESTABLE_PREFIXES`.
- [ ] Ajouter un testeur Gemini dans `PROVIDERS` (appel réel via le gateway).
- [ ] Rejouer `python llm-cli/model_watch.py` → doit sortir **exit 1** tant que P0 n'est pas poussé.

⚠️ Troisième incident du même genre après Groq (09/07) et DeepSeek (24/07) : **une surveillance
qui exclut un fournisseur finit par payer cette exclusion.**

## P2 — Sélecteur de moteur STT (le cœur de la demande)

Patron à copier **exactement** : le sélecteur `aiEngine` qui existe déjà
(`index.html:1315-1318`, `getAIEngine()` 1734, `saveAIEngine()` ~1745, restauration au boot
~1691, clé `localStorage`).

- [ ] `<select id="sttEngine">` avec **3 options** : `groq` · `gemini` · `croise`.
- [ ] Clé `localStorage` **`sw_sttengine`**, symétrique de `sw_aiengine`.
- [ ] **Défaut = `groq`** — comportement actuel strictement inchangé, zéro régression pour
      quelqu'un qui ne touche à rien. Quang bascule quand il veut.
      📌 Conforme à la règle « pas d'auto-switch silencieux, l'utilisateur garde le contrôle ».
- [ ] Branchement : **une seule ligne**, en tête de la cascade `index.html:1941-1943`.
- [ ] Pastille d'état `GEM` déjà présente dans `API_DOTS` — vérifier qu'elle reflète le STT.

## P3 — `transcribeGemini()` + fabrication des blocs SRT

- [ ] `transcribeChunkGemini()` calqué sur `transcribeChunkGroq()` (`index.html:2547-2579`).
      **Contrat de retour à respecter** : `{ srt, lang, segments:[{start,end,text}], rawSegments }`.
- [ ] Appel : `POST {GATEWAY_URL}/api/gemini/v1beta/interactions`, corps
      `{model:"gemini-3.5-transcribe", input:[{type:"audio", mime_type, data:<b64>}],
      generation_config:{transcription_config:{mode:{type:"verbatim",
      timestamp_granularities:["word"]}}}}`.
      **Auto-détection : omettre `language_codes`** — c'est l'usage de Quang, et ça ne coûte
      rien (mesuré : ±1 pt).
- [ ] **Fabriquer les blocs depuis les mots** : couper sur une pause > 0,6 s **ou** à 84
      caractères. ✅ Mesuré : plus conforme que les segments Groq — sur du FR, **5 violations
      sur 13 blocs (38 %) contre 9 sur 11 (82 %) pour Groq**.
- [ ] Réutiliser `transcribeGroq()` pour tout le reste (chunking, traduction, affichage) :
      il contient déjà toute la logique.
- [ ] Conserver le garde-fou anti-hallucination existant : `relEnd = min(seg.end, relStart+30, maxRelEnd)`.

## P4 — Mode « croisé » : Groq en garde-fou de Gemini

Mesuré le 07/09 sur 60 phrases / 6 langues — **séparation nette** : l'hallucination ressort à
**190 % de désaccord**, la pire phrase saine à **20,5 %** (médiane 2,7 %). Aucun recouvrement.

Seuil **30 %** : 1 bascule sur 60, hallucination rattrapée, **0 bascule inutile**.
Erreur moyenne **3,4 %** contre 6,3 % (Groq seul) et 5,3 % (Gemini seul) → **bat les deux**.

- [ ] Lancer les deux moteurs **en parallèle** (`Promise.all`) : la latence reste le max, pas
      la somme. Coût **0,30 + 0,04 = 0,34 $/h, soit +13 %** — ce n'est **pas** un doublement.
- [ ] Bascule sur Groq si : désaccord > 30 % **OU** Gemini rend vide (le cas des 9/40).
- [ ] **Tracer chaque bascule dans le log visible** (`appendLog`) : jamais de substitution
      silencieuse.
- [ ] ⚠️ Réserve à garder en tête : **une seule hallucination observée** sur 60 phrases. La
      séparation est nette mais le détecteur n'est validé que sur un cas positif.

## P5 — Ressusciter la diarisation et la vue RICH

Elles existent dans l'UI et **ne font rien** (voir « État des lieux »). Gemini fournit les mots
horodatés qui leur manquent.

- [ ] Remplir `wordData` depuis `annotations[].word_info` → le bouton RICH s'active seul.
- [ ] Brancher `optDiarize` sur `transcription_config` (diarisation Gemini, **3 locuteurs max**).
- [ ] ⚠️ Rappeler dans l'UI que diarisation et `custom_vocabulary` s'excluent (on choisit le calage).

## P6 — Tests et livraison

- [ ] Bump **v9.43 → v9.50** aux **4 endroits** : `<title>` l.15, badge `.ver-badge` l.1141,
      footer l.1481, champ `version:` l.4144.
- [ ] `node --check` sur toute string JS éditée (règle projet).
- [ ] Test **live réel** : une vidéo JP, une ZH, une avec dialogue — sur les 3 modes, avec le
      **switch auto activé** (c'est ainsi que Quang s'en sert) et **traduction FR via DeepSeek**.
- [ ] Vérifier les 3 défauts connus : blocs muets, boucles, hallucination.
- [ ] Commit + push (⚠️ dépôt `App` **public**, un push déploie ; **zéro secret**).

---

## Journal

- **07/09/2026** — Campagne de mesure (4 régimes, ~500 appels), roadmap ouverte.
  P0 corrigé localement, non poussé. Corpus de bancs (4,1 Go) supprimés après usage.
