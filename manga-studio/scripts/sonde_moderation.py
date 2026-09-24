# -*- coding: utf-8 -*-
"""SONDE DE MODERATION REELLE (24/09/2026, § 4-decies « essai reel ») : quelles pages un moteur refuse-t-il VRAIMENT ?

Les bancs de moderation utilisent des refus SIMULES. Ici on pose une vraie question (celle des noms, la moins chere,
reflexion « minimal » pour Gemini) sur de vraies pages, et on compte les refus reconnus par moderation.py + la reponse
brute du 1er refus (pour verifier que le format reel est bien celui que le code attend). Ne modifie rien, n'ecrit que
son rapport (scripts/sonde_moderation_<moteur>.json).
Usage : python sonde_moderation.py claymore/ch_2 --moteur gemini [--pages 1-179 | --echantillon 20]
"""
import argparse, base64, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre"); ap.add_argument("--moteur", default="gemini", choices=["gemini", "kimi"])
    ap.add_argument("--pages", default=""); ap.add_argument("--echantillon", type=int, default=0)
    ap.add_argument("--sortie", default="", help="rapport ailleurs que scripts/ (application secondaire : ses donnees)")
    a = ap.parse_args()
    if a.moteur == "gemini":
        os.environ["MANGA_GEMINI_REFLEXION"] = "minimal"
    import narrate_chapter as nc, moderation as mod
    nc.SECRET = nc._secret()
    cd = os.path.join(nc.SOURCES, a.chapitre)
    pages = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))["pages"]
    nums = list(range(1, len(pages) + 1))
    if a.pages:
        d, f = (a.pages.split("-") + [a.pages])[:2]; nums = list(range(int(d), int(f) + 1))
    if a.echantillon:
        nums = sorted(random.Random(5).sample(nums, min(a.echantillon, len(nums))))
    refus, ok, erreurs, cout, t0 = [], 0, [], 0.0, time.time()
    for n in nums:
        p = pages[n - 1]
        img = base64.b64encode(nc.page_jpeg(os.path.join(cd, p["file"]))).decode()
        content = [{"type": "text", "text": nc.Q_NOMS}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img}}]
        try:
            _txt, u = nc.appel_vision(a.moteur, "Reponds uniquement en JSON.", content, 4000)
            cout += nc.cout(nc.ENGINES[a.moteur][1], u); ok += 1
        except mod.Refus as e:
            refus.append({"page": n, "fichier": p["file"], "motif": e.motif[:300]})
            print("  REFUS p.%d : %s" % (n, e.motif[:120]), flush=True)
        except Exception as e:
            erreurs.append({"page": n, "err": str(e)[:200]})
            print("  erreur p.%d : %s" % (n, str(e)[:120]), flush=True)
        if n % 20 == 0:
            print("  ... p.%d (%d ok, %d refus)" % (n, ok, len(refus)), flush=True)
    r = {"chapitre": a.chapitre, "moteur": a.moteur, "pages": len(nums), "ok": ok, "refus": refus, "erreurs": erreurs,
         "cout": round(cout, 4), "s": round(time.time() - t0), "quand": time.strftime("%Y-%m-%dT%H:%M:%S")}
    __import__("depenses").noter("essai", a.chapitre, "sonde-moderation", a.moteur, cout)     # une depense reste une depense
    json.dump(r, open(a.sortie or os.path.join(HERE, "sonde_moderation_%s.json" % a.moteur), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%s %s : %d pages · %d acceptees · %d REFUS · %d erreurs · %.3f $ · %d s"
          % (a.moteur, a.chapitre, len(nums), ok, len(refus), len(erreurs), cout, r["s"]))


if __name__ == "__main__":
    main()
