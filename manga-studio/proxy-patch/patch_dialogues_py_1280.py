"""dialogues.py 1.27.0 -> 1.28.0 (S2-bis) : reparation AUTOMATIQUE de ce que <= 1.25.0 a abime -- une bulle entouree qui recouvrait
une bulle deja traduite etait traduite une 2e fois, ajoutee a traduction.json et REECRITE sur l'image. A chaque preparation (pages
demandees) : ces doublons sortent de traduction.json ; si TOUS les ajouts d'une page etaient des doublons, l'image d'avant les ajouts
(.avant_ajouts) est remise. Sauvegardes .avant_reparation. Jamais de retouche a la main (regle de Quang, 27/09 20h30). Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/dialogues.py"
s = open(F, encoding="utf-8", newline="").read()
if "def reparer_ajouts_doubles(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-1270")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "1.27.0"  # 1.27.0 (27/09, S4)',
    'VERSION = "1.28.0"  # 1.28.0 (27/09, S2-bis) : doublons laisses par <= 1.25.0 (bulle entouree autour d\'une bulle traduite) repares a la preparation ;  # 1.27.0 (27/09, S4)')

rep('''def traduire_ajouts(chap_dir, dd, a, voulues):''', '''def reparer_ajouts_doubles(chap_dir, voulues):
    """1.28.0 (S2-bis) : <= 1.25.0 traduisait et REECRIVAIT sur l'image une bulle entouree qui recouvrait une bulle deja traduite.
    Pages voulues : ces doublons sortent de traduction.json ; si TOUS les ajouts d'une page en etaient, l'image d'avant les ajouts
    (.avant_ajouts) est remise (sinon on n'y touche pas : un vrai ajout y est dessine). -> nombre de doublons retires."""
    import shutil as _sh
    tf = os.path.join(chap_dir, "traduction", "fr", "traduction.json")
    tr = lire_json(tf)
    if not tr:
        return 0
    n = 0
    for p in tr.get("pages") or []:
        if p.get("page") not in voulues:
            continue
        bl = p.get("bulles") or []
        dbl = [b for b in bl if b.get("ajout") and b.get("box")
               and any(couvre(b["box"], c["box"]) >= 0.8 for c in bl if not c.get("ajout") and c.get("box"))]
        if not dbl:
            continue
        p["bulles"] = [b for b in bl if not any(b is d for d in dbl)]
        n += len(dbl)
        img = os.path.join(chap_dir, "traduction", "fr", p.get("file") or "page_%03d.png" % p["page"])
        remise = ""
        if not any(b.get("ajout") for b in p["bulles"]) and os.path.isfile(img + ".avant_ajouts") and os.path.isfile(img):
            if not os.path.isfile(img + ".avant_reparation"):
                _sh.copy2(img, img + ".avant_reparation")
            _sh.copy2(img + ".avant_ajouts", img)
            remise = ", image d'avant remise"
        log("  page %d : %d bulle(s) entouree(s) en DOUBLE retiree(s) de la traduction%s" % (p["page"], len(dbl), remise))
    if n:
        if not os.path.isfile(tf + ".avant_reparation"):
            _sh.copy2(tf, tf + ".avant_reparation")
        ecrire_json(tf, tr)
    return n


def traduire_ajouts(chap_dir, dd, a, voulues):''')

rep('''        _tr0 = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
        traduire_ajouts(chap_dir, dd, a, set(nc_plage(a.pages, [p["page"] for p in _tr0.get("pages") or []])))''',
    '''        _tr0 = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
        _v0 = set(nc_plage(a.pages, [p["page"] for p in _tr0.get("pages") or []]))
        reparer_ajouts_doubles(chap_dir, _v0)                           # 1.28.0 (S2-bis) : AVANT de traduire de nouveaux ajouts
        traduire_ajouts(chap_dir, dd, a, _v0)''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 1.28.0")
