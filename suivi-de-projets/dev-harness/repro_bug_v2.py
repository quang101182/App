"""
Reproduction ciblee des 2 bugs (bug signale par Quang le 2026-07-20).

SCENARIO 1 — verrou fantome / bascule lecture seule
  creerNouveauProjetDeSauvegarde() ne cree pas le .lock du nouveau projet, mais
  isLockedByCurrentUser reste herite a true. Au tick suivant (<=60s),
  checkExternalLockTakeover() ne trouve pas le .lock -> "(fichier disparu)" ->
  disableEditing() + bandeau rouge LECTURE SEULE.

SCENARIO 2 — contamination croisee
  sauvegarderBackupAutomatique() n'est pas atomique : le nom de fichier (l.3875)
  et les donnees (l.3926) sont lus a des instants differents, separes par des await
  disque. Si le projet courant change entre les deux, on ecrit les donnees d'un
  projet dans le fichier d'un autre. On inspecte le CONTENU des backups pour le prouver.

Vrais FileSystemDirectoryHandle via OPFS + latence artificielle (lecteur reseau/VPN).
Usage : python repro_bug_v2.py [latence_ms]
"""
import http.server, socketserver, threading, time, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8773
URL = f"http://127.0.0.1:{PORT}/index.html"
LATENCE_MS = int(sys.argv[1]) if len(sys.argv) > 1 else 400

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
    return { [Symbol.asyncIterator]() {
      const inner = it[Symbol.asyncIterator]();
      return { async next() { await sleep(window.__LAT / 3); return inner.next(); } };
    } };
  };
})();
""" % LATENCE_MS


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def contenu_backups(page):
    """Lit le CONTENU reel de chaque backup : quel projet, combien de thematiques, lesquelles."""
    return page.evaluate("""async () => {
        const root = await navigator.storage.getDirectory();
        const dir = await root.getDirectoryHandle('backup', { create: true });
        const out = [];
        for await (const e of dir.values()) {
            if (!e.name.endsWith('.json') || !e.name.startsWith('backup_')) { out.push({ fichier: e.name }); continue; }
            try {
                const f = await (await dir.getFileHandle(e.name)).getFile();
                const d = JSON.parse(await f.text());
                out.push({ fichier: e.name,
                           themes: (d.projects || []).map(p => p.name),
                           nbActions: (d.actions || []).length });
            } catch (err) { out.push({ fichier: e.name, err: String(err) }); }
        }
        return out.sort((a, b) => a.fichier.localeCompare(b.fichier));
    }""")


def etat(page):
    return page.evaluate("""() => ({
        profil: typeof selectedProjectSaveId !== 'undefined' ? selectedProjectSaveId : null,
        nom: typeof getProjectSaveName === 'function' ? getProjectSaveName(selectedProjectSaveId) : null,
        verrouCru: typeof isLockedByCurrentUser !== 'undefined' ? isLockedByCurrentUser : null,
        themes: typeof projects !== 'undefined' ? projects.map(p => p.name) : [],
        nbActions: typeof actions !== 'undefined' ? actions.length : -1,
        bandeauRouge: (() => { const b = document.getElementById('top-info-banner');
            return b && b.style.display !== 'none' ? b.textContent.trim().slice(0, 90) : null; })(),
        message: document.getElementById('message-area')?.textContent?.trim().slice(0, 110) || null,
    })""")


def creer_theme(page, nom, prefixe):
    """Cree une thematique via le VRAI formulaire (pas d'injection DOM)."""
    page.click('.tablink[onclick*="tab2"]'); time.sleep(0.4)
    page.click("#add-project-button"); time.sleep(0.4)
    page.fill("#project-name", nom)
    page.fill("#project-prefix", prefixe)
    page.fill("#project-client", "CLIENT-TEST")
    page.evaluate("""() => { const f = document.getElementById('projectForm');
        f.querySelectorAll('input[required]').forEach(i => { if (!i.value) i.value = i.type === 'date' ? '2026-07-20' : 'X'; }); }""")
    page.click("#add-project-form .form-buttons button.btn-success"); time.sleep(1.5)
    page.click('.tablink[onclick*="tab1"]'); time.sleep(0.4)


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
        page.on("console", lambda m: console.append(m.text[:150]))
        # 1er prompt = nom utilisateur, puis les noms de projets.
        rep = iter(["TESTEUR", "PROJET-A", "PROJET-B", "PROJET-C"])
        page.on("dialog", lambda d: d.accept(next(rep, "X")) if d.type == "prompt" else d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("h1", timeout=10000); time.sleep(1.0)
        page.click("#autoriser-button"); time.sleep(2.0)
        page.click("#autoriser-button"); time.sleep(2.0)
        page.click("#charger-button"); time.sleep(3.0)

        # ---------- SCENARIO 1 : verrou fantome ----------
        page.click("button:has-text('Créer Projet')"); time.sleep(4.0)
        R["S1_apres_creation"] = etat(page)
        R["S1_fichiers"] = [f["fichier"] for f in contenu_backups(page)]
        R["S1_lock_du_nouveau_projet_existe"] = page.evaluate("""async () => {
            const root = await navigator.storage.getDirectory();
            const dir = await root.getDirectoryHandle('backup', { create: true });
            const attendu = typeof getLockFileName === 'function' ? getLockFileName() : null;
            const noms = []; for await (const e of dir.values()) noms.push(e.name);
            return { lock_attendu: attendu, locks_presents: noms.filter(n => n.endsWith('.lock')),
                     present: attendu ? noms.includes(attendu) : null };
        }""")

        # On laisse tourner le check externe (interval 60s) sans rien toucher.
        if "--skip-s1" not in sys.argv:
            print("[*] Attente du tick de verification du verrou (65s)...", file=sys.stderr)
            time.sleep(65)
            R["S1_apres_65s"] = etat(page)
            R["S1_console_verrou"] = [c for c in console if "ock" in c or "akeover" in c][-6:]

        # ---------- SCENARIO 2 : contamination croisee ----------
        page.reload(wait_until="domcontentloaded"); time.sleep(3.0)
        page.click("#charger-button"); time.sleep(3.5)
        R["S2_depart"] = etat(page)

        # On peuple PROJET-B (projet courant) avec une thematique identifiable.
        creer_theme(page, "THEME-DU-PROJET-B", "BBB")
        time.sleep(1.0)
        R["S2_avant_creation_C"] = etat(page)

        # Geste declencheur : une sauvegarde auto est en vol (CRUD ci-dessus),
        # et on cree un nouveau projet SANS attendre qu'elle se termine.
        page.click("button:has-text('Créer Projet')")
        time.sleep(6.0)
        R["S2_apres_creation_C"] = etat(page)
        R["S2_contenu_backups"] = contenu_backups(page)

        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        R["ERREUR_SCENARIO"] = f"{type(e).__name__}: {str(e)[:400]}"
    print(json.dumps(R, indent=2, ensure_ascii=False))
