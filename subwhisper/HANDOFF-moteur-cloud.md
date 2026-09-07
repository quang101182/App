# HANDOFF — déployer et valider le choix de moteur STT sur le chemin cloud

> Ouvert le **07/09/2026**. **Autosuffisant** : tout est ici, ne renvoie à aucune mémoire externe.
> Le code est **écrit, commité, poussé** (`App` **000ec17**) mais **JAMAIS EXÉCUTÉ EN RÉEL**.

## ✅ CLOS le 07/09/2026 au soir — déployé, testé, mesuré

Les 6 étapes ci-dessous ont été exécutées. **Le chemin cloud fonctionne sur les 3 moteurs** :
Fly **1.32.0** et le worker Cloudflare sont déployés, et un test sur une vraie vidéo de
**14 min 47 / 33 Mo** est passé sur `groq`, `gemini` et `croise`.

| Moteur | Chunks | Segments | SRT | Durée | HTTP 400 |
|---|---|---|---|---|---|
| `groq` | 2 × 24 Mo | **56** | 3007 car | 64,7 s | 0 |
| `gemini` | 3 × 11 Mo | 22 | 1263 car | 63,7 s | **0** |
| `croise` | 3 × 11 Mo | 22 | 1249 car | 63,7 s | **0** |

**Les deux réserves ouvertes en fin de soirée ont été mesurées, et toutes deux sont tombées** :
la progression **arrive bien**, et le déclencheur du mode croisé **ne doit pas être élargi**.

🔴 **Puis Quang a lancé une vraie vidéo, et elle s'est bloquée à 35 %.** C'était une régression
introduite le matin même, sur la voie **multipart** (fichiers > 100 Mo) — celle qu'aucun de mes
tests n'empruntait. Corrigée en **v9.53** / worker redéployé. Détail : § « Le blocage à 35 % ».
⇒ **Aucun chantier ouvert, mais lire ce paragraphe avant de retoucher au dispatch.**

### Historique — l'état au matin du 07/09 (conservé)

Le sélecteur de moteur (Groq / Gemini / Croisé) fonctionne et est validé pour les fichiers
traités dans le navigateur. Sur le **chemin cloud** — gros fichiers **non-WAV** — le code vient
d'être écrit pour que le choix traverse jusqu'au serveur, mais **rien n'a été déployé ni testé**.

## Pourquoi ce chemin existe

SubWhisper tourne dans un navigateur, qui n'a pas ffmpeg. Pour un fichier volumineux non-WAV, il
délègue donc à un serveur Fly qui, lui, a ffmpeg (`index.html:2088` : `if (!isWavFile && workerUrl)`).
C'est exactement ce que telegram-video fait en local avec son propre ffmpeg — d'où le fait que
telegram-video, lui, n'a jamais eu ce problème.

⚠️ **Un fichier WAV ne passe PAS par là** (byte-slicing local), ni un fichier < 24 Mo.

## Ce qui a été fait, et où

`sttEngine` traverse trois maillons — les trois sont commités :

| Fichier | Rôle |
|---|---|
| `index.html:2407` | envoie `sttEngine: getSttEngine()` dans le POST `/process` |
| `cloudflare-worker/src/index.js` | lit `sttEngine` du body et le relaie à Fly `/extract` |
| `fly-ffmpeg/src/server.js` | `transcribeChunkAuto()` dispatche `groq` \| `gemini` \| `croise` |

`transcribeWithGemini()` est le miroir exact de `transcribeWithGroq()` : même signature, même
tableau de segments en sortie. Mode **`verbatim`** (jamais `smart`), auto-détection, et
fabrication des blocs depuis les mots — **Gemini ne rend aucun timestamp en granularité
`segment`, c'est le mot ou rien**.

Versions : client **v9.52**, serveur Fly **1.31.0**.

## ⛔ Le point qui va casser, et il est connu d'avance

**Gemini refuse au-delà d'environ 16 Mo de base64.** Mesuré le 07/09 par dichotomie, côté
telegram-video, sur de vraies tranches mp3 mono 16 kHz :

