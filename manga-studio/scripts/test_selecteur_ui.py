# -*- coding: utf-8 -*-
"""Banc v2.69.0 : SELECTEUR RAPIDE « Aller au … » (maquette_selecteur_chapitre_v1). APP REELLE, lecture seule (rien n'est ecrit).
Chapitres (bulle de la barre + glisser vers le haut), recherche n° exact / prefixe / absent (plus proche), filtres, cas « absent »,
video (grise sans video, versions), pages de la visionneuse, fermeture (✕, Echap, glisser vers le bas), 360 et 1280 px.
Usage : python test_selecteur_ui.py [port] [serie]      (defaut 8190 one-punch-man)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SERIE = sys.argv[2] if len(sys.argv) > 2 else "one-punch-man"
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""))
def glisser(pg, sel, dx, dy):
    pg.evaluate("""([sel, dx, dy]) => { const el = document.querySelector(sel), r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      const T = (a, b) => new Touch({ identifier: 1, target: el, clientX: a, clientY: b });
      el.dispatchEvent(new TouchEvent('touchstart', { touches: [T(x, y)], bubbles: true }));
      el.dispatchEvent(new TouchEvent('touchmove', { touches: [T(x + dx / 2, y + dy / 2)], bubbles: true }));
      el.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [T(x + dx, y + dy)], bubbles: true })); }""", [sel, dx, dy])

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (360, 1280):
        print("== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": 820}, is_mobile=w < 500, has_touch=True); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4000)
        i = pg.evaluate("(s) => { const l = CHAPS.map((c, i) => ({ c, i })).filter(x => x.c.dir.startsWith(s + '/')).sort((a, b) => chapNum(a.c) - chapNum(b.c)); return l[Math.min(3, l.length - 1)].i; }", SERIE)
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(2500); pg.evaluate("() => { scrollTo(0, 600); nfMaj(); }"); pg.wait_for_timeout(900)
        # 1) ouvrir par la bulle
        pg.evaluate("() => $('nfInfo').click()"); pg.wait_for_timeout(500)
        st = pg.evaluate("() => [!$('selFeuille').hidden, $('selTitre').textContent, document.querySelectorAll('#selGrille .sel-c').length, (document.querySelector('#selGrille .cour') || {}).textContent]")
        check("bulle → feuille ouverte, chapitre courant en vert", st[0] and st[2] > 1 and st[3], st)
        box = pg.evaluate("() => { const r = $('selFeuille').getBoundingClientRect(); return [r.left >= -1, r.right <= innerWidth + 1, r.bottom <= innerHeight + 1, document.documentElement.scrollWidth <= innerWidth]; }")
        check("feuille dans l'écran, pas de débordement", all(box), box)
        # 2) recherche : prefixe filtre, n° exact = y aller
        pg.fill("#selNum", "1"); pg.wait_for_timeout(200)
        lab = pg.evaluate("() => [...document.querySelectorAll('#selGrille .sel-c')].map(b => b.firstChild.textContent)")
        check("taper « 1 » : seulement des numéros qui commencent par 1", lab and all(x.startswith("1") for x in lab), lab[:8])
        pg.fill("#selNum", "99999"); pg.keyboard.press("Enter"); pg.wait_for_timeout(300)
        check("n° absent : « absent — le plus proche »", "absent" in pg.evaluate("() => $('selInfo').textContent"), pg.evaluate("() => $('selInfo').textContent"))
        cible = pg.evaluate("(s) => { const l = CHAPS.filter(c => c.dir.startsWith(s + '/')).sort((a, b) => chapNum(a) - chapNum(b)); return l[0]; }", SERIE)
        pg.fill("#selNum", str(cible["chapter"])); pg.keyboard.press("Enter"); pg.wait_for_timeout(2000)
        check("n° exact + Entrée → chapitre ouvert, feuille fermée", pg.evaluate("() => [CHAP_OPEN, $('selFeuille').hidden]") == [cible["dir"], True], pg.evaluate("() => CHAP_OPEN"))
        # 3) glisser la barre vers le haut ; filtres ; Echap
        pg.evaluate("() => { scrollTo(0, 600); nfMaj(); }"); pg.wait_for_timeout(900)
        glisser(pg, "#navFlot", 0, -120); pg.wait_for_timeout(400)
        check("glisser la barre vers le haut → feuille ouverte", pg.evaluate("() => !$('selFeuille').hidden"))
        n0 = pg.evaluate("() => document.querySelectorAll('#selGrille .sel-c').length")
        pg.evaluate("() => document.querySelector('#selFiltres [data-f=vid]').click()"); pg.wait_for_timeout(200)
        n1 = pg.evaluate("() => [...document.querySelectorAll('#selGrille .sel-c')].map(b => b.textContent)")
        check("filtre 🎬 vidéo : moins de cases, toutes avec 🎬", 0 < len(n1) < n0 and all("🎬" in x for x in n1), [n0, len(n1)])
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        check("Échap ferme", pg.evaluate("() => $('selFeuille').hidden"))
        # 4) video : lecteur ouvert -> contexte video, chapitres sans video grises
        pg.evaluate("async (s) => { await vidCharger(s); const o = VIDS.chapitres.map((c, i) => ({ c, i })).filter(x => (x.c.videos || []).length); vidOuvrir(o[0].i); vEl().pause(); }", SERIE)
        pg.wait_for_timeout(1500)
        pg.evaluate("() => $('vidLecTitre').click()"); pg.wait_for_timeout(400)
        v = pg.evaluate("() => [$('selTitre').textContent, document.querySelectorAll('#selGrille .sel-c.off').length, document.querySelectorAll('#selGrille .sel-c:not(.off)').length]")
        check("lecteur vidéo : titre → sélecteur vidéo, sans-vidéo grisés", v[0].startswith("Vidéo") and v[2] >= 1, v)
        if v[1]:
            pg.evaluate("() => document.querySelector('#selGrille .sel-c.off').click()"); pg.wait_for_timeout(200)
            check("case grisée : raison affichée, rien ne s'ouvre", "⚠" in pg.evaluate("() => $('selInfo').textContent") and not pg.evaluate("() => $('selFeuille').hidden"))
        t0 = pg.evaluate("() => $('vidLecTitre').textContent")
        pg.evaluate("() => { const l = [...document.querySelectorAll('#selGrille .sel-c:not(.off):not(.cour)')]; if (l.length) l[0].click(); }"); pg.wait_for_timeout(1500)
        info = pg.evaluate("() => $('selInfo').textContent")
        if "version" in info:
            pg.evaluate("() => document.querySelector('#selInfo [data-ver]').click()"); pg.wait_for_timeout(1500)
        check("choisir une autre vidéo → elle se lance", pg.evaluate("() => $('vidLecTitre').textContent") != t0 and pg.evaluate("() => $('selFeuille').hidden"), pg.evaluate("() => $('vidLecTitre').textContent"))
        pg.evaluate("() => { vEl().pause(); $('vidLecFermer').click(); }")
        # 5) glisser la feuille vers le bas = fermer
        pg.evaluate("() => selOuvrir(selCtxChapitres(serieDe(CHAP_OPEN)))"); pg.wait_for_timeout(300)
        glisser(pg, ".sel-tete", 0, 140); pg.wait_for_timeout(300)
        check("glisser la feuille vers le bas ferme", pg.evaluate("() => $('selFeuille').hidden"))
        check("aucune erreur JS", not errs, errs[:3])
        pg.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
