# -*- coding: utf-8 -*-
"""Banc v2.12.0 (4-undecies) : basculer « ☁ / 🖥 » PENDANT un traitement, dans l'app reelle, comme Quang. 0 $.

Un FAUX lot tourne (deux processus python qui dorment, ecrits dans le vrai sources/_suivi/etat.json) sur une serie
jetable « banc-interrupt-ui ». L'etat, le journal des passages et l'interrupteur sont SAUVES puis RESTAURES a l'identique.
Refuse de tourner si un vrai traitement est en cours (il pourrait etre interrompu).
  1. clic pastille -> la question s'affiche : ce qui tourne (lot compte UNE fois), « finit en ☁ », « 1 chapitre restant
     passerait en 🖥 » ; Annuler -> rien ne change.
  2. « Basculer pour la suite » -> mode 🖥, le lot continue (processus vivants).
  3. « Interrompre et basculer » -> processus tues, mode ☁, bilan exact (fini / coupe + analyse gardee / pas commence) ;
     « Reprendre » envoie le BON lot (ch.2 coupe + ch.3) -- requete interceptee, rien n'est lance.
Captures : scripts/interruption_question_360.png, interruption_bilan_360.png.
"""
import json, os, shutil, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import reglages, suivi_nuit as sn
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
BANC = os.path.join(SRC, "banc-interrupt-ui")
URL = "http://127.0.0.1:8190/manga/#k=" + KEY
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def api(chemin):
    rq = urllib.request.Request("http://127.0.0.1:8190" + chemin, headers={"Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(rq, timeout=30))


def dormeur():
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], creationflags=CREATE)


if api("/manga/activite")["items"]:
    print("un vrai traitement tourne : banc refusé (il pourrait l'interrompre)"); sys.exit(2)
