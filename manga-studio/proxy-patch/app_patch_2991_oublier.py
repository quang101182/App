# -*- coding: utf-8 -*-
"""v2.99.1 (27/09, Quang 16h26 : « oui go ») : « 🗑 Oublier cette plage » dans le menu ⋯ d'une plage des Dialogues
(maquette_dialogues_compact_v1 A3). Confirmation qui dit ce qui est range ; POST /manga/dialogues_oublier (patch_dialogues_11 :
rien n'est efface, tout est archive) ; puis la liste revient sur une autre plage. Suppose v2.99.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.99.1" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v2.99.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_2990_dialogues_compacts.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.99.0</title>", "<title>Manga Studio v2.99.1</title>")
rep('<span class="ver" id="verBadge">v2.99.0</span>', '<span class="ver" id="verBadge">v2.99.1</span>')
rep('const VERSION = "2.99.0";', 'const VERSION = "2.99.1";   // v2.99.1 : « Oublier cette plage » (Dialogues, rien n est efface : archive)')
rep("""      + '<button data-dpl="refaire" data-k="' + esc(k) + '">↻ <span>Refaire la préparation<small>l\\'IA relit ces pages</small></span></button></div>';""",
    """      + '<button data-dpl="refaire" data-k="' + esc(k) + '">↻ <span>Refaire la préparation<small>l\\'IA relit ces pages</small></span></button>'
      + '<button data-dpl="oublier" data-k="' + esc(k) + '" style="color:var(--ko)">🗑 <span>Oublier cette plage<small>rangée à part, rien n\\'est effacé</small></span></button></div>';""")
rep("""    else if (act === "nouv"){""",
    """    else if (act === "oublier") dplOublier(k);
    else if (act === "nouv"){""")
rep("""async function dplLire(k){""",
    """async function dplOublier(k){                   // v2.99.1 : la plage quitte la liste ; repliques et video sont ARCHIVEES
  const x = dplInfo(k);
  if (!confirm("Oublier " + dplTitre(k) + " ?\\n\\n" + x.reps + " réplique" + (x.reps > 1 ? "s" : "") + (x.v ? " et sa vidéo" : "")
      + " quittent la liste. Rien n'est effacé : c'est rangé à part dans le dossier du chapitre."
      + "\\nLes pages encore couvertes par une autre plage gardent leurs répliques.")) return;
  DPL.menu = "";
  try { const r = await api("/manga/dialogues_oublier", { d: CHAP_OPEN, portee: k }); if (r.error) throw new Error(r.error);
        toast("🗑 " + dplTitre(k) + " oubliée (rangée à part)"); }
  catch (err) { return toast("oublier : " + err.message); }
  DLG.d = "";                                   // recharge complete (comme un chapitre ouvert a neuf)
  await dlgCharger();
  const ks = dplListe();
  if (ks.length) dplChoisir(ks[ks.length - 1]); else { DLG.portee = "chap"; $("dlgDe").value = ""; $("dlgA").value = ""; dlgRendre(); }
}
async function dplLire(k){""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v2.99.1")
