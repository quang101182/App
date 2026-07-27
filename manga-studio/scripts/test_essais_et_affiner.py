# -*- coding: utf-8 -*-
"""Revenir en arriere sur une case, et ne plus rouvrir ⚙ a chaque fois.

Quang, 27/07 : « une proposition de corriger ou de regenerer l'image […] tout en
pouvant revenir en arriere ou choisir celle que l'on prefere » et « ce n'est pas
tres ergonomique de cliquer a chaque fois sur le bouton Affiner ».

Le blocage etait invisible : `harvest(p.id + ".png")` utilisait un nom de fichier
FIXE, donc chaque « Regenerer » ECRASAIT l'image precedente. Aucun retour en
arriere n'etait possible -- et la ROADMAP affirmait pourtant le contraire
(« chaque generation ecrit un fichier de plus »), ce qui n'etait vrai que pour la
zone. Constat faux, corrige.

Ce que le banc verifie :
  - deux generations produisent DEUX fichiers distincts (le coeur du sujet) ;
  - les deux essais sont proposes, celui qui est RETENU est marque ;
  - toucher un essai precedent le remet SANS rien supprimer -- « revenir en
    arriere » ne doit pas etre un aller simple ;
  - le choix survit au rechargement ;
  - ⚙ ouvert une fois reste ouvert sur TOUTES les cases, et apres rechargement.

Zero GPU : le moteur est intercepte, on fabrique deux « rendus » distincts.

Usage:
    python test_essais_et_affiner.py [--headed]
    python test_essais_et_affiner.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_essais_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


PREPARE = """async ([nom]) => {
    const rep = await api('/manga/projects', {name: nom, slug: nom, recipe: {}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                prompt: 'a girl walking', idx: 0});
    await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                prompt: 'a boy running', idx: 1});
    S.proj = proj; S.page = page;
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                 .sort((a, b) => a.idx - b.idx);
    renderPlate();
    return {proj: proj.id, p0: S.panels[0].id, p1: S.panels[1].id};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="le nom de fichier redevient FIXE : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    n_gen = [0]

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 390, "height": 900},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        pg.route("**/comfy/prompt", lambda r: r.fulfill(
            status=200, content_type="application/json", body='{"prompt_id": "_banc_"}'))

        def hist(route):
            n_gen[0] += 1
            route.fulfill(status=200, content_type="application/json", body=json.dumps({
                "_banc_": {"outputs": {"7": {"images": [
                    {"filename": "essai%d.png" % n_gen[0], "subfolder": "", "type": "output"}]}}}}))
        pg.route("**/comfy/history/**", hist)

        # `harvest` range le fichier : on renvoie un chemin DIFFERENT a chaque
        # appel, comme le vrai proxy le ferait avec un nom unique.
        def rangement(route):
            try:
                d = json.loads(route.request.post_data or "{}")
                dest = d.get("dest") or "x.png"
            except Exception:
                dest = "x.png"
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"ok": True, "path": NOM + "/" + dest}))
        pg.route("**/manga/harvest", rangement)
        pg.route("**/manga/file*", lambda r: r.fulfill(
            status=200, content_type="image/png", body=PNG))

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        pg.evaluate("localStorage.removeItem('manga_affiner')")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM])
        sel = '[data-pid="%s"]' % d["p0"]

        if args.muter:
            # MUTATION : retour au nom FIXE. Les deux generations ecrivent le
            # meme fichier ; l'app croit avoir deux essais, ils pointent au meme
            # endroit -- « revenir en arriere » ne ramene alors rien.
            pg.evaluate("""() => {
                const vrai = harvest;
                window.harvest = async (img, dest) =>
                    vrai(img, dest.replace(/_v[a-z0-9]+\\.png$/, ".png"));
            }""")

        # ---------- 1. ⚙ ouvert une fois = ouvert partout ----------
        verifie("le panneau est ferme au depart",
                pg.eval_on_selector_all(".panel .affiner", "els => els.length") == 0)
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(600)
        n = pg.eval_on_selector_all(".panel .affiner", "els => els.length")
        verifie("l'ouvrir une fois l'ouvre sur TOUTES les cases", n == 2,
                "%d panneau(x) pour 2 cases" % n)

        # ---------- 2. deux generations = deux fichiers ----------
        pg.click(sel + ' [data-act="gen"]')
        pg.wait_for_timeout(3000)
        f1 = pg.evaluate("(id) => (S.panels.find(x => x.id === id) || {}).file", d["p0"])
        pg.click(sel + ' [data-act="gen"]')
        pg.wait_for_timeout(3000)
        f2 = pg.evaluate("(id) => (S.panels.find(x => x.id === id) || {}).file", d["p0"])
        verifie("deux générations = deux FICHIERS distincts", bool(f1) and f1 != f2,
                "%s vs %s" % (f1, f2))
        vs = pg.evaluate("(id) => ((S.panels.find(x => x.id === id).recipe || {}).versions || []).length",
                         d["p0"])
        verifie("les deux essais sont gardes", vs == 2, "%d essai(s)" % vs)

        # ---------- 3. l'ecran les propose, et marque le retenu ----------
        vign = pg.eval_on_selector_all(sel + " [data-vers]", "els => els.length")
        verifie("les essais sont proposes a l'ecran", vign == 2, "%d vignette(s)" % vign)

        # ---------- 4. revenir en arriere, SANS rien perdre ----------
        pg.eval_on_selector(sel + ' [data-vers][data-file="%s"]' % f1, "el => el.click()")
        pg.wait_for_timeout(1500)
        actuel = pg.evaluate("(id) => (S.panels.find(x => x.id === id) || {}).file", d["p0"])
        verifie("toucher un essai precedent le remet", actuel == f1, "%s" % actuel)
        vs2 = pg.evaluate("(id) => ((S.panels.find(x => x.id === id).recipe || {}).versions || []).length",
                          d["p0"])
        verifie("revenir en arriere ne SUPPRIME rien", vs2 == 2, "%d essai(s)" % vs2)

        # ---------- 5. tout survit au rechargement ----------
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        pg.evaluate("(id) => ouvrirProjet(id)", d["proj"])
        pg.wait_for_timeout(2500)
        relu = pg.evaluate("(id) => (S.panels.find(x => x.id === id) || {}).file", d["p0"])
        verifie("l'essai retenu survit au rechargement", relu == f1, "%s" % relu)
        verifie("et ⚙ est toujours ouvert",
                pg.eval_on_selector_all(".panel .affiner", "els => els.length") >= 1)

        verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
        try:
            pg.evaluate("(id) => api('/manga/projects', {delete: id})", d["proj"])
        except Exception:
            pass
        pg.wait_for_timeout(400)
        br.close()

    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


def _png():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (120, 160), (40, 40, 40))
    ImageDraw.Draw(im).ellipse((20, 20, 100, 100), fill=(230, 230, 230))
    b = io.BytesIO(); im.save(b, "PNG")
    return b.getvalue()


PNG = _png()

if __name__ == "__main__":
    sys.exit(main())
