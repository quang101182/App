# -*- coding: utf-8 -*-
"""v2.82.3 (27/09, R6 -- Quang 03h35 : « ce format qui deborde en haut et en bas, sans liberte, ne respectant pas la largeur de
l'application ») : l'ecran ✏ « Corriger et régler » des Dialogues prend le GABARIT de l'app (.modal + .modal-in, comme « Suivi &
coûts ») : fenetre centree a la largeur de l'app (<= 760 px), hauteur bornee, en-tete (« ← Chapitre », titre, solde) et pied
(« Générer… », crédits) DANS la fenetre, seul le contenu defile ; toucher a cote = fermer. Suppose app_patch_2822. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.82.3" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.82.2" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2822_doublons.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("""dlgPrep.innerHTML = '<div class="dlgp-haut"><button class="btn sm retour" id="dlgpRet">← Chapitre</button><b id="dlgpTitre">🎭 Dialogues</b>'
  + '<span style="flex:1"></span><span class="dlg-pill cr" id="dlgpSolde"></span></div><div class="dlgp-corps" id="dlgpCorps"></div>'
  + '<div class="dlgp-pied" id="dlgpPied"></div>';""",
    """dlgPrep.className = "modal";                    // v2.82.3 (R6) : le gabarit des fenetres de l'app (comme « Suivi & coûts »)
dlgPrep.innerHTML = '<div class="modal-in dlgp-in"><div class="dlgp-haut"><button class="btn sm retour" id="dlgpRet">← Chapitre</button><b id="dlgpTitre">🎭 Dialogues</b>'
  + '<span style="flex:1"></span><span class="dlg-pill cr" id="dlgpSolde"></span></div><div class="dlgp-corps" id="dlgpCorps"></div>'
  + '<div class="dlgp-pied" id="dlgpPied"></div></div>';""")
rep("""document.body.appendChild(dlgPrep);""", """document.body.appendChild(dlgPrep);
dlgPrep.addEventListener("click", e => { if (e.target === dlgPrep) $("dlgpRet").click(); });   // v2.82.3 : toucher a cote = fermer""")
rep(""".dlgp-pied .muted{font-size:12.5px}""", """.dlgp-pied .muted{font-size:12.5px}
/* v2.82.3 (R6) : fenetre de l'app, pas un plein ecran -- en-tete et pied DANS la fenetre, seul le contenu defile */
#dlgPrep.modal{z-index:85;background:rgba(0,0,0,.62);overflow:hidden}
#dlgPrep .dlgp-in{display:flex;flex-direction:column;padding:0;max-height:90vh;overflow:hidden}
#dlgPrep .dlgp-haut{position:static;background:none;border-bottom:1px solid var(--line);padding:12px 16px}
#dlgPrep .dlgp-corps{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;max-width:none;margin:0;padding:6px 16px 14px}
#dlgPrep .dlgp-pied{position:static;background:var(--panel2);border-radius:0 0 var(--r) var(--r)}
#dlgPrep .dlgp-pied:empty{display:none}""")
s = s.replace("<title>Manga Studio v2.82.2</title>", "<title>Manga Studio v2.82.3</title>", 1)
s = s.replace('id="verBadge">v2.82.2<', 'id="verBadge">v2.82.3<', 1)
s = s.replace('const VERSION = "2.82.2";', 'const VERSION = "2.82.3";   // v2.82.3 : ecran ✏ des Dialogues au gabarit des fenetres de l app (R6)', 1)
assert s.count("2.82.3") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