| Taille | Base64 | Résultat |
|---|---|---|
| 11,4 Mo | 15,3 Mo | ✅ OK en 100 s |
| 13,4 Mo | 17,8 Mo | ❌ HTTP 400 |
| 23,7 Mo | 31,5 Mo | ❌ HTTP 400 |

Or Fly découpe en chunks de `CHUNK_MAX_BYTES` ≈ **24 Mo** (`fly-ffmpeg/src/server.js:54-55`).
⇒ **Tous les chunks dépasseront.** Le filet Groq du mode `croise` les rattrapera, donc rien ne
cassera visiblement — mais **Gemini ne servira jamais**, ce qui vide la fonctionnalité de son sens.

📌 C'est exactement le piège déjà rencontré côté telegram-video : *un filet qui fonctionne peut
masquer que la fonction, elle, ne sert à rien.*

~~**Correctif à appliquer**~~ → ✅ **APPLIQUÉ ET VÉRIFIÉ EN PROD** (Fly 1.32.0, commit `App` 7a81957).
`chunkMaxBytesPour(sttEngine)` rend 24 Mo pour Groq, **11 Mo** pour Gemini et Croisé.
**Preuve mesurée** (log Fly du 07/09 18:43) : `Moteur STT = gemini -> chunks de 11.0 Mo (360s)`,
puis `3 chunk(s)`, et **les 3 ont répondu** (2, 12 et 8 segments) — **aucun HTTP 400**.
Le même fichier en `groq` donne bien `2 chunk(s)` de 24 Mo : la borne suit le moteur.

## Les étapes, dans l'ordre

1. ~~**Authentifier flyctl**~~ — ✅ **il n'y avait aucun blocage.** `fly auth whoami` répond
   « No access token available », mais le token du 06/04 est **valide** dans
   `C:/Users/quang/.fly/config.yml` ; le binaire ne le lit simplement pas depuis ce shell.
   ```bash
   export FLY_API_TOKEN="$(sed -n 's/^access_token: //p' ~/.fly/config.yml)"
   ```
   📌 **Un « pas authentifié » de flyctl ne veut pas dire « pas de token ».** Vérifier le
   `config.yml` avant de réclamer un `fly auth login` à Quang.
2. ✅ **Question tranchée : CE N'EST PAS UN OOM.** La piste « manque de mémoire » était fausse.
   Le log est sans ambiguïté — la machine s'éteint **elle-même**, proprement :
   ```
   [AUTO-SHUTDOWN] Aucun job depuis 30min — arrêt du serveur.
   INFO Main child exited normally with code: 0
   machine exited with exit code 0, not restarting
   ```
   puis Fly la rallume à la requête suivante (`request.url="force://..." Starting machine`).
   C'est `IDLE_SHUTDOWN_MS = 30 min`, voulu, avec `auto_stop_machines = "off"`.
   ⇒ **Ne PAS passer à 4 Go** : ce serait un correctif pour un problème inexistant.
   ⚠️ La vraie conséquence, elle, reste entière : la machine s'éteignant, **les jobs gardés en
   mémoire (`const hlsJobs = new Map()`) disparaissent** — c'est la cause du 404 traité en v9.51
   côté client. La persistance des jobs reste la seule vraie parade.
3. **Appliquer le correctif de taille de chunk** (§ ci-dessus) AVANT de déployer — sinon le test
   ne prouvera rien sur Gemini.
4. ✅ **Déployé le 07/09** (les deux) :
   ```
   cd App/subwhisper/fly-ffmpeg && fly deploy
   cd ../cloudflare-worker && npx wrangler deploy
   ```
   ⚠️ L'OAuth wrangler est mort : utiliser `CLOUDFLARE_API_TOKEN`.
5. ✅ **Version vérifiée** : `/health` rend `"version":"1.32.0"`.
   🪤 **Piège trouvé en le vérifiant** : la version vivait à **deux endroits** et ils avaient
   divergé — `/health` disait 1.32.0 pendant que la bannière de démarrage annonçait encore
   **1.30.0**. Un log de démarrage qui ment est pire qu'absent : c'est justement lui qu'on lit
   pour vérifier un déploiement. Les deux lisent désormais la constante unique `SERVER_VERSION`.
