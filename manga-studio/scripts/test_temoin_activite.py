# -*- coding: utf-8 -*-
"""Aucun bouton silencieux (demande Quang, 27/07).

« Il me faut un temoin d'activite visuel pour savoir que c'est en cours et quand
c'est fini. Il ne faut pas un bouton silencieux, d'ailleurs partout ou c'est
necessaire dans l'application. »

Le banc verifie les TROIS moments, sur une VRAIE generation (pas un stub : une
generation dure 10 a 20 s, c'est justement la duree qui rend le temoin necessaire) :

  1. pendant  -> le temoin est visible et nomme ce qui se passe ;
  2. apres    -> il annonce la fin, puis s'efface tout seul ;
  3. en cas de REFUS -> le motif reste affiche DANS la case.

Le point 3 vient d'un cas reel : Quang a clique « Générer » sur une case sans
prompt. L'app refusait par un toast de 2,6 s, il ne l'a pas vu, et a conclu que
le bouton ne faisait rien. Un refus doit rester lisible.

Le point 2 compte autant que le point 1 : un temoin bloque sur « en cours… »
serait pire que pas de temoin -- il ferait croire a un travail qui n'a pas lieu.

Usage:
    python test_temoin_activite.py [--headed]
"""
import argparse
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_temoin_%d" % os.getpid()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, res = [], {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom});
            const p = await api('/manga/pages', {project_id: proj.id, title:'t', chapter:1});
            const a = await api('/manga/panels',
                {page_id: p.id, kind:'dialogue', prompt:'', idx:0});
            const b = await api('/manga/panels',
                {page_id: p.id, kind:'dialogue', prompt:'close-up portrait, neutral', idx:1});
            S.proj = {id: proj.id, slug: nom};
            S.page = {id: p.id, layout:{cols:2}};
            S.panels = [
              {id:a.id, page_id:p.id, kind:'dialogue', prompt:'', bubbles:[], recipe:{}},
              {id:b.id, page_id:p.id, kind:'dialogue',
               prompt:'close-up portrait, neutral', bubbles:[], recipe:{}}];
            renderPlate();
        }""", NOM)
        pg.wait_for_timeout(800)

        # --- 3. le REFUS reste affiche -----------------------------------
        pg.click(".panel:nth-child(1) [data-act=gen]")
        pg.wait_for_timeout(1000)
        res["refus"] = pg.evaluate("""() => {
            const e = document.querySelector('.panel:nth-child(1) .refus');
            return e && !e.hidden ? e.textContent.trim() : '';
        }""")
        pg.wait_for_timeout(3200)   # au-dela de la duree d'un toast
        res["refus_apres"] = pg.evaluate("""() => {
            const e = document.querySelector('.panel:nth-child(1) .refus');
            return e && !e.hidden ? e.textContent.trim() : '';
        }""")
        print("refus affiche          : %r" % res["refus"][:60])
        print("refus encore la a 4 s  : %s" % bool(res["refus_apres"]))

        # --- 1. PENDANT une vraie generation ------------------------------
        pg.click(".panel:nth-child(2) [data-act=gen]")
        vu, texte = False, ""
        t0 = time.time()
        while time.time() - t0 < 12:
            e = pg.evaluate("""() => { const b = document.getElementById('busy');
                return (b && !b.hidden && !b.classList.contains('done'))
                       ? document.getElementById('busyTxt').textContent : ''; }""")
            if e:
                vu, texte = True, e
                break
            pg.wait_for_timeout(200)
        res["pendant"] = vu
        print("temoin PENDANT         : %s %r" % (vu, texte))

        # --- 2. APRES : message de fin, puis effacement --------------------
        fin = ""
        t0 = time.time()
        while time.time() - t0 < 120:
            fin = pg.evaluate("""() => { const b = document.getElementById('busy');
                return (b && !b.hidden && b.classList.contains('done'))
                       ? document.getElementById('busyTxt').textContent : ''; }""")
            if fin:
                break
            pg.wait_for_timeout(500)
        res["fin"] = fin
        print("temoin de FIN          : %r" % fin)
        pg.wait_for_timeout(3200)
        res["efface"] = pg.evaluate(
            "() => document.getElementById('busy').hidden")
        print("temoin efface ensuite  : %s" % res["efface"])
        res["image"] = pg.evaluate(
            "() => !!document.querySelector('.panel:nth-child(2) .img img')")
        print("image reellement produite : %s" % res["image"])

        pg.evaluate("""async () => { const l = await api('/manga/projects');
            for (const p of (l.items || []))
                if (p.name && p.name.startsWith('_temoin_'))
                    await api('/manga/projects', {delete: p.id}); }""")
        br.close()

    print("erreurs JS : %d" % len(erreurs))
    vert = (res["refus"] and res["refus_apres"] and res["pendant"]
            and res["fin"] and res["efface"] and res["image"] and not erreurs)
    print("\nVERDICT : %s" % ("VERT — l'app dit qu'elle travaille, dit quand c'est fini,"
                              " et explique ses refus."
                              if vert else "ROUGE — voir les lignes ci-dessus."))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
