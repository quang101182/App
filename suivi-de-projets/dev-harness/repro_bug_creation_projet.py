"""
Reproduction du bug signalé le 2026-07-20 (Quang) sur la création de projet.

Symptômes rapportés :
  1. À la création d'un projet -> bascule en lecture seule, aucun fichier backup sur le disque.
  2. Après F5, en naviguant entre projets, le projet neuf affiche les thématiques/actions
     du projet précédemment sélectionné (contamination croisée).
  3. Les projets créés AVANT (qui ont déjà un backup disque) ne posent aucun problème.
  4. Latence réseau au changement de projet, sans indicateur de chargement.

Méthode : on n'utilise AUCUN stub applicatif. `window.showDirectoryPicker` est redirigé vers
OPFS (navigator.storage.getDirectory), qui fournit de VRAIS FileSystemDirectoryHandle
(getFileHandle / createWritable / values / removeEntry). Tout le chemin de code de l'app
s'exécute donc réellement : verrou .lock, backups JSON, rotation, IndexedDB.
Une latence artificielle simule le lecteur réseau (VPN) de la prod.

Sortie : verdict chiffré + journal des I/O disque réellement effectuées.
"""
import http.server, socketserver, threading, time, json, sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8771
URL = f"http://127.0.0.1:{PORT}/index.html"

# Latence par opération disque, en ms (simule le lecteur réseau / VPN).
LATENCE_MS = int(sys.argv[1]) if len(sys.argv) > 1 else 120

# Resultats collectes au fil du scenario : au niveau module pour etre imprimes
# meme si une etape casse (sinon on perd tout le diagnostic deja obtenu).
R = {}

INIT = r"""
(() => {
  window.__FSLOG = [];
  window.__LAT = %d;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const log = (op, name) => window.__FSLOG.push({ t: Date.now(), op, name });

  // Vrais handles OPFS a la place du picker interactif.
  window.showDirectoryPicker = async (opts) => {
    const root = await navigator.storage.getDirectory();
    const which = (opts && opts.id || '').startsWith('pj') ? 'pj' : 'backup';
    return await root.getDirectoryHandle(which, { create: true });
  };

  // OPFS n'expose pas queryPermission/requestPermission -> l'app en depend.
  const HP = FileSystemHandle.prototype;
  if (!HP.queryPermission)   HP.queryPermission   = async () => 'granted';
  if (!HP.requestPermission) HP.requestPermission = async () => 'granted';

  // Latence + journalisation sur les I/O reellement utilisees par l'app.
  const DP = FileSystemDirectoryHandle.prototype;
  const _get = DP.getFileHandle, _rm = DP.removeEntry, _values = DP.values;
  DP.getFileHandle = async function (name, o) { await sleep(window.__LAT); log('getFileHandle', name); return _get.call(this, name, o); };
  DP.removeEntry   = async function (name, o) { await sleep(window.__LAT); log('removeEntry',   name); return _rm.call(this, name, o); };
  DP.values = function () {
    const it = _values.call(this);
    log('values', this.name);
    return { [Symbol.asyncIterator]() {
      const inner = it[Symbol.asyncIterator]();
      return { async next() { await sleep(window.__LAT / 4); return inner.next(); } };
    } };
  };
})();
""" % LATENCE_MS


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def dump_fs(page):
    """Liste le contenu reel du dossier backup OPFS."""
    return page.evaluate("""async () => {
        const root = await navigator.storage.getDirectory();
        const dir = await root.getDirectoryHandle('backup', { create: true });
        const out = [];
        for await (const e of dir.values()) out.push(e.name);
        return out.sort();
    }""")


def etat(page):
    return page.evaluate("""() => ({
        profil:   typeof selectedProjectSaveId !== 'undefined' ? selectedProjectSaveId : null,
        nom:      typeof getProjectSaveName === 'function' ? getProjectSaveName(selectedProjectSaveId) : null,
        verrou:   typeof isLockedByCurrentUser !== 'undefined' ? isLockedByCurrentUser : null,
        nbThemes: typeof projects !== 'undefined' ? projects.length : -1,
        nbActions:typeof actions  !== 'undefined' ? actions.length  : -1,
        themes:   typeof projects !== 'undefined' ? projects.map(p => p.name) : [],
        selectSauv: (() => { const s = document.getElementById('select-sauvegarde');
                     return s ? Array.from(s.options).map(o => o.value || o.text) : []; })(),
        overlay:  !!document.querySelector('.loading-overlay'),
    })""")


def main():
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    global R
    perrs = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: perrs.append(str(e)))
        page.add_init_script(INIT)

        # Les prompt() de creation de projet : on repond en sequence.
        noms = iter(["PROJET-A", "PROJET-B", "PROJET-C"])
        page.on("dialog", lambda d: d.accept(next(noms, "X")) if d.type == "prompt" else d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("h1", timeout=10000)
        time.sleep(1.0)

        # --- 1. Autoriser les dossiers (vrai bouton, vrai chemin) ---
        page.click("#autoriser-button")
        time.sleep(1.5)
        page.click("#autoriser-button")   # 2e passe : dossier PJ
        time.sleep(1.5)
        R["apres_autorisation"] = etat(page)

        # Prise du verrou par le vrai chemin (bouton Charger), sinon tout est desactive.
        page.click("#charger-button")
        time.sleep(2.5)
        R["apres_charger"] = etat(page)

        # --- 2. Creer PROJET-A, y mettre une thematique, sauvegarder ---
        page.click("button:has-text('Créer Projet')")
        time.sleep(2.5)
        R["A_apres_creation"] = etat(page)
        R["A_fichiers"] = dump_fs(page)

        # Thematique via le vrai formulaire de l'onglet Thematiques
        page.click('.tablink[onclick*="tab2"]')
        time.sleep(0.6)
        page.click("#add-project-button")          # ouvre le formulaire (cache par defaut)
        time.sleep(0.5)
        page.fill("#project-name", "THEME-DE-A")
        page.fill("#project-prefix", "AAA")
        page.click("#projectForm button[type=submit]")
        time.sleep(2.0)
        R["A_apres_theme"] = etat(page)

        page.click('.tablink[onclick*="tab1"]')
        time.sleep(0.5)
        page.click("#save-now-dashboard-button")
        time.sleep(2.5)
        R["A_apres_save"] = etat(page)
        R["A_fichiers_apres_save"] = dump_fs(page)

        # --- 3. Creer PROJET-B pendant qu'on est sur A (le geste qui declenche le bug) ---
        page.click("button:has-text('Créer Projet')")
        time.sleep(3.0)
        R["B_apres_creation"] = etat(page)
        R["B_fichiers"] = dump_fs(page)
        R["B_fslog"] = page.evaluate("() => window.__FSLOG.slice(-25)")

        # --- 4. F5 (comme Quang) ---
        page.reload(wait_until="domcontentloaded")
        time.sleep(2.5)
        R["B_apres_F5"] = etat(page)

        # --- 5. Aller-retour B -> A -> B ---
        page.select_option("#projet-select", label="PROJET-A")
        time.sleep(3.5)
        R["switch_vers_A"] = etat(page)

        page.select_option("#projet-select", label="PROJET-B")
        time.sleep(3.5)
        R["retour_sur_B"] = etat(page)
        R["fichiers_final"] = dump_fs(page)

        R["pageerrors"] = perrs
        b.close()

    httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        R["ERREUR_SCENARIO"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(json.dumps(R, indent=2, ensure_ascii=False))
