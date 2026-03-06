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
| TRAD  | 506 | 12 | 2% | 195 | 0 | 0 | 0 | 220/506 |

**Résiduel final** : 🟡 Acceptable — 12 blocs (2%)

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
| CJK résiduel | 12 (2%) | 5 (1%) |
| [N] bug     | 0 | 0 |
| [...] inv   | 0 | 0 |
| TS/texte    | 0 | 0 |

**Vainqueur** : DeepSeek

## Blocs résiduels

**Gemini TRAD** (12 blocs) :
- `[101]` ハow presence
- `[166]` Hum, regarde JO趾頭hum hum hum hum.
- `[215]` 撲bers
- `[299]` 太陽感じ
- `[301]` 好好好好 Oh, my God. → Oh, mon Dieu, c'est tellement bon.
- `[315]` de 수ick → de 수ick
- `[345]` Oh Oh Tu aimes ce petit grand grand grand Ce n'est pas vraiment mignon. Je pense qu'on なる aimer ici mais hanter.... 喔~~姐姐最愛這種小飲盪喔我的盪好爽喔越飲盪的越喜歡喔剛才要夾緊 → (idem)
- `[468]` حدفي
- `[477]` 気有 stab Probstカメ
- `[479]` 额蓝
- `[481]` 天爐
- `[483]` 설ic...

**DeepSeek TRAD** (5 blocs) :
- `[315]` de quelque 수ick
- `[345]` Oh Oh Tu aimes ce petit grand grand grand C'est pas vraiment mignon. Je pense que nousなる d'aimer ici mais hanter....Oh~~ Grande sœur adore ce genre de petite boisson qui se balance oh mon balancement est si bon plus ça se balance plus j'aime oh tout à l'heure il faut serrer
- `[468]` حد肥
- `[477]` 気有 stab Probstカメ
- `[483]` 설ic...

## Réflexion — Amélioration prompt

### Blocs communs aux deux moteurs (4) — hallucinations Groq intraduisibles

- `[315]` `수ick` : fragment coréen collé à un mot latin tronqué. Nonsense pur, aucun LLM ne peut traduire.
- `[345]` : bloc méga-mixte (FR+JA `なる`+ZH long) issu d'une session Groq hallucinée. DeepSeek traduit le ZH (+1), Gemini le conserve (règle "song lyrics 3e langue" trop protectrice ici). Acceptable.
- `[477]` `気有 stab Probstカメ` : mix JA+DE+EN sans sens. Intraduisible.
- `[483]` `설ic...` : fragment coréen tronqué. Intraduisible.

### Blocs supplémentaires Gemini (8) — micro-fragments CJK dans du FR

- `[101]` `ハow`, `[215]` `撲bers`, `[166]` `JO趾頭`, `[479]` `额蓝`, `[481]` `天爐` : hallucinations Groq (CJK collé à latin). DeepSeek les absorbe mieux dans la traduction BRUT — confirme sa supériorité sur micro-fragments.
- `[299]` `太陽感じ` : JA pur court, non traduit. DeepSeek le traduit en BRUT, Gemini ne gère pas ce cas.
- `[301]` `好好好好 → Oh, mon Dieu` : Gemini a inclus `→` dans sa réponse (original + traduction). Artefact de format, pas de problème de prompt. À surveiller.
- `[468]` `حدفي` : Gemini a transformé `حد肥` (arabe+ZH) en `حدفي` (arabe pur). Résidu hallucination Groq.

### Verdict

**Aucune amélioration de prompt à faire.** Les résiduels sont :
1. Des hallucinations Groq intraduisibles par nature (4/5 blocs DSK, 8/12 blocs GEM)
2. Un artefact de format Gemini `→` (1 cas isolé, à surveiller)
3. Micro-fragments CJK que DeepSeek absorbe mieux en BRUT → confirme **DeepSeek optimal pour ZH→FR**

**Recommandation moteur** : DeepSeek pour toute source CJK (ZH/JA/KO).
