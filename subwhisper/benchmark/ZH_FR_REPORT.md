# SubWhisper Benchmark — ZH→FR — 2026-03-06

**Pipeline** : RAW_GROQ → BRUT → IA → TRAD  
**Moteurs** : Gemini + DeepSeek  
**Source** : `ZH` → `FR`

## RAW_GROQ
- Blocs : **506**
- CJK   : 453 (90%)

## Gemini

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 506 | 116 | 23% | 153 | 0 | 0 | 0 | — |
| IA    | 506 | 11 | 2% | 195 | 0 | 0 | 0 | 149/506 |
| TRAD  | 506 | 11 | 2% | 195 | 0 | 0 | 0 | 220/506 |

**Résiduel final** : 🟡 Acceptable — 11 blocs (2%)

## DeepSeek

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 506 | 5 | 1% | 193 | 0 | 0 | 0 | — |
| IA    | 506 | 5 | 1% | 193 | 0 | 0 | 0 | 84/506 |
| TRAD  | 506 | 5 | 1% | 193 | 0 | 0 | 0 | 8/506 |

**Résiduel final** : 🟡 Acceptable — 5 blocs (1%)

## Comparaison finale

|             | Gemini | DeepSeek |
|-------------|--------|----------|
| CJK résiduel | 11 (2%) | 5 (1%) |
| [N] bug     | 0 | 0 |
| [...] inv   | 0 | 0 |
| TS/texte    | 0 | 0 |

**Vainqueur** : DeepSeek

## Recommandations prompt

- **Gemini** : 11 blocs CJK résiduels → renforcer règle 7 source `ZH` dans `getTranslateTextPrompt`
- **DeepSeek** : 5 blocs CJK résiduels → idem
