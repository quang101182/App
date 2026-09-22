# HANDOFF — Manga Studio, volet LECTURE NARRÉE (maj 22/09/2026, 13h30)

> Autosuffisant. « Fait » = `git log` (version courante : v1.85.0). Ce fichier ne porte
> que le RESTANT, les pièges et le pourquoi. Le détail des mesures est dans `ROADMAP.md` § 4-ter et 4-ter-bis.

## ⭐ ÉTAT AU 22/09 16h55 — v2.4.3 + manga-fetch v0.5.1 (lire d'abord)
- Depuis 15h40 : v2.4.1 musique dans le profil · v2.4.2 ⏮/⏭ dans le lecteur VIDÉO · v2.4.3 boutons ⏮/⏭ = VRAIS numéros voisins,
  sauts signalés partout (orange + « ⚠ saut : ch. 297 sans narration / pas dans la bibliothèque ») · proxy : renommer = dossier
  D'ABORD + réessais (WinError 5 vu par Quang ; état incohérent « a » réparé à la main → corbeille).
- manga-fetch v0.5.0/0.5.1 : WEBTOONS découpés en pages (ROADMAP § 28), Raijin Scans (VF) validé (sites.json), enchaînement
  générique « chapter-N », avatars des commentaires exclus. Reste § 28 : traduction encadrés texte clair sur fond sombre,
  deux onglets sur la même adresse.
- Lot OPM de Quang (Gemini, trad fr) : 295→301 FAITS, 0 erreur (16h49). Bibliothèque : « banc raijin » = Solo Leveling VF ch.1-2
  (à renommer par Quang). Bancs du jour : test_chaine, test_profil(_ui), test_profil_musique_ui, test_video_nav_ui,
  test_nav_sauts_ui, test_renommer, test_capture_serie(_ui), test_sites_ui.
## (ancien) ÉTAT AU 22/09 15h40 — v2.4.0 : ÉTAPE 27 FAITE (profil de série + « Tout traiter », ROADMAP § 27). Chaîne = `scripts/suivi_nuit.py`
##    (nuit ET bouton), défaut général `sources/_profil_defaut.json`, profil `sources/<serie>/suivi.json`. Bancs : test_chaine / test_profil / test_profil_ui.
## (ancien) ÉTAT AU 22/09 14h20 — v2.3.0 (lire d'abord ; le reste du fichier = historique)
- Livré ce jour (détail + mesures : ROADMAP étapes 5-bis, 7, 9, 10, 14 à 24) : Précédemment/rattrapage, app installable (PWA, WebAPK),
  vidéo (📜, voix, nom de fichier, groupe .zip), chapitre préc./suiv., suivi de nuit (tâche `MangaStudioSuiviNuit` 01:30, moteur au choix),
  hors-ligne dans le téléphone, capture depuis le téléphone (Partager → Manga Studio, lien, 🕹 télécommande CDP) en 4 étapes, résumé
  de la bibliothèque, langue d'origine (MangaDex/pages) + refus fr→fr, frein commun + gateway v1.60 (compteur Manga Studio 60/min),
  repérage des noms parallèle (3,8×), coûts en direct, volume général, moteur mémorisé.
- ✅ **18 FAIT (v2.3.0, manga-fetch v0.4.0)** : « puis N suivants / jusqu'au ch. Y » ; MangaDex (API, même langue) et MANGA Plus
  (page de la série) vérifiés en réel. Règle 5 de manga-fetch (« pas de crawl ») LEVÉE par Quang (usage privé) : ne pas la rouvrir.
  Instance de test : `python scripts/proxy_8191.py <copie patchée>` (ComfyUI venv) ; tuée → supprimer `_studio_llm_proxy_8191.py`.
- RESTE (ROADMAP) : **19** liste des sites validés — les mesures du 22/09 sont prêtes dans le README manga-fetch § « plusieurs chapitres » ;
  plus tard : 4 (case par case), 6 (Lecture avancée), « qui est qui ». K3 anormalement lent le 22/09 (journal `reseau` désormais).
- Tests : Gemini pour déboguer, K3 quand c'est sûr (Quang 10h36). Bancs : `scripts/test_*_ui.py <port>` (8190 réel / 8191 copie).
- ⚠ Autre session (Generate Studio) modifie ET relance le proxy : relire avant d'écrire, diff = mes patchs seuls.

