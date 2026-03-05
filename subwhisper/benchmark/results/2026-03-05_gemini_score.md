# SubWhisper Benchmark — GEMINI — 2026-03-05

## Résumé

| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |
|---------|-----|-----------|---------|-----------|----------------|
| 20260304.ZH_BRUT.srt | FR | 🔴 **55** | 🟢 **100** | 0 | — |
| aaa.EN_BRUT.srt | FR | 🔴 **64** | 🟢 **100** | 0 | — |
| DIALOGUES EN FRANÇAIS.FR_BRUT.srt | FR | 🟢 **97** | 🟢 **94** | 1 | — |
| S01E07-Assault [21D8A02E].JA_BRUT.s | FR | 🟢 **100** | 🟢 **100** | 0 | — |
| Sentenced.to.Be.a.Hero.JA_BRUT.srt | FR | 🟢 **100** | 🟡 **85** | 2 | — |
| videoplayback.KR_BRUT.srt | FR | 🟢 **100** | 🟢 **100** | 0 | — |

**Score moyen BRUT (pipeline) : 86/100**
**Score moyen AI (cleanAI) : 97/100**

## 20260304.ZH_BRUT.srt

### Pipeline BRUT — Score: 55/100
Stats: {"microCount":0,"totalRepeat":71,"foreignWords":5,"bigGaps":0,"overlaps":0,"longBlocks":5}
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 71 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[HIGH] FOREIGN_LANG_IN_FR** : 5 blocs avec caractères non-latins dans SRT français
    Ex: #22: оп, 發 微笑, 笑 | #230: Eh всего mom | #270: как
- ⚠ **[LOW] LONG_BLOCKS** : 5 blocs > 20s → under-segmentation

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté

## aaa.EN_BRUT.srt

### Pipeline BRUT — Score: 64/100
Stats: {"microCount":6,"totalRepeat":77,"foreignWords":0,"bigGaps":1,"overlaps":0,"longBlocks":10}
- ⚠ **[HIGH] MICRO_BLOCKS** : 6 micro-blocs <500ms consécutifs → over-segmentation Groq
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 77 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[LOW] LONG_BLOCKS** : 10 blocs > 20s → under-segmentation

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté

## DIALOGUES EN FRANÇAIS.FR_BRUT.srt

### Pipeline BRUT — Score: 97/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":2,"overlaps":1,"longBlocks":1}
- ⚠ **[HIGH] OVERLAPS** : 1 chevauchements de timestamps

### AI CleanAI — Score: 94/100
Penalties: 6 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":1,"exclamationRemoved":0,"typoRegressed":0}

- **[MEDIUM] PROPER_NOUN_CHANGED** : #422 Nom propre modifié: "Dijonaises" absent du texte AI

## S01E07-Assault [21D8A02E].JA_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":3,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":2}
✓ Pipeline propre

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté

## Sentenced.to.Be.a.Hero.JA_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":1}
✓ Pipeline propre

### AI CleanAI — Score: 85/100
Penalties: 15 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] BLOCK_COUNT** : Block count: BRUT=319 AI=318 (diff=1)
- **[HIGH] SENTENCE_COMPLETED** : #318 Phrase tronquée complétée
    BRUT: Spriggan. Veuillez m'appeler
    AI  : Spriggan. Veuillez m'appeler Spriggan.

## videoplayback.KR_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":0}
✓ Pipeline propre

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté
