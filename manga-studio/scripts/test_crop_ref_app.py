# -*- coding: utf-8 -*-
"""L'app recadre-t-elle la reference sur le visage, par ses DEUX chemins ?

Mesure du 28/07 (`test_crop_ref.py`) : avec les references brutes de Quang — des
planches de personnage — la case ne contient les deux personnages demandes que
**4 fois sur 6** ; recadrees sur le visage, **6/6**. Une fois, la case avait
littéralement herite d'une mise en page a cases. Ce banc verifie que l'app fait
ce recadrage la ou une image entre dans une fiche.

Deux chemins mènent a une reference, et ils sont faciles a oublier l'un ou
l'autre : le bouton « ＋ image de reference » (import) et « 🎨 Dessiner » →
garder une vue. Le banc couvre l'import (le second passe par le meme
`recadrerSurLeVisage`, verifie ici par lecture du graphe d'appel).

Ce qu'il verifie :
  1. une image importee ressort sous un nom `_crop` — donc recadree ;
  2. le VISAGE y occupe une part nettement plus grande qu'avant ;
  3. une image SANS visage n'est pas recadree, et l'app le DIT au lieu de
     couper au hasard (une reference peut etre un decor ou un objet) ;
  4. la reference reste en niveaux de gris apres recadrage (la mesure du 27/07
     ne doit pas tomber en passant par le nouveau chemin) ;
  5. aucune erreur JS.

Usage:
    python test_crop_ref_app.py [--headed]
    python test_crop_ref_app.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_crop_%d" % os.getpid()
ICI = os.path.dirname(os.path.abspath(__file__))
IN_COMFY = r"C:\Users\quang\Documents\ComfyUI\input"
# Une vraie planche de personnage de Quang : c'est exactement le cas qui pose
# probleme (visage a 1,9 % de l'image).
PLANCHE = os.path.join(IN_COMFY, "ref_mh19fa2e0f510038_1785163796125.png")

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


# Le banc tourne avec le Python qui a PLAYWRIGHT ; YOLO vit dans un autre
# environnement (kohya). Aucun interpreteur n'a les deux ici — plutot que d'en
# fabriquer un, la mesure du visage est deleguee au MEME sous-processus que celui
# qu'appelle le proxy. Le banc mesure donc avec l'outil de production, pas avec
# une copie qui pourrait deriver.
KOHYA_PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"


def part_du_visage(chemin):
    """Part de l'image occupee par le plus grand visage — la mesure qui compte."""
    import json
    import subprocess
    import tempfile
    jetable = os.path.join(tempfile.gettempdir(), "_mesure_crop.png")
    p = subprocess.run([KOHYA_PY, os.path.join(ICI, "crop_ref.py"), chemin,
                        "--out", jetable, "--json"],
                       capture_output=True, timeout=180)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    try:
        return float(json.loads(out.splitlines()[-1]).get("visage_avant") or 0.0)
    except Exception:
        return 0.0


def sans_visage():
    """Une image franchement dessinee, mais sans aucun visage : un damier."""
    from PIL import Image
    p = os.path.join(ICI, "refs_out", "_sans_visage.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im = Image.new("RGB", (600, 800))
    px = im.load()
    for y in range(800):
        for x in range(600):
            px[x, y] = (30, 30, 30) if (x // 50 + y // 50) % 2 else (225, 225, 225)
    im.save(p)
    return p


def ouvrir_fiche(pg, ident):
    """Deplier la fiche SI elle ne l'est pas deja.

    Le clic sur la ligne est une BASCULE : cliquer aveuglement referme une fiche
    deja ouverte, et le champ de fichier disparait. Un banc qui pilote une UI
    doit viser un ETAT, pas repeter un geste.
    """
    for _ in range(2):
        if pg.evaluate("(id) => !!document.querySelector('input[data-chref=\"'+id+'\"]')",
                       ident):
            return True
        pg.click('[data-chopen="%s"]' % ident)
        pg.wait_for_timeout(500)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true")
    args = ap.parse_args()
    from PIL import Image
    from playwright.sync_api import sync_playwright

    if not os.path.isfile(PLANCHE):
        print("ARRET : planche de reference introuvable : %s" % PLANCHE)
        return 2
    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    avant = part_du_visage(PLANCHE)
    print("planche source : le visage occupe %.1f %% de l'image" % (100 * avant))

    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : le recadrage est neutralise (comportement d'avant la
            # v1.53.0). Le banc doit rougir — sinon il ne mesure pas ce qu'il dit.
            pg.evaluate("""() => { recadrerSurLeVisage = async (nom) => nom; }""")

        ident = pg.evaluate("""async (nom) => {
            const c = await api('/manga/chars', {name: nom, tags: '1girl'});
            CHARS = (await api('/manga/chars')).items || [];
            renderChars();
            return c.id;
        }""", NOM)

        print("\n--- 1. importer une PLANCHE de personnage par le vrai champ ---")
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(500)
        ouvrir_fiche(pg, ident)                  # la fiche doit etre DEPLIEE (v1.38.0)
        pg.set_input_files('input[data-chref="%s"]' % ident, PLANCHE)
        pg.wait_for_timeout(12000)
        refs = pg.evaluate("(id) => (CHARS.find(c => c.id === id) || {}).refs || []", ident)
        verifie("la reference est enregistree", len(refs) == 1, str(refs))
        if refs:
            verifie("elle a ete RECADREE (nom en _crop)", refs[0].endswith("_crop.png"),
                    refs[0])
            chemin = os.path.join(IN_COMFY, refs[0])
            if os.path.isfile(chemin):
                apres = part_du_visage(chemin)
                verifie("le visage occupe une part nettement plus grande",
                        apres > avant * 2, "%.1f %% -> %.1f %%"
                        % (100 * avant, 100 * apres))
                im = Image.open(chemin).convert("RGB")
                px = list(im.getdata())[::503]
                sat = sum(max(p) - min(p) for p in px) / len(px)
                verifie("elle est toujours en niveaux de gris apres recadrage",
                        sat < 2.0, "saturation %.2f" % sat)
                verifie("elle reste carree et bornee en taille",
                        im.width == im.height and max(im.size) <= 768,
                        "%sx%s" % im.size)
            else:
                verifie("le fichier recadre existe dans ComfyUI/input", False, chemin)

        print("\n--- 2. une image SANS visage n'est pas coupee au hasard ---")
        p2 = sans_visage()
        pg.evaluate("""async (id) => {
            const c = CHARS.find(x => x.id === id); c.refs = [];
            await api('/manga/chars', c); await loadChars(); renderChars();
        }""", ident)
        pg.wait_for_timeout(600)
        ouvrir_fiche(pg, ident)
        pg.set_input_files('input[data-chref="%s"]' % ident, p2)
        pg.wait_for_timeout(12000)
        refs2 = pg.evaluate("(id) => (CHARS.find(c => c.id === id) || {}).refs || []", ident)
        verifie("l'image sans visage est quand meme enregistree", len(refs2) == 1,
                str(refs2))
        verifie("elle n'a PAS ete recadree",
                bool(refs2) and not refs2[0].endswith("_crop.png"), str(refs2))
        journal = pg.evaluate("window.MangaLog ? MangaLog.dump(60) : ''")
        verifie("l'app DIT qu'elle l'a gardee entiere",
                "entière" in str(journal) or "entiere" in str(journal), "")

        print("\n--- 3. les deux chemins passent par la meme fonction ---")
        # « 🎨 Dessiner → garder » coute 2 min de GPU : on ne le rejoue pas ici,
        # on verifie qu'il n'a pas ete oublie — c'est le defaut typique quand une
        # etape s'ajoute a un seul des deux chemins.
        src = pg.evaluate("""() => {
            const t = [...document.querySelectorAll('script')].map(s => s.textContent).join('');
            return (t.match(/recadrerSurLeVisage\\(/g) || []).length;
        }""")
        verifie("recadrerSurLeVisage est appelee sur les DEUX chemins (import + garder)",
                src >= 3, "%s occurrences (1 definition + 2 appels)" % src)

        pg.evaluate("async (id) => { await api('/manga/chars', {delete: id}); }", ident)
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT sans recadrage. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