6. ✅ **Testé en réel** — vidéo de 14 min 47 / 33 Mo (concaténation de 7 clips réels, dialogue
   EN+FR), les 3 modes, chemin cloud complet (presign → R2 → `/process` → poll `/job-status`).
   - ✅ `segments reçus de Gemini` bien présent dans `fly logs`, sur les 3 chunks ;
   - ✅ **aucun HTTP 400** ;
   - ✅ **le log client nomme bien le moteur** — vérifié sur un job long, le navigateur reçoit
     `53% · 🎯 Chunk 5/8 → Gemini+Groq (croise) (24m01s → 30m02s)`.

## Deux autres choses réparées le 07/09 sur ce chemin (déjà poussées)

- **v9.51** : un job disparu du serveur laissait le navigateur figé **30 minutes en silence**.
  Le serveur garde ses jobs **en mémoire** (`const hlsJobs = new Map()`), donc un redémarrage les
  perd et `/job-status` rend 404 — et le client avalait ce 404 dans un `catch(e) {}` **vide**.
  Désormais : rejet en 3 s avec un message clair.
  📌 Piste d'amélioration non traitée : **persister les jobs** côté Fly, pour qu'un redémarrage
  ne les perde plus du tout.
- Le warning « le serveur a probablement redémarré » existait déjà mais était **inatteignable** :
  il exige `status.status === 'processing'`, jamais vrai sur un 404.

## Contexte utile pour juger

Réglages recommandés, mesurés : **STT = Croisé · IA = DeepSeek · sortie FR · switch auto**.
DeepSeek plutôt que Gemini en traducteur parce que Gemini-flash *répare* les erreurs de
transcription et masque donc le gain du moteur, alors que DeepSeek les propage — c'est avec lui
qu'un meilleur STT paie (japonais : −0,2 pt du plafond d'une transcription parfaite, contre
+2,2 pt via Groq).

Feuille de route complète du chantier : `ROADMAP-moteurs-stt.md` (même dossier).


---

# ✅ Les deux réserves, mesurées et refermées le 07/09 au soir

Les deux points que j'avais ouverts en fin de journée étaient **l'un faux, l'autre à ne pas
corriger**. Ils sont conservés ici avec ce qui les a tranchés, pour que personne ne les rouvre.

## 1. « La progression n'atteint jamais le navigateur » → ❌ FAUX, c'était mon échantillon

**Ce que j'avais écrit** : le client ne voit rien pendant tout le traitement, il faudrait changer
le transport d'état (Durable Object ou poll direct sur Fly).

**Ce que la mesure a montré** : sur un job long, la progression **arrive**, et elle nomme le
moteur. Relevé réel sur 43 min d'audio (`banc_43min.py`) :

```
[   0.6s] None% | None
[  53.5s]  53% | 🎯 Chunk 5/8 → Gemini (24m01s → 30m02s)...
[  96.3s] 100% | Transcription terminée.
```

**Mon erreur de raisonnement** : mon premier test durait **53 s**, soit moins que le TTL du cache
de lecture KV (~60 s). Dans ce régime — et seulement dans celui-là — on ne voit effectivement
rien. J'en avais conclu, à tort, que rien ne passait *jamais*, et j'avais extrapolé « une barre
immobile pendant vingt minutes sur une vidéo de 2 h ». **C'est l'inverse** : plus le job est long,
plus il reçoit de mises à jour.

📌 **Ce que Quang a corrigé, et il avait raison** : *« l'outil a toujours fonctionné avant, même
sur une vidéo de 2 h voire 3 h »*. Un outil qui marche depuis des mois est une donnée ; une mesure
qui semble dire le contraire doit d'abord être suspectée, elle.

