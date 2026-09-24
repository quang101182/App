"""ESSAI (24/09) : un VLM LOCAL (Ollama) peut-il faire le travail de Gemini -- lire la bulle ET la traduire en francais ?

Reference = ce que Gemini a produit (traduction.json : texte lu + traduction). Pour N bulles tirees des chapitres
donnes, on decoupe la bulle (boite + marge) dans l'ORIGINAL et on demande au modele local {texte, trad} en JSON.
Mesures : lecture (similarite caractere a caractere avec le texte lu par Gemini), temps par bulle, JSON valide ;
les traductions sont ecrites cote a cote pour une lecture humaine. Ne modifie rien.
Usage : python essai_vlm_local.py --modele qwen3-vl:8b --n 30 one-punch-man/ch_3 one-punch-man/ch_10
"""
import argparse, base64, difflib, io, json, os, random, re, sys, time, urllib.request
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONSIGNE = ("Voici une bulle de manga (texte en chinois traditionnel ou japonais, souvent VERTICAL, lu de droite a "
            "gauche). 1) Recopie exactement le texte original. 2) Traduis-le en francais naturel, registre de manga, "
            "sans rien ajouter. Reponds UNIQUEMENT en JSON : {\"texte\": \"...\", \"trad\": \"...\"}")


def ollama(modele, img, timeout=180):
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=92)
    body = {"model": modele, "prompt": CONSIGNE, "images": [base64.b64encode(buf.getvalue()).decode()], "stream": False,
            "format": "json", "options": {"temperature": 0.2, "num_ctx": 4096}, "keep_alive": "10m"}
    r = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))["response"]


def norm(t):
    return re.sub(r"[\s…\.\,，。！？!?、「」『』\-~ー]+", "", t or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitres", nargs="+"); ap.add_argument("--modele", default="qwen3-vl:8b")
    ap.add_argument("--n", type=int, default=30); ap.add_argument("--graine", type=int, default=7)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    bulles = []
    for rel in a.chapitres:
        t = json.load(open(os.path.join(SRC, rel, "traduction", "fr", "traduction.json"), encoding="utf-8"))
        for p in t["pages"]:
            for b in p["bulles"]:
                if (b.get("texte") or "").strip() and (b.get("trad") or "").strip() and b.get("type") in ("dialogue", "narration"):
                    bulles.append((rel, p["source"], b))
    random.Random(a.graine).shuffle(bulles)
    bulles = bulles[:a.n]
    res, t_tot, ok_json = [], 0.0, 0
    for i, (rel, src, b) in enumerate(bulles, 1):
        im = Image.open(os.path.join(SRC, rel, src)).convert("RGB"); W, H = im.size
        x, y, w, h = b["box"]["x"] * W, b["box"]["y"] * H, b["box"]["w"] * W, b["box"]["h"] * H
        m = 0.25
        crop = im.crop((max(0, x - m * w), max(0, y - m * h), min(W, x + w * (1 + m)), min(H, y + h * (1 + m))))
        if max(crop.size) < 300:
            k = 300 / max(crop.size); crop = crop.resize((int(crop.width * k), int(crop.height * k)))
        t0 = time.time()
        try:
            brut = ollama(a.modele, crop); dt = time.time() - t0
            j = json.loads(brut); ok_json += 1
        except Exception as e:
            dt = time.time() - t0; j = {"texte": "", "trad": "ERREUR %s" % str(e)[:60]}
        t_tot += dt
        sim = difflib.SequenceMatcher(None, norm(b["texte"]), norm(j.get("texte"))).ratio()
        res.append({"ref_texte": b["texte"], "loc_texte": j.get("texte"), "sim": round(sim, 2),
                    "ref_trad": b["trad"], "loc_trad": j.get("trad"), "s": round(dt, 1)})
        print("%2d. lecture %3d %% | %4.1f s | Gemini : %s\n    %s : %s" % (i, 100 * sim, dt, b["trad"][:70], a.modele.split(":")[0], (j.get("trad") or "")[:70]))
    sims = sorted(r["sim"] for r in res)
    print("\n=== %s sur %d bulles : lecture mediane %d %% (>= 90 %% : %d/%d), JSON valide %d/%d, %.1f s/bulle ==="
          % (a.modele, len(res), 100 * sims[len(sims) // 2], sum(s >= 0.9 for s in sims), len(sims), ok_json, len(res), t_tot / len(res)))
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
