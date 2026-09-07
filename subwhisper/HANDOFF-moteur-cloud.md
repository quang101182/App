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

Deux choses restent ouvertes, elles sont détaillées en bas de ce fichier :
🔴 **la progression n'atteint jamais le navigateur** (mesuré) — et
🟠 **Gemini rate ~60 % des répliques sur ce type d'audio**, sans que le mode croisé le rattrape.

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
   - ❌ **le log client ne nomme PAS le moteur** — pour une raison sans rapport avec le moteur :
     **aucun log intermédiaire n'atteint le navigateur**. Voir la section rouge en bas.

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

# 🔴 Ce que le test a révélé, et qui n'était pas dans le périmètre

## 1. La progression n'atteint JAMAIS le navigateur (mesuré, pas supposé)

**Le symptôme** : pendant les 53 s de traitement, le client ne voit **rien**. Mesure faite en
traçant l'état complet renvoyé par `/job-status`, et pas seulement le champ `log` :

```
[  0.2s] ('processing', None, None)
[ 52.9s] ('done', 100, 'Transcription terminée.')
```

Rien entre les deux. Or Fly a bien émis au moins cinq mises à jour (`Audio…`, `Chunk 1/3 → …`,
2/3, 3/3, fin), et **aucune n'a échoué** : `fly logs` ne contient aucun `[updateWorker] Callback
HTTP` ni `Erreur callback`. Les écritures partent, le worker répond 200.

**Où ça se perd** : `handleJobDone` écrit l'état dans **Cloudflare KV**, et `handleJobStatus`
le relit avec `env.JOB_KV.get(key)`. KV est un cache de lecture à l'edge : une valeur relue en
boucle depuis le même POP reste figée le temps de son TTL. Un job de 53 s se termine donc
**avant** que la moindre mise à jour devienne visible.

⛔ **Ce n'est pas réglable en restant sur KV** : le `cacheTtl` de KV a un **plancher de 60 s**,
soit plus long que le job entier. Il faut changer de transport — Durable Object, ou faire poller
le client directement sur Fly.

📌 **Pourquoi ça compte plus qu'il n'y paraît** : c'est la moitié invisible du bug du 07/09.
La v9.51 a réparé la *détection* d'un job mort (404 → rejet en 3 s). Mais le **silence** de
l'interface pendant tout un traitement n'a jamais été causé par le job mort : il est structurel.
Sur une vidéo de 2 h, l'utilisateur regarde une barre immobile pendant vingt minutes.

🛑 **Non corrigé volontairement** — changer le transport d'état est une décision d'architecture,
hors du mandat « déployer et valider le choix de moteur ». **En attente d'arbitrage de Quang.**

## 2. Sur ce type d'audio, Gemini rate ~60 % des répliques — et le croisé ne le rattrape pas

Sur la même vidéo : **Groq 56 segments, Gemini 22**. Le mode `croise` rend exactement le même
résultat que Gemini seul (22 segments) et **n'a basculé aucune fois**.

C'est **conforme au code**, et c'est précisément le point : le croisé ne bascule que si Gemini
rend **totalement vide**. Un chunk où Gemini rend *2 segments au lieu de 12* passe pour un succès.
Ici les chunks 0 et 1 portent un contenu très comparable (les mêmes clips, répétés) et rendent
**2** contre **12** segments : Gemini est instable, jamais muet, donc jamais rattrapé.

⚠️ Le corpus est le régime défavorable déjà documenté dans la ROADMAP (« audio à faible parole
articulée », Gemini muet 9/40) : clips courts, musique, répliques éparses. **Ce n'est pas une
contradiction des mesures de la campagne**, qui portaient sur du dialogue continu japonais et
chinois. Mais ça montre que le filet a une maille trop large : *muet* est un cas particulier de
*lacunaire*, et seul le cas particulier est couvert.

🛑 **Non corrigé volontairement** : élargir le déclencheur (p. ex. « Gemini rend moins de N % des
segments de Groq ») obligerait à faire tourner les deux moteurs systématiquement et à recalibrer
sur corpus — exactement le genre de seuil dont le 07/09 a montré qu'il ne se transporte pas d'un
corpus à l'autre. **À décider, pas à improviser.**

## Le harness de test, réutilisable

`test_cloud.py` (scratchpad de session) rejoue le chemin cloud complet hors navigateur :
presign → PUT R2 → `POST /process` avec `sttEngine` → poll `/job-status`. Il lit le
`WORKER_SECRET` sans jamais l'imprimer.
🪤 **Piège de mesure payé ici** : sa première version ne traçait que le champ `log`, et faisait
donc conclure « aucun log » alors que la vraie question était l'état complet. **Tracer le tuple
`(status, progress, log)`**, jamais un seul champ — sinon on mesure son propre harness.
