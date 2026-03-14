# SubWhisper Benchmark — JA→FR — 2026-03-06

**Pipeline** : RAW_GROQ → BRUT → IA → TRAD  
**Moteurs** : Gemini + DeepSeek  
**Source** : `JA` → `FR`

## RAW_GROQ
- Blocs : **323**
- CJK   : 297 (92%)

## Gemini

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 323 | 0 | 0% | 214 | 0 | 0 | 0 | — |
| IA    | 323 | 0 | 0% | 214 | 0 | 0 | 0 | 0/323 |
| TRAD  | 323 | 0 | 0% | 214 | 0 | 0 | 0 | 1/323 |

**Résiduel final** : ✅ Parfait — 0 résiduel

## DeepSeek

| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |
|-------|-------|-----|------|----|--------|----------|----------|------------|
| BRUT  | 323 | 0 | 0% | 213 | 0 | 0 | 0 | — |
| IA    | 323 | 0 | 0% | 213 | 0 | 0 | 0 | 27/323 |
| TRAD  | 323 | 0 | 0% | 213 | 0 | 0 | 0 | 17/323 |

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

## Réflexion — Évolution prompt JA→FR

> ⏳ À compléter par Claude après analyse des blocs résiduels ci-dessus.
> 
> **Rappel méthodologique :**
> - Les prompts ne se **remplacent pas** — ils **évoluent** : chaque ajustement s'appuie sur les versions précédentes.
> - Chaque langue source (`JA`, ZH, JA, KO, EN…) a ses **prompts dédiés** dans `prompts.js` — toute évolution ne s'applique qu'à la langue concernée.
> - Questions à traiter : (1) Les résiduels sont-ils des hallucinations Groq intraduisibles ? (2) Y a-t-il un pattern répété qui justifie une règle supplémentaire ? (3) Quel moteur bénéficierait d'un ajustement spécifique ?
