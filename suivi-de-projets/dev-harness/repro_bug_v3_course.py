"""
Scenario 3 — course entre une sauvegarde auto EN VOL et un changement de projet.

Hypothese testee : sauvegarderBackupAutomatique() lit le nom de fichier (l.3875) et les
donnees (l.3926) a des instants differents, separes par des await disque. Si
selectedProjectSaveId change entre les deux, on peut ecrire les donnees d'un projet
dans le fichier d'un autre -> contamination croisee au rechargement.

Deux gestes testes, SANS aucun delai (l'utilisateur enchaine sur un lecteur reseau lent) :
  A) modification puis creation d'un nouveau projet dans la foulee
  B) modification puis changement de projet dans la foulee

Verdict = contenu reel des fichiers backup : un fichier au nom du projet X qui
contient les thematiques du projet Y prouve la contamination.

Usage : python repro_bug_v3_course.py [latence_ms]
"""
import http.server, socketserver, threading, time, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8774
URL = f"http://127.0.0.1:{PORT}/index.html"
LAT = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
R = {}

INIT = r"""
(() => {
  window.__LAT = %d;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  window.showDirectoryPicker = async (opts) => {
    const root = await navigator.storage.getDirectory();
    const which = (opts && opts.id || '').startsWith('pj') ? 'pj' : 'backup';
    return await root.getDirectoryHandle(which, { create: true });
  };
  const HP = FileSystemHandle.prototype;
  if (!HP.queryPermission)   HP.queryPermission   = async () => 'granted';
  if (!HP.requestPermission) HP.requestPermission = async () => 'granted';
  const DP = FileSystemDirectoryHandle.prototype;
  const _get = DP.getFileHandle, _rm = DP.removeEntry, _values = DP.values;
  DP.getFileHandle = async function (n, o) { await sleep(window.__LAT); return _get.call(this, n, o); };
  DP.removeEntry   = async function (n, o) { await sleep(window.__LAT); return _rm.call(this, n, o); };
  DP.values = function () {
    const it = _values.call(this);
    return { [Symbol.asyncIterator]() { const inner = it[Symbol.asyncIterator]();
      return { async next() { await sleep(window.__LAT / 3); return inner.next(); } }; } };
  };
})();
""" % LAT


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def backups(page):
    return page.evaluate("""async () => {
        const root = await navigator.storage.getDirectory();
        const dir = await root.getDirectoryHandle('backup', { create: true });
        const out = [];
        for await (const e of dir.values()) {
            if (!e.name.startsWith('backup_')) continue;
            try { const f = await (await dir.getFileHandle(e.name)).getFile();
                  const d = JSON.parse(await f.text());
                  out.push({ fichier: e.name, themes: (d.projects||[]).map(p=>p.name) });
            } catch (err) { out.push({ fichier: e.name, err: String(err) }); }
        }
        return out.sort((a,b)=>a.fichier.localeCompare(b.fichier));
    }""")


def noms_projets(page):
    return page.evaluate("() => Object.fromEntries(projectSaveList.map(p => [p.id, p.name]))")


def ajouter_theme_sans_attendre(page, nom, prefixe):
    """Remplit et valide le formulaire, puis rend la main IMMEDIATEMENT."""
    page.click('.tablink[onclick*="tab2"]'); time.sleep(0.4)
    page.click("#add-project-button"); time.sleep(0.4)
    page.fill("#project-name", nom); page.fill("#project-prefix", prefixe)
    page.fill("#project-client", "C")
    page.evaluate("""() => { document.querySelectorAll('#projectForm input[required]').forEach(i => {
        if (!i.value) i.value = i.type === 'date' ? '2026-07-20' : 'X'; }); }""")
    page.click("#add-project-form .form-buttons button.btn-success")
    page.click('.tablink[onclick*="tab1"]')   # retour dashboard, aucun sleep


def main():
    global R
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.add_init_script(INIT)
        rep = iter(["TESTEUR", "ALPHA", "BETA", "GAMMA"])
        page.on("dialog", lambda d: d.accept(next(rep, "X")) if d.type == "prompt" else d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("h1", timeout=10000); time.sleep(1.0)
        page.click("#autoriser-button"); time.sleep(2.0)
        page.click("#autoriser-button"); time.sleep(2.0)
        page.click("#charger-button"); time.sleep(3.0)

        # ALPHA + BETA, tous deux avec un backup et une thematique identifiable.
        page.click("button:has-text('Créer Projet')"); time.sleep(5.0)   # ALPHA
        ajouter_theme_sans_attendre(page, "THEME-ALPHA", "ALP"); time.sleep(6.0)
        page.click("#save-now-dashboard-button"); time.sleep(6.0)
        R["etat_alpha"] = {"themes": page.evaluate("() => projects.map(p=>p.name)")}

        # --- GESTE A : modifier ALPHA puis creer un projet DANS LA FOULEE ---
        ajouter_theme_sans_attendre(page, "THEME-ALPHA-2", "AL2")
        page.click("button:has-text('Créer Projet')")     # zero delai : sauvegarde en vol
        time.sleep(10.0)
        R["A_projet_courant"] = page.evaluate("() => getProjectSaveName(selectedProjectSaveId)")
        R["A_backups"] = backups(page)

        # --- GESTE B : modifier BETA puis CHANGER de projet dans la foulee ---
        page.click("#charger-button"); time.sleep(5.0)
        ajouter_theme_sans_attendre(page, "THEME-BETA", "BET")
        page.select_option("#projet-select", label="ALPHA")   # zero delai
        time.sleep(12.0)
        R["B_projet_courant"] = page.evaluate("() => getProjectSaveName(selectedProjectSaveId)")
        R["B_themes_affiches"] = page.evaluate("() => projects.map(p=>p.name)")
        R["B_backups"] = backups(page)
        R["noms"] = noms_projets(page)

        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        R["ERREUR"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(json.dumps(R, indent=2, ensure_ascii=False))
