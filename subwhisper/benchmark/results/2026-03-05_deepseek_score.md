# SubWhisper Benchmark — DEEPSEEK — 2026-03-05

## Résumé

| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |
|---------|-----|-----------|---------|-----------|----------------|
| 20260304.ZH_BRUT.srt | FR | 🔴 **55** | 🔴 **0** | 53 | — |

**Score moyen BRUT (pipeline) : 55/100**
**Score moyen AI (cleanAI) : 0/100**

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
