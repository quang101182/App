# -*- coding: utf-8 -*-
"""Banc v3.0.0 (maquette_series_synthese_v1). App REELLE 8190, lecture seule (non-GET intercepte, service worker bloque,
confirm() REFUSE : rien n'est ecrit). Largeurs 360 / 476 / 704 / 933x700 / 1280.
V : 🎬 Videos de la serie courte, chapitres sans narration replies (voir / masquer), « › » = chapitre bloc 🎬.
D : 🎭 Dialogues de la serie : plages en pastilles, « › » = chapitre bloc 🎭, « ＋ plage » = formulaire pret, autre chapitre.
VX : voix groupees Hommes / Femmes, genre du personnage d'abord. C : couleurs de la famille du genre en tete, bouton recolorer.
Usage : python test_series_synthese_ui.py <serie longue> <serie/ch_N avec dialogues> [--ancien f.html]"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
args = sys.argv[1:]
ANCIEN = None
if "--ancien" in args:
    i = args.index("--ancien"); ANCIEN = open(args[i + 1], encoding="utf-8").read(); del args[i:i + 2]
SERIE, CH = args[0], args[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsung_out")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


def page(b, w, h):
    ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 800, has_touch=w < 800, service_workers="block")
    pg = ctx.new_page(); errs, ecrit, dlg = [], [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: (dlg.append(d.message), d.dismiss()))
    def route(rt):
        u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
        if rt.request.method != "GET":
            if not u.endswith("/savelog"): ecrit.append(u.split("/manga/")[-1])
            return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
        if ANCIEN and u.endswith("/manga"):
            return rt.fulfill(status=200, body=ANCIEN, content_type="text/html; charset=utf-8")
        return rt.continue_()
    pg.route("**/*", route)
    pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(3000)
    return ctx, pg, errs, ecrit, dlg


def serie(pg, s):
    pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_chap_bloc',''); }", s)
    pg.reload(); pg.wait_for_timeout(4000)


DEB = "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((360, 780), (476, 900), (704, 900), (933, 700), (1280, 900)):
        print("=== %d px" % w)
        ctx, pg, errs, ecrit, dlg = page(b, w, h)
        print("     version : " + pg.evaluate("() => VERSION"))
        # ---- V
        serie(pg, SERIE)
        pg.evaluate("() => $('btnVideos').click()"); pg.wait_for_timeout(3500)
        v = pg.evaluate("""() => { const vis = [...document.querySelectorAll('#vidListe > .vid-it')].filter(x => x.offsetParent);
            return { h: Math.round($('vidBox').getBoundingClientRect().height), vis: vis.length, tot: document.querySelectorAll('#vidListe > .vid-it').length,
                     plie: !!(document.getElementById('vdPlie') && document.getElementById('vdPlie').offsetParent), resume: ($('vdResume') || {}).textContent || '',
                     cam: !!$('vidCamSerie').offsetParent, chev: vis.every(x => x.querySelector('[data-vd-chap]')) }; }""")
        print("     🎬 hauteur %d px · %d ligne(s) visibles sur %d" % (v["h"], v["vis"], v["tot"]))
        check("V. synthese courte (< 900 px) avec resume", v["h"] < 900 and v["resume"], v)
        check("V. chapitres sans narration replies en une ligne", v["plie"] and v["vis"] < v["tot"], v)
        check("V. reglages / camera ranges, « › » sur chaque ligne visible", not v["cam"] and v["chev"], v)
        check("V. aucun debordement", not pg.evaluate(DEB))
        pg.evaluate("() => document.querySelector('#vidListe [data-vd-tout]').click()"); pg.wait_for_timeout(400)
        n2 = pg.evaluate("() => [...document.querySelectorAll('#vidListe > .vid-it')].filter(x => x.offsetParent).length")
        check("V. « voir › » deplie toutes les lignes", n2 == v["tot"], (n2, v["tot"]))
        pg.evaluate("() => document.querySelector('#vidListe [data-vd-tout]').click()"); pg.wait_for_timeout(300)
        pg.evaluate("() => $('vdReg').click()"); pg.wait_for_timeout(300)
        check("V. « ⚙ Reglages et selection » montre camera et cases", pg.evaluate("() => !!$('vidCamSerie').offsetParent && !!document.querySelector('#vidListe [data-vid-coche]')"))
        pg.evaluate("() => $('vdReg').click()"); pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#vidListe .vid-it:not(.vd-plie) [data-vd-chap]').click()"); pg.wait_for_timeout(3500)
        r = pg.evaluate("() => ({ chap: !$('chapDetail').hidden, bloc: CL_OUVERT, vid: !$('vidBox').hidden })")
        check("V. « › » ouvre le chapitre, bloc 🎬 deplie, panneau ferme", r["chap"] and r["bloc"] == "vid" and not r["vid"], r)
        if w == 360:
            serie(pg, SERIE); pg.evaluate("() => $('btnVideos').click()"); pg.wait_for_timeout(3000)
            pg.query_selector("#vidBox").screenshot(path=os.path.join(OUT, "series_vid_360.png"))
        # ---- D
        serie(pg, CH.split("/")[0])
        pg.evaluate("() => $('btnDlgSerie').click()"); pg.wait_for_timeout(4000)
        d = pg.evaluate("""d => { const L = $('dlgsListe'), c = [...L.querySelectorAll('.dpl')].filter(x => x.offsetParent);
            return { h: Math.round($('dlgsBox').getBoundingClientRect().height), n: c.length, pl: [...L.querySelectorAll('.dls-pl:not(.plus)')].map(x => x.textContent),
                     plus: !!L.querySelector('[data-dlgs2=plage]'), autre: !!L.querySelector('[data-dlgs2=autre]'), filtres: [...document.querySelectorAll('#dlgsBox .dlgs-f')].some(x => x.offsetParent) }; }""", CH)
        print("     🎭 hauteur %d px · %d chapitre(s) · plages %s" % (d["h"], d["n"], d["pl"]))
        check("D. une ligne par chapitre avec dialogues, plages en pastilles", d["n"] >= 1 and len(d["pl"]) >= 1, d)
        check("D. « ＋ plage » et « ＋ autre chapitre », anciens filtres caches", d["plus"] and d["autre"] and not d["filtres"], d)
        check("D. aucun debordement", not pg.evaluate(DEB))
        if w == 360:
            pg.query_selector("#dlgsBox").screenshot(path=os.path.join(OUT, "series_dlg_360.png"))
        pg.evaluate("() => document.querySelector('#dlgsListe [data-dlgs2=plage]').click()"); pg.wait_for_timeout(5000)
        r = pg.evaluate("() => ({ chap: !$('chapDetail').hidden, bloc: CL_OUVERT, form: !!(document.querySelector('.dpl-nouv') && document.querySelector('.dpl-nouv').offsetParent), dlgs: !$('dlgsBox').hidden })")
        check("D. « ＋ plage » : chapitre ouvert, bloc 🎭, formulaire « Nouvelle plage » pret", r["chap"] and r["bloc"] == "dlg" and r["form"] and not r["dlgs"], r)
        # ---- VX + C (ecran ✏ du chapitre ouvert)
        pg.evaluate("() => { const b = document.querySelector('[data-dpl=annuler]'); if (b) b.click(); }"); pg.wait_for_timeout(500)
        pg.evaluate("() => $('dlgOuvrir').click()"); pg.wait_for_timeout(3000)
        vx = pg.evaluate("""() => dlgPersos().filter(p => !p.narrateur && /^(homme|femme)$/i.test(p.genre || '')).map(p => {
              const c = [...document.querySelectorAll('#dlgpCorps .dlgp-carte')].find(x => x.dataset.nom === p.nom); if (!c) return null;
              const seps = [...c.querySelectorAll('select[data-k=voix_el] option[disabled]')].map(o => o.textContent);
              const i1 = c.querySelector('.dlgp-coul i');
              return { nom: p.nom, g: p.genre.toLowerCase(), seps, first: i1 && i1.dataset.coul, fam: (dlgPalDe(p.genre) || []).includes(i1 && i1.dataset.coul) }; }).filter(Boolean)""")
        ok_vx = bool(vx) and all(any(("— " + ("femmes" if x["g"] == "femme" else "hommes")) in s for s in x["seps"][:3]) and
                                 [s for s in x["seps"] if "— hommes" in s or "— femmes" in s][0].endswith(("femmes ────" if x["g"] == "femme" else "hommes ────")) for x in vx)
        check("VX. voix groupees par genre, celui du personnage d'abord (%d perso.)" % len(vx), ok_vx, [(x["nom"], x["seps"][:3]) for x in vx][:2])
        check("C. pastilles : la famille du genre en tete", bool(vx) and all(x["fam"] for x in vx), [(x["nom"], x["first"]) for x in vx][:3])
        nb = len(dlg)
        pg.evaluate("() => $('dlgpRecol').click()"); pg.wait_for_timeout(600)
        check("C. « 🎨 Couleurs selon le genre » : demande confirmation ou dit que tout est deja bon", len(dlg) > nb or pg.evaluate("() => /déjà dans la famille/.test(document.body.innerText)"), dlg[nb:][:1])
        if w == 360:
            pg.screenshot(path=os.path.join(OUT, "series_dlgp_360.png"))
        check("0 erreur JS", not errs, errs[:2])
        check("0 ecriture envoyee (confirm refuse)", not ecrit, ecrit[:4])
        ctx.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
