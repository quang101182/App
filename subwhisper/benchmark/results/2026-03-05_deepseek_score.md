# SubWhisper Benchmark — DEEPSEEK — 2026-03-05

## Résumé

| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |
|---------|-----|-----------|---------|-----------|----------------|
| aaa.EN_BRUT.srt | FR | 🔴 **64** | 🟡 **70** | 4 | — |

**Score moyen BRUT (pipeline) : 64/100**
**Score moyen AI (cleanAI) : 70/100**

## aaa.EN_BRUT.srt

### Pipeline BRUT — Score: 64/100
Stats: {"microCount":6,"totalRepeat":77,"foreignWords":0,"bigGaps":1,"overlaps":0,"longBlocks":10}
- ⚠ **[HIGH] MICRO_BLOCKS** : 6 micro-blocs <500ms consécutifs → over-segmentation Groq
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 77 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[LOW] LONG_BLOCKS** : 10 blocs > 20s → under-segmentation

### AI CleanAI — Score: 70/100
Penalties: 30 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":3,"properNounChanged":1,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #360 [...] sur contenu valide
    BRUT: p decir
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #368 [...] sur contenu valide
    BRUT: le pledging se noie
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #371 [...] sur contenu valide
    BRUT: get uit
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #483 Nom propre modifié: "Waouh" absent du texte AI