mode0 = reglages.lire()["mode"]
etat0 = open(sn.ETAT, "rb").read() if os.path.isfile(sn.ETAT) else None
jr0 = os.path.getsize(sn.JOURNAL) if os.path.isfile(sn.JOURNAL) else 0
lot, etape = dormeur(), dormeur()
try:
    shutil.rmtree(BANC, ignore_errors=True)
    for n in (1, 2, 3):
        cd = os.path.join(BANC, "ch_%d" % n); os.makedirs(cd)
        json.dump({"chapter": str(n), "title": "banc interrupt ui", "slug": "banc-interrupt-ui", "pages": []},
                  open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"))
    time.sleep(1.1)
    nd = os.path.join(BANC, "ch_2", "narration", "gemini-charon"); os.makedirs(nd)
    json.dump({"pages": [{"p": 1}]}, open(os.path.join(nd, "vision.json"), "w", encoding="utf-8"))
    json.dump({"etape": "voix", "fait": 3, "total": 12, "t": time.time(), "pid": etape.pid},
              open(os.path.join(nd, "progress.json"), "w", encoding="utf-8"))
    sn.ecrire_etat({"version": sn.VERSION, "etat": "en cours", "pid": lot.pid, "debut": time.time() - 60, "declencheur": "lot",
                    "serie": "banc-interrupt-ui", "refaire": False, "file": ["banc-interrupt-ui/ch_%d" % n for n in (1, 2, 3)],
                    "fait": [{"d": "banc-interrupt-ui/ch_1", "num": "1", "res": {}}], "erreurs": [],
                    "en_cours": {"d": "banc-interrupt-ui/ch_2", "num": "2", "etape": "voix", "pid": etape.pid,
                                 "etapes": {"narration": "faire"}}})
    reglages.ecrire(mode="cloud")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 360, "height": 800}); errs, relance = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/manga/suivi_lancer", lambda r: (relance.append(json.loads(r.request.post_data or "{}")),
                                                   r.fulfill(status=200, content_type="application/json", body='{"ok": true}')))
        pg.goto(URL); pg.wait_for_timeout(3500)
        check("version affichée = celle du fichier", pg.inner_text("#verBadge") == "v" + __import__("banc_outils").version_app())
        # 1. la question
        pg.click("#hdrMode"); pg.wait_for_timeout(2500)
        vis = pg.is_visible("#ask"); txt = pg.inner_text("#askX") if vis else ""
        check("clic pastille pendant un lot -> question à l'écran", vis and pg.inner_text("#askT") == "Un traitement tourne en ☁ En ligne",
              pg.inner_text("#askT") if vis else "")
        check("le lot est listé UNE fois (sa narration n'est pas comptée en double)", txt.count("•") == 1 and "⚙ Lot" in txt and "ch. 2" in txt, txt[:200])
        check("« finit en ☁ » + « 1 chapitre restant passerait en 🖥 »", "FINIT en ☁ En ligne" in txt and "1 chapitre(s) restant(s) du lot passeraient en 🖥 Sur mon PC" in txt)
        check("3 choix : Basculer / Annuler / Interrompre", pg.inner_text("#askYes") == "Basculer pour la suite" and pg.inner_text("#askNo") == "Annuler"
              and pg.is_visible("#askAlt") and pg.inner_text("#askAlt") == "Interrompre et basculer")
        larg = pg.evaluate("() => { const r = document.querySelector('.askbox').getBoundingClientRect(); return [r.left, r.right, r.bottom]; }")
        check("360 px : la question tient à l'écran", larg[0] >= 0 and larg[1] <= 360 and larg[2] <= 800, larg)
        pg.screenshot(path=os.path.join(HERE, "interruption_question_360.png"))
        pg.click("#askNo"); pg.wait_for_timeout(800)
        check("Annuler -> mode inchangé, lot vivant", reglages.lire()["mode"] == "cloud" and lot.poll() is None and etape.poll() is None)
        # 2. basculer pour la suite
        pg.click("#hdrMode"); pg.wait_for_timeout(2500); pg.click("#askYes"); pg.wait_for_timeout(1500)
        check("Basculer -> 🖥, le lot continue", reglages.lire()["mode"] == "pc" and lot.poll() is None and etape.poll() is None)
        # 3. interrompre
        pg.click("#hdrMode"); pg.wait_for_timeout(2500)
        check("la question dit maintenant « tourne en 🖥 »", pg.inner_text("#askT") == "Un traitement tourne en 🖥 Sur mon PC")
        pg.click("#askAlt"); pg.wait_for_timeout(6000)
        time.sleep(0.5)
        check("Interrompre -> processus du lot ET de l'étape tués", lot.poll() is not None and etape.poll() is not None)
        check("… et mode basculé en ☁", reglages.lire()["mode"] == "cloud")
        bil = pg.inner_text("#askX") if pg.is_visible("#ask") else ""
        check("bilan affiché", pg.is_visible("#ask") and pg.inner_text("#askT") == "Interrompu — voici où tu en es", bil[:80])
        check("bilan : fini ch.1 · coupé ch.2 + analyse gardée · pas commencé ch.3",
              "✅ fini(s) : ch. 1" in bil and "✂ coupé : ch. 2" in bil and "analyse des pages gardée" in bil and "⏸ pas commencé(s) : ch. 3" in bil, bil)
        check("« Reprendre en ☁ En ligne » proposé", pg.inner_text("#askYes") == "▶ Reprendre en ☁ En ligne")
        pg.screenshot(path=os.path.join(HERE, "interruption_bilan_360.png"))
        e = sn.lire_etat()
        check("état serveur : interrompu, coupé = ch.2 (tag gemini-charon)", e.get("etat") == "interrompu"
              and ((e.get("interruption") or {}).get("coupe") or {}).get("tag") == "gemini-charon")
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(5000)
        fin = pg.evaluate("() => [ACT.finis.filter(x => (x.d || x.titre || '').startsWith('banc-interrupt-ui')).length, $('hdrAct').textContent]")
        check("rien de coupé n'est présenté comme « fini »", fin[0] == 0 and "✓" not in fin[1], fin)
        pg.click("#askYes"); pg.wait_for_timeout(1500)
        r = relance[0] if relance else {}
        check("Reprendre -> le bon lot (ch.2 coupé + ch.3), rien d'autre", r.get("serie") == "banc-interrupt-ui" and r.get("lot") is True
              and r.get("chapitres") == ["banc-interrupt-ui/ch_2", "banc-interrupt-ui/ch_3"] and r.get("refaire") is False, r)
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    for x in (lot, etape):
        if x.poll() is None:
            x.kill()
    shutil.rmtree(BANC, ignore_errors=True)
    if etat0 is None:
        os.path.isfile(sn.ETAT) and os.remove(sn.ETAT)
    else:
        open(sn.ETAT, "wb").write(etat0)
    if os.path.isfile(sn.JOURNAL):
        with open(sn.JOURNAL, "r+b") as f:
            f.truncate(jr0)
    reglages.ecrire(mode=mode0)
print("restauré : interrupteur « %s » · état des passages %s · journal %d octets · série de banc retirée %s" % (
    reglages.lire()["mode"], "identique" if (open(sn.ETAT, "rb").read() if os.path.isfile(sn.ETAT) else None) == etat0 else "DIFFÉRENT",
    os.path.getsize(sn.JOURNAL) if os.path.isfile(sn.JOURNAL) else 0, not os.path.isdir(BANC)))
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
