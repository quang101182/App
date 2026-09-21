# HANDOFF — Manga Studio, volet LECTURE NARRÉE (21/09/2026, 19h25)

> Autosuffisant. « Fait » = `git log` (dernier commit du volet : `fb5a1c1`, v1.72.0). Ce fichier ne porte
> que le RESTANT, les pièges et le pourquoi. Le détail des mesures est dans `ROADMAP.md` § 4-ter et 4-ter-bis.

## Où on en est (v1.72.0)
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
