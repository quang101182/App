# -*- coding: utf-8 -*-
"""La SCENE : le contexte est-il repris, et s'arrete-t-il a la bonne frontiere ?

Demande de Quang (28/07) : « je pensais que, quand j'ajoutais une case, le
contexte des cases precedentes etait pris en compte ». Il pointe lui-meme
l'effet de bord : au changement de scene, ce contexte doit CESSER.

Ce banc verifie les DEUX sens, et le second compte autant que le premier :
  1. une case au milieu d'une scene recoit les cases precedentes ;
  2. une case qui OUVRE une scene n'en recoit AUCUNE ;
  3. le contexte s'arrete a la frontiere (une scene ne voit pas la precedente) ;
  4. le contexte part REELLEMENT dans la requete /enhance -- mesure sur le corps
     HTTP, pas sur ce que le code a l'air de faire ;
  5. le contexte n'entre PAS dans le prompt envoye au moteur d'image ;
  6. le separateur bascule dans les deux sens et survit a un rechargement.

⚠ Le point 4 se mesure en ecoutant `fetch`, pas en remplacant `api()` : un banc
qui court-circuite le vrai chemin peut etre vert pendant que le bug vit chez
l'utilisateur (lecon du 21/07, Jarvis).

Usage:
    python test_scene_contexte.py
    python test_scene_contexte.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_scene_%d" % os.getpid()
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out")

# Une planche a deux scenes : trois cases au dojo, puis deux dans un couloir.
CASES = [
    "le maitre entre dans le dojo desert",
    "il s'assoit en seiza au centre",
    "elle le regarde depuis la porte",
    "le couloir du lycee, des eleves passent",      # <- debut de scene 2
    "elle marche vers la salle de classe",
]
DEBUT_SCENE = 3   # index de la case qui ouvre la 2e scene

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok)))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


ESPION = """() => {
  // On ECOUTE fetch, on ne remplace pas api(). Le vrai chemin reste le vrai
  // chemin : si demain api() cesse d'appeler /enhance, ce banc le verra.
  window.__vus = [];
  const vrai = window.fetch;
  window.fetch = async (url, opt) => {
    try {
      const u = String(url);
      if (u.indexOf('/enhance') >= 0 && opt && opt.body)
        window.__vus.push(JSON.parse(opt.body).idea || '');
    } catch (e) { /* un espion qui casse la page serait pire que pas d'espion */ }
    return vrai(url, opt);
  };
  return true;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 900})
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.set_default_timeout(120000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof casesAvantDansScene === 'function'")
        pg.evaluate(ESPION)

        if args.muter:
            # MUTATION : la frontiere de scene est ignoree (comportement d'avant
            # la v1.59.0). Les cas « la scene 2 ne voit pas la scene 1 » DOIVENT
            # tomber, et eux seuls.
            pg.evaluate("() => { window.ouvreUneScene = (p, i) => i === 0; }")

        base = pg.evaluate("""async ([nom, textes, coupe]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            S.proj = proj; S.page = page;
            for (let i = 0; i < textes.length; i++){
              await api('/manga/panels', {pageId: page.id, kind: 'dialogue', idx: i,
                        prompt: textes[i],
                        recipe: i === coupe ? {debutScene: true} : {}});
            }
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            renderPlate();
            return {proj: proj.id, page: page.id, n: S.panels.length};
        }""", [NOM, CASES, DEBUT_SCENE])
        verifie("la planche de test est montée (5 cases)", base["n"] == 5,
                "%d case(s)" % base["n"])

        # --- 1/2/3 : les frontieres -----------------------------------------
        vus = pg.evaluate("""() => S.panels.map((p, i) => ({
            i: i, n: casesAvantDansScene(p).length,
            scene: reperesScene(p).scene, rang: reperesScene(p).rang,
            ctx: contexteScene(p, 5) }))""")
        attendu = [0, 1, 2, 0, 1]          # case 4 ouvre la scene 2
        verifie("le contexte s'arrête à la frontière de scène",
                [v["n"] for v in vus] == attendu,
                "cases précédentes vues : %s (attendu %s)"
                % ([v["n"] for v in vus], attendu))
        verifie("la case qui OUVRE une scène ne reprend rien",
                vus[DEBUT_SCENE]["n"] == 0 and vus[DEBUT_SCENE]["ctx"] == "",
                "contexte = %r" % vus[DEBUT_SCENE]["ctx"][:50])
        verifie("la scène 2 ne voit pas le dojo de la scène 1",
                "dojo" not in (vus[4]["ctx"] or "").lower(),
                (vus[4]["ctx"] or "")[:70])
        verifie("les repères sont justes (scène 2, case 2 pour la dernière)",
                vus[4]["scene"] == 2 and vus[4]["rang"] == 2,
                "scène %s case %s" % (vus[4]["scene"], vus[4]["rang"]))

        # --- 4 : le contexte part VRAIMENT dans la requete -------------------
        pg.evaluate("() => { window.__vus = []; }")
        pg.evaluate("""async () => { await traduire(S.panels[2]); }""")
        envois = pg.evaluate("() => window.__vus")
        # ⚠ TOUTES les requetes, pas seulement la derniere : la traduction se
        # RELANCE quand le modele repond en francais. Le premier jet ne regardait
        # que `[-1]` et echouait une fois sur deux -- un banc non deterministe est
        # inexploitable. Il a quand meme servi : la relance perdait REELLEMENT le
        # contexte de scene, et c'est ainsi qu'on l'a vu.
        corps = "".join(envois) if envois else ""
        # ⛔ v1.64.1 : le contexte est SORTI de la traduction. Il y était « pour
        # désambiguïser », avec consigne explicite de ne rien en reprendre — et ce
        # banc a attrapé « seiza » (venu de la case précédente) dans les tags d'une
        # case qui parlait d'autre chose, UNE FOIS SUR DEUX. Un défaut intermittent
        # est le pire : il passe les contrôles et vit chez l'utilisateur.
        # Le banc vérifie donc l'inverse de sa 1re version : le chemin FIDÈLE ne
        # reçoit rien, le chemin qui ENRICHIT reçoit tout.
        verifie("la traduction (chemin fidèle) ne porte PAS le contexte",
                bool(envois) and all("CONTEXT" not in c and "seiza" not in c
                                     for c in envois),
                "%d requête(s), extrait : %s" % (len(envois), corps[:80].replace("\n", " ⏎ ")))
        verifie("… et elle porte bien la phrase de la case",
                "elle le regarde" in corps, "")

        # --- 5 : le contexte n'entre pas dans le prompt IMAGE ----------------
        # ⚠ CE TEST DOIT PASSER AVANT TOUTE AMELIORATION, et c'est la lecon :
        # `ameliorerPrompt` a le DROIT de reprendre le decor du contexte -- c'est
        # sa raison d'etre. Mesure a l'appui, il reprend parfois davantage
        # (« seiza », une posture d'une AUTRE case). Le tester apres l'avoir
        # appele revenait donc a lui reprocher son travail : le banc echouait une
        # fois sur deux sur un comportement voulu. Ici on mesure le chemin
        # TRADUIT, celui qui doit rester fidele.
        final = pg.evaluate("() => promptFinal(S.panels[2])")
        fuites = [m for m in ("seiza", "panel 1", "panel 2", "dojo desert")
                  if m in final.lower()]
        verifie("après TRADUCTION seule, le contexte n'entre pas dans le prompt image",
                not fuites,
                ("a fui : %s | " % ", ".join(fuites) if fuites else "") + final[:120])

        pg.evaluate("() => { window.__vus = []; }")
        pg.evaluate("""async () => { await ameliorerPrompt(S.panels[2]); }""")
        amel = pg.evaluate("() => window.__vus")
        verifie("l'amélioration, elle, REÇOIT le contexte de la scène",
                bool(amel) and any("seiza" in c for c in amel),
                "%d requête(s)" % len(amel))

        pg.evaluate("() => { window.__vus = []; }")
        pg.evaluate("""async () => { await ameliorerPrompt(S.panels[3]); }""")
        amel2 = pg.evaluate("() => window.__vus")
        verifie("… et une case qui OUVRE une scène n'en reçoit aucun",
                bool(amel2) and all("Previous panels" not in c for c in amel2),
                "%d requête(s)" % len(amel2))


        # --- 6 : le separateur bascule, et il tient au rechargement ----------
        avant = pg.evaluate("() => S.panels.map((p,i) => ouvreUneScene(p,i))")
        pg.click('[data-scenecut="%s"]' % pg.evaluate("() => S.panels[1].id"))
        pg.wait_for_timeout(600)
        apres = pg.evaluate("() => S.panels.map((p,i) => ouvreUneScene(p,i))")
        verifie("le séparateur coupe là où on clique",
                apres[1] and not avant[1], "%s -> %s" % (avant, apres))
        pg.click('[data-scenecut="%s"]' % pg.evaluate("() => S.panels[1].id"))
        pg.wait_for_timeout(600)
        rendu = pg.evaluate("() => S.panels.map((p,i) => ouvreUneScene(p,i))")
        verifie("… et il recolle (le bouton est bien une bascule)",
                rendu == avant, "%s" % rendu)

        rechargees = pg.evaluate("""async () => {
            const l = ((await api('/manga/panels?page=' + S.page.id)).items || []);
            return l.map((p, i) => !!(p.recipe && p.recipe.debutScene));
        }""")
        verifie("la coupure survit à un rechargement (elle est en base)",
                rechargees[DEBUT_SCENE] is True
                and sum(1 for x in rechargees if x) == 1,
                "%s" % rechargees)

        # Capture : la frontiere doit SE VOIR, pas seulement exister.
        pg.locator('[data-pid="%s"]' % pg.evaluate("() => S.panels[3].id")) \
          .scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        # ⚠ Le run MUTE ecrit sa propre capture. Sans ce suffixe, il ECRASE celle
        # du run normal -- et on finit par regarder l'ecran d'une app sabotee en
        # croyant regarder l'app. Attrape en la lisant : le temoin y annoncait
        # « scene 1 · case 4 », ce qui EST le comportement mute, attendu.
        pg.screenshot(path=os.path.join(
            SORTIE, "scene_separateur%s.png" % ("_MUTE" if args.muter else "")))

        deb = pg.evaluate("""() => {
            const d = document.documentElement;
            const inners = [...document.querySelectorAll('*')]
              .filter(e => e.scrollWidth > e.clientWidth + 1
                        && getComputedStyle(e).overflowX !== 'visible').length;
            return { page: d.scrollWidth - d.clientWidth, inners: inners };
        }""")
        verifie("rien ne déborde à 360 px avec le séparateur",
                deb["page"] <= 0 and deb["inners"] == 0, "%s" % deb)

        pg.evaluate("""async (proj) => { await api('/manga/projects', {delete: proj}); }""",
                    base["proj"])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    ko = [n for n, ok in cas if not ok]
    print("\n%d/%d" % (len(cas) - len(ko), len(cas)))
    print("capture : " + os.path.join(
        SORTIE, "scene_separateur%s.png" % ("_MUTE" if args.muter else "")))
    if args.muter:
        if ko:
            print("MUTATION : rouge comme attendu (%d cas) — le banc mord." % len(ko))
            return 0
        print("MUTATION : VERTE = le banc ne teste pas la frontière. A réparer.")
        return 1
    for n in ko:
        print("  - " + n)
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