**Le fait exact, à retenir** : la progression a une **granularité d'environ 45 à 55 s** (écarts
mesurés : 52,8 · 42,9 s), imposée par le cache KV dont le `cacheTtl` a un plancher de 60 s. Un
job de 43 min d'audio (96 s de traitement) donne 3 mises à jour. **Ce n'est pas un blocage, c'est
une cadence** — et elle n'a jamais gêné personne.

⇒ **Rien à corriger.** Rendre la progression fluide supposerait de faire relayer l'état par Fly
en direct : du confort, pour un défaut que l'usage réel n'a jamais fait remonter.

## 2. « Le mode croisé a une maille trop large » → ⛔ VRAI, mais NE PAS le corriger

L'observation de départ était juste : le croisé ne bascule que si Gemini rend **totalement vide**,
donc un chunk simplement *lacunaire* passe pour un succès. J'allais élargir le déclencheur avec un
ratio Gemini/Groq. **La calibration l'interdit.**

Mesure sur 7 extraits réels, 3 régimes, chunks de 6 min, les deux moteurs appelés par les mêmes
endpoints que Fly (`calibrer_croise.py`) — ratio de **caractères** transcrits :

| ratio | extrait | régime |
|---|---|---|
| **0,00** | cjk-2 | dialogue CJK réel *(Gemini muet)* |
| 0,37 | cjk-3 | dialogue CJK réel |
| 0,50 | cjk-1 | dialogue CJK réel |
| 0,78 | perso-2 | parole spontanée bruitée |
| 0,99 | perso-1 | parole spontanée bruitée |
| 1,03 | cjk-4 | dialogue CJK réel |
| **1,15** | clips-1 | faible parole — *Gemini fait MIEUX que Groq* |

⛔ **Le ratio ne sépare rien.** Il va de **0,00 à 1,03 à l'intérieur du seul régime CJK**. Un seuil
à 0,60 ferait basculer `cjk-1` et `cjk-3` sans qu'aucune mesure ne dise que Gemini y a tort — il
peut simplement être plus concis là où Whisper se répète. Pire : le régime que je croyais
défavorable à Gemini (`clips-1`) est celui où il gagne.

⚠️ **Le même contenu peut donner deux ratios opposés selon le découpage** : les clips YouCut
donnent **0,42** en concaténation de 15 min et **1,15** sur un extrait isolé. Une grandeur aussi
instable ne peut pas piloter une bascule.

📌 **Deuxième fois en une journée qu'un seuil comparatif entre deux moteurs échoue.** Le 07/09 au
matin, c'était le seuil de *désaccord textuel* à 30 % ; le soir, le ratio de *volume*. Les deux
paraissaient nets sur un corpus, aucun ne s'est transporté. ⇒ voir `feedback_seuil_comparatif_deux_moteurs.md`.

✅ **Le déclencheur actuel est le bon, et la mesure le valide** : `cjk-2` rend un ratio de 0,00,
c'est-à-dire exactement le cas « Gemini muet » que le croisé attrape déjà. Le seul signal fiable
est **binaire** (vide / pas vide), et il est en place.

⇒ **Ne pas rouvrir ce point.** Le croisé restera imparfait sur les chunks lacunaires : c'est un
choix mesuré, pas un oubli. Quiconque veut le rouvrir doit d'abord produire un discriminant qui
sépare sur les 7 points ci-dessus.

## Les harnesses, réutilisables

Dans le scratchpad de session, versionnables si besoin :
- `test_cloud.py` — rejoue le chemin cloud complet hors navigateur (presign → R2 → `/process` → poll).
- `banc_43min.py` — le même audio dans les 3 moteurs + cadence réelle des mises à jour reçues.
- `calibrer_croise.py` — appelle Groq et Gemini sur les mêmes chunks, rend le tableau de ratios.

Tous lisent le `WORKER_SECRET` sans jamais l'imprimer (`secret.py`).

🪤 **Piège de mesure payé deux fois ce soir, à ne pas repayer** :
1. la première version de `test_cloud.py` ne traçait que le champ `log` — d'où « aucun log » alors
   que la question portait sur l'état complet. **Tracer le tuple `(status, progress, log)`.**
