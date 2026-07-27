# -*- coding: utf-8 -*-
"""🔎 Qu'est-ce qui cloche ? — une critique qui REGARDE l'image.

Quang, 27/07 : « un bouton qui analyse et ameliore, avec potentiellement un score
et la possibilite de relancer une generation ».

La reserve ecrite dans la ROADMAP avant de coder portait sur le SCORE : celui de
Generate Studio note le PROMPT (`ImageScorer`), pas l'image -- il mettrait une
bonne note a une case aux mains ratees. Le proxy expose autre chose : `/critique`
envoie l'image a Pixtral, qui la REGARDE. Le score porte donc sur du reel, mais
il mesure la CONFORMITE a la demande, pas la qualite du dessin -- et l'ecran doit
le dire, sinon un chiffre dont on ignore ce qu'il mesure est pire qu'un chiffre
absent.

Ce que le banc verifie :
  - l'IMAGE est bien envoyee au juge (pas seulement le prompt) ;
  - le prompt envoye est celui REELLEMENT utilise pour generer (`recipe.positive`),
    pas celui qu'on recalculerait aujourd'hui -- la recette a pu changer depuis ;
  - le score est affiche AVEC ce qu'il mesure, mot pour mot ;
  - « regenerer avec la correction » envoie le prompt CORRIGE au moteur, et
    n'ecrit pas ce positif complet dans le champ de la case (sinon le style et
    l'identite doubleraient a la generation suivante) ;
  - quand le juge ne propose aucune correction, l'app ne fabrique pas un faux
    bouton : elle renvoie vers ⬚ Zone pour les defauts de dessin.

La reponse du juge est FIGEE. Zero GPU.

Usage:
    python test_critique.py [--headed]
    python test_critique.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_crit_%d" % os.getpid()

POSITIF_UTILISE = "kabukigravure, monochrome, old master, walking in a corridor"
CORRIGE = "kabukigravure, monochrome, old master, 1boy, walking in a corridor"

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


PREPARE = """async ([nom, positif]) => {
    const rep = await api('/manga/projects', {name: nom, slug: nom,
        recipe: {style: 'kabukigravure, monochrome'}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                prompt: 'walking in a corridor', idx: 0});
    S.proj = proj; S.page = page;
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
    const p = S.panels[0];
    p.file = nom + '/case.png';
    // `positive` = ce qui a REELLEMENT servi a generer, fige a l'epoque.
    p.recipe = Object.assign({}, p.recipe, {positive: positif, seed: 111});
    await api('/manga/panels', p);
    renderPlate();
    return {proj: proj.id, pid: p.id};
}"""

PNG = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="la correction est ecrite dans le champ de la case : DOIT rougir")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (200, 200), (30, 30, 30))
    ImageDraw.Draw(im).rectangle((50, 50, 150, 150), fill=(220, 220, 220))
    buf = io.BytesIO(); im.save(buf, "PNG"); corps = buf.getvalue()

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, juges, moteur = [], [], []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 390, "height": 820},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.route("**/manga/file*", lambda r: r.fulfill(
            status=200, content_type="image/png", body=corps))

        def juge(route):
            try:
                juges.append(json.loads(route.request.post_data or "{}"))
            except Exception:
                juges.append({})
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"score": 62,
                                           "issues": "Le personnage est seul alors que deux "
                                                     "silhouettes sont visibles.",
                                           "prompt": CORRIGE}))
        pg.route("**/critique", juge)

        def gen(route):
            try:
                wf = (json.loads(route.request.post_data or "{}").get("prompt")) or {}
                for n in wf.values():
                    if n.get("class_type") == "CLIPTextEncode":
                        moteur.append(n.get("inputs", {}).get("text", ""))
                        break
            except Exception:
                pass
            route.fulfill(status=200, content_type="application/json",
                          body='{"prompt_id": "_banc_"}')
        pg.route("**/comfy/prompt", gen)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM, POSITIF_UTILISE])
        sel = '[data-pid="%s"]' % d["pid"]

        if args.muter:
            # MUTATION : la correction est ecrite dans le CHAMP de la case, comme
            # une proposition de « 3 suites ». Ca marche a l'ecran -- et a la
            # generation suivante le style et l'identite sont en double, parce
            # que `promptFinal` les rajoute par-dessus.
            pg.evaluate("""() => {
                document.getElementById('plate').addEventListener('click', (ev) => {
                    const f = ev.target.closest('[data-critfix]');
                    if (!f) return;
                    const c = ev.target.closest('[data-pid]');
                    const pp = S.panels.find(x => x.id === c.dataset.pid);
                    pp.prompt = f.dataset.critfix;
                    const ch = c.querySelector('[data-prompt]');
                    if (ch) ch.value = pp.prompt;
                    ev.stopImmediatePropagation();
                }, true);
            }""")

        # ---------- 1. le bouton est dans ⚙ ----------
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(500)
        verifie("le bouton vit dans ⚙ Affiner",
                pg.eval_on_selector_all(sel + ' .affiner [data-act="critique"]',
                                        "els => els.filter(e => e.offsetParent !== null).length") == 1)

        # ---------- 2. ce qui est envoye au juge ----------
        pg.click(sel + ' [data-act="critique"]')
        pg.wait_for_timeout(3000)
        verifie("une demande est partie au juge", len(juges) == 1, "%d" % len(juges))
        env = juges[0] if juges else {}
        verifie("l'IMAGE est envoyee (pas seulement le texte)",
                bool(env.get("image")) and len(env.get("image", "")) > 100,
                "%d octets de base64" % len(env.get("image", "")))
        verifie("le prompt envoye est celui REELLEMENT utilise",
                env.get("prompt") == POSITIF_UTILISE, str(env.get("prompt"))[:80])

        # ---------- 3. le score dit CE QU'IL MESURE ----------
        txt = pg.eval_on_selector(sel + " [data-idees]", "el => el.textContent")
        verifie("le score est affiche", "62" in txt, txt[:70])
        verifie("... avec ce qu'il mesure, en toutes lettres",
                "PAS la qualité du dessin" in txt, txt[:150])
        verifie("ce qui cloche est dit en francais",
                "deux silhouettes" in txt, txt[:150])

        # ---------- 4. regenerer AVEC la correction ----------
        avant_champ = pg.eval_on_selector(sel + " [data-prompt]", "el => el.value")
        pg.click(sel + " [data-critfix]")
        pg.wait_for_timeout(3500)
        verifie("le moteur recoit le prompt CORRIGE",
                any(CORRIGE in m for m in moteur), (moteur[-1] if moteur else "(rien)")[:90])
        apres_champ = pg.eval_on_selector(sel + " [data-prompt]", "el => el.value")
        verifie("le positif complet n'est PAS ecrit dans le champ de la case",
                apres_champ == avant_champ,
                "champ : %r -> %r" % (avant_champ, apres_champ))
        verifie("... et il ne doublonne donc pas le style",
                moteur and moteur[-1].count("kabukigravure") == 1,
                (moteur[-1] if moteur else "")[:90])

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


if __name__ == "__main__":
    sys.exit(main())
