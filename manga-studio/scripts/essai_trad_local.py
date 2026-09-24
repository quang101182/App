"""ESSAI (24/09) : TRADUCTION par un LLM local (Ollama), a partir du texte deja lu -- isole la qualite de traduction.

Pour chaque page tiree des chapitres donnes : les textes lus (traduction.json, colonne « texte ») sont envoyes EN BLOC
(le contexte de la page aide : qui parle, ton), le modele rend une traduction par bulle. On compare a Gemini (colonne
« trad »). Juge : --juge kimi|groq|deepseek appelle llm.py a l'aveugle (A/B melanges) et note chaque ligne 0/1/2.
Ne modifie rien. Usage :
  python essai_trad_local.py --modele qwen3:30b-a3b-instruct-2507-q4_K_M --pages 6 one-punch-man/ch_3 one-punch-man/ch_10
"""
import argparse, json, os, random, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
LLM = r"D:/Download/02-Apps-Web/Repo-github/llm-cli/llm.py"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONSIGNE = ("Tu traduis une page de manga (chinois traditionnel) en francais. Ci-dessous, les bulles de la page dans "
            "l'ordre de lecture, une par ligne « id: texte ». Traduis chacune en francais naturel et vivant, registre de "
            "manga, en gardant les noms propres (Genos, Saitama...) et le ton (cris en MAJUSCULES si l'original crie). "
            "Reponds UNIQUEMENT en JSON : {\"<id>\": \"traduction\", ...}\n\n")


def ollama(modele, prompt, timeout=600):
    body = {"model": modele, "prompt": prompt, "stream": False, "format": "json", "think": False,
            "options": {"temperature": 0.3, "num_ctx": 8192}, "keep_alive": "15m"}
    r = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))["response"]


def juger(juge, lignes):
    """Juge a l'aveugle : pour chaque bulle, deux traductions A/B (ordre tire au sort) notees 0/1/2."""
    ordre = [random.random() < 0.5 for _ in lignes]
    txt = "\n".join("%d. ORIGINAL: %s\n   A: %s\n   B: %s" % (i, l["texte"], *( (l["loc"], l["gem"]) if o else (l["gem"], l["loc"]) ))
                    for i, (l, o) in enumerate(zip(lignes, ordre)))
    q = ("Tu es relecteur de traductions de manga chinois -> francais. Pour chaque bulle, note A et B : 2 = juste et "
         "naturel, 1 = sens correct mais maladroit, 0 = contresens / oubli / pas du francais. Reponds UNIQUEMENT en JSON "
         "{\"notes\": [[noteA, noteB], ...]} dans l'ordre.\n\n" + txt)
    out = subprocess.run([sys.executable, LLM, juge, q, "--max-tokens", "16000"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=600).stdout
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        raise SystemExit("juge : reponse illisible -- " + out[-600:])
    notes = json.loads(m.group(0))["notes"]
    return [(n[0], n[1]) if o else (n[1], n[0]) for n, o in zip(notes, ordre)]      # -> (local, gemini)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitres", nargs="+"); ap.add_argument("--modele", required=True)
    ap.add_argument("--pages", type=int, default=6); ap.add_argument("--graine", type=int, default=3)
    ap.add_argument("--juge", default=""); ap.add_argument("--out", default="")
    a = ap.parse_args()
    pages = []
    for rel in a.chapitres:
        t = json.load(open(os.path.join(SRC, rel, "traduction", "fr", "traduction.json"), encoding="utf-8"))
        for p in t["pages"]:
            bs = [b for b in p["bulles"] if (b.get("texte") or "").strip() and (b.get("trad") or "").strip()
                  and b.get("type") in ("dialogue", "narration")]
            if len(bs) >= 3:
                pages.append((rel, p["page"], bs))
    random.Random(a.graine).shuffle(pages)
    lignes, t_tot = [], 0.0
    for rel, num, bs in pages[:a.pages]:
        prompt = CONSIGNE + "\n".join("%s: %s" % (b["id"], b["texte"].replace("\n", " ")) for b in bs)
        t0 = time.time()
        try:
            r = json.loads(ollama(a.modele, prompt))
        except Exception as e:
            r = {}; print("  ERREUR", e)
        dt = time.time() - t0; t_tot += dt
        print("== %s p.%d : %d bulles, %.1f s" % (rel, num, len(bs), dt))
        for b in bs:
            loc = str(r.get(str(b["id"])) or "")
            lignes.append({"texte": b["texte"], "gem": b["trad"], "loc": loc})
            print("   G: %-60s\n   L: %s" % (b["trad"][:60], loc[:60]))
    print("\n%d bulles, %.1f s par page" % (len(lignes), t_tot / max(1, a.pages)))
    if a.juge:
        notes = juger(a.juge, lignes)
        for l, n in zip(lignes, notes):
            l["note_local"], l["note_gemini"] = n
        sl, sg = sum(n[0] for n in notes), sum(n[1] for n in notes)
        print("JUGE %s (aveugle) : local %d/%d (%d %%) | Gemini %d/%d (%d %%) | local >= Gemini sur %d/%d bulles"
              % (a.juge, sl, 2 * len(notes), 50 * sl // len(notes), sg, 2 * len(notes), 50 * sg // len(notes),
                 sum(n[0] >= n[1] for n in notes), len(notes)))
    if a.out:
        json.dump(lignes, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