2. un job de 53 s est **plus court que le cache** qu'on prétend observer. **Un banc doit durer plus
   longtemps que le phénomène qu'il mesure**, sinon il mesure sa propre fenêtre.


---

# 🔴 Le blocage à 35 % — une régression du matin, révélée par le premier usage réel

## Le symptôme, tel que Quang l'a vu

*« Je ne sais pas si c'est bloqué ou si ça avance ; ça en est à l'étape du serveur cloud. »*
Puis : *« Traitement sur serveur cloud à 35 %. »* — et ça n'a plus bougé.

**Ce n'était ni lent ni capricieux** : `fly logs` montrait que le job avait été **abandonné cinq
minutes plus tôt**, après 5 × `Groq HTTP 401 Invalid API Key`. Et `/job-status` rendait
`status: "uploaded"`, sans progression ni erreur : le worker n'avait **jamais** eu de nouvelles
de Fly. Le navigateur interrogeait donc un état figé, pour toujours.

## La cause — un argument manquant, et deux implémentations au lieu d'une

Le matin (`000ec17`), `dispatchToFly` a gagné un paramètre **`sttEngine` en 5ᵉ position**. Or il
existait **deux** implémentations du même dispatch vers Fly :

| Chemin | Implémentation | A suivi ? |
|---|---|---|
| `handleProcess` (≤ 100 Mo) | un `fetch` **inline**, dupliqué | ✅ oui |
| `handleUploadComplete` (> 100 Mo) | `dispatchToFly` | ❌ **non** |

Les arguments étant **positionnels**, tout s'est décalé d'un cran chez le second :

```
sttEngine         <- groqKey (null)
groqKey           <- l'URL de callback   => Fly présentait une URL à Groq comme clé => 401
workerCallbackUrl <- la clé du gateway   => les updates partaient dans le vide
gatewayKey        <- gatewayUrl
```

⛔ **Rien ne pouvait le signaler** : les deux valeurs mal placées étaient des **chaînes non
vides**, donc aucun contrôle de présence ne mordait, et `if (groqKey)` était même *vrai* — ce qui
a fait basculer Fly sur l'appel direct à Groq au lieu du gateway.

## Pourquoi mes six tests de la soirée sont tous passés au vert

`index.html` : `isMultipart = filesize > 100 * 1024 * 1024`. **Tous mes fichiers de test faisaient
moins de 100 Mo** et empruntaient donc l'autre branche. La branche cassée est précisément celle
que le poids réserve aux **vraies grosses vidéos** — les seules qui aillent dans le cloud.

📌 **Une branche non testée n'est pas une branche qui marche.** Quand un code choisit son chemin
sur un **seuil** (taille, durée, format), le banc doit franchir ce seuil, sinon il valide l'autre
moitié du code en croyant tout valider. Mon corpus était biaisé par sa commodité : des fichiers
petits, parce qu'ils s'uploadent vite.

## Ce qui a été corrigé — la cause, pas le symptôme

- **`dispatchToFly` prend un objet nommé.** Un appelant qui oublie un champ passe désormais
  `undefined` sur *ce* champ ; il ne décale plus les suivants. Le mode de panne devient
  structurellement impossible.
- **`handleProcess` n'a plus son `fetch` inline** : un seul point de dispatch, donc plus aucune
  copie à oublier de mettre à jour. C'était ça, la cause profonde.
- **La voie multipart transmet enfin `sttEngine`** (client *et* worker). ⚠️ À noter : même sans
  le décalage, le sélecteur de moteur n'avait **aucun effet** sur les fichiers > 100 Mo — le
  client ne l'envoyait pas dans `/upload-complete`. Le chantier du matin était donc incomplet
  sur sa moitié la plus utile.
- **`/upload-complete` marque le job `processing`** et non plus `uploaded` : c'est l'état figé
  que Quang avait sous les yeux.

## La preuve

Voie multipart, 363 Mo / 22 min, mode croisé :

