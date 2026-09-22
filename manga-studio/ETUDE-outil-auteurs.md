# ÉTUDE À MENER — un outil « webtoon → vidéo narrée » pour les AUTEURS (leurs propres œuvres)

> Cadrage écrit le 22/09/2026 à 19h20, à la demande de Quang (19h17). **Rien n'est décidé, rien n'est codé.**
> Autosuffisant : tout ce qu'il faut pour mener l'étude est ici. À faire dans une session NEUVE.

## La question posée par Quang

> « Il faut faire une étude concrète. […] Je ne te dis pas que ça doit rapporter beaucoup, mais en tout cas pas zéro.
> Il faut être sûr qu'il y ait de quoi marcher, et faire attention à la concurrence existante. »
> Puis, précision du 22/09 19h18 : **« Le temps, je suis prêt à le perdre si le jeu en vaut la chandelle. »**

⇒ La contrainte n'est PAS le temps passé : c'est que ça VAILLE LA CHANDELLE. Ne pas rogner l'étude « pour aller vite »,
ne pas rogner le produit non plus. Ce qui disqualifie le projet : un marché qui ne paie pas, ou un concurrent gratuit
qui fait déjà la même chose — pas l'effort demandé.
⇒ **Livrable attendu : un GO / NO-GO argumenté, chiffré et sourcé**, pas un plan produit.

## D'où vient l'idée

Les outils « AI manga recap » vendus aujourd'hui (RecapManga, RecapDrop, MangaRecap AI Studio ~25 $/mois, scripts
Fiverr dès 10 $) servent surtout à faire des recaps d'œuvres SOUS DROITS : les vendre, c'est fournir un outil de
contrefaçon (risque de complicité, coupure des prestataires de paiement). Recherche sourcée du 22/09 : voir la synthèse
dans l'historique de session + `ROADMAP.md` § 28 (webtoons). La seule version défendable identifiée :
**servir les AUTEURS sur LEURS propres œuvres** (WEBTOON Canvas, Tapas, indépendants), pour qui la promotion en vidéo
courte est un vrai besoin et où la question des droits ne se pose pas.

## Ce qu'on a déjà (atouts réels, mesurés)

- Narration fidèle : noms repérés par vote et figés, ~1 erreur grave / 15 pages, bancs de fidélité (ROADMAP § 4-ter).
- Chaîne complète en un geste : profil de série → narration → karaoké → traduction → « Précédemment » → vidéo 9:16.
- Découpage des bandes webtoon en pages, sans couper une réplique (manga-fetch v0.5.0, 26 bandes → 129 pages en 13 s).
- Sous-titres karaoké, musique de fond avec ducking, file de fabrication vidéo, traitement de nuit.
- Coûts MESURÉS par chapitre (~50 pages) : Gemini ~1 $ / ~15 min · Kimi K3 ~2,50 $ / ~1 h · traduction ~0,009 $/page
  · karaoké ~0,003 $ · voix Chirp 3 HD comprise dans les chiffres ci-dessus.

## Ce qui manque (coût du passage en produit)

Tout tourne sur le PC de Quang : proxy local 8190, fenêtre Edge de capture, Windows, venv kohya. Un produit = service
en ligne (comptes, stockage, file de rendu, paiement), donc une reconstruction, pas un portage.

## Les 7 questions à trancher (dans cet ordre, on s'arrête à la première rédhibitoire)

1. **Le concurrent structurel : WEBTOON « Cuts »** (lancé 10/2025, 70 000 $/mois de récompenses) fait-il DÉJÀ, gratuitement
   et nativement, ce qu'on vendrait ? Lire la fonctionnalité, ses limites (formats, narration, voix, export).
   👉 Si Cuts couvre le besoin sans payer : **NO-GO**, écrire pourquoi et fermer.
2. **Le marché** : combien d'auteurs actifs (Canvas FR/EN, Tapas, indépendants) publient régulièrement ? Combien
   gagnent de l'argent ? Sources : chiffres publics WEBTOON/Naver/Tapas, rapports annuels, articles de presse.
3. **Leur volonté de payer** : que paient-ils déjà (Clip Studio ~5 €/mois, Canva, CapCut, ElevenLabs) ? Un auteur qui
   gagne 0 € ne paiera pas 20 €/mois. Chercher des témoignages datés (Reddit r/webtoons, r/Tapas, Discord) —
   ⚠ Reddit : passer par `python llm-cli/forums.py search "..."` (WebSearch/WebFetch bloqués sur reddit.com).
4. **La concurrence directe** : outils de recap existants (positionnement, prix, ce qu'ils savent faire), mais aussi
   le « fait maison » CapCut + ElevenLabs, et les monteurs Fiverr (10-50 $ la vidéo). Qu'apporte-t-on de plus,
   concrètement ? (fidélité mesurée, karaoké, chaîne complète, multi-chapitres).
5. **Le prix possible et la marge** : coût réel par chapitre (ci-dessus) + rendu vidéo ; quel prix tient face à Fiverr ?
   Modèle à l'usage (par chapitre) plutôt qu'abonnement ?
6. **L'acquisition** : où sont ces auteurs (Discord Canvas, r/webtoons, X, Instagram) ? Peut-on les toucher sans budget ?
7. **Le seuil de Quang** : « pas zéro », et le temps n'est pas un frein. À CHIFFRER AVEC LUI avant de conclure
   (ex. : 200 €/mois récurrents au bout de 6 mois ? ou simplement : 10 auteurs qui paient ?). Sans ce seuil, le
   GO/NO-GO n'a pas de critère.

## Méthode imposée

- Recherche web **sourcée et datée** (agent `web-researcher`), en distinguant fait vérifié / estimation / rumeur.
- Passe critique obligatoire sur le rapport de l'agent : vérifier les claims importants soi-même (cf. l'erreur de date
  « juillet 2026 » vue le 22/09 sur la politique YouTube, en fait juillet 2025).
