# -*- coding: utf-8 -*-
"""Banc v2.63.0 : ECRAN DE CHOIX du manga (maquette_choix_manga_v1, validee par Quang 25/09 17h13).
APP REELLE (8190). Tactile : 360, 476 (Fold ferme), 704 / 933x700 (Fold deplie) ; souris : 1280. Tout POST est BLOQUE.
Tactile :
1. le champ est un BOUTON (lecture seule) : le toucher ouvre l'ecran plein ecran, AUCUN clavier (rien n'a le focus) ;
2. la recherche part VIDE (jamais collee au nom propose) ; le nom deja choisi est marque ✓ ;
3. taper : rien ne defile (recherche a la meme place) ; « cl » = seulement ce qui COMMENCE ainsi (plus « exclusive ») ;
4. clavier simule (hauteur visible 380 px) : l'ecran se raccourcit, recherche et liste au-dessus du clavier ;
5. toucher un resultat = choisi + ferme ; « ➕ Nouvelle série » = le texte tape ; Echap / ← Fermer / retour Android = rien ne change ;
6. 3 000 series : 61 lignes dessinees au plus a l'ouverture, la suite au defilement, barre de lettres (S -> une serie en S),
   recherche < 150 ms.
Souris (1280) : la liste sous le champ, comme avant, et taper ne fait plus defiler la page.
Usage : python test_choix_manga_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ETAT = """() => { const c = $('choix'), r = c.getBoundingClientRect(), q = $('choixRech').getBoundingClientRect(), l = $('choixListe').getBoundingClientRect();
  return { vis: !c.hidden, top: Math.round(r.top), h: Math.round(r.height), rechTop: Math.round(q.top), rechBas: Math.round(q.bottom),
           listeBas: Math.round(l.bottom), focus: (document.activeElement || {}).id || '', val: $('choixRech').value,
           items: [...document.querySelectorAll('#choixListe .choix-i:not(.nouv)')].map(b => b.querySelector('span').textContent),
           nouv: !!document.querySelector('#choixListe .choix-i.nouv'), sel: (document.querySelector('#choixListe .choix-i.sel span') || {}).textContent || '',
           nb: document.querySelectorAll('#choixListe [data-i], #choixListe .choix-g').length, lettres: !$('choixLettres').hidden,
           deb: document.documentElement.scrollWidth - document.documentElement.clientWidth, barre: !$('navFlot').hidden }; }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((360, 780), (476, 860), (704, 900), (933, 700), (1280, 900)):
        tact = w < 1000
        print("=== %d x %d (%s)" % (w, h, "tactile" if tact else "souris"))
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tact, has_touch=tact)
        pg = c.new_page(); errs, posts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "savelog")):
                posts.append(r.url.split("?")[0]); return rt.abort()
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        url0 = pg.url
        pg.evaluate("() => { $('capBox').open = true; $('capTitre').value = 'Claymore'; }"); pg.wait_for_timeout(400)
        pg.evaluate("() => $('capTitre').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(300)
        et = lambda: pg.evaluate(ETAT)
        if tact:
            check("le champ est un bouton (lecture seule, pas de clavier)", pg.evaluate("() => $('capTitre').readOnly && $('capTitre').inputMode === 'none'"))
            pg.tap("#capTitre"); pg.wait_for_timeout(400)
            e = et()
            check("toucher : écran de choix PLEIN écran, aucun clavier", e["vis"] and e["top"] == 0 and abs(e["h"] - h) <= 1
                  and e["focus"] not in ("capTitre", "choixRech") and not e["barre"], e)
            check("… recherche VIDE, « Claymore » marqué ✓, récentes + A à Z", e["val"] == "" and e["sel"] == "Claymore"
                  and pg.evaluate("() => [...document.querySelectorAll('#choixListe .choix-g')].map(g => g.textContent).join('|')").count("|") >= 1,
                  pg.evaluate("() => [...document.querySelectorAll('#choixListe .choix-g')].map(g => g.textContent)"))
            check("… aucun débordement horizontal", e["deb"] == 0, e["deb"])
            pg.tap("#choixRech"); y0 = et()["rechTop"]; sy = pg.evaluate("() => scrollY")
            pg.keyboard.type("cl", delay=80); pg.wait_for_timeout(250); e = et()
            check("taper : RIEN ne défile (recherche à la même place, page immobile)", e["rechTop"] == y0 and pg.evaluate("() => scrollY") == sy, [y0, e["rechTop"]])
            check("« cl » : seulement ce qui COMMENCE ainsi (Claymore)", e["items"] == ["Claymore"], e["items"])
            pg.fill("#choixRech", ""); pg.keyboard.type("solo", delay=40); pg.wait_for_timeout(250); e = et()
            check("« solo » : les deux Solo Leveling en tête", len(e["items"]) >= 2 and all(x.lower().startswith("solo") for x in e["items"][:2]), e["items"])
            pg.set_viewport_size({"width": w, "height": 380}); pg.wait_for_timeout(400); e = et()
            check("clavier simulé (380 px visibles) : écran raccourci, recherche et liste au-dessus", e["h"] <= 381 and e["rechBas"] <= 380 and e["listeBas"] <= 380, e)
            pg.set_viewport_size({"width": w, "height": h}); pg.wait_for_timeout(300)
            pg.tap("#choixListe .choix-i:not(.nouv)"); pg.wait_for_timeout(300)
            check("toucher un résultat : choisi, écran fermé", not et()["vis"] and pg.evaluate("() => $('capTitre').value").lower().startswith("solo"), pg.evaluate("() => $('capTitre').value"))
            pg.tap("#capTitre"); pg.wait_for_timeout(300); pg.tap("#choixRech"); pg.keyboard.type("zzz nouveau", delay=20); pg.wait_for_timeout(250)
            e = et(); check("nom inconnu : « ➕ Nouvelle série »", e["nouv"] and not e["items"], e)
            pg.tap("#choixListe .choix-i.nouv"); pg.wait_for_timeout(300)
            check("… la toucher = le texte tapé", pg.evaluate("() => $('capTitre').value") == "zzz nouveau")
            pg.evaluate("() => { $('capTitre').value = 'Claymore'; }")
            pg.tap("#capTitre"); pg.wait_for_timeout(300); pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
            check("Échap : fermé, rien ne change", not et()["vis"] and pg.evaluate("() => $('capTitre').value") == "Claymore")
            pg.tap("#capTitre"); pg.wait_for_timeout(300); pg.tap("#choixFermer"); pg.wait_for_timeout(400)
            check("← Fermer : fermé, rien ne change, on reste sur l'app", not et()["vis"] and pg.url == url0 and pg.evaluate("() => $('capTitre').value") == "Claymore", pg.url)
            pg.tap("#capTitre"); pg.wait_for_timeout(300); pg.go_back(); pg.wait_for_timeout(600)
            check("retour Android : ferme l'écran, sans quitter l'app", not et()["vis"] and pg.url == url0 and pg.evaluate("() => typeof $") == "function", pg.url)
            pg.tap("#capTitreFl"); pg.wait_for_timeout(300)
            check("la flèche ▾ ouvre aussi l'écran", et()["vis"]); pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
            # DETECTION d'apres l'onglet (idee Quang 17h40) : faux onglets, la vraie fenetre de capture n'est pas touchee
            ONG = """(l) => { CAP_TABS = l; $('capTab').innerHTML = l.map((t, i) => '<option value="' + i + '">' + t.title + '</option>').join(''); }"""
            CHOISIR = "(i) => { $('capTab').value = String(i); $('capTab').dispatchEvent(new Event('change')); return $('capTitre').value; }"
            pg.evaluate(ONG, [{"url": "https://site.org/manga/one-punch-man/chapter-302", "title": "Read Chapter 302 online"},
                              {"url": "https://site.org/solo-leveling-season-2/ch-5", "title": "Solo Leveling Season 2 Ch 5"},
                              {"url": "https://site.org/read/fantasy-theater-deluxe/1", "title": "Fantasy Theater Deluxe Chapter 1"},
                              {"url": "https://unsite.org/", "title": "UnSite - Read Manhwa Online Free"}])
            pg.evaluate("() => { CAP_TITRE_AUTO = true; }")        # plus haut, un nom a ete CHOISI a la main : on repart d'un nom propose
            v = pg.evaluate(CHOISIR, 0)
            check("détection par l'ADRESSE : « one-punch-man » → le nom EXACT « One Punch-Man »", v == "One Punch-Man", v)
            v = pg.evaluate(CHOISIR, 1)
            check("autre saison : « Solo Leveling » proposé (tu peux changer)", v == "Solo Leveling", v)
            v = pg.evaluate(CHOISIR, 2)
            check("partiel (2 mots sur 3) : PAS de remplissage imposé, nom deviné de la page", v == "Fantasy Theater Deluxe", v)
            v = pg.evaluate(CHOISIR, 3)
            check("page d'ACCUEIL d'un site : champ vide (pas « UnSite » comme nom de manga)", v == "", v)
            pg.evaluate(CHOISIR, 2)
            pg.tap("#capTitre"); pg.wait_for_timeout(400)
            d = pg.evaluate("""() => { const g = document.querySelector('#choixListe .choix-g'); const i = document.querySelectorAll('#choixListe .choix-i');
                return [g && g.textContent, g && g.classList.contains('det'), [...i].slice(0, 2).map(b => b.querySelector('span').innerHTML),
                        getComputedStyle(document.querySelector('#choixListe mark.detecte') || document.body).color]; }""")
            check("liste : « Détecté sur la page » en tête, mots reconnus en DORÉ", d[0] == "Détecté sur la page" and d[1]
                  and all('<mark class="detecte">Fantasy</mark>' in x and '<mark class="detecte">Theater</mark>' in x and "Mini" in x and "<mark class=\"detecte\">Mini" not in x for x in d[2])
                  and d[3] == "rgb(255, 210, 87)", d)
            pg.tap("#choixListe .choix-i >> nth=0"); pg.wait_for_timeout(300)
            v = pg.evaluate(CHOISIR, 0)
            check("un nom CHOISI n'est jamais écrasé par la détection", v.startswith("Mini Fantasy Theater"), v)
            pg.evaluate("() => { CAP_TITRE_AUTO = true; $('capTitre').value = 'Claymore'; }")
            # 3 000 series
            pg.evaluate("""() => { const m = ['alpha','bravo','charlie','delta','echo','foxtrot','golf','hotel','india','juliet','kilo','lima','mike',
                'nova','oscar','papa','quebec','romeo','sierra','tango','ultra','victor','whisky','xray','yankee','zulu'];
                for (let i = 0; i < 3000; i++) SERIES_VIDES.push({ slug: 'banc-' + i, title: m[i % 26] + ' ' + m[(i * 7) % 26] + ' ' + i, serie_info: null }); }""")
            pg.tap("#capTitre"); pg.wait_for_timeout(500); e = et()
            check("3 000 séries : au plus 61 lignes dessinées à l'ouverture, barre de lettres", e["nb"] <= 61 and e["lettres"], [e["nb"], e["lettres"]])
            pg.evaluate("() => { const l = $('choixListe'); l.scrollTop = l.scrollHeight; }"); pg.wait_for_timeout(300)
            check("… défiler dessine la suite", et()["nb"] > 61, et()["nb"])
            pg.evaluate("() => choixSauter('S')"); pg.wait_for_timeout(200)
            prem = pg.evaluate("""() => { const l = $('choixListe'), r = l.getBoundingClientRect();
                const b = [...l.querySelectorAll('.choix-i')].find(x => x.getBoundingClientRect().top >= r.top - 2); return b ? b.querySelector('span').textContent : ''; }""")
            check("… lettre S : la liste saute aux séries en S", prem.lower().startswith("s"), prem)
            ms = pg.evaluate("() => { const t = performance.now(); $('choixRech').value = 'sierra tan'; choixConstruire(); return performance.now() - t; }")
            check("… recherche parmi 3 000 : < 150 ms", ms < 150, "%.0f ms" % ms)
            pg.keyboard.press("Escape")
        else:
            check("souris : champ modifiable (pas de lecture seule)", not pg.evaluate("() => $('capTitre').readOnly"))
            pg.click("#capTitre"); pg.wait_for_timeout(300)
            check("… la liste s'ouvre SOUS le champ (pas l'écran plein)", not pg.evaluate("() => $('capSugg').hidden") and not et()["vis"])
            pg.fill("#capTitre", "")
            # le champ EN BAS de l'ecran : la ou l'ancien code recalait la page a chaque lettre
            pg.evaluate("() => { const r = $('capTitre').getBoundingClientRect(); scrollBy(0, r.bottom - innerHeight + 30); }"); pg.wait_for_timeout(300)
            sy = pg.evaluate("() => scrollY")
            pg.keyboard.type("cl", delay=80); pg.wait_for_timeout(250)
            check("… taper ne fait PAS défiler la page", pg.evaluate("() => scrollY") == sy, [sy, pg.evaluate("() => scrollY")])
            items = pg.evaluate("() => [...document.querySelectorAll('#capSugg .cap-sugg-i')].map(b => b.dataset.titre)")
            check("… « cl » : seulement Claymore (même classement)", items == ["Claymore"], items)
            r = pg.evaluate("""() => [rangTitres('cl', ['All About Dominative and Exclusive Destruction']), rangTitres('cl', ['Claymore']),
                                       rangTitres('toy', ['Toying With Daddy']), rangTitres('the del', ['The Delinquent Girl']),
                                       rangTitres('del', ['The Delinquent Girl']), rangTitres('clay', ['Claymore']) > rangTitres('clay', ['Playing with Karma'])]""")
            check("classement : « cl » ≠ « exclusive » ; débuts de titre / de mot trouvés ; le vrai début avant la faute tolérée",
                  r[0] == 0 and r[1] == 100 and r[2] == 100 and r[3] == 100 and r[4] == 80 and r[5], r)
        check("RIEN n'est parti (aucun POST)", not posts, posts[:4])
        check("aucune erreur JS", not errs, errs[:3])
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
