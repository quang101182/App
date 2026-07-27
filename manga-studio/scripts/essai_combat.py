# -*- coding: utf-8 -*-
"""Un ESSAI d'utilisateur : 10 cases de combat d'arts martiaux, Jo contre Kimiko.

Demande de Quang (28/07) : « fais l'essai toi-meme, en pilotant comme si tu etais
moi, pour voir si au niveau ergonomie et efficacite tout est en ordre ».

Ce n'est donc PAS un banc de non-regression : c'est un parcours reel, et ce qu'il
rapporte n'est pas « vert/rouge » mais **le nombre de gestes, le temps, et les
frictions rencontrees**. Regle qu'il s'impose : **aucun appel a `api()`**, aucun
raccourci JS pour agir — uniquement ce qu'un doigt peut faire (clics, saisie,
defilement). Un script qui triche mesure son propre confort, pas celui de
l'utilisateur. Le JS n'est utilise que pour MESURER (positions, hauteurs).

Usage:
    python essai_combat.py [--headed] [--cases 10] [--largeur 360] [--sans-gpu]
"""
import argparse
import io
import json
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "essai_out")
PROJET = "Duel au dojo"

# Le decoupage, ecrit en francais comme Quang l'ecrirait — c'est l'app qui
# traduit (v1.23.0), et c'est justement un des chemins qu'on veut eprouver.
SCENARIO = [
    "les deux adversaires se font face dans un dojo, plan large, tension",
    "gros plan sur le visage de la femme, regard determine",
    "gros plan sur le visage de l'homme, il serre les dents",
    "la femme s'elance et donne un coup de pied saute, lignes de vitesse",
    "l'homme bloque le coup avec son avant-bras, impact",
    "l'homme contre-attaque d'un coup de poing vers le visage de la femme",
    "la femme esquive en se penchant en arriere, cheveux en mouvement",
    "les deux combattants s'immobilisent, garde haute, sueur",
    "plan large du dojo, les deux silhouettes de profil",
    "la femme tend la main vers l'homme, fin du combat, respect",
]

gestes, frictions = [], []


def geste(nom, t0, detail=""):
    dt = time.time() - t0
    gestes.append((nom, dt, detail))
    print("  %-44s %6.1f s  %s" % (nom, dt, detail), flush=True)


