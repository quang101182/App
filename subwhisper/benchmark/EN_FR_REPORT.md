# SubWhisper Benchmark — EN→FR — 2026-03-06

**Pipeline** : RAW_GROQ → BRUT → IA → TRAD  
**Moteurs** : Gemini + DeepSeek  
**Source** : `EN` → `FR`

## RAW_GROQ
- Blocs : **271**
- CJK   : 0 (0%)

## Gemini

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 271 | 0 | 0% | 115 | 0 | 0 | 0 | — |
| IA    | 271 | 0 | 0% | 115 | 0 | 0 | 0 | 0/271 |
| TRAD  | 271 | 0 | 0% | 115 | 0 | 0 | 0 | 5/271 |

**Résiduel final** : ✅ Parfait — 0 résiduel

## DeepSeek

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 271 | 0 | 0% | 117 | 0 | 0 | 0 | — |
| IA    | 271 | 0 | 0% | 117 | 0 | 0 | 0 | 32/271 |
| TRAD  | 271 | 0 | 0% | 90 | 0 | 0 | 0 | 79/271 |

**Résiduel final** : ✅ Parfait — 0 résiduel

## Comparaison finale

|             | Gemini | DeepSeek |
|-------------|--------|----------|
| CJK résiduel | 0 (0%) | 0 (0%) |
| [N] bug     | 0 | 0 |
| [...] inv   | 0 | 0 |
| TS/texte    | 0 | 0 |

**Vainqueur** : Ex-aequo

## Recommandations prompt

✅ Aucune régression détectée — prompts OK pour `EN→FR`
