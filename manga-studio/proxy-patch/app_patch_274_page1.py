# -*- coding: utf-8 -*-
"""v2.74.0 (Quang 26/09 13h06) : capture -- « depuis la page 1 » COCHEE d'office, et le choix est MEMORISE sur l'appareil.
Rejouable : python app_patch_274_page1.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.74.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""$("capBox").addEventListener("toggle", () => { try { localStorage.setItem("manga_capture_ouvert", $("capBox").open ? "1" : "0"); } catch {} });""",
"""$("capBox").addEventListener("toggle", () => { try { localStorage.setItem("manga_capture_ouvert", $("capBox").open ? "1" : "0"); } catch {} });
// v2.74.0 : « depuis la page 1 » cochee d'office ; si on la decoche, le choix est garde sur l'appareil
try { $("capPage1").checked = localStorage.getItem("manga_cap_page1") !== "0"; } catch { $("capPage1").checked = true; }
$("capPage1").addEventListener("change", () => { try { localStorage.setItem("manga_cap_page1", $("capPage1").checked ? "1" : "0"); } catch {} });""")
rep("<title>Manga Studio v2.73.1</title>", "<title>Manga Studio v2.74.0</title>")
rep('<span class="ver" id="verBadge">v2.73.1</span>', '<span class="ver" id="verBadge">v2.74.0</span>')
rep('const VERSION = "2.73.1";', 'const VERSION = "2.74.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.74.0 applique")