def friction(quoi):
    frictions.append(quoi)
    print("  ⚠ FRICTION : " + quoi, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--cases", type=int, default=10)
    ap.add_argument("--largeur", type=int, default=360)
    ap.add_argument("--nettoyer", action="store_true",
                    help="passe les fiches par 🧹 Nettoyer avant l'essai "
                         "(tags d'origine sauvegardes dans essai_out/tags_avant.json)")
    ap.add_argument("--sans-gpu", action="store_true", dest="sans_gpu",
                    help="tout le parcours SAUF les generations (mesure l'ergonomie seule)")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    os.makedirs(SORTIE, exist_ok=True)
    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    scenario = SCENARIO[:args.cases]
    erreurs = []
    depart = time.time()
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": args.largeur, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.set_default_timeout(240000)

        t = time.time()
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        geste("ouvrir l'app", t, pg.evaluate(
            "document.getElementById('verBadge').textContent"))

        # ---------- 0. ce qu'un utilisateur ferait d'abord : 🧹 Nettoyer les fiches
        # Mesure du 28/07 : avec « character design » et « simple background » dans
        # les tags, la case sort en PLANCHE DE PERSONNAGE quoi qu'on fasse aux
        # images. Le bouton existe pour ça (v1.51.0), on s'en sert — et on garde
        # les tags d'origine sur le disque pour pouvoir revenir en arriere.
        taps_net = [0]
        if args.nettoyer:
            t = time.time()
            avant = pg.evaluate("""() => (CHARS || []).map(c =>
                ({id: c.id, name: c.name, tags: c.tags}))""")
            with open(os.path.join(SORTIE, "tags_avant.json"), "w", encoding="utf-8") as f:
                json.dump(avant, f, ensure_ascii=False, indent=2)
            pg.click('nav button[data-tab="tPerso"]')
            pg.wait_for_timeout(600)
            for qui in ("Kimiko", "Jo"):
                # ⚠ `CHARS` est un `let` de module : il est visible depuis le
                # contexte global, mais PAS sous `window.CHARS` (qui vaut
                # undefined). La regle etait deja ecrite pour les bancs de la
                # v1.39.0 — je l'ai repayee ici : le nettoyage ne trouvait aucune
                # fiche et passait en silence.
                ident = pg.evaluate("""(qui) => ((CHARS || [])
                    .find(c => (c.name || '') === qui) || {}).id""", qui)
                if not ident:
                    friction("fiche « %s » introuvable" % qui)
                    continue
                if not pg.evaluate("(id) => !!document.querySelector('[data-chnet=\"'+id+'\"]')",
                                   ident):
                    pg.click('[data-chopen="%s"]' % ident)
                    pg.wait_for_timeout(500)
                pg.click('[data-chnet="%s"]' % ident)
                pg.wait_for_timeout(1200)
                # 🧹 Nettoyer ne s'execute pas en douce : il DEMANDE, en listant les
                # mots qu'il va retirer (question a l'ecran, v1.34.0). Il faut donc
                # repondre — c'est un geste de plus, et c'est un bon design : on ne
                # modifie pas une fiche de quelqu'un sans lui montrer quoi.
                if pg.evaluate("() => { const a = document.getElementById('ask');"
                               " return !!a && !a.hidden; }"):
                    mots = pg.evaluate("() => (document.getElementById('askX')||{}).textContent")
                    print("     🧹 %s → %s" % (qui, (mots or "").strip()[:110]))
                    pg.click("#askYes")
                    taps_net[0] += 1
                pg.wait_for_timeout(2500)
            apres = pg.evaluate("""() => (CHARS || []).map(c => c.name + ' : ' + (c.tags||''))""")
            geste("🧹 Nettoyer les 2 fiches", t, "%d gestes" % (4 + taps_net[0]))
            for l in apres:
                if l.startswith(("Kimiko", "Jo")):
                    print("     " + l[:150])

        # ---------- 1. projet + planche, par le seul bouton prevu pour ça
        t = time.time()
        pg.click('nav button[data-tab="tProj"]')
        pg.fill("#npName", PROJET)
        pg.fill("#npCases", str(len(scenario)))
        pg.click("#btnDemarrer")
        pg.wait_for_timeout(5000)
        cases = pg.evaluate("document.querySelectorAll('[data-pid]').length")
        geste("créer le projet + %d cases (3 gestes)" % len(scenario), t,
              "%d cases à l'écran" % cases)
        if cases != len(scenario):
            friction("%d cases demandées, %d affichées" % (len(scenario), cases))

        ids = pg.evaluate("[...document.querySelectorAll('[data-pid]')].map(e => e.dataset.pid)")

        # ---------- 2. ecrire les 10 actions + caster les 2 personnages
        t = time.time()
        taps = 0
        for i, texte in enumerate(scenario):
            pid = ids[i]
            champ = '[data-pid="%s"] [data-prompt]' % pid
            pg.click(champ)
            pg.fill(champ, texte)
            pg.dispatch_event(champ, "change")
            taps += 2
            pg.wait_for_timeout(150)
            # « Qui est là » : une pastille par personnage, DANS la case (v1.49.0)
            for qui in ("Kimiko", "Jo"):
                sel = ('[data-pid="%s"] .quila .pers' % pid)
                trouve = pg.evaluate("""([pid, qui]) => {
                    const b = [...document.querySelectorAll('[data-pid="'+pid+'"] .quila .pers')]
                        .find(x => x.textContent.trim() === qui);
                    return b ? (b.classList.contains('on') ? 'deja' : 'a-cliquer') : 'absent';
                }""", [pid, qui])
                if trouve == "absent":
                    # Sur un projet NEUF la troupe est vide : aucune pastille n'est
                    # proposee, il faut d'abord deplier « + ajouter (n) ». C'est un
                    # geste de plus, et c'est exactement ce qu'on est venu mesurer.
                    plus = '[data-pid="%s"] .quila .pers.plus' % pid
                    if pg.evaluate("(s) => !!document.querySelector(s)", plus):
                        pg.click(plus)
                        taps += 1
                        pg.wait_for_timeout(500)
                        if i == 0:
                            friction("projet neuf : il faut déplier « + ajouter » "
                                     "avant de voir les personnages")
                        trouve = pg.evaluate("""([pid, qui]) => {
                            const b = [...document.querySelectorAll('[data-pid="'+pid+'"] .quila .pers')]
                                .find(x => x.textContent.trim() === qui);
                            return b ? (b.classList.contains('on') ? 'deja' : 'a-cliquer') : 'absent';
                        }""", [pid, qui])
                    if trouve == "absent":
                        friction("case %d : « %s » introuvable même après « + ajouter »"
                                 % (i + 1, qui))
                if trouve == "a-cliquer":
                    pg.evaluate("""([pid, qui]) => {
                        const b = [...document.querySelectorAll('[data-pid="'+pid+'"] .quila .pers')]
                            .find(x => x.textContent.trim() === qui);
                        b.scrollIntoView({block: 'center'});
                    }""", [pid, qui])
                    pg.click('[data-pid="%s"] .quila .pers:has-text("%s")' % (pid, qui))
                    taps += 1
                    pg.wait_for_timeout(700)
        geste("écrire 10 actions + caster 2 persos par case", t, "%d gestes" % taps)

        # ---------- 3. MESURE d'ergonomie : la hauteur d'une case
        m = pg.evaluate("""() => {
            const c = document.querySelector('[data-pid]');
            const r = c.getBoundingClientRect();
            const ta = c.querySelector('[data-prompt]');
            const doc = document.documentElement;
            return {caseH: Math.round(r.height), ecran: doc.clientHeight,
                    champH: ta ? Math.round(ta.getBoundingClientRect().height) : null,
                    pageH: Math.round(doc.scrollHeight),
                    debordeX: doc.scrollWidth > doc.clientWidth};
        }""")
        print("\n  MESURE : une case fait %d px de haut pour un écran de %d px"
              " (%.1f écran) · champ de texte %d px · planche entière %d px (%.1f écrans)"
              % (m["caseH"], m["ecran"], m["caseH"] / m["ecran"], m["champH"],
                 m["pageH"], m["pageH"] / m["ecran"]))
        if m["caseH"] > m["ecran"] * 0.9:
            friction("une seule case occupe %.0f %% de l'écran : on ne voit jamais"
                     " deux cases à la fois" % (100 * m["caseH"] / m["ecran"]))
        if m["debordeX"]:
            friction("la page déborde horizontalement")

        # ---------- 4. generer, par le bouton « tout generer »
        if not args.sans_gpu:
            t = time.time()
            pg.click("#btnGenAll")
            # On attend que toutes les cases aient une image, en regardant l'ecran
            # (c'est ce que fait un utilisateur : il regarde).
            fini, tmax = False, time.time() + 900
            while time.time() < tmax:
                pg.wait_for_timeout(5000)
                n = pg.evaluate("document.querySelectorAll('[data-pid] .img img').length")
                if n >= len(scenario):
                    fini = True
                    break
            geste("générer les %d cases (1 geste)" % len(scenario), t,
                  "%d images" % pg.evaluate(
                      "document.querySelectorAll('[data-pid] .img img').length"))
            if not fini:
                friction("toutes les cases n'ont pas abouti en 15 min")

            # ---------- 5. exporter
            t = time.time()
            with pg.expect_download() as dl:
                pg.click("#btnExport")
            chemin = os.path.join(SORTIE, "planche_combat.png")
            dl.value.save_as(chemin)
            geste("exporter la planche en PNG (1 geste)", t, os.path.basename(chemin))

        # ---------- 6. ce que l'app a dit en chemin
        journal = pg.evaluate("window.MangaLog ? MangaLog.dump(200) : ''")
        with open(os.path.join(SORTIE, "journal.txt"), "w", encoding="utf-8") as f:
            f.write(str(journal))
        refus = pg.evaluate("""() => [...document.querySelectorAll('.refus, [data-refus]')]
            .map(e => e.textContent.trim()).filter(Boolean)""")
        for r in refus:
            friction("refus affiché : " + r[:120])

        pg.screenshot(path=os.path.join(SORTIE, "ecran_planche.png"), full_page=False)
        br.close()

    print("\n===================== ESSAI TERMINE =====================")
    print("durée totale : %.1f min" % ((time.time() - depart) / 60))
    print("gestes :")
    for nom, dt, det in gestes:
        print("  %-44s %6.1f s  %s" % (nom, dt, det))
    print("erreurs JS : %s" % (erreurs or "aucune"))
    print("frictions (%d) :" % len(frictions))
    for f in frictions:
        print("  - " + f)
    print("sorties -> %s" % SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
