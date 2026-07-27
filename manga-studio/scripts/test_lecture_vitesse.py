# -*- coding: utf-8 -*-
"""Vitesse de defile d'une sequence : GLOBALE, persistante, et reglable a chaud.

Demande de Quang (27/07) : « il faudrait pouvoir controler directement la
persistance memoire, quel que soit le projet, la vitesse de defilement des
images de facon globale ».

Trois mots, trois exigences distinctes -- et ce banc les separe :

  - « globale »      : le reglage ne vit pas dans le projet. Le banc regle la
                       vitesse sur un projet, en CREE un second, y rejoue une
                       sequence, et exige la meme cadence.
  - « persistance »  : elle survit a un rechargement complet de la page.
  - « directement »  : bouger le curseur PENDANT la lecture change la cadence
                       tout de suite, sans repartir de la premiere image.

Ce qui est mesure est la CADENCE REELLE (nombre de changements de `src` par
seconde, releves par un MutationObserver), jamais la valeur affichee : un
curseur peut afficher 60 ms et continuer a defiler a 180. C'est exactement le
genre d'ecart qu'un banc qui lit son propre reglage ne verrait jamais.

Zero GPU : les vignettes n'ont pas besoin d'exister sur le disque pour que le
minuteur tourne -- on compte des changements d'attribut, pas des pixels.

Usage:
    python test_lecture_vitesse.py [--headed]
    python test_lecture_vitesse.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_vitesse_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


# --- JS : cree un projet + une planche + N cases de sequence, puis joue -------
PREPARE = """async ([nom, n]) => {
    const proj = await api('/manga/projects', {name: nom, slug: nom});
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    for (let i = 0; i < n; i++){
        await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                    prompt: 'vignette ' + i, idx: i});
    }
    S.proj = proj; S.page = page;
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                 .sort((a, b) => a.idx - b.idx);
    // Une sequence deja generee : meme seed, index ordonnes, un fichier par case.
    // Le fichier n'a pas besoin d'exister -- on mesure un minuteur, pas une image.
    S.panels.forEach((p, i) => {
        p.file = nom + '/v' + i + '.png';
        p.recipe = {seed: 777777, sequence: {index: i, total: n, geste: 'marche'}};
    });
    renderPlate();
    return {proj: proj.id, pid: S.panels[0].id};
}"""

# Compte les changements de src de l'image du lecteur, sur une fenetre donnee.
COMPTE = """async (ms) => {
    const img = document.getElementById('lbImg');
    let n = 0;
    const obs = new MutationObserver(muts => {
        for (const m of muts) if (m.attributeName === 'src') n++;
    });
    obs.observe(img, {attributes: true, attributeFilter: ['src']});
    await new Promise(r => setTimeout(r, ms));
    obs.disconnect();
    return n;
}"""


def cadence(pg, fenetre_ms=1400):
    """Images par seconde reellement affichees par le lecteur."""
    n = pg.evaluate(COMPTE, fenetre_ms)
    return n * 1000.0 / fenetre_ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="la vitesse n'est plus ecrite dans le stockage : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    projets = []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        # On part d'un stockage vierge pour ce reglage : sinon le banc validerait
        # la valeur laissee par la session precedente, pas le defaut du code.
        pg.evaluate("localStorage.removeItem('manga_vitesse')")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : le reglage n'est plus ECRIT. Tout reste juste a l'ecran
            # -- le curseur bouge, la cadence change -- et seule la persistance
            # meurt. C'est precisement le defaut qu'un banc visuel laisse passer.
            pg.evaluate("""() => {
                const vrai = localStorage.setItem.bind(localStorage);
                localStorage.setItem = (k, v) => { if (k !== 'manga_vitesse') vrai(k, v); };
            }""")

        # ---------- 1. defaut ----------
        v0 = pg.evaluate("OPT.vitesse")
        verifie("valeur par defaut = 180 ms", v0 == 180, "lu %s" % v0)

        a = pg.evaluate(PREPARE, [NOM + "a", 4])
        projets.append(a["proj"])

        # ---------- 2. le curseur n'existe QUE pendant une lecture ----------
        cache_avant = pg.eval_on_selector("#lbVitWrap", "el => el.hidden")
        verifie("curseur de vitesse cache hors lecture", cache_avant is True)

        pg.click('[data-pid="%s"] [data-act="jouer"]' % a["pid"])
        pg.wait_for_timeout(400)
        visible = pg.eval_on_selector("#lbVitWrap", "el => !el.hidden")
        verifie("curseur visible pendant la lecture", visible is True)

        # ---------- 3. la cadence par defaut est bien celle annoncee ----------
        c180 = cadence(pg)
        verifie("cadence a 180 ms ≈ 5,6 img/s", 4.2 <= c180 <= 7.2,
                "mesure %.1f img/s" % c180)

        # ---------- 4. reglage A CHAUD, sans repartir du debut ----------
        avant = pg.evaluate("document.getElementById('lbImg').src")
        pg.evaluate("setVitesse(700)")
        apres = pg.evaluate("document.getElementById('lbImg').src")
        verifie("regler la vitesse ne fait pas sauter au debut", avant == apres,
                "image inchangee a l'instant du reglage")
        c700 = cadence(pg)
        verifie("cadence a 700 ms ≈ 1,4 img/s", 0.8 <= c700 <= 2.2,
                "mesure %.1f img/s" % c700)
        verifie("le curseur change VRAIMENT la cadence", c700 < c180 / 2,
                "%.1f contre %.1f img/s" % (c700, c180))

        # ---------- 5. la fermeture arrete le minuteur ----------
        pg.click("#lbClose")
        pg.wait_for_timeout(300)
        cfin = cadence(pg, 900)
        verifie("la lecture s'arrete avec la fenetre", cfin == 0,
                "%.1f img/s apres fermeture" % cfin)
        verifie("le curseur disparait avec la lecture",
                pg.eval_on_selector("#lbVitWrap", "el => el.hidden") is True)

        # ---------- 6. GLOBALE : un AUTRE projet herite du reglage ----------
        pg.evaluate("setVitesse(120)")
        b = pg.evaluate(PREPARE, [NOM + "b", 4])
        projets.append(b["proj"])
        pg.click('[data-pid="%s"] [data-act="jouer"]' % b["pid"])
        pg.wait_for_timeout(300)
        cb = cadence(pg)
        verifie("un autre projet lit a la meme vitesse", cb > 5.5,
                "mesure %.1f img/s (120 ms attendu ≈ 8,3)" % cb)
        pg.click("#lbClose")

        # ---------- 7. PERSISTANCE : survit a un rechargement ----------
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        v1 = pg.evaluate("OPT.vitesse")
        verifie("la vitesse survit au rechargement", v1 == 120, "relu %s" % v1)
        curseur = pg.eval_on_selector("#lbVit", "el => el.value")
        verifie("le curseur du lecteur montre la valeur relue", str(curseur) == "120",
                "curseur a %s" % curseur)

        # ---------- 8. une valeur aberrante ne casse pas la lecture ----------
        pg.evaluate("localStorage.setItem('manga_vitesse', 'nawak')")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        v2 = pg.evaluate("OPT.vitesse")
        verifie("une valeur illisible retombe sur 180", v2 == 180, "lu %s" % v2)

        # --- menage : un banc ne laisse pas ses projets derriere lui ---
        for pid in projets:
            try:
                pg.evaluate("(id) => api('/manga/projects', {delete: id})", pid)
            except Exception:
                pass
        pg.wait_for_timeout(400)
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:3]))

    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
