# -*- coding: utf-8 -*-
"""Banc S0 (compartiment secret, 24/09/2026) : une seule racine de donnees, reglable par MANGA_SOURCES_DIR.

A. Les 20 lignes qui calculent la racine (18 scripts + manga-fetch + proxy) : sans la variable -> ../sources
   (exactement l'ancien chemin) ; avec -> le dossier donne.
B. Bout en bout : avec la variable pointee sur un dossier JETABLE, un vrai « manga_fetch import » y ecrit le
   chapitre, une vraie alerte (moderation.ajouter_alerte) et une vraie depense (depenses.noter) aussi -- et le vrai
   sources/ n'a pas bouge (liste + date de modification de chaque entree de 1er niveau, avant/apres).
Le dossier jetable est efface a la fin. Ne touche a aucun vrai chapitre.
"""
import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MS = os.path.dirname(HERE)
VRAI = os.path.normpath(os.path.join(MS, "sources"))
PROXY = os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy.py")
MF_PY = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-fetch", "venv", "Scripts", "python.exe")
FICHIERS = ["cases_video", "controle_traduction", "depenses", "estimation", "interruption", "langue_chapitre",
            "moderation", "narrate_chapter", "refaire_opm_latin", "refaire_traductions", "reglages", "suivi_nuit",
            "tts_local", "video_chapitre", "karaoke_mots", "declaration_gpu", "vram_parts", "video_lot"]
ok = ko = 0


def check(nom, cond, detail=""):
    global ok, ko
    ok += bool(cond); ko += not cond
    print("  [%s] %s%s" % ("OK" if cond else "KO", nom, (" -- " + str(detail)) if detail and not cond else ""))


def expression(chemin):
    """(nom, expression) de LA ligne qui lit MANGA_SOURCES_DIR ; une seule attendue par fichier."""
    lignes = [l for l in open(chemin, encoding="utf-8") if "MANGA_SOURCES_DIR" in l and not l.lstrip().startswith("#")]
    assert len(lignes) == 1, "%s : %d ligne(s)" % (chemin, len(lignes))
    m = re.match(r"\s*(\w+)\s*=\s*(.+?)(\s+#.*)?$", lignes[0].rstrip("\r\n"))
    return m.group(1), m.group(2)


def evalue(chemin, env):
    nom, ex = expression(chemin)
    sauve = os.environ.pop("MANGA_SOURCES_DIR", None)
    if env: os.environ["MANGA_SOURCES_DIR"] = env
    try:
        return nom, os.path.normpath(eval(ex, {"os": os, "HERE": os.path.dirname(chemin), "__file__": chemin,
                                               "MANGA_ROOT": MS}))
    finally:
        os.environ.pop("MANGA_SOURCES_DIR", None)
        if sauve is not None: os.environ["MANGA_SOURCES_DIR"] = sauve


def photo():
    return {e: os.path.getmtime(os.path.join(VRAI, e)) for e in os.listdir(VRAI)}


print("A. les 20 lignes")
jet = tempfile.mkdtemp(prefix="banc-racine-")
cibles = [os.path.join(HERE, f + ".py") for f in FICHIERS] + [os.path.join(MS, "manga-fetch", "manga_fetch.py"), PROXY]
for c in cibles:
    nom, sans = evalue(c, None)
    _n, avec = evalue(c, jet)
    suffixe = {"GPU_DIR": "_gpu", "DIR": "_gpu", "FILE": "_videos_file"}.get(nom, "")
    attendu_sans = os.path.join(VRAI, suffixe) if suffixe else VRAI
    attendu_avec = os.path.join(jet, suffixe) if suffixe else os.path.normpath(jet)
    check("%s (%s) sans variable = ancien chemin" % (os.path.basename(c), nom),
          os.path.normcase(sans) == os.path.normcase(attendu_sans), sans)
    check("%s (%s) avec variable = dossier donne" % (os.path.basename(c), nom),
          os.path.normcase(avec) == os.path.normcase(attendu_avec), avec)

if ko:   # securite : une racine fausse ferait ecrire la partie B dans les VRAIES donnees
    shutil.rmtree(jet, ignore_errors=True)
    print("\nB. SAUTEE (partie A en echec)\n%d/%d" % (ok, ok + ko)); sys.exit(1)
print("B. bout en bout dans un dossier jetable")
avant = photo()
env = dict(os.environ, MANGA_SOURCES_DIR=jet, PYTHONIOENCODING="utf-8")
pages = tempfile.mkdtemp(prefix="banc-racine-pages-")
try:
    src = next(os.path.join(r, d) for r, ds, _f in os.walk(VRAI) for d in ds
               if d.startswith("ch_") and not os.path.relpath(r, VRAI).startswith("_")
               and len([x for x in os.listdir(os.path.join(r, d)) if x.lower().endswith((".jpg", ".png", ".webp"))]) >= 3)
    for x in sorted(y for y in os.listdir(src) if y.lower().endswith((".jpg", ".png", ".webp")))[:3]:
        shutil.copyfile(os.path.join(src, x), os.path.join(pages, x))
    r = subprocess.run([MF_PY, os.path.join(MS, "manga-fetch", "manga_fetch.py"), "import", pages,
                        "--title", "banc racine", "--chapter", "1"], env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    chap = [os.path.join(rr, d) for rr, ds, _f in os.walk(jet) for d in ds if d.startswith("ch_")]
    check("import : code retour 0", r.returncode == 0, (r.stdout + r.stderr)[-300:])
    check("import : chapitre cree dans le dossier jetable",
          len(chap) == 1 and os.path.isfile(os.path.join(chap[0], "manifest.json")), chap)
    code = ("import moderation, depenses; moderation.ajouter_alerte('banc-racine/ch_1', 'narration', [1], 'banc', "
            "'banc'); depenses.noter('banc', 'banc-racine/ch_1', 'banc', 'banc', 0.001)")
    r2 = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=env, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=60)
    check("alerte + depense : code retour 0", r2.returncode == 0, r2.stderr[-300:])
    check("alerte ecrite dans le dossier jetable", os.path.isfile(os.path.join(jet, "_alertes.json")))
    check("depense ecrite dans le dossier jetable", os.path.isfile(os.path.join(jet, "_depenses.jsonl")))
    apres = photo()
    check("vrai sources/ : memes entrees", set(avant) == set(apres), set(apres) ^ set(avant))
    bouge = [e for e in avant if e in apres and apres[e] != avant[e]]
    check("vrai sources/ : aucune entree modifiee", not bouge, bouge)
finally:
    shutil.rmtree(jet, ignore_errors=True)
    shutil.rmtree(pages, ignore_errors=True)
print("\n%d/%d" % (ok, ok + ko))
sys.exit(1 if ko else 0)
