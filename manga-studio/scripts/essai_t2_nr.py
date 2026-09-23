"""Essai REEL T2 + NR (4-sexies, 23/09/2026) sur des COPIES : traduire_chapitre v1.94.0 compare a la traduction actuelle.

T2 : OPM (chinois) sur les pages citees par Video Studio -> les textes hors bulles sont-ils traduits ?
NR : Black Jack ch.1 (japonais -> fr ET -> en), Noritaka ch.1 p.1-15 (anglais -> fr) -> rien ne se degrade ?
Par page : blanche ou non ; bulles traduites AVANT / APRES ; textes « hors zones » ajoutes (texte -> traduction).
Les copies zz- sont GARDEES (relecture a l'oeil), supprimees par : python essai_t2_nr.py --nettoyer
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import banc_outils as bo                                  # noqa: E402
from PIL import Image, ImageStat                          # noqa: E402

PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"
PLAN = [("one-punch-man", "zz-banc-opm", {"ch_1": "12-22", "ch_2": "9-10", "ch_3": "1-13", "ch_4": "11-23", "ch_5": "2-14",
                                          "ch_6": "1-11", "ch_7": "1-6", "ch_8": "1-11", "ch_9": "7-18", "ch_10": "22-22"}, ["fr"]),
        ("black-jack-ni-yoroshiku", "zz-banc-bj", {"ch_1": "1-19"}, ["fr", "en"]),
        ("noritaka", "zz-banc-nori", {"ch_1": "1-15"}, ["fr"])]
SEULES = [x for x in sys.argv[1:] if x.startswith("zz-")]          # ex. zz-banc-bj zz-banc-nori : seulement ces series
if SEULES:
    PLAN = [x for x in PLAN if x[1] in SEULES]
if "--nettoyer" in sys.argv:
    for _, dst, _, _ in PLAN:
        bo.supprimer_serie(dst)
    print("copies supprimees"); sys.exit(0)


def traduites(p):
    return sum(1 for b in p["bulles"] if (b.get("trad") or "").strip() and b.get("effacement") and not b.get("ecarte"))


def petits(p):
    return sum(1 for b in p["bulles"] if b.get("taille") and int(b["taille"]) < 12 and b.get("effacement") and not b.get("ecarte"))


def lum(f):
    return ImageStat.Stat(Image.open(f).convert("L")).mean[0]


env = dict(os.environ, PYTHONIOENCODING="utf-8")
cout, bilan = 0.0, []
for src, dst, chs, langues in PLAN:
    bo.copier_serie(src, dst, list(chs), avec=("serie.json",))
    for ch, plage in chs.items():
        for lg in langues:
            tj_av = os.path.join(bo.SRC, src, ch, "traduction", lg, "traduction.json")
            avant = {p["page"]: p for p in json.load(open(tj_av, encoding="utf-8"))["pages"]} if os.path.isfile(tj_av) else {}
            r = subprocess.run([PY, os.path.join(HERE, "traduire_chapitre.py"), dst + "/" + ch, "--langue", lg, "--engine", "gemini",
                                "--pages", plage], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            td = os.path.join(bo.SRC, dst, ch, "traduction", lg)
            t = json.load(open(os.path.join(td, "traduction.json"), encoding="utf-8"))
            cout += (t.get("stats") or {}).get("cout", 0)
            ta = tp = pa = pp = 0; blanches, ajouts, moins = [], [], []
            for p in t["pages"]:
                av = avant.get(p["page"])
                n_av, n_ap = (traduites(av) if av else 0), traduites(p)
                ta += n_av; tp += n_ap; pa += petits(av) if av else 0; pp += petits(p)
                if n_ap < n_av:
                    moins.append((p["page"], n_av, n_ap))
                lt, lo = lum(os.path.join(td, p["file"])), lum(os.path.join(bo.SRC, dst, ch, p["source"]))
                if lt > 235 and lt - lo >= 15:
                    blanches.append(p["page"])
                for b in p["bulles"]:
                    if b.get("hors_zone"):
                        ajouts.append("p%d %s « %s » -> « %s »" % (p["page"], "POSE" if b.get("effacement") and not b.get("ecarte")
                                      else "ecarte(%s)" % (b.get("ecarte") or b.get("effacement")), (b.get("texte") or "")[:30], (b.get("trad") or "")[:40]))
            ligne = "%s %s -> %s p.%s : code %d | blanches %s | bulles traduites %d -> %d | textes minuscules (<12) %d -> %d%s | hors zones %d" % (
                dst, ch, lg, plage, r.returncode, blanches or 0, ta, tp, pa, pp, (" | EN MOINS %s" % moins) if moins else "", len(ajouts))
            print(ligne, flush=True)
            for x in ajouts:
                print("    " + x, flush=True)
            bilan.append(ligne)
print("\ncout de l'essai : %.3f $ ; copies GARDEES pour relecture (--nettoyer pour supprimer)" % cout)
