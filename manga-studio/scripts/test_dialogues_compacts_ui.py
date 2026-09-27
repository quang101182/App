# -*- coding: utf-8 -*-
"""Banc v2.99.0 (maquette_dialogues_compact_v1) : bloc 🎭 du chapitre en PLAGES de pages + ecran ✏ en lignes.
App REELLE (8190), LECTURE SEULE : toute requete non-GET est interceptee (rien n'est prepare, rien n'est paye).
Largeurs : 360, 476 (Fold ferme), 704 (Fold ouvert), 933x700 (Fold paysage), 1280.
Usage : python test_dialogues_compacts_ui.py <serie/ch_N> [<serie/ch_N> ...] [--ancien fichier.html]  (--ancien = sabotage : doit etre ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
args = sys.argv[1:]
ANCIEN = None
if "--ancien" in args:
    i = args.index("--ancien"); ANCIEN = open(args[i + 1], encoding="utf-8").read(); del args[i:i + 2]
CHAPS = args
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsung_out")
os.makedirs(OUT, exist_ok=True)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""), flush=True)


LARGEURS = ((360, 780), (476, 900), (704, 900), (933, 700), (1280, 900))
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in LARGEURS:
        for ci, ch in enumerate(CHAPS if w == 360 else CHAPS[:1]):
            print("=== %d px · %s" % (w, ch))
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 800, has_touch=w < 800, service_workers="block")
            pg = ctx.new_page(); errs, ecrit, jlog = [], [], []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            def route(rt):
                u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
                if rt.request.method != "GET" and u.endswith("/savelog"):      # journal client : lu, pas une donnee
                    corps = rt.request.post_data or ""; jlog.append(corps); return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
                if rt.request.method != "GET":
                    ecrit.append(u.split("/manga/")[-1]); return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
                if ANCIEN and u.endswith("/manga"):
                    return rt.fulfill(status=200, body=ANCIEN, content_type="text/html; charset=utf-8")
                return rt.continue_()
            pg.route("**/*", route)
            pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(3500)
            pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", ch.split("/")[0])
            pg.reload(); pg.wait_for_timeout(4000)
            pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", ch); pg.wait_for_timeout(3000)
            print("     version servie : " + pg.evaluate("() => VERSION"))
            pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
            r = pg.evaluate("""() => { const box = $('dlgBox'), L = document.querySelector('#dplListe');
              const cartes = L ? [...L.querySelectorAll('.dpl')] : [], sel = L ? L.querySelector('.dpl.sel') : null, et = $('dplEtapes');
              const vis = el => !!(el && el.offsetParent && !el.hidden);
              return { liste: !!L, n: cartes.length, titres: cartes.map(c => c.querySelector('.t').textContent), sel: sel && sel.querySelector('.t').textContent,
                etapesApres: !!(sel && et && sel.nextElementSibling === et), prepFait: vis($('dplPrepFait')), prepBtn: vis($('dlgPreparer')),
                voix: vis($('dlgVoix')), regler: vis($('dlgOuvrir')), vid: vis($('dlgVid')), plus: vis(L && L.querySelector('[data-dpl=nouv]')),
                h: Math.round(box.getBoundingClientRect().height), deborde: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                interne: [...box.querySelectorAll('*')].filter(e => e.offsetParent && e.scrollWidth > e.clientWidth + 1 && /(auto|scroll)/.test(getComputedStyle(e).overflowX)).length,
                horsBoite: [...box.querySelectorAll('button,input,.dpl')].filter(e => e.offsetParent && e.getBoundingClientRect().right > box.getBoundingClientRect().right + 1).map(e => e.id || e.className).slice(0, 3),
                ancienVisible: vis(box.querySelector('.dlg-portee')) }; }""")
            check("A. liste des plages affichee (%d carte(s) : %s)" % (r["n"], ", ".join(r["titres"])), r["liste"] and r["n"] >= 1, r)
            check("A. la plage choisie est marquee et ses etapes sont JUSTE dessous", bool(r["sel"]) and r["etapesApres"], (r["sel"], r["etapesApres"]))
            check("A. plage deja preparee : « ✓ Prepare » (pas de bouton Preparer payant)", r["prepFait"] and not r["prepBtn"], r)
            check("A. etapes Regler / Voix / Video visibles", r["regler"] and r["voix"] and r["vid"], r)
            check("A. « ＋ Nouvelle plage » visible, anciens choix de portee caches", r["plus"] and not r["ancienVisible"], r)
            tr = pg.evaluate("() => [...document.querySelectorAll('#dplEtapes > *')].filter(e => e.offsetParent && e.scrollWidth > e.clientWidth + 1).map(e => e.textContent)")
            check("A. etapes lisibles en entier (aucun libelle tronque)", not tr, tr)
            check("A. rien ne deborde (page, conteneurs internes, boutons)", not r["deborde"] and not r["interne"] and not r["horsBoite"], (r["deborde"], r["interne"], r["horsBoite"]))
            print("     hauteur du bloc : %d px" % r["h"])
            lu = pg.evaluate("() => { const s = dlgLueur(), b = [...document.querySelectorAll('#dlgBox .btn.dlg-suiv')]; return { s, vis: b.filter(x => x.offsetParent).map(x => x.id || x.textContent) }; }")
            check("A. lueur de l'etape suivante (%s) sur un bouton VISIBLE du bloc" % (lu["s"] or "aucune"), (not lu["s"] or lu["s"] == "lire") or bool(lu["vis"]), lu)
            if w in (360, 704) and ci == 0:
                pg.query_selector("#dlgBox").screenshot(path=os.path.join(OUT, "dlg_compact_%d.png" % w))
            # nouvelle plage
            pg.evaluate("() => document.querySelector('#dplListe [data-dpl=nouv]').click()"); pg.wait_for_timeout(700)
            n = pg.evaluate("""() => { const f = document.querySelector('.dpl-nouv'), vis = el => !!(el && el.offsetParent && !el.hidden);
              return { form: vis(f), champs: !!(f && f.contains($('dlgDe')) && f.contains($('dlgA'))), prep: vis($('dlgPreparer')) && f.contains($('dlgPreparer')),
                txt: $('dlgPreparer').textContent, regler: vis($('dlgOuvrir')), autres: document.querySelectorAll('#dplListe .dpl').length, de: $('dlgDe').value }; }""")
            check("A2. « ＋ » : formulaire avec les champs de/à et Preparer (prix affiche)", n["form"] and n["champs"] and n["prep"] and "≈" in n["txt"], n)
            tr2 = pg.evaluate("() => [...document.querySelectorAll('#dplEtapes > *')].filter(e => e.offsetParent && e.scrollWidth > e.clientWidth + 1).map(e => e.textContent)")
            check("A2. bouton du formulaire lisible en entier (prix compris)", not tr2, tr2)
            import re as _re
            pt = _re.search(r"p\. (\d+)(?:-(\d+))?", n["txt"]); dd = pg.evaluate("() => [+$('dlgDe').value, +($('dlgA').value || $('dlgDe').value), CHAP_PAGES]")
            check("A2. le bouton dit EXACTEMENT les pages envoyees (pas de « fin » trompeur)", bool(pt) and int(pt.group(1)) == dd[0] and int(pt.group(2) or pt.group(1)) == dd[1] and "fin" not in n["txt"], (n["txt"], dd))
            check("A2. la nouvelle plage va jusqu'a la derniere page du chapitre", dd[1] == dd[2], dd)
            check("A2. les plages existantes restent listees ; « Regler » cache dans le formulaire", n["autres"] == r["n"] and not n["regler"], n)
            if w == 360 and ci == 0:
                pg.query_selector("#dlgBox").screenshot(path=os.path.join(OUT, "dlg_compact_nouv_360.png"))
            pg.evaluate("() => document.querySelector('[data-dpl=annuler]').click()"); pg.wait_for_timeout(600)
            check("A2. ✕ ramene sur une plage existante", pg.evaluate("() => !!document.querySelector('#dplListe .dpl.sel') && !document.querySelector('.dpl-nouv')"))
            # menu ⋯
            pg.evaluate("() => document.querySelector('#dplListe .dpl.sel [data-dpl=menu]').click()"); pg.wait_for_timeout(500)
            m = pg.evaluate("() => [...document.querySelectorAll('.dpl-menu button')].map(b => b.textContent.trim().slice(0, 22))")
            check("A3. ⋯ : corriger + refaire (+ video si elle existe)", any("Corriger" in x for x in m) and any("Refaire" in x for x in m), m)
            # ecran ✏
            pg.evaluate("() => $('dlgOuvrir').click()"); pg.wait_for_timeout(3000)
            e = pg.evaluate("""() => { const c = [...document.querySelectorAll('#dlgpCorps .dlgp-carte')];
              return { n: c.length, fermees: c.filter(x => x.classList.contains('ferme')).length, res: c.filter(x => x.querySelector('.dlgp-res')).length,
                h: Math.round(c.reduce((s, x) => s + x.getBoundingClientRect().height, 0)), deb: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }""")
            print("     ✏ titre : " + pg.evaluate("() => $('dlgpTitre').textContent"))
            check("B. ✏ : un personnage par ligne, tous replies (%d)" % e["n"], e["n"] >= 1 and e["fermees"] == e["n"] and e["res"] == e["n"], e)
            pg.evaluate("() => document.querySelectorAll('#dlgpCorps .dlgp-res')[0].click()"); pg.wait_for_timeout(300)
            o1 = pg.evaluate("() => [...document.querySelectorAll('#dlgpCorps .dlgp-carte')].map(x => !x.classList.contains('ferme'))")
            if len(o1) > 1:
                pg.evaluate("() => document.querySelectorAll('#dlgpCorps .dlgp-res')[1].click()"); pg.wait_for_timeout(300)
            o2 = pg.evaluate("() => [...document.querySelectorAll('#dlgpCorps .dlgp-carte')].map(x => !x.classList.contains('ferme'))")
            vis_voix = pg.evaluate("() => { const c = document.querySelector('#dlgpCorps .dlgp-carte:not(.ferme)'); const s = c && c.querySelector('select[data-k=voix_el]'); return !!(s && s.offsetParent); }")
            check("B. toucher = reglages deplies (voix visible), un seul a la fois", o1[0] and sum(o1) == 1 and sum(o2) == 1 and vis_voix, (o1, o2))
            check("B. ✏ ne deborde pas", not e["deb"])
            print("     ✏ hauteur des personnages replies : %d px" % e["h"])
            if w == 360 and ci == 0:
                pg.screenshot(path=os.path.join(OUT, "dlgp_compact_360.png"))
            check("0 erreur JS", not errs, errs[:2])
            mes = [l for c in jlog for l in c.split("\n") if "compact" in l.lower()]
            check("journal client : aucune erreur des Dialogues compacts", not mes, mes[:2])
            check("0 ecriture envoyee au serveur", not ecrit, ecrit[:4])
            ctx.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
