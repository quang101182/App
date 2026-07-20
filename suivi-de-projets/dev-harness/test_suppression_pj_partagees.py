"""
Test du correctif 3 — la suppression d'un projet ne doit PAS effacer les pieces jointes
d'un autre projet.

Contexte : le dossier PJ est un fourre-tout PARTAGE et supprimerProjetDeSauvegarde()
supprime les fichiers par NOM (l.4296). Si les donnees d'un projet ont ete contaminees
par celles d'un autre (bug n2), supprimer ce projet effacait physiquement les PJ du
projet legitime, de maniere irreversible (pas de corbeille dans l'app).

Mise en situation : on reproduit l'etat DEJA PRESENT chez l'utilisateur, c'est-a-dire
un projet neuf dont les donnees locales referencent les PJ d'un autre projet. L'etat de
depart est injecte comme DONNEE ; le comportement teste est la vraie fonction de
suppression, declenchee par le vrai bouton.

Verdict : le fichier PJ du projet legitime est-il encore sur le disque apres suppression ?

Usage : python test_suppression_pj_partagees.py
"""
import http.server, socketserver, threading, time, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8775
URL = f"http://127.0.0.1:{PORT}/" + (sys.argv[1] if len(sys.argv) > 1 else "index.html")
PJ_ALPHA = "document-important-de-ALPHA.pdf"
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


def fichiers_pj(page):
    return page.evaluate("""async () => {
        const root = await navigator.storage.getDirectory();
        const dir = await root.getDirectoryHandle('pj', { create: true });
        const out = []; for await (const e of dir.values()) out.push(e.name);
        return out.sort();
    }""")


def main():
    global R
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    console = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.add_init_script(INIT)
        page.on("console", lambda m: console.append(m.text[:160]))
        rep = iter(["TESTEUR", "ALPHA", "BETA"])
        page.on("dialog", lambda d: d.accept(next(rep, "X")) if d.type == "prompt" else d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("h1", timeout=10000); time.sleep(1.0)
        page.click("#autoriser-button"); time.sleep(1.5)
        page.click("#autoriser-button"); time.sleep(1.5)
        page.click("#charger-button"); time.sleep(2.5)

        page.click("button:has-text('Créer Projet')"); time.sleep(4.0)   # ALPHA
        alpha = page.evaluate("() => selectedProjectSaveId")
        page.click("button:has-text('Créer Projet')"); time.sleep(4.0)   # BETA
        beta = page.evaluate("() => selectedProjectSaveId")
        R["projets"] = {"ALPHA": alpha, "BETA": beta}

        # Etat de depart : un vrai fichier PJ appartenant a ALPHA, reference par ALPHA
        # ET (a cause du bug de contamination) par BETA.
        page.evaluate("""async ([alpha, beta, nomPJ, cfg]) => {
            const root = await navigator.storage.getDirectory();
            const dir = await root.getDirectoryHandle('pj', { create: true });
            const fh = await dir.getFileHandle(nomPJ, { create: true });
            const w = await fh.createWritable(); await w.write('contenu important'); await w.close();
            const refs = JSON.stringify({ "1": [{ name: nomPJ }] });
            const acts = JSON.stringify([{ id: 1, numeroRef: 'ALP-001-001', description: 'action ALPHA' }]);
            localStorage.setItem(`profile_C${cfg}_${alpha}_attachments`, refs);
            localStorage.setItem(`profile_C${cfg}_${alpha}_actions`, acts);
            localStorage.setItem(`profile_C${cfg}_${beta}_attachments`, refs);   // contamination
            localStorage.setItem(`profile_C${cfg}_${beta}_actions`, acts);
        }""", [alpha, beta, PJ_ALPHA, page.evaluate("() => activeConfig")])

        R["pj_avant_suppression"] = fichiers_pj(page)

        # Suppression de BETA par le VRAI bouton (confirm auto-accepte).
        page.evaluate("() => { const s = document.getElementById('projet-select'); s.value = arguments[0]; }") if False else None
        page.select_option("#projet-select", value=beta); time.sleep(3.0)
        page.click("button:has-text('Supprimer Projet')"); time.sleep(6.0)

        R["pj_apres_suppression"] = fichiers_pj(page)
        R["pj_alpha_preservee"] = PJ_ALPHA in R["pj_apres_suppression"]
        R["console_pj"] = [c for c in console if "PJ" in c][-8:]
        R["projet_courant_final"] = page.evaluate("() => getProjectSaveName(selectedProjectSaveId)")

        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        R["ERREUR"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(json.dumps(R, indent=2, ensure_ascii=False))
    print("\nVERDICT :", "OK - PJ du projet legitime preservee" if R.get("pj_alpha_preservee")
          else "ECHEC - la PJ d'ALPHA a ete supprimee avec BETA")
