# -*- coding: utf-8 -*-
"""App v1.90.0 -> v1.91.0 : temps restant dans la cellule d'activite et son detail (Quang, 22/09 05h37).
Le chiffre vient du proxy (vitesse MESUREE de l'etape) ; absent tant qu'il n'est pas fiable. Verifie ses ancres."""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v191")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.90.0</title>", "<title>Manga Studio v1.91.0</title>"),
             ('id="verBadge">v1.90.0<', 'id="verBadge">v1.91.0<'),
             ('const VERSION = "1.90.0";', 'const VERSION = "1.91.0";')):
    rep(a, b)
rep('''const actFini = it =>''',
    '''// v1.91.0 : temps restant (mesure par le proxy sur la vitesse reelle de l'etape) ; rien tant qu'il n'est pas fiable
const actReste = s => s == null ? "" : s < 60 ? "< 1 min" : s < 3600 ? "~" + Math.round(s / 60) + " min"
  : "~" + Math.floor(s / 3600) + " h " + String(Math.round(s % 3600 / 60)).padStart(2, "0");
const actFini = it =>''')
rep('''  $("actTxt").textContent = it ? ACT_LBL[it.type] + " " + actNom(it) + " " + actProg(it)''',
    '''  $("actTxt").textContent = it ? ACT_LBL[it.type] + " " + actNom(it) + " " + actProg(it) + (it.reste_s != null ? " · " + actReste(it.reste_s) : "")''')
rep('''    const detail = [x.tag || (x.langue ? "→ " + x.langue : ""), ACT_ETAPE[x.etape] || x.etape || "", actProg(x)].filter(Boolean).join(" · ");''',
    '''    const detail = [x.tag || (x.langue ? "→ " + x.langue : ""), ACT_ETAPE[x.etape] || x.etape || "", actProg(x),
                    x.reste_s != null ? "reste " + actReste(x.reste_s) + (x.type === "narration" ? " pour cette étape" : "") : "calcul du temps restant…"]
                   .filter(Boolean).join(" · ");''')
open(p, "w", encoding="utf-8").write(s)
print("patch app v1.91.0 OK")
