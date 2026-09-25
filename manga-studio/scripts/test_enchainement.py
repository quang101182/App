# -*- coding: utf-8 -*-
"""Banc v2.17.0 : l'app (capEnchainement, manga_studio.html) et l'outil de capture (enchainement_possible,
manga_fetch.py) disent la MEME chose, pour chaque adresse, sur « ce site permet-il d'enchainer les chapitres ? ».
Les adresses « oui » reprennent les formats reellement suivis par chapitre_suivant() ; les « non » sont des lecteurs
reels sans format suivi (adresse a identifiant interne) et des pages qui ne sont pas des chapitres.
Execute la fonction JS EXTRAITE de l'app (node), pas une copie."""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); MS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(MS, "manga-fetch"))
import importlib.util
sp = importlib.util.spec_from_file_location("mf", os.path.join(MS, "manga-fetch", "manga_fetch.py"))
mf = importlib.util.module_from_spec(sp); sp.loader.exec_module(mf)
CAS = [("https://mangadex.org/chapter/0c5b1f7e-3b52-4a9f-9d0b-12a3b4c5d6e7", True),
       ("https://mangadex.org/title/abc", False),
       ("https://mangaplus.shueisha.co.jp/viewer/1000233", True),
       ("https://www.webtoons.com/fr/fantasy/x/episode-1/viewer?title_no=123&episode_no=1", True),
       ("https://www.webtoons.com/fr/canvas/x/list?title_no=688324", True),
       ("https://manga-scantrad.io/manga/one-piece/vol-12/", True),
       ("https://manga-scantrad.io/manga/one-piece/vol-12-chapitre-105/", True),
       ("https://exemple-scan.fr/manga/serie/chapter-12/", True),
       ("https://exemple-scan.fr/manga/serie/chapitre-12-5/", True),
       ("https://exemple.com/manhwa/serie/chapter-001/", True),
       ("https://exemple.org/series/comic/serie-test/chapter/1", True),      # v0.7.2 / v2.40.0
       ("https://exemple.org/series/comic/serie-test", False),
       ("https://www.exemple.com/lecture-en-ligne/Serie-Chapitre-1-FR_356798.html", False),
       ("https://www.exemple.com/TOP-54.html", False),
       ("https://mangadex.org/", False), ("", False)]
html = open(os.path.join(MS, "manga_studio.html"), encoding="utf-8").read()
fn = re.search(r"function capEnchainement\(url\)\{.*?\n\}\n", html, re.S).group(0)
js = fn + "console.log(JSON.stringify(%s.map(u => capEnchainement(u))));" % json.dumps([u for u, _ in CAS])
res_js = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8").stdout)
ok = ko = 0
for (u, attendu), (j_ok, j_quoi) in zip(CAS, res_js):
    p_ok, p_quoi = mf.enchainement_possible(u)
    bon = p_ok == j_ok == attendu and p_quoi == j_quoi
    ok += bon; ko += not bon
    print("  [%s] %-70s app=%s outil=%s attendu=%s%s" % ("OK" if bon else "KO", u[:70] or "(vide)", j_ok, p_ok, attendu,
                                                       "" if p_quoi == j_quoi else "  libelles: %r / %r" % (j_quoi, p_quoi)))
print("\n%d/%d" % (ok, ok + ko)); sys.exit(1 if ko else 0)
