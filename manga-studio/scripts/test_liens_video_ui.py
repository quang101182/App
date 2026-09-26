# -*- coding: utf-8 -*-
"""Banc v2.79.0 (maquette_liens_video_v1, B) : fiche du chapitre -- « → 🎬 » sur Narration / Traduction / Musique, ingredients
de la video (🎙 / 🌐 FR|VO / 🎵 N), UNE seule lueur sur l'etape utile suivante. APP REELLE, lecture seule (tout POST bloque).
Chapitres choisis d'apres les donnees : un NON narre, un narre en VO non traduit (s'il existe), un narre deja dans la langue cible.
1280 et 360 px (pastilles visibles, chevron dans le cadre, pas de debordement) + « reduire les animations ».
Usage : python test_liens_video_ui.py [port] [--mutation]   (--mutation : app v2.78.0 servie -> doit sortir ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:220] if detail else ""), flush=True)
ETAT = """() => { const rows = [...document.querySelectorAll('#chapDetail .cl-tete')];
  const suiv = [...document.querySelectorAll('#chapDetail .cl-suiv')];
  const v = document.querySelector('#chapDetail .cl-tete[data-cl=vid]');
  return { ordre: rows.map(h => h.dataset.cl), vers: rows.map(h => !!h.querySelector('.cl-vers')),
    versVisibles: rows.map(h => { const x = h.querySelector('.cl-vers'); return !!x && x.checkVisibility(); }),
    ing: v ? [...v.querySelectorAll('.cl-ing')].map(x => [x.textContent, x.className.replace('cl-ing', '').trim()]) : [],
    ingVisibles: v ? [...v.querySelectorAll('.cl-ing')].every(x => x.checkVisibility()) : false,
    suiv: suiv.map(b => b.closest('.cl-tete').dataset.cl), anim: suiv.length ? getComputedStyle(suiv[0]).animationName : '',
    narr: document.querySelectorAll('#narrRuns [data-ecoute]').length, tradOk: typeof clTradOk === 'function' ? clTradOk() : null,
    video: !!$('chapVid').querySelector('[data-vid-voir]'),
    chevDedans: rows.every(h => { const c = h.querySelector('.cl-chev').getBoundingClientRect(), b = h.closest('.cl-box').getBoundingClientRect(); return c.right <= b.right + 1; }),
    narrEtatL: Math.round(document.querySelector('#chapDetail .cl-tete[data-cl=narr] .cl-etat').getBoundingClientRect().width),
    ingSous: (() => { if (!v) return false; const i = v.querySelector('.cl-est').getBoundingClientRect(), t = v.querySelector('.cl-etat').getBoundingClientRect();
                      return i.top >= t.bottom - 1 && t.width > 120; })(),
    deborde: document.documentElement.scrollWidth > innerWidth }; }"""

def ouvrir(pg, d):
    pg.evaluate("async (d) => { await openChap(CHAPS.findIndex(c => c.dir === d)); }", d); pg.wait_for_timeout(4500)
    pg.evaluate("() => clMaj()"); pg.wait_for_timeout(300)
    return pg.evaluate(ETAT)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h, reduit in ((1280, 900, False), (360, 780, False), (360, 780, True)):
        print("== %d px%s" % (w, " · réduire les animations" if reduit else ""))
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500, reduced_motion="reduce" if reduit else "no-preference")
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/*", lambda r: r.abort() if r.request.method == "POST" else r.continue_())    # lecture seule
        if MUT:
            pg.route("**/manga", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8",
                     body=open(os.path.join(ICI, "..", "manga_studio.html.bak-20260926-v2790"), encoding="utf-8").read()))   # = v2.78.0
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4500)
        pg.evaluate("async () => { for (let i = 0; i < 30 && !RESUME; i++) await new Promise(r => setTimeout(r, 300)); }")
        choix = pg.evaluate("""() => { const R = RESUME.chapitres, cible = $('tradLangue').value || 'fr', L = Object.entries(R);
            const pris = f => (L.find(([d, r]) => CHAPS.some(c => c.dir === d) && f(r)) || [])[0] || null;
            return { non_narre: pris(r => !r.narr), vo: pris(r => r.narr && r.langue && r.langue !== cible && !(r.trad || []).includes(cible)),
                     cible_ok: pris(r => r.narr && (r.langue === cible || (r.trad || []).includes(cible))) }; }""")
        print("  chapitres :", choix)
        # 1) NON narre : lueur sur « Narrer », 🎙 « à faire »
        if choix["non_narre"]:
            e = ouvrir(pg, choix["non_narre"])
            check("ordre narr → trad → mus → vid", e["ordre"] == ["narr", "trad", "mus", "vid"], e["ordre"])
            check("« → 🎬 » sur Narration, Traduction, Musique (pas sur Vidéo)", e["vers"] == [True, True, True, False], e["vers"])
            check("« → 🎬 » visibles : Traduction + Musique partout, Narration sur PC seulement",
                  e["versVisibles"][1:3] == [True, True] and e["versVisibles"][0] == (w > 480), e["versVisibles"])
            if w <= 480: check("téléphone : ingrédients de la Vidéo SOUS l'état (2e ligne), état lisible", e["ingSous"], e["ingSous"])
            check("Vidéo : 3 ingrédients visibles, 🎙 « à faire »", len(e["ing"]) == 3 and e["ingVisibles"] and "à faire" in e["ing"][0][0], e["ing"])
            check("non narré : UNE lueur, sur la Narration", e["suiv"] == ["narr"], e["suiv"])
            check("lueur animée" + (" : COUPÉE (réduire les animations)" if reduit else ""), (e["anim"] == "none") if reduit else (e["anim"] == "clLueur"), e["anim"])
            check("chevrons dans leur cadre, page sans débordement", e["chevDedans"] and not e["deborde"], [e["chevDedans"], e["deborde"]])
        # 2) narre, VO non traduit : lueur sur « Traduire », 🌐 « VO » pointille
        if choix["vo"]:
            e = ouvrir(pg, choix["vo"])
            check("narré en VO non traduit : 🌐 « VO » en pointillé (facultatif)", "VO" in e["ing"][1][0] and "opt" in e["ing"][1][1], e["ing"])
            check("narré en VO non traduit : la lueur passe sur « Traduire »", e["suiv"] == ["trad"], e["suiv"])
            check("état de la Narration pas plus étroit qu'en v2.78.0 (66 px mesurés à 360)", e["narrEtatL"] >= (66 if w <= 480 else 60), e["narrEtatL"])
        else:
            print("  (aucun chapitre narré en VO non traduit dans la bibliothèque : cas non exerçable ici)")
        # 3) narre, deja dans la langue cible : 🌐 vert ; lueur sur la video seulement si elle n'existe pas
        if choix["cible_ok"]:
            e = ouvrir(pg, choix["cible_ok"])
            check("langue cible atteinte : 🎙 et 🌐 en vert", e["ing"][0][1] == "ok" and e["ing"][1][1] == "ok", e["ing"])
            attendu = [] if e["video"] else ["vid"]
            check("lueur : %s" % ("aucune (vidéo déjà faite)" if e["video"] else "sur « Faire la vidéo »"), e["suiv"] == attendu, e["suiv"])
            check("jamais plus d'UNE lueur", len(e["suiv"]) <= 1, e["suiv"])
        check("aucune erreur JS", not errs, errs[:3])
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