- **Aucune ligne de code** tant que le GO n'est pas donné par Quang.
- Preuve de demande AVANT de construire : idéalement 5-10 échanges réels avec des auteurs (message direct, Discord),
  ou une page d'offre et des inscriptions. Un « marché » sans une seule personne qui dit « je paierais » = NO-GO.

## Pièges à éviter (déjà payés ailleurs)

- Se fier à un chiffre de blog vendant l'outil : ce sont des arguments commerciaux (cf. « 47 K abonnés en 4 mois »).
- Confondre « beaucoup d'auteurs » et « beaucoup d'auteurs qui paient ».
- Oublier que YouTube démonétise le contenu produit en masse : nos clients doivent publier de l'ORIGINAL (le leur).
- Sous-estimer le travail de service en ligne (comptes, paiement, support) par rapport au moteur, déjà fait.

---

# RÉSULTATS (session du 22/09/2026, 19h25 →)

## Q1 — WEBTOON Cuts : ❌ ne couvre PAS le besoin → on continue (vérifié 22/09 19h35)

Sources : sous-agent web-researcher + vérification directe des pages clés.
- **Corée uniquement** : lancé le 01/09/2025 « in Korea » (communiqué officiel https://about.webtoon.com/press-release/198,
  04/09/2025). L'annonce « Unified International CANVAS » (26/03/2026) ne le mentionne pas → pas accessible à un auteur
  Canvas EN/FR à ce jour (ESTIMATION par absence, à re-vérifier si Cuts s'internationalise).
- **Diffusion fermée** : vidéos < 2 min visibles DANS l'app WEBTOON ; aucun export TikTok/Shorts documenté.
- **Autre produit** : UGC/fans (mèmes, « Webtoon MV » = planches en clip musical, app Cuts Make 25/06/2026, Corée,
  Android). Aucune voix off narrée, aucun sous-titre karaoké, aucune traduction documentés.
- Récompenses 70 000 $/mois : pilote de 3 mois (11/2025 → 01/2026), reconduction non trouvée.

⚠ **Le vrai concurrent n'est pas Cuts** :
- **ComicInk** (https://www.comicink.ai/video, lu le 22/09) : narration IA scène par scène, sous-titres incrustés,
  musique, 720p. MAIS ~150 crédits/seconde → **Basic 9,99 $ = ~10 s de vidéo/mois, Plus 19,99 $ = ~30 s/mois**
  (≈ 0,67 $/s). Vise les BD créées DANS ComicInk (générateur de BD IA), pas un auteur qui arrive avec ses planches.
- **WTN Suite** (https://www.wtn-suite.com/, lu le 22/09) : logiciel de bureau, 14,99-129,99 $/mois, détection de cases
  YOLO, narration Gemini/OpenAI, TTS Edge/Kokoro, 4K. Livré avec « WT-Downloader » + « Script Rewriter » → vise les
  **chaînes de recap d'œuvres des autres** (le segment écarté pour raison de droits), pas les auteurs.
- FlexClip, LlamaGen, Elser AI, Frameo, Anijam : cités, NON VÉRIFIÉS.

## Signaux de terrain r/WebtoonCanvas (forums.py, lus le 22/09)

- **Demande payée réelle** : 13/11/2025, un auteur Canvas (« relatively big readership », 40 épisodes déjà doublés par
  un comédien) cherche un monteur pour TikTok/Insta/Shorts à **50 $ la vidéo**, collaboration longue.
  https://www.reddit.com/r/WebtoonCanvas/comments/1ovwjue/
- **Le besoin de promo est criant** : 17/09/2026, 43 pts / 78 comm., « 1 an de promo, < 100 abonnés » ; « promouvoir
  m'épuise plus que faire la BD » ; la vidéo courte citée comme la piste à essayer (« je n'ai pas encore compris comment »).
  https://www.reddit.com/r/WebtoonCanvas/comments/1wifqxo/
- **Bandes-annonces maison fréquentes** (≥ 8 entre le 23/08 et le 16/09/2026), presque toutes à 2-3 pts : les auteurs
  en font, elles ne percent pas.
- 🔴 **RISQUE NON PRÉVU PAR LE CADRAGE : l'hostilité à l'IA.** « Why is AI content allowed in this subreddit? » (13/09/2026),
  « Ai in WEBTOON is insulting » (19/08/2026), une excuse publique d'un auteur ayant publié un manga IA (08/08/2026),
  des auteurs qui s'excusent d'une simple musique Suno dans leur promo (07/2025), un projet voix+musique qui précise
  « Strictly NO Gen-AI » (20/06/2026), et une offre de trailers IA gratuits à 0 pt (29/07/2026).
  ⇒ Une **voix off IA** sur une œuvre dessinée à la main peut être rejetée par les auteurs ET leurs lecteurs. À
  instruire en Q3 : c'est peut-être le vrai frein, plus que la concurrence.
