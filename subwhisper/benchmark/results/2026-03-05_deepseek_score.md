# SubWhisper Benchmark — DEEPSEEK — 2026-03-05

## Résumé

| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |
|---------|-----|-----------|---------|-----------|----------------|
| 20260304.ZH_BRUT.srt | FR | 🔴 **55** | 🔴 **0** | 53 | — |
| aaa.EN_BRUT.srt | FR | 🔴 **64** | 🔴 **0** | 33 | — |
| DIALOGUES EN FRANÇAIS.FR_BRUT.srt | FR | 🟢 **97** | 🔴 **0** | 20 | — |
| S01E07-Assault [21D8A02E].JA_BRUT.s | FR | 🟢 **100** | 🟡 **76** | 3 | — |
| Sentenced.to.Be.a.Hero.JA_BRUT.srt | FR | 🟢 **100** | 🟢 **92** | 1 | — |
| videoplayback.KR_BRUT.srt | FR | 🟢 **100** | 🔴 **65** | 6 | — |

**Score moyen BRUT (pipeline) : 86/100**
**Score moyen AI (cleanAI) : 39/100**

## 20260304.ZH_BRUT.srt

### Pipeline BRUT — Score: 55/100
Stats: {"microCount":0,"totalRepeat":71,"foreignWords":5,"bigGaps":0,"overlaps":0,"longBlocks":5}
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 71 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[HIGH] FOREIGN_LANG_IN_FR** : 5 blocs avec caractères non-latins dans SRT français
    Ex: #22: оп, 發 微笑, 笑 | #230: Eh всего mom | #270: как
- ⚠ **[LOW] LONG_BLOCKS** : 5 blocs > 20s → under-segmentation

### AI CleanAI — Score: 0/100
Penalties: 401 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":45,"properNounChanged":1,"exclamationRemoved":7,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #22 [...] sur contenu valide
    BRUT: оп, 發 微笑, 笑
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #23 [...] sur contenu valide
    BRUT: 再 substances
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #25 [...] sur contenu valide
    BRUT: Hmm, Zhonggong
    AI  : [...]
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
- **[HIGH] INVALID_ELLIPSIS** : #70 [...] sur contenu valide
    BRUT: Ah ah ah ah ah ah ah ah ah ah ah ah ah ah ah Je vais jouir ah ah ah ah ah Je suis sur le point de énorme ah ch continue
    AI  : Ah ah ah ah ah ah ah ah ah ah ah ah ah ah ah Je vais jouir ah ah ah ah ah Je suis sur le point de [...] ah [...] continue
- **[HIGH] INVALID_ELLIPSIS** : #74 [...] sur contenu valide
    BRUT: Weiwei abuse
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #93 [...] sur contenu valide
    BRUT: Tropאני Yup
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #118 [...] sur contenu valide
    BRUT: etCEG
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #118 Interjection remplacée: "etCEG" → "[...]"
- **[MEDIUM] EXCLAMATION_REMOVED** : #119 Interjection remplacée: "de" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #129 [...] sur contenu valide
    BRUT: Doucementrament
    AI  : Doucement [...]
