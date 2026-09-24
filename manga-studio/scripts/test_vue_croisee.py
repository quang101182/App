# -*- coding: utf-8 -*-
"""Banc S5 (compartiment, 24/09/2026) : chaque application voit que l'autre travaille -- la principale SANS aucun titre.

Un traitement FACTICE est pose dans chaque application (une « narration » dont le progress.json porte le PID d'un
processus qui dort : le serveur la voit « en cours », rien n'est genere, rien n'est paye). Verifie :
1. serveur : la principale recoit l'activite de la secondaire ANONYME (type, etape, avancement ; ni titre, ni dossier) ;
   la secondaire recoit celle de la principale avec son titre ;
2. app principale (Edge sans fenetre, 1280 et 360 px) : « 🔒 1 traitement en cours », et le titre de la secondaire
   n'apparait NULLE PART dans la page ;
3. question avant un lancement lourd : refuser -> la demande n'est jamais envoyee ; accepter -> elle part ;
4. jauge VRAM : un moteur declare par la secondaire compte dans la jauge de la principale.
Tout ce que le banc cree est efface a la fin (dossiers, declaration GPU, processus).
"""
import json, os, shutil, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__)); MS = os.path.dirname(HERE)
NORMAL = os.path.join(MS, "sources"); PRIVE = os.path.expanduser(r"~\Documents\MangaStudio-donnees\prive")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SECRET = "ZZTITREBANCSECRET"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""), flush=True)


def api(port, chemin):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, chemin), headers={"Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(r, timeout=20))


def poser(racine, slug, titre, pid):
    d = os.path.join(racine, slug, "ch_1")
    os.makedirs(os.path.join(d, "narration", "banc"), exist_ok=True)
    json.dump({"title": titre, "chapter": "1", "pages": []}, open(os.path.join(d, "manifest.json"), "w", encoding="utf-8"))
    json.dump({"pid": pid, "t": time.time(), "etape": "voix", "fait": 3, "total": 12},
              open(os.path.join(d, "narration", "banc", "progress.json"), "w", encoding="utf-8"))
    return os.path.join(racine, slug)


dormeur = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(240)"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
crees = [poser(PRIVE, "zz-banc-s5", SECRET, dormeur.pid), poser(NORMAL, "zz-banc-s5-principale", "Titre principal banc", dormeur.pid)]
gpu = os.path.join(PRIVE, "_gpu"); os.makedirs(gpu, exist_ok=True); fgpu = os.path.join(gpu, "%d.json" % dormeur.pid)
try:
    print("1. serveur")
    a = api(8190, "/manga/activite_autre")
    brut = json.dumps(a, ensure_ascii=False)
    check("principale : l'autre travaille (1 traitement vu)", a.get("joignable") and len([x for x in a["items"] if x.get("type") == "narration"]) >= 1, a)
    check("principale : version ANONYME (type/etape/avancement seulement)", a.get("anonyme") and all(set(x) <= {"type", "etape", "fait", "total"} for x in a["items"]), a["items"])
    check("principale : ni titre ni dossier de la secondaire", SECRET not in brut and "zz-banc-s5" not in brut, brut[:200])
    b = api(8192, "/manga/activite_autre")
    check("secondaire : voit la principale avec son titre", any(x.get("titre") == "Titre principal banc" for x in b["items"]), b)
    json.dump({"nom": "voix", "mo": 700, "pid": dormeur.pid, "t": time.time()}, open(fgpu, "w"))
    v = api(8190, "/manga/vram")
    check("jauge VRAM de la principale : compte le moteur de la secondaire", any(x.get("quoi") == "PID %d" % dormeur.pid for x in v.get("detail") or []), v.get("detail"))

    with sync_playwright() as pw:
        nav = pw.chromium.launch(channel="msedge", headless=True)
        for larg in (1280, 360):
            print("2-3. app principale a %d px" % larg)
            pg = nav.new_page(viewport={"width": larg, "height": 900}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("actRafraichir()"); pg.wait_for_timeout(2500)
            txt = pg.evaluate("() => $('actTxt').textContent")
            # la principale a AUSSI un traitement (factice) : son temoin montre le sien puis « · 🔒 1 »
            check("temoin : le sien + « 🔒 1 » pour l'autre", "🔒 1" in txt and "Titre principal banc" in txt, txt)
            pg.evaluate("() => $('hdrAct').click()"); pg.wait_for_timeout(600)
            check("le titre de la secondaire n'apparait NULLE PART dans la page", SECRET not in pg.content() and SECRET not in pg.evaluate("() => document.body.innerText"))
            ligne = pg.evaluate("() => { const e = document.querySelector('#actListe .act-autre'); return e ? [e.innerText, !!e.querySelector('.act-bar i')] : null; }")
            check("detail : une ligne « 🔒 autre application » avec sa jauge", ligne and "🔒" in ligne[0] and ligne[1] and "3/12" in ligne[0], ligne)
            pg.evaluate("chargerCouts()"); pg.wait_for_timeout(1500)
            c = pg.evaluate("() => [COUTS.aujourdhui, COUTS.propre && COUTS.propre.aujourdhui, COUTS.autre && COUTS.autre.aujourdhui]")
            check("pastille des couts = principale + secondaire", c[1] is not None and abs(c[0] - (c[1] + c[2])) < 1e-6, c)
            check("la page ne deborde pas", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"))
            vues = []
            pg.on("request", lambda r: vues.append(r.url) if "/manga/narrate" in r.url else None)
            pg.once("dialog", lambda d: d.dismiss())
            r = pg.evaluate("async () => { try { await api('/manga/narrate', {d: 'zz-inexistant/ch_1'}); return 'parti'; } catch (e) { return e.message; } }")
            check("question refusee : rien n'est envoye", "annulé" in r and not vues, (r, vues))
            msg = []
            pg.once("dialog", lambda d: (msg.append(d.message), d.accept()))
            r = pg.evaluate("async () => { try { await api('/manga/narrate', {d: 'zz-inexistant/ch_1'}); return 'parti'; } catch (e) { return e.message; } }")
            check("question acceptee : la demande part", "annulé" not in r and vues, (r, vues))
            check("la question ne cite pas le titre secret", msg and SECRET not in msg[0] and "🔒" in msg[0], msg)
            if larg == 360:                                   # la principale au REPOS, la secondaire travaille
                shutil.rmtree(crees[1], ignore_errors=True); pg.evaluate("actRafraichir()"); pg.wait_for_timeout(2500)
                txt = pg.evaluate("() => $('actTxt').textContent")
                check("principale au repos : « 🔒 1 traitement en cours · Narration · voix 3/12 »",
                      txt.startswith("🔒 1 traitement en cours") and "voix" in txt and SECRET not in txt, txt)
            check("aucune erreur JavaScript", not errs, errs[:2])
            pg.close()
        nav.close()
finally:
    dormeur.kill()
    for d in crees: shutil.rmtree(d, ignore_errors=True)
    try: os.remove(fgpu)
    except OSError: pass
check("nettoyage : rien ne reste", not any(os.path.exists(d) for d in crees) and not os.path.exists(fgpu))
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
