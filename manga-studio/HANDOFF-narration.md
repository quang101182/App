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
1. **Étape 2 — fiche personnages par SÉRIE** : il faut d'abord un **2ᵉ chapitre d'une même série**
   (Quang le capture via l'app : premier vrai test utilisateur de la capture). Puis référence manuelle
   des faits de ce chapitre → banc `scripts/juge_narration.py`.
2. Étape 4 — lecture case par case + bulles effacées ; 5 — vidéo MP4 (= mode hors-ligne) ;
   6 — modes Récit / **Lecture avancée** (voix par personnage, réutiliser le multi-voix de StoryVoice) ;
   7 — « Précédemment… » ; 8 — voix (changer sans relire, aperçu, voix par série) ; 9 — suivi de séries ;
   10 — hors-ligne sans PC ; 11 — **toutes langues → français** (narration + pages relettrées).
3. **Stockage (règle Quang : tout ce qui prend de la place sur C:)** : déplacer `sources/` et `output/`
   sur C: avec une **jonction** à l'ancien chemin (aucun code à changer) — au moment opportun.
   `scripts/*_out` (~650 Mo, bancs de juillet) : déplacer ou supprimer = **décision de Quang, en attente**.

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
