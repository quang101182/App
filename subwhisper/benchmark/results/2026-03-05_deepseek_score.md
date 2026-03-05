# SubWhisper Benchmark — DEEPSEEK — 2026-03-05

## Résumé

| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |
|---------|-----|-----------|---------|-----------|----------------|
| 20260304.ZH_BRUT.srt | FR | 🔴 **55** | 🔴 **0** | 31 | — |
| aaa.EN_BRUT.srt | FR | 🔴 **64** | 🟡 **78** | 3 | — |
| DIALOGUES EN FRANÇAIS.FR_BRUT.srt | FR | 🟢 **97** | 🟡 **84** | 2 | — |
| S01E07-Assault [21D8A02E].JA_BRUT.s | FR | 🟢 **100** | 🟢 **100** | 0 | — |
| Sentenced.to.Be.a.Hero.JA_BRUT.srt | FR | 🟢 **100** | 🟢 **100** | 0 | — |
| videoplayback.KR_BRUT.srt | FR | 🟢 **100** | 🟢 **100** | 0 | — |

**Score moyen BRUT (pipeline) : 86/100**
**Score moyen AI (cleanAI) : 77/100**

## 20260304.ZH_BRUT.srt

### Pipeline BRUT — Score: 55/100
Stats: {"microCount":0,"totalRepeat":71,"foreignWords":5,"bigGaps":0,"overlaps":0,"longBlocks":5}
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 71 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[HIGH] FOREIGN_LANG_IN_FR** : 5 blocs avec caractères non-latins dans SRT français
    Ex: #22: оп, 發 微笑, 笑 | #230: Eh всего mom | #270: как
- ⚠ **[LOW] LONG_BLOCKS** : 5 blocs > 20s → under-segmentation

### AI CleanAI — Score: 0/100
Penalties: 236 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":24,"properNounChanged":4,"exclamationRemoved":2,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #22 [...] sur contenu valide
    BRUT: оп, 發 微笑, 笑
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #23 [...] sur contenu valide
    BRUT: 再 substances
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #25 [...] sur contenu valide
    BRUT: Hmm, Zhonggong
    AI  : Hmm, [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #25 Nom propre modifié: "Zhonggong" absent du texte AI
- **[HIGH] INVALID_ELLIPSIS** : #26 [...] sur contenu valide
    BRUT: 哈哈 esfuer
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #43 [...] sur contenu valide
    BRUT: Sup a
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #45 [...] sur contenu valide
    BRUT: Tuotherapy
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #46 [...] sur contenu valide
    BRUT: C soul
    AI  : [...]
- **[HIGH] SENTENCE_COMPLETED** : #70 Phrase tronquée complétée
    BRUT: Ah ah ah ah ah ah ah ah ah ah ah ah ah ah ah Je vais jouir ah ah ah ah ah Je suis sur le point de énorme ah ch continue
    AI  : Ah ah ah ah ah ah ah ah ah ah ah ah ah ah ah Je vais jouir ah ah ah ah ah Je suis sur le point de... énorme ah... ch... continue
- **[HIGH] INVALID_ELLIPSIS** : #85 [...] sur contenu valide
    BRUT: Ne regarde pas directement Google
    AI  : Ne regarde pas directement [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #85 Nom propre modifié: "Google" absent du texte AI
- **[HIGH] INVALID_ELLIPSIS** : #93 [...] sur contenu valide
    BRUT: Tropאני Yup
    AI  : Trop... [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #93 Nom propre modifié: "Yup" absent du texte AI
- **[HIGH] INVALID_ELLIPSIS** : #118 [...] sur contenu valide
    BRUT: etCEG
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #118 Interjection remplacée: "etCEG" → "[...]"
- **[MEDIUM] EXCLAMATION_REMOVED** : #119 Interjection remplacée: "de" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #135 [...] sur contenu valide
    BRUT: Courench
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #150 [...] sur contenu valide
    BRUT: what mode which I'm going to be playing when I use theadia
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #151 [...] sur contenu valide
    BRUT: to push it these類 to come in with another pixel
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #152 [...] sur contenu valide
    BRUT: I think both people I mentioned, worth $4,000 in so much money...
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #156 [...] sur contenu valide
    BRUT: doing hang long
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #159 [...] sur contenu valide
    BRUT: Does're you remember that
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #160 [...] sur contenu valide
    BRUT: I can't remember that
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #161 [...] sur contenu valide
    BRUT: My eye will go into a shortcut
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #162 [...] sur contenu valide
    BRUT: when I see, can I see a screen in text�ers
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #163 [...] sur contenu valide
    BRUT: I know you've been reading
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #165 [...] sur contenu valide
    BRUT: Those were all見ples
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #166 [...] sur contenu valide
    BRUT: Just like exact
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #167 [...] sur contenu valide
    BRUT: Regardless, if all of her�도 isarya bothering to Publiai root moralowiąz like
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #167 Nom propre modifié: "Publiai" absent du texte AI
- **[HIGH] INVALID_ELLIPSIS** : #168 [...] sur contenu valide
    BRUT: it'sajes and
    AI  : [...]

## aaa.EN_BRUT.srt

### Pipeline BRUT — Score: 64/100
Stats: {"microCount":6,"totalRepeat":77,"foreignWords":0,"bigGaps":1,"overlaps":0,"longBlocks":10}
- ⚠ **[HIGH] MICRO_BLOCKS** : 6 micro-blocs <500ms consécutifs → over-segmentation Groq
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 77 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[LOW] LONG_BLOCKS** : 10 blocs > 20s → under-segmentation

### AI CleanAI — Score: 78/100
Penalties: 22 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":2,"properNounChanged":1,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #360 [...] sur contenu valide
    BRUT: p decir
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #371 [...] sur contenu valide
    BRUT: get uit
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #483 Nom propre modifié: "Waouh" absent du texte AI

## DIALOGUES EN FRANÇAIS.FR_BRUT.srt

### Pipeline BRUT — Score: 97/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":2,"overlaps":1,"longBlocks":1}
- ⚠ **[HIGH] OVERLAPS** : 1 chevauchements de timestamps

### AI CleanAI — Score: 84/100
Penalties: 16 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":1,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] SENTENCE_COMPLETED** : #173 Phrase tronquée complétée
    BRUT: Ces derniers temps, les ventes ne vont pas
    AI  : Ces derniers temps, les ventes ne vont pas bien.
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
