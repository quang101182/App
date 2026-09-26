# -*- coding: utf-8 -*-
"""Banc v2.68.0 (+ v2.70.0 : barre permanente hors plein ecran) : LECTEUR VIDEO (maquette_lecteur_video_v1, validee 26/09 11h05, A-H). APP REELLE, vraies videos de la serie donnee.
Lecture seule : navigateur pilote -> la position n'est PAS envoyee au serveur (navigator.webdriver) ; rien n'est ecrit.
Usage : python test_lecteur_video_ui.py [port] [serie]      (defaut 8190 one-punch-man)
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
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:220] if detail else ""))

def clic(pg, sel):
    """Comme un utilisateur : si la barre s'est effacee (F), un toucher la ramene d'abord."""
    pg.evaluate("() => vidReveil()"); pg.wait_for_timeout(150); pg.click(sel)

def glisser(pg, sel, dx):
    pg.evaluate("""([sel, dx]) => { const el = document.querySelector(sel), r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      const T = (x2) => new Touch({ identifier: 1, target: el, clientX: x2, clientY: y });
      el.dispatchEvent(new TouchEvent('touchstart', { touches: [T(x)], bubbles: true }));
      for (let k = 1; k <= 6; k++) el.dispatchEvent(new TouchEvent('touchmove', { touches: [T(x + dx * k / 6)], bubbles: true }));
      el.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [T(x + dx)], bubbles: true })); }""", [sel, dx])

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4000)
    i = pg.evaluate("""async (serie) => { await vidCharger(serie);
        const o = VIDS.chapitres.map((c, i) => ({ c, i })).filter(x => (x.c.videos || []).length).sort((a, b) => vidNum(a.c) - vidNum(b.c));
        return o.length >= 3 ? o[1].i : -1; }""", SERIE)
    check("série avec ≥ 3 vidéos chargée", i >= 0, i)
    pg.evaluate("(i) => vidOuvrir(i)", i); pg.wait_for_timeout(2500)
    st = pg.evaluate("""() => { const e = vEl(); return { controls: e.controls, t: e.currentTime, paused: e.paused, pp: $('vidPP').textContent,
        prev: !$('vidLecPrev').hidden, next: !$('vidLecNext').hidden, titre: $('vidLecTitre').textContent }; }""")
    check("A : plus de commandes natives", st["controls"] is False, st)
    check("A : ⏮ ch. et ch. ⏭ visibles (chapitre du milieu)", st["prev"] and st["next"], st)
    check("lecture lancée (le temps avance, ⏸ affiché)", not st["paused"] and st["t"] > 0 and st["pp"] == "⏸", st)
    # largeurs : rien ne deborde, la barre tient
    larg = {}
    for w in (360, 476, 704, 933, 1280):
        pg.set_viewport_size({"width": w, "height": 780}); pg.wait_for_timeout(250)
        larg[w] = pg.evaluate("""() => { const r = $('vidBar').getBoundingClientRect(), bas = $('vidBas').getBoundingClientRect();
            return [document.documentElement.scrollWidth <= innerWidth, r.right <= innerWidth + 1 && r.left >= -1, bas.bottom <= innerHeight + 1,
                    [...document.querySelectorAll('#vidBar > .btn')].filter(x => !x.hidden).every(x => x.getBoundingClientRect().height >= 38)]; }""")
    check("aucun débordement, barre dans l'écran, boutons ≥ 38 px (360 → 1280)", all(all(v) for v in larg.values()), larg)
    pg.set_viewport_size({"width": 360, "height": 780})
    # A/C : ±10 s
    t0 = pg.evaluate("() => vEl().currentTime"); clic(pg, "#vidP10"); pg.wait_for_timeout(200); t1 = pg.evaluate("() => vEl().currentTime")
    check("+10 s", 9 <= t1 - t0 <= 11.5, [t0, t1])
    clic(pg, "#vidM10"); pg.wait_for_timeout(200); t2 = pg.evaluate("() => vEl().currentTime")
    check("−10 s", 8.5 <= t1 - t2 <= 11, [t1, t2])
    # ⏯
    clic(pg, "#vidPP"); pg.wait_for_timeout(300)
    check("⏯ : pause (▶ affiché)", pg.evaluate("() => [vEl().paused, $('vidPP').textContent]") == [True, "▶"])
    clic(pg, "#vidPP"); pg.wait_for_timeout(300)
    check("⏯ : reprise", pg.evaluate("() => !vEl().paused"))
    # F (v2.70.0, Quang 11h48) : hors plein ecran la barre RESTE ; elle ne s'efface qu'en plein ecran, un toucher la ramene
    pg.wait_for_timeout(4000)
    check("F : hors plein écran, barre TOUJOURS affichée après 4 s de lecture", pg.evaluate("() => [!$('vidLecteur').classList.contains('calme'), !vEl().paused]") == [True, True]
          and pg.is_visible("#vidPP") and pg.evaluate("() => getComputedStyle($('vidBas')).opacity") == "1")
    pg.click("#vidMenu .plus"); pg.wait_for_timeout(200); pg.click("#vidPlein"); pg.wait_for_timeout(500)
    check("F : ⋯ → Plein écran = le lecteur en plein écran", pg.evaluate("() => document.fullscreenElement === $('vidLecteur')"))
    pg.evaluate("() => vEl().play()"); pg.wait_for_timeout(3600)
    check("F : en plein écran, barre effacée après 3 s de lecture", pg.evaluate("() => $('vidLecteur').classList.contains('calme')"))
    pg.evaluate("() => { const z = $('vidZone').getBoundingClientRect(); $('vidZone').dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: z.left + z.width / 2, clientY: z.top + z.height / 2 })); }")
    pg.wait_for_timeout(500)
    check("F : un toucher ramène la barre, la lecture continue", pg.evaluate("() => [!$('vidLecteur').classList.contains('calme'), !vEl().paused]") == [True, True])
    pg.evaluate("() => document.exitFullscreen()"); pg.wait_for_timeout(4000)
    check("F : sortie du plein écran → barre rendue et qui RESTE (4 s)", pg.evaluate("() => [document.fullscreenElement, $('vidLecteur').classList.contains('calme'), !vEl().paused]") == [None, False, True])
    # B : toucher simple (barre visible) = pause ; double toucher a droite = +10
    pg.evaluate("() => { const z = $('vidZone').getBoundingClientRect(); $('vidZone').dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: z.left + z.width / 2, clientY: z.top + z.height / 2 })); }")
    pg.wait_for_timeout(500)
    check("B : toucher l'image = pause", pg.evaluate("() => vEl().paused"))
    t3 = pg.evaluate("() => vEl().currentTime")
    pg.evaluate("""() => { const z = $('vidZone').getBoundingClientRect(), o = { bubbles: true, clientX: z.left + z.width * 0.85, clientY: z.top + z.height / 2 };
        $('vidZone').dispatchEvent(new MouseEvent('click', o)); setTimeout(() => $('vidZone').dispatchEvent(new MouseEvent('click', o)), 120); }""")
    pg.wait_for_timeout(700); t4 = pg.evaluate("() => vEl().currentTime")
    check("B : deux touches à droite = +10 s (et pas de ⏯)", 9 <= t4 - t3 <= 11 and pg.evaluate("() => vEl().paused"), [t3, t4])
    # clavier
    pg.keyboard.press(" "); pg.wait_for_timeout(300)
    check("clavier : Espace = ⏯", pg.evaluate("() => !vEl().paused"))
    t5 = pg.evaluate("() => vEl().currentTime"); pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(200)
    check("clavier : ← = −10 s", 8.5 <= t5 - pg.evaluate("() => vEl().currentTime") <= 11)
    # G : vitesse
    pg.evaluate("() => document.querySelector('#vidMenu [data-vit=\"1.5\"]').click()"); pg.wait_for_timeout(200)
    check("G : vitesse 1,5×", pg.evaluate("() => vEl().playbackRate") == 1.5)
    # A : glisser la barre vers la droite = chapitre suivant
    avant = pg.evaluate("() => $('vidLecTitre').textContent")
    pg.evaluate("() => vidReveil()"); glisser(pg, "#vidBar", 140); pg.wait_for_timeout(1800)
    apres = pg.evaluate("() => $('vidLecTitre').textContent")
    check("A : glisser la barre → chapitre suivant", apres != avant and "ch." in apres, [avant, apres])
    check("G : la vitesse choisie reste au chapitre suivant", pg.evaluate("() => vEl().playbackRate") == 1.5)
    pg.evaluate("() => vidReveil()"); glisser(pg, "#vidBar", -140); pg.wait_for_timeout(1800)
    check("A : glisser vers la gauche → retour au chapitre précédent", pg.evaluate("() => $('vidLecTitre').textContent") == avant)
    # D : reprise a la position gardee
    # fermer (la position reelle est gardee), puis simuler une position de 42 s venue d'un autre appareil, et rouvrir
    clic(pg, "#vidLecFermer"); pg.wait_for_timeout(300)
    pg.evaluate("() => { const f = VID.cour.fichier; BIB.videos_pos = BIB.videos_pos || {}; BIB.videos_pos[f] = { pos: 42, duree: 999, t: 1 }; }")
    pg.evaluate("() => vidOuvrir(VID_COUR)"); pg.wait_for_timeout(2500)
    tr = pg.evaluate("() => vEl().currentTime")
    check("D : reprise à la position gardée (42 s)", 42 <= tr <= 46, tr)
    # E : fin -> compte a rebours vers le suivant, Annuler
    pg.evaluate("() => { const e = vEl(); e.currentTime = e.duration - 0.5; }"); pg.wait_for_timeout(2500)
    su = pg.evaluate("() => [!$('vidSuite').hidden, $('vidSuiteTxt').textContent, $('vidCpt').textContent]")
    check("E : fin de vidéo → « ch. N dans 5 s »", su[0] and "dans" in su[1], su)
    clic(pg, "#vidSuiteNon"); pg.wait_for_timeout(1500)
    check("E : Annuler = on reste, compte à rebours arrêté", pg.evaluate("() => $('vidSuite').hidden") and pg.evaluate("() => $('vidLecTitre').textContent") == avant)
    # fermeture
    clic(pg, "#vidLecFermer"); pg.wait_for_timeout(300)
    check("← Fermer : lecteur fermé, vidéo arrêtée", pg.evaluate("() => [$('vidLecteur').hidden, vEl().paused]") == [True, True])
    check("aucune erreur JS", not errs, errs[:3])
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
