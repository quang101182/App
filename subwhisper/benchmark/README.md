# SubWhisper — Benchmark de prompts

Framework de test automatisé pour valider et améliorer les prompts IA de SubWhisper.

## Structure

```
benchmark/
  run.js          ← Script principal
  prompts.js      ← Prompts (source unique — synchroniser avec index.html)
  score.js        ← Heuristiques de scoring
  test-files/     ← Fichiers *_BRUT.srt de référence
  results/        ← Rapports générés (YYYY-MM-DD_engine_score.md)
```

## Convention de nommage des fichiers test

```
nom_video_ZH_BRUT.srt    ← source chinoise → FR
nom_video_JA_BRUT.srt    ← source japonaise → FR
nom_video_KR_BRUT.srt    ← source coréenne → FR
nom_video_EN_BRUT.srt    ← source anglaise → FR
nom_video_FR_BRUT.srt    ← source française (transcription seule)
```

La langue indiquée = langue de la vidéo source. Le SRT est toujours en français.

## Utilisation

```bash
# Tester avec Gemini
node run.js --engine gemini --key YOUR_GEMINI_KEY --testdir "D:\Download\10-brut sub"

# Tester avec DeepSeek
node run.js --engine deepseek --key YOUR_DEEPSEEK_KEY --testdir "D:\Download\10-brut sub"

# Comparer les deux (lancer séquentiellement)
node run.js --engine gemini --key GEM_KEY --testdir "D:\path"
node run.js --engine deepseek --key DSK_KEY --testdir "D:\path"
```

## Workflow d'amélioration des prompts

1. Lancer le benchmark sur tous les fichiers
2. Lire le rapport dans `results/`
3. Identifier les types d'erreurs récurrents
4. Modifier `prompts.js`
5. Re-lancer → comparer les scores
6. Si meilleur → synchroniser `prompts.js` → `index.html` + commit

## Critères de scoring (100 points)

| Critère | Pénalité |
|---------|---------|
| Block count modifié | -5 par bloc manquant/ajouté |
| Timestamp injecté dans texte | -20 (CRITICAL) |
| [...] sur contenu valide | -8 par occurrence |
| Phrase tronquée complétée | -10 |
| Nom propre modifié | -6 |
| Régression typographie FR | -4 |
| Interjection supprimée | -5 |
| Bonus correction réelle | +2 à +3 |

## Ajouter un nouveau fichier test

Copier le SRT dans `test-files/` avec la convention de nommage.
Plus de diversité = prompts plus robustes.
