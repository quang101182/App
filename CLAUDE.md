# SubWhisper — Contexte pour Claude Code

## Vue d'ensemble

SubWhisper est une SPA single-file HTML pour la transcription et traduction audio/vidéo.

- Fichier principal : `subwhisper/index.html` (tout le CSS, JS et HTML dans un seul fichier)
- Prompts IA : `subwhisper/prompts.js` (exporté comme module ES)
- Service Worker : `subwhisper/sw.js` (cache offline)

## Architecture

**Gateway-only** : tous les appels API (Groq, Gemini, DeepSeek, Claude, Azure, AssemblyAI, DeepL) passent par le CF Worker gateway (`api-gateway.quang101182.workers.dev`). Aucune clé API n'est stockée côté client — le gateway gère les secrets via KV.

Les fonctions clés sont dans `index.html` :
- Transcription (Groq Whisper, AssemblyAI)
- Nettoyage IA (clean prompt)
- Traduction IA (multi-passes)
- Formatage SRT
- Export DIAG (diagnostic JSON)
- Gestion du cache et du service worker

## Règles de versioning

À chaque modification, **toujours** incrémenter la version dans ces 4 endroits :
1. `<title>` tag dans `index.html`
2. Le `<span>` du badge de version (visible dans l'UI)
3. La variable `CACHE` dans `sw.js` (ex: `subwhisper-v8.89`)
4. L'objet d'export DIAG (champ `version`)

## Prompts dans prompts.js

Les prompts sont organisés comme suit :

| Prompt | Usage |
|---|---|
| `PROMPTS.translate_full` | Traduction complète du SRT |
| `PROMPTS.clean` | Nettoyage IA du texte brut transcrit |
| `PROMPTS.detect_foreign` | Détection de passages en langue étrangère |
| `PROMPTS.translate_targeted` | Traduction ciblée (passages détectés uniquement) |
| `PROMPTS.translate_second_pass` | Deuxième passe de traduction (correction) |

### Règles dynamiques dans les prompts

- `_typoRule` : correction typographique contextuelle
- `_srcSpecific` : règles spécifiques à la langue source
- `_bracketsRule` : gestion des crochets `[...]` (musique, descriptions)
- `_langSpecific` : règles spécifiques à la langue cible

## Anomalies DIAG — Mapping des corrections

Le système DIAG exporte un JSON d'anomalies. Voici où intervenir selon le type :

| Anomalie | Où corriger |
|---|---|
| `DUPLICATE_BLOCKS` | Améliorer la logique de déduplication dans `cleanAI` ou le post-traitement après nettoyage |
| `LOST_BLOCKS` | Vérifier `parseSRT`, le chunking de traduction, ou l'étape de formatage |
| `BRACKET_BLOCKS` (`[...]`) | Améliorer les règles de crochets dans le prompt clean (`_bracketsRule`) |
| `LONG_LINES` | Vérifier l'étape de formatage et le découpage des lignes longues |
| `FOREIGN_CHARS` | Améliorer le prompt de traduction ou la logique de second pass |

## Règles obligatoires

1. **Backup systématique** : toujours créer un `.bak` avant de modifier un fichier existant
2. **Pas de getters de clés vides** : ne jamais utiliser `getGroqKey()`, `getGeminiKey()` etc. — ces fonctions n'existent plus. Toutes les clés sont gérées par le gateway
3. **Vérification API** : utiliser `API_DOTS` pour vérifier le statut des API (points verts/rouges dans l'UI)
4. **Single-file** : `index.html` doit rester autonome (CSS + JS inline), sauf `prompts.js` et `sw.js` qui sont des fichiers séparés
5. **Langue** : les commentaires de code et messages de commit doivent être descriptifs ; les réponses à l'utilisateur en français
