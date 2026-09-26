# -*- coding: utf-8 -*-
"""v2.79.2 (journal du telephone de Quang, 26/09 12h54:31) : UN SEUL suivi de capture a la fois. En arriere-plan, le telephone
empilait les suivis (un toutes les 1,5 s, chacun en attente du reseau) ; au retour, ~40 finissaient ENSEMBLE : 40 lignes
« capture en serie terminee » en 50 ms, 40 rechargements de la bibliotheque (et 40 pochettes/fiches demandees en v2.75+).
Rejouable : python app_patch_2792_suivi_unique.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.79.2"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""async function suivreCapture(){
  const s = await api("/manga/fetch_status");""",
"""// v2.79.2 : un seul suivi a la fois (le telephone en arriere-plan les empilait, puis ~40 finissaient ensemble)
let SUIVI_OCCUPE = false;
async function suivreCapture(){
  if (SUIVI_OCCUPE) return;
  SUIVI_OCCUPE = true;
  try { await suivreCaptureCorps(); } finally { SUIVI_OCCUPE = false; }
}
async function suivreCaptureCorps(){
  const s = await api("/manga/fetch_status");""")
rep("<title>Manga Studio v2.79.1</title>", "<title>Manga Studio v2.79.2</title>")
rep('<span class="ver" id="verBadge">v2.79.1</span>', '<span class="ver" id="verBadge">v2.79.2</span>')
rep('const VERSION = "2.79.1";', 'const VERSION = "2.79.2";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.79.2 applique")