- **[HIGH] INVALID_ELLIPSIS** : #135 [...] sur contenu valide
    BRUT: Courench
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #148 Nom propre modifié: "Ahh" → "Ahh…"
- **[HIGH] INVALID_ELLIPSIS** : #150 [...] sur contenu valide
    BRUT: what mode which I'm going to be playing when I use theadia
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #151 [...] sur contenu valide
    BRUT: to push it these類 to come in with another pixel
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #152 [...] sur contenu valide
    BRUT: I think both people I mentioned, worth $4,000 in so much money...
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #153 [...] sur contenu valide
    BRUT: Oh, my God.
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #154 [...] sur contenu valide
    BRUT: Good boy.
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #155 [...] sur contenu valide
    BRUT: ha ha ha ha ha So long
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
- **[HIGH] INVALID_ELLIPSIS** : #164 [...] sur contenu valide
    BRUT: Honestly
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
- **[HIGH] INVALID_ELLIPSIS** : #168 [...] sur contenu valide
    BRUT: it'sajes and
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #222 [...] sur contenu valide
    BRUT: Chief L chowhat
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #230 [...] sur contenu valide
    BRUT: Eh всего mom
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #235 [...] sur contenu valide
    BRUT: comentarios
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #245 [...] sur contenu valide
    BRUT: talking ball Then if you're good in a ceramic Without the
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #246 [...] sur contenu valide
    BRUT: ones failing
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #247 [...] sur contenu valide
    BRUT: adalah
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #247 Interjection remplacée: "adalah" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #248 [...] sur contenu valide
    BRUT: ymfore
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #248 Interjection remplacée: "ymfore" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #249 [...] sur contenu valide
    BRUT: spend
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #249 Interjection remplacée: "spend" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #250 [...] sur contenu valide
    BRUT: high
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #250 Interjection remplacée: "high" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #302 [...] sur contenu valide
    BRUT: j uno
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #303 [...] sur contenu valide
    BRUT: mira
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #303 Interjection remplacée: "mira" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #305 [...] sur contenu valide
    BRUT: 妮子 said dutoto what is going to do in line there ?
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #309 [...] sur contenu valide
    BRUT: I need don't sign Tr miner
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #316 [...] sur contenu valide
    BRUT: Make the
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #317 [...] sur contenu valide
    BRUT: I'm done the first
    AI  : [...]

## aaa.EN_BRUT.srt

### Pipeline BRUT — Score: 64/100
Stats: {"microCount":6,"totalRepeat":77,"foreignWords":0,"bigGaps":1,"overlaps":0,"longBlocks":10}
- ⚠ **[HIGH] MICRO_BLOCKS** : 6 micro-blocs <500ms consécutifs → over-segmentation Groq
- ⚠ **[MEDIUM] PHONETIC_HALLUCINATION** : 77 blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence
- ⚠ **[LOW] LONG_BLOCKS** : 10 blocs > 20s → under-segmentation

### AI CleanAI — Score: 0/100
Penalties: 242 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":23,"properNounChanged":8,"exclamationRemoved":2,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #84 [...] sur contenu valide
    BRUT: à travers l'APS
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #89 [...] sur contenu valide
    BRUT: 1, 15h
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #90 [...] sur contenu valide
    BRUT: Ensuite rouler
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #91 [...] sur contenu valide
    BRUT: aulas
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #91 Interjection remplacée: "aulas" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #92 [...] sur contenu valide
    BRUT: 2, 16h
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #93 [...] sur contenu valide
    BRUT: Tête
    AI  : [...]
- **[MEDIUM] EXCLAMATION_REMOVED** : #93 Interjection remplacée: "Tête" → "[...]"
- **[HIGH] INVALID_ELLIPSIS** : #94 [...] sur contenu valide
    BRUT: C'est arrivé
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #95 [...] sur contenu valide
    BRUT: la chemise
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #158 Nom propre modifié: "Mmm" → "j'ai"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #158 Nom propre modifié: "Oui" → "de"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #158 Nom propre modifié: "Mmm" → "le"
- **[HIGH] INVALID_ELLIPSIS** : #283 [...] sur contenu valide
    BRUT: Maintenant, toutes les approches facilement
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #284 [...] sur contenu valide
    BRUT: Ce qui fait qu'il va s'atténuer
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #285 [...] sur contenu valide
    BRUT: D'une manière ou d'une autre
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #286 [...] sur contenu valide
    BRUT: Maintenant que vous êtes des réglementations
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #287 [...] sur contenu valide
    BRUT: Et maintenant, les Raptors généralement
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #288 [...] sur contenu valide
    BRUT: inscrivent les suivants
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #289 [...] sur contenu valide
    BRUT: Sauf si vous choisissez ou quelque chose
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #290 [...] sur contenu valide
    BRUT: Donc, je n'ai presque aucun problème
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #294 [...] sur contenu valide
    BRUT: ressemble à un mauvais隔
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #295 [...] sur contenu valide
    BRUT: The Budill oui Il y a Oh oh putain
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #360 [...] sur contenu valide
    BRUT: p decir
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #365 [...] sur contenu valide
    BRUT: Haha une différence
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #366 Nom propre modifié: "Dieu" → "Dieu."
- **[HIGH] INVALID_ELLIPSIS** : #368 [...] sur contenu valide
    BRUT: le pledging se noie
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #369 [...] sur contenu valide
    BRUT: Je suis une chatte
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #371 [...] sur contenu valide
    BRUT: get uit
    AI  : [...]
