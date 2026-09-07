# Harnesses du chemin cloud SubWhisper

Trois bancs qui exercent le **chemin cloud** (gros fichiers non-WAV : navigateur → Worker
Cloudflare → R2 → Fly + ffmpeg → Groq/Gemini) **sans passer par le navigateur**. Écrits le
07/09/2026 pour valider le sélecteur de moteur STT, et conservés parce qu'ils ont chacun
tranché une question qu'aucune lecture de code n'aurait tranchée.

## Ce que chacun sert à décider

| Script | Répond à |
|---|---|
| `test_cloud.py <moteur>` | *Le chemin cloud fonctionne-t-il de bout en bout, pour ce moteur ?* Rejoue presign → PUT R2 → `POST /process` → poll `/job-status`. |
| `banc_43min.py [moteurs…]` | *Que rend chaque moteur sur le même audio, et à quelle cadence la progression arrive-t-elle vraiment au client ?* |
| `calibrer_croise.py` | *Existe-t-il un seuil qui distingue « Gemini a décroché » de « Gemini est juste plus concis » ?* (**Réponse mesurée : non.**) |

## Mise en route

```bash
pip install requests
export SUBWHISPER_GATEWAY_KEY="…"        # ou laisser le coffre local par défaut
export SUBWHISPER_TEST_FILE="ma_video.mp4"
python test_cloud.py croise
```

⚠️ Le fichier de test doit être **non-WAV et > 24 Mo**, sinon le client ne prend pas le chemin
cloud (`index.html` : `if (!isWavFile && workerUrl)`) et le banc mesure autre chose.

Pour `calibrer_croise.py`, créer un `corpus.json` à côté du script (**gitignoré** : il désigne
des fichiers personnels) :

```json
[{"etiquette": "cjk-1", "regime": "dialogue CJK reel",
  "chemin": "D:/.../video.mp4", "offset_s": 600}]
```

Viser **au moins deux régimes opposés** — un où le moteur est censé exceller, un où il est censé
échouer. Sinon on ne mesure pas un discriminant, on mesure un point.

## Les trois pièges de mesure, tous payés en direct le 07/09

1. **Ne tracer qu'un seul champ** — la 1ʳᵉ version de `test_cloud.py` ne regardait que `log` et
   faisait conclure « aucun log » alors que la question portait sur l'état entier. **Tracer le
   tuple `(status, progress, log)`.**
2. **Un banc plus court que le phénomène observé.** Un job de 53 s face à un cache KV dont le
   plancher est de 60 s ne mesure pas le système, il mesure sa propre fenêtre — et rend un faux
   négatif crédible. C'est ce qui m'a fait déclarer cassé un outil qui marchait.
   ⇒ `banc_43min.py` existe pour ça : il dure plus longtemps que ce qu'il observe.
3. **`transcribe()` rend la main AVANT que le SRT soit posé** côté client (`showRes()` vit dans un
   `setTimeout(…, 400)`). Lire `getCurrentSRT()` juste après fait conclure à tort « le moteur n'a
   rien rendu ».

## Aucun secret ici

`secret.py` ne contient **aucune valeur** : il lit `SUBWHISPER_GATEWAY_KEY`, sinon un fichier
désigné par `SUBWHISPER_SECRET_FILE`, sinon le coffre local. Les scripts ne l'impriment jamais.
Ce dossier est dans un dépôt **public** — n'y écrire ni clé, ni chemin de bibliothèque personnelle.

Contexte complet et résultats : `../HANDOFF-moteur-cloud.md`.
