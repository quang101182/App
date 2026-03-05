# SubWhisper Benchmark — GEMINI — 2026-03-05

## Résumé

| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |
|---------|-----|-----------|---------|-----------|----------------|
| DIALOGUES EN FRANÇAIS.FR_BRUT.srt | FR | 🟢 **97** | 🟢 **94** | 1 | — |
| English Routine.EN_BRUT.srt | FR | 🟢 **100** | 🟢 **100** | 0 | — |
| S01E07-Assault [21D8A02E].JP_BRUT.s | FR | 🟡 **89** | 🟢 **100** | 0 | — |
| Sentenced.to.Be.a.Hero.JP_BRUT.srt | FR | 🟢 **97** | 🟢 **100** | 0 | — |
| videoplayback.KR_BRUT.srt | FR | 🟢 **100** | 🟢 **100** | 0 | — |

**Score moyen BRUT (pipeline) : 97/100**
**Score moyen AI (cleanAI) : 99/100**

## DIALOGUES EN FRANÇAIS.FR_BRUT.srt

### Pipeline BRUT — Score: 97/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":2,"overlaps":1,"longBlocks":1}
- ⚠ **[HIGH] OVERLAPS** : 1 chevauchements de timestamps

### AI CleanAI — Score: 94/100
Penalties: 6 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":1,"exclamationRemoved":0,"typoRegressed":0}

- **[MEDIUM] PROPER_NOUN_CHANGED** : #422 Nom propre modifié: "Dijonaises" absent du texte AI

## English Routine.EN_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":1,"overlaps":0,"longBlocks":2}
✓ Pipeline propre

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté

## S01E07-Assault [21D8A02E].JP_BRUT.srt

### Pipeline BRUT — Score: 89/100
Stats: {"microCount":0,"totalRepeat":2,"foreignWords":2,"bigGaps":0,"overlaps":1,"longBlocks":1}
- ⚠ **[HIGH] FOREIGN_LANG_IN_FR** : 2 blocs avec caractères non-latins dans SRT français
    Ex: #37: me копnime場所に行けば エル ニクティング呪われた僕の未来を想像して | #40: 世界が待ってるこの一瞬を
- ⚠ **[HIGH] OVERLAPS** : 1 chevauchements de timestamps

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté

## Sentenced.to.Be.a.Hero.JP_BRUT.srt

### Pipeline BRUT — Score: 97/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":0,"overlaps":1,"longBlocks":2}
- ⚠ **[HIGH] OVERLAPS** : 1 chevauchements de timestamps

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté

## videoplayback.KR_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":0}
✓ Pipeline propre

### AI CleanAI — Score: 100/100
Penalties: 0 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

✓ Aucun problème détecté
