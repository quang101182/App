# -*- coding: utf-8 -*-
"""Dessiner un personnage depuis sa fiche — GENERATION REELLE.

Quang, 27/07 : « je ne vois toujours pas dans le personnage la creation des
images des personnages. Ca fait un moment qu'on en parle et ca n'a toujours pas
ete fait. » Verifie dans le code avant de repondre : il avait raison. L'app
savait IMPORTER une image de reference (v1.25.0), pas en FABRIQUER une -- or une
fiche neuve n'a aucune photo de depart, le personnage n'existe que dans ses tags.

Ce banc DEPENSE DU GPU (3 images, ~1 a 2 min) et c'est voulu : la question posee
est « est-ce que ca dessine vraiment ce personnage-la ? », et aucun stub ne
repond a ca.

Ce qu'il verifie :
  - le bouton refuse poliment une fiche SANS traits (rien a dessiner) ;
  - trois vues sortent, et elles s'affichent AU FUR ET A MESURE (trois attentes
    muettes de 25 s donnent l'impression que rien ne se passe) ;
  - le prompt envoye contient les traits de la FICHE et le style du projet, mais
    NI le LoRA, NI le declencheur, NI l'identite du PROJET -- sinon on dessine le
    heros du manga en cours a la place de la fiche, exactement le defaut corrige
    le 27/07 ou chaque case heritait de la lyceenne de test ;
  - tant qu'on n'a rien garde, la fiche n'a AUCUNE reference : un brouillon qui
    s'installe tout seul, c'est un choix fait a la place de l'utilisateur ;
  - « garder » ajoute bien la reference, et elle survit au rechargement.

Usage:
    python test_perso_dessiner.py [--headed]
    python test_perso_dessiner.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_perso_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


# Un projet qui a un style ET une identite de heros : sans eux, on ne pourrait
# pas verifier que l'identite du PROJET reste dehors.
PREPARE = """async ([nom]) => {
    const rep = await api('/manga/projects', {name: nom, slug: nom,
        recipe: {style: 'kabukigravure, black and white',
                 lora: '', trigger: 'herosduprojet', ident: 'blonde, blue eyes'}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    S.proj = proj;
    fillRecipe();
    const vide = await api('/manga/chars', {name: nom + '-vide', tags: '', role: 'secondaire'});
    const plein = await api('/manga/chars', {name: nom + '-plein',
        tags: 'vieux maitre barbu, cicatrice sur la joue, kimono sombre', role: 'heros'});
    await loadChars();
    return {proj: proj.id, vide: vide.id, plein: plein.id};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="l'identite du PROJET repasse dans le prompt : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, prompts = [], []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        # On ESPIONNE ce qui part au moteur, sans l'empecher de dessiner.
        def voir(route):
            try:
                import json as _j
                wf = (_j.loads(route.request.post_data or "{}").get("prompt")) or {}
                for n in wf.values():
                    if n.get("class_type") == "CLIPTextEncode":
                        prompts.append(n.get("inputs", {}).get("text", ""))
                        break
            except Exception:
                pass
            route.continue_()
        pg.route("**/comfy/prompt", voir)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM])
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(1500)

        def ouvrir(cid):
            """Deplie la fiche. Depuis la v1.38.0 la liste est REPLIEE (une fiche
            = une ligne) : sans ce geste, les boutons de la fiche n'existent pas
            dans le DOM. Ce banc coute 2 min de GPU, il n'avait donc pas ete
            rejoue depuis -- il etait casse sans que rien ne le signale."""
            if pg.eval_on_selector_all('[data-chdraw="%s"]' % cid, "e => e.length") == 0:
                pg.click('[data-chopen="%s"]' % cid)
                pg.wait_for_timeout(600)

        ouvrir(d["vide"])

        if args.muter:
            # MUTATION : la fiche est dessinee AVEC l'identite du projet. Trois
            # belles images sortent quand meme -- ce sont juste celles du heros
            # du manga, pas du personnage demande. Rien ne plante.
            pg.evaluate("""() => {
                const vrai = recipe;
                window.recipe = () => vrai();
                const d0 = dessinerPersonnage;
                window.dessinerPersonnage = async (c) => {
                    const r = recipe();
                    const base = Object.assign({}, r);   // <-- on ne neutralise plus rien
                    const seed = 4242;
                    BROUILLONS[c.id] = [];
                    const positive = [base.style, base.trigger, base.ident,
                                      (c.tags||''), 'upper body'].filter(Boolean).join(', ');
                    const imgs = await runGraph(
                        wfPanel(base, positive, seed, 'manga/_perso/mut', null, null, .9, null),
                        'mutation');
                    BROUILLONS[c.id] = [{cle:'buste', nom:'buste', img: imgs[0]}];
                    renderChars();
                };
            }""")

        # ---------- 1. une fiche sans traits : refus poli ----------
        pg.click('[data-chdraw="%s"]' % d["vide"])
        pg.wait_for_timeout(1500)
        verifie("une fiche sans traits n'envoie rien au moteur",
                len(prompts) == 0, "%d appel(s)" % len(prompts))

        # ---------- 2. dessiner pour de vrai ----------
        print("   generation reelle en cours (3 vues, ~1-2 min)…", flush=True)
        ouvrir(d["plein"])
        pg.click('[data-chdraw="%s"]' % d["plein"])
        vues = 0
        for _ in range(120):                       # jusqu'a 6 min
            pg.wait_for_timeout(3000)
            vues = pg.eval_on_selector_all('[data-chkeep="%s"]' % d["plein"],
                                           "els => els.length")
            if vues >= 3:
                break
        verifie("trois vues sont dessinees", vues == 3, "%d vue(s)" % vues)
        verifie("trois appels au moteur", len(prompts) == 3, "%d appel(s)" % len(prompts))

        env = " ||| ".join(prompts)
        # La fiche a ete ecrite en FRANCAIS -- comme Quang l'ecrit. Ce qui part au
        # moteur doit etre de l'ANGLAIS : un texte francais n'y est pas mal
        # compris, il est IGNORE, et le personnage dessine n'aurait aucun rapport.
        verifie("le prompt porte les traits de la FICHE",
                "scar" in env or "beard" in env or "kimono" in env, env[:110])
        verifie("les traits francais ont ete TRADUITS avant de partir",
                "cicatrice" not in env and "vieux maitre" not in env, env[:110])
        verifie("la fiche est corrigee en base, pas seulement pour ce dessin",
                "cicatrice" not in (pg.evaluate(
                    "(id) => (CHARS.find(c => c.id === id) || {}).tags || ''", d["plein"])),
                pg.evaluate("(id) => (CHARS.find(c => c.id === id) || {}).tags || ''",
                            d["plein"])[:90])
        verifie("... et le style du projet", "kabukigravure" in env, env[:90])
        verifie("... mais PAS le declencheur du projet",
                "herosduprojet" not in env, env[:90])
        verifie("... ni l'identite du projet", "blue eyes" not in env, env[:90])
        verifie("les trois cadrages sont demandes",
                all(t in env for t in ["close-up on face", "upper body", "full body"]),
                env[:90])

        # ---------- 3. rien n'est garde tant qu'on n'a pas choisi ----------
        refs = pg.evaluate("(id) => (CHARS.find(c => c.id === id).refs || []).length", d["plein"])
        verifie("aucune reference ajoutee sans choix explicite", refs == 0, "%d ref(s)" % refs)

        # ---------- 4. garder une vue ----------
        pg.click('[data-chkeep="%s"][data-vue="buste"]' % d["plein"])
        for _ in range(40):
            pg.wait_for_timeout(1500)
            refs = pg.evaluate("(id) => { const c = CHARS.find(x => x.id === id);"
                               " return c ? (c.refs || []).length : -1; }", d["plein"])
            if refs >= 1:
                break
        verifie("la vue gardee devient une reference", refs == 1, "%d ref(s)" % refs)
        verifie("les brouillons sont ranges apres le choix",
                pg.eval_on_selector_all('[data-chkeep="%s"]' % d["plein"],
                                        "els => els.length") == 0)

        # ---------- 5. elle survit au rechargement ----------
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(2000)
        refs2 = pg.evaluate("(id) => { const c = CHARS.find(x => x.id === id);"
                            " return c ? (c.refs || []).length : -1; }", d["plein"])
        verifie("la reference survit au rechargement", refs2 == 1, "%d ref(s)" % refs2)

        for cid in (d["vide"], d["plein"]):
            try:
                pg.evaluate("(id) => api('/manga/chars', {delete: id})", cid)
            except Exception:
                pass
        try:
            pg.evaluate("(id) => api('/manga/projects', {delete: id})", d["proj"])
        except Exception:
            pass
        pg.wait_for_timeout(500)
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:3]))
    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
