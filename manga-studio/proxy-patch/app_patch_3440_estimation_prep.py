# -*- coding: utf-8 -*-
"""v3.4.4 (27/09, Quang 19h20 : « tu as bien fait attention a ce que le calcul des couts soit juste ») : les estimations de
PREPARATION des Dialogues utilisaient une constante devinee (0,004 $ / page) ; mesure reelle = ~0,011 $ / page (x 2,8).
Desormais : dlgPrepUsd() = l'etalonnage MESURE (estimation.py 1.1.0 -> ETAL.dialogues.usd, mediane du journal des
depenses), repli 0,011. Toutes les annonces (bloc, nouvelle plage, verification, Tout faire / refaire, oublier, aide) le
suivent. Suppose v3.4.3. Rejouable."""
import re, sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.4.4" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.4.3" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3430_video_musique.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)
rep("<title>Manga Studio v3.4.3</title>", "<title>Manga Studio v3.4.4</title>")
rep('<span class="ver" id="verBadge">v3.4.3</span>', '<span class="ver" id="verBadge">v3.4.4</span>')
rep('const VERSION = "3.4.3";', 'const VERSION = "3.4.4";   // v3.4.4 : estimation de preparation des Dialogues MESUREE (etalonnage), plus 0,004 $ devine')
n0 = s.count("0.004 * ") + s.count("fmtUsd(0.004)")
s = s.replace("fmtUsd(0.004)", "fmtUsd(dlgPrepUsd())").replace("0.004 * ", "dlgPrepUsd() * ")
assert n0 == 9, n0
rep("const dlgTarifTrad = () =>", "const dlgPrepUsd = () => (ETAL && ETAL.dialogues && ETAL.dialogues.usd) || 0.011;   // v3.4.4 : $ / page MESURE (estimation.py 1.1.0)" + N + "const dlgTarifTrad = () =>")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.4.4 (%d estimations remplacees)" % n0)
