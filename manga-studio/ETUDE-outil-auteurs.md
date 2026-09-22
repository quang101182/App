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
