"""Banc de controle des pages TRADUITES (T0, feuille de route 4-sexies, 23/09/2026).

(a) PAGES BLANCHES (defaut 1, remontee Video Studio) : luminosite moyenne de la page traduite > 235 ET superieure d'au
    moins 15 points a celle de l'original -> le dessin a ete efface. Gratuit, instantane.
(b) TEXTE NON LATIN RESTANT (defaut 2, option --cjk) : une question Gemini par page traduite (« reste-t-il du texte
    chinois / japonais / coreen, hors onomatopees dessinees ? ») -> nombre de textes restes, par type. ~0,001 $ / page,
    freine a 18 appels/min par le gateway (nc.post).
(c) CASES EFFACEES (remontee Video Studio 24/09, leur critere) : blocs de 24 px blancs unis dans la traduction la ou
    l'original avait du dessin (mesure_cases_effacees.py). > 20 % de la page = SIGNALE, a regarder (non bloquant : une
    page de grands encadres correctement blanchis monte aussi a ~20 %, OPM ch.5 p.3). Gratuit.
Sortie : une ligne par chapitre + total ; `--json` ecrit le detail. Ne modifie RIEN.
Usage : python controle_traduction.py one-punch-man [1-10] [--cjk] [--pages 1:12,3:7] [--langue fr]
"""
import argparse, base64, json, os, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import narrate_chapter as nc          # noqa: E402  (appel_vision, parse_json, cout, frein du gateway)
from PIL import Image, ImageStat      # noqa: E402
from mesure_cases_effacees import cases_effacees   # noqa: E402
SEUIL_CASES = 20.0

SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
Q_CJK = ("Page de manga TRADUITE en francais. Reste-t-il du texte en caracteres chinois, japonais ou coreens ? "
         "Ignore les onomatopees DESSINEES (effets sonores stylises integres au dessin) : ne les compte pas. "
         "Compte tout le reste : bulles, encadres de narration ou de pensee, cris, panneaux, titres. "
         "JSON uniquement : {\"restes\":[{\"texte\":\"...\",\"type\":\"bulle|encadre|cri|titre|autre\",\"ou\":\"haut gauche...\"}]}")


def lum(f):
    return ImageStat.Stat(Image.open(f).convert("L")).mean[0]


def cjk_page(f, stats):
    content = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(nc.page_jpeg(f, 1000)).decode()}}]
    for budget in (3000, 8000):
        texte, u = nc.appel_vision("gemini", Q_CJK, content, budget)
        stats["cout"] += nc.cout(nc.ENGINES["gemini"][1], u)
        try:
            return [r for r in nc.parse_json(texte).get("restes") or [] if isinstance(r, dict)]
        except Exception:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("serie")
    ap.add_argument("chapitres", nargs="?", default="")
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--cjk", action="store_true")
    ap.add_argument("--pages", default="", help="restreindre (b) a ces pages : 1:12,3:7")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    nc.SECRET = nc._secret()
    chs = sorted((d for d in os.listdir(os.path.join(SRC, a.serie)) if d.startswith("ch_")), key=lambda d: float(d[3:].replace("-", ".")))
    if a.chapitres:
        lo, _, hi = a.chapitres.partition("-")
        chs = [d for d in chs if float(lo) <= float(d[3:]) <= float(hi or lo)]
    cibles = {tuple(x.split(":")) for x in a.pages.split(",") if ":" in x}
    stats, detail, tot_b, tot_c, tot_cases = {"cout": 0.0}, {}, 0, 0, 0
    for d in chs:
        cd = os.path.join(SRC, a.serie, d); td = os.path.join(cd, "traduction", a.langue)
        tj = os.path.join(td, "traduction.json")
        if not os.path.isfile(tj):
            print("%-7s pas de traduction %s" % (d, a.langue)); continue
        t = json.load(open(tj, encoding="utf-8"))
        pages = [x for x in t.get("pages") or [] if os.path.isfile(os.path.join(td, x["file"])) and os.path.isfile(os.path.join(cd, x["source"]))]
        blanches = []
        for x in pages:
            lt, lo_ = lum(os.path.join(td, x["file"])), lum(os.path.join(cd, x["source"]))
            if lt > 235 and lt - lo_ >= 15:
                blanches.append(x["page"])
        cases = [(x["page"], round(v, 1)) for x in pages
                 for v in [cases_effacees(Image.open(os.path.join(cd, x["source"])), Image.open(os.path.join(td, x["file"])))]
                 if v > SEUIL_CASES]
        tot_cases += len(cases)
        restes = {}
        if a.cjk:
            vis = [x for x in pages if not cibles or (d[3:], str(x["page"])) in cibles]
            with ThreadPoolExecutor(max_workers=4) as ex:
                for x, r in zip(vis, ex.map(lambda x: cjk_page(os.path.join(td, x["file"]), stats), vis)):
                    if r:
                        restes[x["page"]] = r
        n_c = sum(len(v) for v in restes.values())
        tot_b += len(blanches); tot_c += n_c
        detail[d] = {"version": t.get("version"), "pages": len(pages), "blanches": blanches, "cases_effacees": cases,
                     "restes": {str(k): v for k, v in restes.items()}}
        print("%-7s v%-7s %3d p. | blanches %2d %s | cases effacees > %d %% : %s%s" % (d, t.get("version"), len(pages), len(blanches), blanches,
              int(SEUIL_CASES), cases or "0",
              (" | textes non latins restes %d sur %d page(s)" % (n_c, len(restes))) if a.cjk else ""), flush=True)
    print("TOTAL : %d page(s) blanche(s) · %d page(s) a cases effacees > %d %% (a regarder)%s%s" % (tot_b, tot_cases, int(SEUIL_CASES), (" · %d texte(s) non latin(s) restant(s)" % tot_c) if a.cjk else "",
                                                 (" · %.3f $" % stats["cout"]) if a.cjk else ""))
    if a.json:
        json.dump(detail, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if tot_b else 0


if __name__ == "__main__":
    sys.exit(main())
