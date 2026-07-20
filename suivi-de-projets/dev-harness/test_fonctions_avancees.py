"""
Test des 3 fonctions avancees de l'onglet Reglages, implementees le 20/07/2026
(elles n'affichaient que "Fonction non implementee" depuis l'origine) :

  - exporterTousProfils()  : archive JSON de tous les projets du domaine
  - importerProfil()       : recree des projets depuis une archive, sans rien ecraser
  - reparerTousProfils()   : analyse de coherence de tous les projets + rapport

Chaque bouton est actionne pour de vrai, et le resultat est verifie sur le contenu
reel (fichier telecharge, liste des projets apres import, rapport de reparation).

Usage : python test_fonctions_avancees.py [page.html]
"""
import http.server, socketserver, threading, time, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8776
URL = f"http://127.0.0.1:{PORT}/" + (sys.argv[1] if len(sys.argv) > 1 else "index.html")
TMP = Path(__file__).resolve().parent / "captures"
R = {}

INIT = r"""
(() => {
  window.showDirectoryPicker = async (opts) => {
    const root = await navigator.storage.getDirectory();
    const which = (opts && opts.id || '').startsWith('pj') ? 'pj' : 'backup';
    return await root.getDirectoryHandle(which, { create: true });
  };
  const HP = FileSystemHandle.prototype;
  if (!HP.queryPermission)   HP.queryPermission   = async () => 'granted';
  if (!HP.requestPermission) HP.requestPermission = async () => 'granted';
})();
"""


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def creer_theme(page, nom, prefixe):
    page.click('.tablink[onclick*="tab2"]'); time.sleep(0.4)
    page.click("#add-project-button"); time.sleep(0.4)
    page.fill("#project-name", nom); page.fill("#project-prefix", prefixe)
    page.fill("#project-client", "C")
    page.evaluate("""() => { document.querySelectorAll('#projectForm input[required]').forEach(i => {
        if (!i.value) i.value = i.type === 'date' ? '2026-07-20' : 'X'; }); }""")
    page.click("#add-project-form .form-buttons button.btn-success"); time.sleep(1.2)
    page.click('.tablink[onclick*="tab1"]'); time.sleep(0.4)


def main():
    global R
    TMP.mkdir(exist_ok=True)
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    alerts = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.add_init_script(INIT)
        rep = iter(["TESTEUR", "PROJET-UN", "PROJET-DEUX"])

        def on_dialog(d):
            if d.type == "prompt": d.accept(next(rep, "X"))
            else:
                alerts.append(d.message[:400]); d.accept()
        page.on("dialog", on_dialog)

        page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("h1", timeout=10000); time.sleep(1.0)
        page.click("#autoriser-button"); time.sleep(1.5)
        page.click("#autoriser-button"); time.sleep(1.5)
        page.click("#charger-button"); time.sleep(2.5)

        page.click("button:has-text('Créer Projet')"); time.sleep(3.5)
        creer_theme(page, "THEME-UN", "TUN")
        page.click("button:has-text('Créer Projet')"); time.sleep(3.5)
        creer_theme(page, "THEME-DEUX", "TDX")
        time.sleep(1.5)
        R["projets_avant"] = page.evaluate("() => projectSaveList.map(p => p.name)")

        # ---------- EXPORT ----------
        page.click('.tablink[onclick*="tab4"]'); time.sleep(0.8)
        with page.expect_download(timeout=30000) as dl_info:
            page.click("#btn-export-all-profiles")
        dl = dl_info.value
        chemin = TMP / "export_test.json"
        dl.save_as(str(chemin))
        archive = json.loads(chemin.read_text(encoding="utf-8"))
        R["export"] = {
            "nom_fichier": dl.suggested_filename,
            "format": archive.get("format"),
            "nb_profils": len(archive.get("profils", [])),
            "profils": [{"nom": p["name"], "themes": [t["name"] for t in p["donnees"]["projects"]]}
                        for p in archive.get("profils", [])],
        }

        # ---------- IMPORT ----------
        with page.expect_file_chooser(timeout=30000) as fc_info:
            page.click("#btn-import-profile")
        fc_info.value.set_files(str(chemin))
        time.sleep(4.0)
        R["projets_apres_import"] = page.evaluate("() => projectSaveList.map(p => p.name)")
        R["import_message"] = page.evaluate("() => document.getElementById('message-area')?.textContent?.trim().slice(0,160)")

        # ---------- REPARATION ----------
        alerts.clear()
        page.click("#btn-repair-all-profiles")
        time.sleep(6.0)
        R["rapport_reparation"] = alerts[-1] if alerts else None
        R["projet_courant_apres_reparation"] = page.evaluate("() => getProjectSaveName(selectedProjectSaveId)")
        R["themes_affiches_apres_reparation"] = page.evaluate("() => projects.map(p => p.name)")

        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        R["ERREUR"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(json.dumps(R, indent=2, ensure_ascii=False))
