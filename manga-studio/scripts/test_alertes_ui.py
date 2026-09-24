"""Banc v2.11.0 (24/09) : alertes de moderation dans le bouton d'activite + interrupteur global « En ligne / Sur mon PC ».
Dans l'app reelle, a 380 px. N'ecrit dans le vrai registre QUE des alertes « zz-essai-al/... », retirees a la fin ;
l'interrupteur est remis dans son etat de depart.
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import moderation as mod, reglages, banc_outils as bo
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def nettoyer():
    doc = mod._lire(); doc["alertes"] = [a for a in doc["alertes"] if not a["d"].startswith("zz-essai-al")]; mod._ecrire(doc)


mode0 = reglages.lire()["mode"]
avant = len(mod.alertes("ouverte"))
nettoyer()
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 380, "height": 800}); errs, dial = [], []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: (dial.append(d.message), d.accept()))
        url = "http://127.0.0.1:8190/manga#k=" + KEY
        pg.goto(url); pg.wait_for_timeout(3500)
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        check("aucune alerte (hors celles de Quang) -> badge conforme", pg.is_hidden("#actAlerte") == (avant == 0))
        mod.ajouter_alerte("zz-essai-al/ch_1", "narration", [2, 5], "gemini", "Gemini a arrete sa reponse pour securite (SAFETY)",
                           detail="etape analyse", tag="gemini-charon")
        pg.goto(url); pg.wait_for_timeout(3500)
        check("badge ⚠ visible avec le compte", pg.is_visible("#actAlerte") and pg.inner_text("#actAlerte") == "⚠ %d" % (avant + 1), pg.inner_text("#actAlerte"))
        check("le badge PULSE (et lui seul)", pg.evaluate("() => getComputedStyle($('actAlerte')).animationName") == "alertePulse")
        pg.click("#hdrAct"); pg.wait_for_timeout(1500)
        if pg.is_hidden("#actVueAlertes"):
            pg.click("#ongAlertes"); pg.wait_for_timeout(600)
        txt = pg.inner_text("#actVueAlertes")
        check("onglet « À traiter » : chapitre, pages, motif en clair", "zz-essai-al — ch. 1" in txt and "2, 5" in txt and "Refusé par la modération de Gemini" in txt, txt[:160])
        check("solution proposée + vidéo en attente", "Proposé : relire ces pages avec Kimi" in txt and "vidéo en attente" in txt)
        pg.check('[data-al]:not([data-al=""]) >> nth=%d' % 0) if avant == 0 else pg.evaluate(
            "() => { const x = [...document.querySelectorAll('[data-al]')].find(i => ALERTES.ouvertes.find(a => a.id === i.dataset.al && a.d.startsWith('zz-'))); x.click(); }")
        pg.wait_for_timeout(300)
        check("bouton « Ignorer » actif une fois coché", pg.is_enabled('[data-al-action="ignorer"]'))
        pg.click('[data-al-action="ignorer"]'); pg.wait_for_timeout(2000)
        check("alerte ignorée côté serveur", not [a for a in mod.ouvertes_pour("zz-essai-al/ch_1")])
        check("badge revenu à l'état de départ", pg.is_hidden("#actAlerte") == (avant == 0))
        check("historique garde la trace", "zz-essai-al" in pg.evaluate("() => $('actVueAlertes').textContent"))
        pg.click("#actFermer")
        # interrupteur
        pg.evaluate("async () => { MODE = 'pc'; await api('/manga/reglages', {mode: 'cloud'}); await modeCharger(); }"); pg.wait_for_timeout(500)
        check("pastille « ☁ En ligne » (bleue)", pg.evaluate("() => $('hdrMode').textContent") == "☁ En ligne" and "pc" not in pg.get_attribute("#hdrMode", "class"))
        pg.click("#hdrMode"); pg.wait_for_timeout(1500)
        check("un clic -> « 🖥 Sur mon PC » (orange), mémorisé côté serveur", pg.evaluate("() => $('hdrMode').textContent") == "🖥 Sur mon PC" and reglages.lire()["mode"] == "pc")
        check("les boutons de lancement portent l'icône 🖥", pg.evaluate("() => $('btnNarrer').querySelector('.mode-ico').textContent") == "🖥")
        pg.goto(url); pg.wait_for_timeout(3000)
        check("rechargé : toujours « Sur mon PC » (persistance)", pg.evaluate("() => $('hdrMode').textContent") == "🖥 Sur mon PC")
        # v2.30.0 (Quang 22h33 : « que je voie en permanence de maniere claire ») : le MOT reste affiche sur telephone
        check("380 px : pastille lisible (icône + « Sur mon PC »)", pg.inner_text("#hdrMode").strip() == "🖥 Sur mon PC")
        check("380 px : la page ne déborde pas", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"),
              pg.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"))
        check("anciens menus « Moteur de voix » masqués", pg.evaluate("() => $('narrTts').parentNode.hidden && $('suiviTts').hidden"))
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    nettoyer()
    reglages.ecrire(mode=mode0)
print("interrupteur remis a « %s »" % reglages.lire()["mode"])
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
