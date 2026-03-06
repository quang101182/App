# SubWhisper Benchmark — IT→FR — 2026-03-06

**Pipeline** : RAW_GROQ → BRUT → IA → TRAD  
**Moteurs** : Gemini + DeepSeek  
**Source** : `IT` → `FR`

## RAW_GROQ
- Blocs : **414**
- CJK   : 0 (0%)

## Gemini

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 414 | 0 | 0% | 278 | 0 | 0 | 0 | — |
| IA    | 414 | 0 | 0% | 278 | 0 | 0 | 0 | 1/414 |
| TRAD  | 414 | 0 | 0% | 278 | 0 | 0 | 0 | 3/414 |

**Résiduel final** : ✅ Parfait — 0 résiduel

## DeepSeek

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 414 | 0 | 0% | 277 | 0 | 0 | 0 | — |
| IA    | 414 | 0 | 0% | 277 | 0 | 0 | 0 | 89/414 |
| TRAD  | 414 | 0 | 0% | 277 | 0 | 0 | 0 | 2/414 |

**Résiduel final** : ✅ Parfait — 0 résiduel

## Comparaison finale

|             | Gemini | DeepSeek |
|-------------|--------|----------|
| CJK résiduel | 0 (0%) | 0 (0%) |
| [N] bug     | 0 | 0 |
| [...] inv   | 0 | 0 |
| TS/texte    | 0 | 0 |

**Vainqueur** : Ex-aequo

## Blocs résiduels

✅ Aucun bloc résiduel — pipeline parfait.

## Réflexion — Évolution prompt IT→FR

> **Rappel méthodologique :**
> - Les prompts ne se **remplacent pas** — ils **évoluent** : chaque ajustement s'appuie sur les versions précédentes.
> - Chaque langue source (`IT`, ZH, JA, KO, EN…) a ses **prompts dédiés** dans `prompts.js` — toute évolution ne s'applique qu'à la langue concernée.

### Verdict

**Aucun résiduel, aucune action nécessaire.** L'italien est une langue latine proche du français — 0% de CJK par nature, et les prompts actuels (`getTranslateTextPrompt` sans règle `srcSpecificRule` pour `it`) suffisent parfaitement.

**Observation notable :** Gemini modifie très peu (BRUT→IA : 1 bloc, IA→TRAD : 3 blocs), DeepSeek retravaille davantage en phase IA (89/414). Les deux arrivent au même résultat final — ex-aequo confirmé pour les langues latines comme IT, EN.

**Pour une future évolution prompt IT** : surveiller les termes argotiques italiens (`cazzo`, `sborrare`, `cappella` au sens sexuel) — les LLMs les traduisent correctement ici mais pourraient les neutraliser sur du contenu moins explicite. Pas de règle à ajouter aujourd'hui.
