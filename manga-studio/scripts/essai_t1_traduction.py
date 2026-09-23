"""Essai REEL de T1 (4-sexies, 23/09/2026) sur des COPIES : les pages OPM devenues blanches, retraduites par
traduire_chapitre v1.93.0, doivent garder leur dessin. Copie zz-banc-trad (supprimee a la fin), plages de pages
couvrant les 20 pages touchees (~73 pages, ~0,7 $). Controle = controle_traduction.py (a).
Usage : python essai_t1_traduction.py
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import banc_outils as bo                                  # noqa: E402

PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"
DST = "zz-banc-trad"
# chapitre -> (plage retraduite, pages blanches AVANT)
CIBLES = {"ch_1": ("12-22", [12, 18, 22]), "ch_2": ("9-9", [9]), "ch_3": ("1-7", [1, 7]), "ch_4": ("11-23", [11, 16, 23]),
          "ch_6": ("1-11", [1, 11]), "ch_7": ("1-6", [1, 6]), "ch_8": ("1-11", [1, 11]), "ch_9": ("7-18", [7, 10, 11, 18]),
          "ch_10": ("22-22", [22])}
env = dict(os.environ, PYTHONIOENCODING="utf-8")
try:
    bo.copier_serie("one-punch-man", DST, list(CIBLES), avec=("serie.json",))
    cout = 0.0
    for ch, (plage, avant) in CIBLES.items():
        r = subprocess.run([PY, os.path.join(HERE, "traduire_chapitre.py"), DST + "/" + ch, "--langue", "fr", "--engine", "gemini",
                            "--pages", plage], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        t = json.load(open(os.path.join(bo.SRC, DST, ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
        cout += (t.get("stats") or {}).get("cout", 0)
        print("%s p.%s : code %d, %d page(s) traduites, etats %s" % (ch, plage, r.returncode, len(t["pages"]),
              sorted({b.get("effacement") for p in t["pages"] for b in p["bulles"] if b.get("effacement")})), flush=True)
    c = subprocess.run([PY, os.path.join(HERE, "controle_traduction.py"), DST], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    print(c.stdout)
    print("cout de l'essai : %.3f $" % cout)
finally:
    bo.supprimer_serie(DST)
    print("copie %s supprimee : %s" % (DST, not os.path.exists(os.path.join(bo.SRC, DST))))
