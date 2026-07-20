"""
Test : supprimer une ACTION ou une THEMATIQUE ne doit pas effacer les pieces jointes
d'un AUTRE projet.

Meme faille que pour la suppression de projet (corrigee precedemment) : le dossier PJ
est un fourre-tout partage et la suppression se fait par NOM. supprimerAction() et
supprimerProjet() n'avaient aucune protection.

Ce cas compte parce que c'est le geste naturel de l'utilisateur face a un projet
contamine : "je vide les thematiques et les actions au lieu de supprimer le projet".

Les vraies fonctions du module sont appelees (supprimerAction / supprimerProjet),
avec confirm() auto-accepte. L'etat de depart contamine est injecte comme DONNEE.

Usage : python test_suppression_action_thematique_pj.py [page.html]
"""
import http.server, socketserver, threading, time, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8777
URL = f"http://127.0.0.1:{PORT}/" + (sys.argv[1] if len(sys.argv) > 1 else "index.html")
PJ = "piece-jointe-de-ALPHA.pdf"
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


def pj_presentes(page):
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

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.add_init_script(INIT)
        rep = iter(["TESTEUR", "ALPHA", "BETA"])
        page.on("dialog", lambda d: d.accept(next(rep, "X")) if d.type == "prompt" else d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("h1", timeout=10000); time.sleep(1.0)
        page.click("#autoriser-button"); time.sleep(1.5)
        page.click("#autoriser-button"); time.sleep(1.5)
        page.click("#charger-button"); time.sleep(2.5)

        page.click("button:has-text('Créer Projet')"); time.sleep(3.5)   # ALPHA
        alpha = page.evaluate("() => selectedProjectSaveId")
        page.click("button:has-text('Créer Projet')"); time.sleep(3.5)   # BETA (courant)
        beta = page.evaluate("() => selectedProjectSaveId")

        # Le fichier PJ appartient a ALPHA ; BETA le reference aussi (contamination).
        page.evaluate("""async ([alpha, nomPJ, cfg]) => {
            const root = await navigator.storage.getDirectory();
            const dir = await root.getDirectoryHandle('pj', { create: true });
            const w = await (await dir.getFileHandle(nomPJ, { create: true })).createWritable();
            await w.write('contenu ALPHA'); await w.close();
            // ALPHA (autre projet) le reference dans ses donnees locales
            localStorage.setItem(`profile_C${cfg}_${alpha}_attachments`, JSON.stringify({ "7": [{ name: nomPJ }] }));
            localStorage.setItem(`profile_C${cfg}_${alpha}_actions`, JSON.stringify([{ id: 7, projectId: 3, numeroRef: 'ALP-001-007' }]));
        }""", [alpha, PJ, page.evaluate("() => activeConfig")])

        # Etat contamine du projet courant BETA : une thematique + une action portant la PJ d'ALPHA.
        page.evaluate("""([nomPJ]) => {
            projects = [{ id: 3, numeroRef: 'BET-001', name: 'THEMATIQUE-CONTAMINEE', prefix: 'BET', numSequentiel: 1 }];
            actions  = [{ id: 7, projectId: 3, numeroRef: 'BET-001-007', description: 'action contaminee', hasAttachments: true, status: 'En cours', priority: 'Moyenne', topic: '', responsible: '', startDate: '2026-07-20', deadline: '2026-07-30', notes: '' }];
            attachments = { 7: [{ name: nomPJ }] };
            projectCounters = { 3: 2 };
            chargerProjets(); chargerActions();
        }""", [PJ])

        R["pj_au_depart"] = pj_presentes(page)

        # 1) Suppression de l'ACTION (vraie fonction du module).
        page.evaluate("() => supprimerAction(7)"); time.sleep(5.0)
        R["pj_apres_suppression_action"] = pj_presentes(page)

        # 2) Suppression de la THEMATIQUE (on re-contamine pour tester ce chemin-la).
        page.evaluate("""([nomPJ]) => {
            actions = [{ id: 8, projectId: 3, numeroRef: 'BET-001-008', description: 'autre', hasAttachments: true, status: 'En cours', priority: 'Moyenne', topic: '', responsible: '', startDate: '2026-07-20', deadline: '2026-07-30', notes: '' }];
            attachments = { 8: [{ name: nomPJ }] };
            chargerActions();
        }""", [PJ])
        page.evaluate("() => supprimerProjet(3)"); time.sleep(5.0)
        R["pj_apres_suppression_thematique"] = pj_presentes(page)

        R["pj_preservee"] = PJ in R["pj_apres_suppression_thematique"]
        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        R["ERREUR"] = f"{type(e).__name__}: {str(e)[:300]}"
    print(json.dumps(R, indent=2, ensure_ascii=False))
    print("\nVERDICT :", "OK - PJ d'ALPHA preservee dans les 2 cas" if R.get("pj_preservee")
          else "ECHEC - la PJ d'ALPHA a ete effacee")
