# HANDOFF — déployer et valider le choix de moteur STT sur le chemin cloud

> Ouvert le **07/09/2026**. **Autosuffisant** : tout est ici, ne renvoie à aucune mémoire externe.
> Le code est **écrit, commité, poussé** (`App` **000ec17**) mais **JAMAIS EXÉCUTÉ EN RÉEL**.

## L'état en une phrase

Le sélecteur de moteur (Groq / Gemini / Croisé) fonctionne et est validé pour les fichiers
traités dans le navigateur. Sur le **chemin cloud** — gros fichiers **non-WAV** — le code vient
d'être écrit pour que le choix traverse jusqu'au serveur, mais **rien n'a été déployé ni testé**.

⚠️ **Ne pas croire ce chemin fonctionnel tant que le test ci-dessous n'est pas passé.**

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

**Correctif à appliquer** (même logique que `telegram-video/moteur/soustitres.py` v0.83.1, à
copier de là) : rendre la taille de chunk dépendante du moteur — ~24 Mo pour Groq, **~11 Mo**
pour Gemini et Croisé.

## Les étapes, dans l'ordre

1. **Authentifier flyctl** — c'est le seul blocage réel :
   ```
   fly auth login
   ```
   (`flyctl` est installé : `C:/Users/quang/.fly/bin/fly`)
2. **Lire les logs du redémarrage du 07/09** — question restée sans réponse : pourquoi la machine
   a-t-elle redémarré ? Piste non prouvée : manque de mémoire (**2 Go, 1 CPU partagé**,
   `fly.toml:39-41`) saturé par ffmpeg sur une grosse vidéo.
   ```
   fly logs --app subwhisper-ffmpeg
   ```
   Si c'est bien un OOM : passer à 4 Go est le correctif direct.
3. **Appliquer le correctif de taille de chunk** (§ ci-dessus) AVANT de déployer — sinon le test
   ne prouvera rien sur Gemini.
4. **Déployer** :
   ```
   cd App/subwhisper/fly-ffmpeg && fly deploy
   cd ../cloudflare-worker && npx wrangler deploy
   ```
   ⚠️ L'OAuth wrangler est mort : utiliser `CLOUDFLARE_API_TOKEN`.
5. **Vérifier la version servie** : `curl https://subwhisper-ffmpeg.fly.dev/health`
   doit rendre `"version":"1.31.0"`.
6. **Tester en réel**, avec une vraie grosse vidéo non-WAV, sur les 3 modes :
   - le log client doit nommer le moteur réellement utilisé ;
   - vérifier dans `fly logs` la ligne `segments reçus de Gemini` (et non de Groq) ;
   - contrôler qu'aucun chunk ne part en HTTP 400.

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
