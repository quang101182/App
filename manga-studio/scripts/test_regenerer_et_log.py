# -*- coding: utf-8 -*-
"""Regenerer DEUX FOIS la meme case, et un journal lisible depuis le PC.

Incident du 27/07, diagnostique grace au journal que Quang a copie-colle :

    06:28:57  [case ...] file d'attente
    06:28:59  [case ...] OK 2s              <- 2 s : ComfyUI a servi son CACHE
    06:28:59  /manga/harvest : source introuvable

La premiere generation DEPLACE l'image hors de ComfyUI (verrou d'isolation avec
Generate Studio). A la seconde, le graphe etant identique, ComfyUI ne recalcule
rien et renvoie le meme nom de fichier -- qui n'existe plus la-bas. L'app avait
donc un bug garanti des qu'on regenerait une case.

Ce banc rejoue exactement ce scenario, et verifie aussi que le journal arrive
sur le PC tout seul : sans lui, ce diagnostic dependait d'un copier-coller.

Usage:
    python test_regenerer_et_log.py [--headed]
"""
import argparse
import io
import json
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
# ⚠ Depuis la v1.11.1, le journal est ecrit PAR APPAREIL (`-pc` / `-mobile`) :
# sans suffixe, le telephone de Quang et les bancs du PC s'ecrasaient l'un
# l'autre. Ce banc visait encore l'ancien nom et declarait « journal ABSENT »
# alors qu'il arrivait bien -- un rouge qui n'accusait que le banc (27/07).
# Playwright n'est pas un mobile pour l'app (userAgent Edge desktop) => "-pc".
LOG_PC = r"C:\Users\quang\Documents\ComfyUI\logs\log-manga-live-pc.json"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_regen_%d" % os.getpid()


def genere(pg, timeout=180):
    """Clique Generer et attend le RESULTAT : un nouveau fichier range.

    Premiere version : elle guettait le temoin « termine ». Mauvais critere --
    ce bandeau s'efface tout seul au bout de 2,6 s, et une generation servie
    depuis le cache dure 2 s : le banc pouvait le manquer entre deux sondages
    et declarer un echec la ou le journal montrait une reussite.
    Le critere qui compte est le fichier, pas le message qui l'annonce.
    """
    avant = pg.evaluate("() => S.panels[0].file || ''")
    pg.click(".panel:nth-child(1) [data-act=gen]")
    t0 = time.time()
    while time.time() - t0 < timeout:
        etat = pg.evaluate("""(avant) => {
            const r = document.querySelector('.panel:nth-child(1) .refus');
            if (r && !r.hidden) return 'refus:' + r.textContent.trim();
            const f = S.panels[0].file || '';
            return (f && f !== avant) ? 'fini:' + f : '';
        }""", avant)
        if etat:
            return time.time() - t0, etat
        pg.wait_for_timeout(300)
    return time.time() - t0, "timeout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    if os.path.isfile(LOG_PC):
        os.remove(LOG_PC)          # on veut voir le journal de CE run
    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom});
            const p = await api('/manga/pages', {project_id: proj.id, title:'r', chapter:1});
            const a = await api('/manga/panels', {page_id: p.id, kind:'dialogue',
                prompt:'close-up portrait, neutral expression', idx:0});
            S.proj = {id: proj.id, slug: nom, name: nom};
            S.projects = [S.proj];
            S.page = {id: p.id, projectId: proj.id, layout:{cols:2}};
            S.panels = [{id:a.id, page_id:p.id, kind:'dialogue',
                         prompt:'close-up portrait, neutral expression',
                         bubbles:[], recipe:{seed: 424242}}];
            renderPlate();
        }""", NOM)
        pg.wait_for_timeout(800)
        # Un seed FIXE : c'est la condition qui declenchait le cache de ComfyUI.
        pg.fill(".panel:nth-child(1) [data-seed]", "424242")

        d1, e1 = genere(pg)
        print("1re generation : %5.1f s | %s" % (d1, e1[:70]))
        fichier1 = pg.evaluate("() => S.panels[0].file || ''")
        print("  fichier range : %s" % fichier1)

        pg.wait_for_timeout(1500)
        d2, e2 = genere(pg)
        print("2e generation  : %5.1f s | %s" % (d2, e2[:70]))
        fichier2 = pg.evaluate("() => S.panels[0].file || ''")
        print("  fichier range : %s" % fichier2)

        pg.evaluate("() => MangaLog.envoyer()")
        pg.wait_for_timeout(2500)
        pg.evaluate("""async () => { const l = await api('/manga/projects');
            for (const p of (l.items || []))
                if (p.name && p.name.startsWith('_regen_'))
                    await api('/manga/projects', {delete: p.id}); }""")
        br.close()

    ok1 = e1.startswith("fini:")
    ok2 = e2.startswith("fini:")
    print("\n1re generation reussie : %s" % ok1)
    print("2e generation reussie  : %s   <- c'est CE cas qui echouait" % ok2)
    print("les deux fichiers different : %s" % (fichier1 != fichier2))

    # Le journal doit etre arrive sur le PC, tout seul.
    print("\n=== journal ecrit sur le PC ? ===")
    jrn = None
    if os.path.isfile(LOG_PC):
        brut = json.load(open(LOG_PC, encoding="utf-8"))
        ctx = brut[0] if brut and brut[0].get("type") == "contexte" else {}
        ev = [x for x in brut if x.get("type") != "contexte"]
        jrn = {"contexte": ctx, "evenements": ev}
        print("  %s" % LOG_PC)
        print("  version %s · projet %s · %d evenement(s)"
              % (ctx.get("version"), ctx.get("projet"), len(ev)))
        print("  contexte present (appareil, ecran, cases) : %s"
              % all(k in ctx for k in ("appareil", "ecran", "cases")))
        for l in ev[-3:]:
            print("   %s %s" % (l.get("t", "?")[:12], str(l.get("msg"))[:70]))
    else:
        print("  ABSENT — le journal n'est pas arrive.")

    print("\nerreurs JS : %d" % len(erreurs))
    vert = (ok1 and ok2 and fichier1 != fichier2 and jrn is not None
            and len(jrn.get("evenements", [])) > 3 and not erreurs)
    print("\nVERDICT : %s" % ("VERT — on peut regenerer une case, et le journal"
                              " arrive seul sur le PC."
                              if vert else "ROUGE — voir les lignes ci-dessus."))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