```
presign multipart OK · 4 parties
/upload-complete -> 200 {"status":"processing"}
[Fly] Moteur STT = croise -> chunks de 11.0 Mo (360s) · 4 chunk(s)
[Fly] Chunk 0..3 : 11, 24, 29, 30 segments reçus de Gemini
[Fly] SRT assemblé: 5148 caractères, 94 segments · Pipeline terminé avec succès
done en 80 s · zéro 401
```

`harness/test_multipart.py` couvre désormais cette branche, et **refuse de tourner sur un fichier
de moins de 100 Mo** — un banc qui ne franchit pas le seuil qu'il prétend tester ne prouve rien.


---

# 🛑 FIN DE SESSION 07/09/2026 — la gestion des sous-titres est revenue au comportement d'avant

Après tout ce qui précède, Quang a testé sur ses vraies vidéos et signalé que le rendu
s'était **dégradé** : *« les textes ne correspondent pas du tout à la vidéo, même les
synchronisations avec les voix, alors qu'avant c'était quasiment parfait »*, puis
*« tu n'as rien à inventer […] mais en gardant les avantages de toutes les mises à jour
d'aujourd'hui »*.

## Ce qui a été RETIRÉ (v9.55 / Fly 1.36.0, commit `App` 100ba47)

Les trois modifications de post-traitement introduites le soir même :
déduplication conditionnée à la contiguïté · suppression des blocs de durée nulle ·
durées d'affichage minimale et maximale.

⚠️ **Les défauts qu'elles corrigeaient sont réels et mesurés** (un bloc affiché 594 s,
168 blocs de durée nulle sur 545, 67 % des blocs sous la seconde). Mais elles changeaient
**l'entrée du nettoyage IA et de la traduction**, donc tout l'aval — et le **traitement
automatique de Quang est toujours actif**, donc elles le touchaient à 100 %.
Le travail retiré est sur la branche **`travail-timings-2026-09-07`**.

✅ Vérifié par empreinte : `autoFormatSRT`, `dedupConsecutiveBlocks`, `motsVersBlocs`,
`parseSRT`, `buildSRT`, `tsToMs`, `msToTs`, `translateSRT`, `cleanAI`, `_cleanAIDetect`,
`shiftSRT`, `secToSrtTime` sont **identiques à la v9.43 du 30/08**, ainsi que le pipeline
automatique.

## Ce qui est CONSERVÉ

Le sélecteur de moteur STT (groq/gemini/croisé), `transcribeChunkGemini` /
`transcribeChunkCroise` / `motsVersBlocs`, la taille de chunk adaptée au moteur (11 Mo pour
Gemini), la voie multipart réparée, les modèles Gemini vivants. Le traitement automatique
reste compatible avec les nouveaux moteurs **par construction** : il travaille sur le SRT
produit sans jamais regarder quel moteur l'a produit.

## ⛔ Ce qui n'est PAS résolu, et l'élément qui manque

**Le problème de rendu signalé par Quang n'a jamais été reproduit** — je n'ai pas eu la
vidéo source, seulement des SRT dont j'ignorais la vérité audio.

Ce qui est **établi** :
- les **timestamps ne dérivent pas** : écart médian **+0,00 s** sur 8 tranches de 500 s,
  entre le SRT d'avant et celui d'après, sur tout un fichier de 66 min ;
- `transcribeWithGroq` côté serveur est **identique** à la veille ;
- les 168 blocs invalides venaient d'**une seule** hallucination Whisper (un segment de
  durée nulle à 429,815 s, rempli de virgules) que le formatage a découpée.

Ce qui reste **inexpliqué** : 378 blocs la veille contre 545 le lendemain sur le même
fichier, avec un code de chemin Groq identique.

⇒ **Pour trancher : demander la vidéo source, ou 2-3 minutes autour d'un passage
visiblement décalé.** Rejouer le même extrait avec le code de la veille et celui du jour
est la seule mesure qui tranche. Sans le fichier, on raisonne sur des sous-titres dont on
ne connaît pas la vérité — c'est exactement ce qui a produit trois correctifs inutiles.