- **[MEDIUM] PROPER_NOUN_CHANGED** : #402 Nom propre modifié: "Dieu" → "Dieu."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #402 Nom propre modifié: "Dieu" → "Dieu."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #483 Nom propre modifié: "Waouh" → "waouh."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #693 Nom propre modifié: "Oui" → "Oui,"

## DIALOGUES EN FRANÇAIS.FR_BRUT.srt

### Pipeline BRUT — Score: 97/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":2,"overlaps":1,"longBlocks":1}
- ⚠ **[HIGH] OVERLAPS** : 1 chevauchements de timestamps

### AI CleanAI — Score: 0/100
Penalties: 120 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":20,"exclamationRemoved":0,"typoRegressed":0}

- **[MEDIUM] PROPER_NOUN_CHANGED** : #44 Nom propre modifié: "Son" → "passeport"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #54 Nom propre modifié: "Non" → "Non,"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #54 Nom propre modifié: "Sur" → "midi."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #54 Nom propre modifié: "Non" → "d'Azur"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #99 Nom propre modifié: "Paris" → "à"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #99 Nom propre modifié: "Alors" → "goûts."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #147 Nom propre modifié: "Mais" → "dis"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #147 Nom propre modifié: "Brest" → "absolument"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #147 Nom propre modifié: "Marseille" → "aller"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #231 Nom propre modifié: "Castocassa" → "Castocassa."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #231 Nom propre modifié: "Saint" → "Saint..."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #231 Nom propre modifié: "Ouais" → "Ouais,"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #231 Nom propre modifié: "Ouais" → "ça"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #296 Nom propre modifié: "Demande" → "vraiment."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #296 Nom propre modifié: "Laurent" → "Demande"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #296 Nom propre modifié: "Ben" → "que"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #409 Nom propre modifié: "Deux" → "finir."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #409 Nom propre modifié: "Dijon" → "moutarde"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #409 Nom propre modifié: "Non" → "mais"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #422 Nom propre modifié: "Dijonaises" → "dijonnaises"

## S01E07-Assault [21D8A02E].JA_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":3,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":2}
✓ Pipeline propre

### AI CleanAI — Score: 76/100
Penalties: 24 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":3,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #41 [...] sur contenu valide
    BRUT: Calexisthoux
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #83 [...] sur contenu valide
    BRUT: Kisema.
    AI  : [...]
- **[HIGH] INVALID_ELLIPSIS** : #160 [...] sur contenu valide
    BRUT: Cheum.
    AI  : [...]

## Sentenced.to.Be.a.Hero.JA_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":1}
✓ Pipeline propre

### AI CleanAI — Score: 92/100
Penalties: 8 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":1,"properNounChanged":0,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] INVALID_ELLIPSIS** : #1 [...] sur contenu valide
    BRUT: Isso ne, isso ne...
    AI  : [...]

## videoplayback.KR_BRUT.srt

### Pipeline BRUT — Score: 100/100
Stats: {"microCount":0,"totalRepeat":0,"foreignWords":0,"bigGaps":0,"overlaps":0,"longBlocks":0}
✓ Pipeline propre

### AI CleanAI — Score: 65/100
Penalties: 35 | Bonuses: 0
Stats: {"timestampInText":0,"ellipsisAdded":0,"properNounChanged":5,"exclamationRemoved":0,"typoRegressed":0}

- **[HIGH] BLOCK_COUNT** : Block count: BRUT=472 AI=473 (diff=1)
- **[MEDIUM] PROPER_NOUN_CHANGED** : #59 Nom propre modifié: "Que" → "désirez-vous"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #137 Nom propre modifié: "Tenez" → "mal."
- **[MEDIUM] PROPER_NOUN_CHANGED** : #275 Nom propre modifié: "Prends" → "peux"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #303 Nom propre modifié: "Fais" → "je"
- **[MEDIUM] PROPER_NOUN_CHANGED** : #364 Nom propre modifié: "Attends" → "s'est"