## Où on en est (v1.72.0 — voir « RESTANT » pour la suite, jusqu'à v1.93.0)
- Onglet 📚 **Chapitres** : liste des chapitres de `sources/`, **capture DANS l'app** (manga-fetch enveloppé),
  avertissements du manifeste + bouton Vérifier, **Narrer** (moteur/voix/pages), lecteur plein écran,
  écoute à l'aveugle, **pastille des coûts** en en-tête (détail au clic).
- **Solution de traitement retenue (décision Quang)** : **Kimi K3, méthode v2.2** = noms repérés par vote
  (Gemini) et figés → faits relevés par K3 (2 pages/appel, étiquette avant chaque image) → récit DeepSeek
  sans ajout → voix Chirp 3 HD. ≈ 1 erreur grave / 15 pages, ~2,50 $ et ~1 h par chapitre de 62 p.
  Gemini = option rapide (~1 $, ~15 min, plus d'erreurs). Pixtral éliminé. Portraits, vérification,
  consensus : **mesurés, non retenus** (options de script).
- Principe Quang : « on peut laisser passer quelques erreurs ; juger le rapport qualité-prix, et la vitesse
  quand c'est nécessaire ». Tests : pas de limite de coût ; solution finale : sobre.

## RESTANT, dans l'ordre (feuille de route § 4-ter-bis)
1. **Étape 2 — MESURÉE le 21/09 soir, aucun gain** (ROADMAP § étape 2) : OPM ch.301 (référence écrite à la main,
   `sources/one-punch-man/ch_301/reference_faits.json`) → v2 7 graves/19 · `--serie` 7 · `--noms v3` 8. Le verrou
   réel = « qui est qui » (un anonyme pris pour un nommé ; un nom CITÉ collé à un présent). Piste suivante non
   mesurée : décision par page « est-ce CELUI de la fiche : oui/non/incertain », incertain = anonyme.
   **Quang n'a pas encore choisi** entre cette piste et l'étape 4.
   manga-fetch **v0.3.0** (21/09, Quang a autorisé cette session à le modifier) : MANGA Plus vertical, canvas
   pleine résolution, capture < 3 pages = échec. Claymore ch.1 **vérifié propre** (Quang + contrôle
   visuel 21/09 22h52 : 801×1200, AUCUNE barre — seul Boruto, en vertical, les avait) → gardé tel quel.
2. Étape 4 — lecture case par case + bulles effacées ; 5 — vidéo MP4 (= mode hors-ligne) ;
   6 — modes Récit / **Lecture avancée** (voix par personnage, réutiliser le multi-voix de StoryVoice) ;
   7 — « Précédemment… » ; 8 — voix (changer sans relire, aperçu, voix par série) ; 9 — suivi de séries ;
   10 — hors-ligne sans PC ; 11 — **toutes langues → français** (narration + pages relettrées).
3. ✅ **Stockage FAIT (21/09 19h30)** : `sources/`, `output/`, `scripts/*_out` → `C:\Users\quang\Documents\MangaStudio-donnees\`,
   jonctions à l'ancien chemin. Tout nouveau dossier lourd : créé sur C: puis joint.
4. ✅ **v1.76.0 (21/09 23h20, `32c80ad`)** : bibliothèque par série + pochettes (AniList / image / page), suppression
   série / chapitre / pages → `sources/_corbeille/`, aperçu ▶/■ des voix, essais sans voix repliés. Proxy patché
   (`proxy-patch/patch_bibliotheque.py`, relancé par `relance-proxy.ps1`). **ORDRE FIXÉ PAR QUANG (22h54)** — socle
   d'abord : 12-ter saisons/tomes + années → 12-quater renommer un titre → reste de l'étape 8 (voix mémorisée par
   série, changer de voix sans relire) → **vidéo MP4 page par page : À DISCUTER avant de coder** (questions posées :
   format 9:16/16:9, usage perso/publication, sous-titres et musique = choix à la génération) → 7, 9, 10.
   Plus tard : case par case (4), mode Lecture (6), codex de série (wiki/AniList) pour « qui est qui ».
   Quang : « ne te perds pas, suis ta trame » — ses idées en cours de route vont dans la ROADMAP, pas dans le code.
   ✅ **Livré ensuite (21/09, 23h20 → 23h45)** : v1.77 tomes + dates (`serie.json`), suppression de narration ;
   v1.78 visionneuse (zoom, balayage) ; v1.79 coûts visibles partout + narrations supprimées comptées + VRAM utilisée ;
   v1.80 onglet **Bibliothèque en premier**, renommer une série (titre + dossier + tout le lié), capture repliable.
   v1.81 recherche intelligente ; v1.82 « Autre voix » (texte repris) + voix par série ; v1.83 barre de temps
   cliquable du lecteur + recherche dans le texte des narrations (proxy : Range 206 — sans lui, pas de seek MP3).
   **ORDRE FIXÉ PAR QUANG (22/09 00h06)** : (1) **traduction des dialogues** ← EN COURS ; (2) musique de fond
   dans l'app (on/off, volume manuel + défaut) ; (2-bis) sous-titres **karaoké** (récupérer Lumen v2.3 /
   PromoClip `generateSubtitleASSFromWords`) ; (3) **vidéo : À DISCUTER avant de coder** ; puis 7, 9, 10.
   ✅ **22/09 00h55 — v1.84.0 traduction + v1.85.0 musique LIVRÉES** (Quang dormait, feu vert « tout ce que tu peux faire en autonome ») :
   traduction branchée (bouton + sélecteur VO/fr grille/visionneuse/lecteur), **Claymore ch.1 entier traduit** (294/305 bulles, 0,54 $) ;
   musique par série (import, choix, corbeille ; lecteur : 🎵 + volume, ducking, boucle en fondu), 4 échantillons importés.
   Détail + chiffres : ROADMAP lignes 11 b et 13. Limites : répliques non détectées par YOLO restées en VO (piste écrite).
   ✅ **v1.86.0 karaoké dans le lecteur** (22/09 01h10) : `scripts/karaoke_mots.py` + bouton « 🎤 Karaoké » + case dans le lecteur
   (détail et pièges Whisper : ROADMAP, paragraphe (2-bis)).
   ✅ **v1.87.0 « Prendre dans Generate Studio »** (05h10). ⚠ Route `/manga/musique_depuis_gs` écrite dans le proxy mais proxy PAS encore
   relancé (narration K3 `kimi-charon` de Claymore en cours, lancée 05h06, ~1 h) → relancer par relance-proxy.ps1 APRÈS, puis rejouer
   `test_musique_gs_ui.py` sur 8190 et caler le karaoké de `kimi-charon`. Les anciennes narrations audibles de Claymore (v1.66,
   avant la méthode v2.2) disaient « Zaki » pour Raki : c'est la raison de cette relance.
   ✅ **v1.88.0 cellule d'activité** (05h25) — route `/manga/activite` écrite, proxy à relancer avec le reste. ENSUITE (Quang 05h15) :
   ergonomie bibliothèque/chapitres (zones fixes, bloc Rafraîchir discret) + boutons de la visionneuse remontés sur téléphone.
   ✅ **v1.89 → v1.92** (06h20) : visionneuse remontée (téléphone), musique série/chapitre (5 morceaux, noms numérotés), coûts complets +
   temps restant + tâche vivante = PID, ergonomie bibliothèque/chapitre (zones fixes). Détail : ROADMAP, ligne « v1.90 → v1.92 ».
   Narration Claymore K3 `kimi-charon` FAITE (Raki correct). ⚠ Si une série est renommée, ses morceaux gardent l'ancien titre.
   ✅ **v1.93.0 VIDÉO** (06h50) : 9:16, le lecteur rejoué, mode série, tag « à refaire » par empreinte, file de fabrication, flux +
   téléchargement. Détail : ROADMAP ligne « 5 — VIDÉO FAITE ». Ensuite : 7 « Précédemment… », 9 suivi de séries, 10 hors-ligne ;
   plus tard 4 (caméra case par case). ⚠ Les vidéos (scans protégés) vivent sous sources/ : jamais dans le dépôt (public).
   ⚠ Une question de Quang (« il me semble que… ») n'est PAS un ordre : répondre, ne rien modifier.
   ✅ **v2.0.0** capture depuis le téléphone (🕹 télécommande, 🔗 lien, Partager → Manga Studio) + moteur du suivi (Gemini pour les tests).
   SUITE : 18 (capture de plusieurs chapitres, vérifier les sites d'abord). Frieren ch.143 : 1er passage du suivi RÉUSSI en Gemini (0,58 $, 10 min 19).
   ✅ **v1.95.1** vidéo : 📜 en tête, choix de la voix, nom de fichier lisible ; pastille des coûts à droite. SUITE : ✅ 16 fait (v1.96.0,
   chapitre précédent/suivant), ✅ 15 fait (v1.97.0, archive .zip), ✅ 9 suivi (v1.98.0, tâche MangaStudioSuiviNuit 01:30 ;
   1er passage réel Demo Frieren lancé 09:36 → `python scripts/test_suivi_ui.py verifier` à passer), ✅ 10 hors-ligne (v1.99.0).
   ✅ **v1.95.0 app INSTALLABLE** (09h00, WebAPK vérifié sur le Samsung ; détail ROADMAP « 14 »).
   ✅ **v1.94.0 « Précédemment… » + rattrapage** (08h55) — détail ROADMAP ligne « 7 — FAIT ». ENSUITE : **14 — app INSTALLABLE
   sur le téléphone** (demande Quang 08h36, PWA : manifeste + icônes LIBRES sans cookie), puis 9, 10. Question ouverte : 
   le « Précédemment… » dans la vidéo ? Claymore 1 et 2 (musique) mis à la corbeille à 08h41 (pas par moi) → vidéo Claymore 🟠, normal.
   ⚠ Quang : ses remarques en cours de route = je finis ce que je fais, et je les ajoute à la ROADMAP.
5. Lien mobile = l'URL du tunnel de Generate Studio (hostname dans `config-generate-agent.yml`, hors dépôt :
   ce dépôt est PUBLIC) suivie de `/manga` (le dossier github.io ne sert que le
   README, il n'a jamais servi l'app). v1.73.0 : l'app rouvre le dernier onglet utilisé.

## PIÈGES (payés le 21/09 — ne pas les repayer)
- ⛔ **Proxy 8190** (`C:\Users\quang\Documents\ComfyUI\_studio_llm_proxy.py`) : le relancer UNIQUEMENT par
  `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\quang\Documents\ComfyUI\relance-proxy.ps1 -Qui "manga-studio" -Pourquoi "<version>"`
  (attend la fin des générations de Quang). Jamais `Stop-Process` : 3 générations coupées le 21/09.
- ⛔ **Deux sessions modifient ce proxy** : relire juste avant d'écrire ; et pour VERSIONNER un diff
  (`proxy-patch/`), rejouer SES patchs sur le `.bak` — un diff « .bak vs vivant » embarque le code de l'autre.
- Tester une route sans redémarrer le 8190 : instance **8191** qui importe le module et ne lance QUE le
  gestionnaire HTTP (jamais une 2ᵉ instance complète : elle relancerait watchdog pods / notifs Telegram).
- **manga-fetch** (domaine d'une autre session, ne pas le modifier) : code de sortie **3 = réussite avec
  avertissements** ; `--force` laisse des **pages orphelines** (le proxy met l'ancien chapitre de côté puis
  le supprime ou le RESTAURE) ; la capture doit viser `--tab <url exacte>` choisie dans l'app.
- Gateway : **20 req/min par IP** → frein 18/min + `retry_after` dans `narrate_chapter.py` ; réessayer les 52x.
- Gemini passe par l'API NATIVE du gateway (l'interface compatible OpenAI est refusée).
- La consigne « reprends les noms déjà connus » VERROUILLE une erreur précoce (Raki/Zaki fusionnés).
- Le juge se trompe quand la référence est trop résumée : vérifier ses « graves » contre la page ; une
  attribution anonyme = mineur.
- Environnement Magi (non retenu) : `%LOCALAPPDATA%\magi\venv` (C:, 4,8 Go), transformers 4.45.2 obligatoire.
- Installations et données lourdes : **toujours sur C:**.
