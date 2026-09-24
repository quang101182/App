# -*- coding: utf-8 -*-
"""BANC (24/09/2026) : la TRADUCTION avec moins de reflexion Gemini est-elle aussi bonne ? Ne modifie pas l'app.

1. `lancer` : traduit le MEME chapitre 3 fois (MANGA_GEMINI_REFLEXION = defaut / low / minimal) dans des dossiers
   d'essai (--sortie), jamais dans traduction/<langue>/ : les vraies traductions ne sont pas touchees.
2. `juger` : pour chaque bulle presente dans les 3 (appariee par page + texte lu), deux juges (DeepSeek, Kimi) notent
   A/B a l'aveugle (ordre tire au sort) : 2 = juste et naturel, 1 = sens correct mais maladroit, 0 = contresens / oubli.
   Comparaisons : defaut vs low, defaut vs minimal. Cout et duree lus dans les traduction.json.
Usage : python banc_reflexion_trad.py lancer one-punch-man/ch_3
        python banc_reflexion_trad.py juger  one-punch-man/ch_3 [--juges deepseek,kimi]
"""
import json, os, random, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
LLM = r"D:/Download/02-Apps-Web/Repo-github/llm-cli/llm.py"
NIVEAUX = ["defaut", "low", "minimal"]
# la traduction a besoin du venv du proxy (ultralytics, torch) -- le meme que MANGA_PY du proxy
PY = os.environ.get("MANGA_PY", "D:/Download/02-Apps-Web/kohya-trainer/.venv/Scripts/python.exe")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sortie(chap, niv):
    return os.path.join(SRC, chap, "_banc_reflexion", niv)


def lancer(chap):
    for niv in NIVEAUX:
        env = dict(os.environ, PYTHONIOENCODING="utf-8", MANGA_GEMINI_REFLEXION="" if niv == "defaut" else niv)
        t0 = time.time()
        r = subprocess.run([PY, os.path.join(HERE, "traduire_chapitre.py"), chap, "--langue", "fr",
                            "--engine", "gemini", "--sortie", sortie(chap, niv)], env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=3600)
        print("%-8s code %d · %.0f s · %s" % (niv, r.returncode, time.time() - t0, (r.stderr or r.stdout).strip().splitlines()[-1:]), flush=True)


def bulles(chap, niv):
    t = json.load(open(os.path.join(sortie(chap, niv), "traduction.json"), encoding="utf-8"))
    out = {}
    for p in t["pages"]:
        for b in p.get("bulles") or []:
            tx, tr = (b.get("texte") or "").strip(), (b.get("trad") or "").strip()
            if tx and tr and b.get("type") in ("dialogue", "narration"):
                out[(p["page"], re.sub(r"\s+", "", tx))] = {"texte": tx, "trad": tr}
    return out, t.get("stats") or {}


def noter(juge, lignes, graine):
    """Par paquets de 20 (un juge qui en saute une sur 56 rend tout le paquet inutilisable) ; un nouvel essai si le
    compte ne tombe pas juste."""
    out = []
    for i in range(0, len(lignes), 20):
        for essai in (1, 2):
            try:
                out += _noter(juge, lignes[i:i + 20], graine + i + essai)
                break
            except SystemExit as e:
                if essai == 2:
                    raise
                print("      (paquet %d : %s -> nouvel essai)" % (i // 20 + 1, str(e)[:80]))
    return out


def _noter(juge, lignes, graine):
    rnd = random.Random(graine)
    ordre = [rnd.random() < 0.5 for _ in lignes]
    txt = "\n".join("%d. ORIGINAL: %s\n   A: %s\n   B: %s" % (i, l["texte"], *((l["x"], l["ref"]) if o else (l["ref"], l["x"])))
                    for i, (l, o) in enumerate(zip(lignes, ordre)))
    q = ("Tu es relecteur de traductions de manga -> francais. Pour chaque bulle, note A et B : 2 = juste et naturel, "
         "1 = sens correct mais maladroit, 0 = contresens / oubli / pas du francais. Reponds UNIQUEMENT en JSON "
         "{\"notes\": [[noteA, noteB], ...]} dans l'ordre, une paire par bulle.\n\n" + txt)
    out = subprocess.run([sys.executable, LLM, juge, q, "--max-tokens", "16000"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900).stdout
    m = re.search(r"\{.*\}", out, re.S)
    notes = json.loads(m.group(0))["notes"] if m else []
    if len(notes) != len(lignes):
        raise SystemExit("juge %s : %d notes pour %d bulles -- %s" % (juge, len(notes), len(lignes), out[-300:]))
    return [(n[1], n[0]) if o else (n[0], n[1]) for n, o in zip(notes, ordre)]          # -> (ref, x)


def juger(chap, juges):
    ref, sref = bulles(chap, "defaut")
    print("defaut  : %d bulles · %.4f $ · %.0f s" % (len(ref), sref.get("cout", 0), sref.get("s", 0)))
    for niv in NIVEAUX[1:]:
        x, sx = bulles(chap, niv)
        cles = [k for k in ref if k in x]
        lignes = [{"texte": ref[k]["texte"], "ref": ref[k]["trad"], "x": x[k]["trad"]} for k in cles]
        ident = sum(l["ref"] == l["x"] for l in lignes)
        print("\n%-8s: %d bulles · %.4f $ (%+.0f %%) · %.0f s · %d appariees, %d identiques au mot pres"
              % (niv, len(x), sx.get("cout", 0), 100 * (sx.get("cout", 0) / max(1e-9, sref.get("cout", 0)) - 1), sx.get("s", 0),
                 len(cles), ident))
        for j in juges:
            n = noter(j, lignes, 7)
            sr, sx_ = sum(a for a, _ in n), sum(b for _, b in n)
            print("   juge %-8s : defaut %d/%d (%d %%) · %s %d/%d (%d %%) · %s pire sur %d bulle(s)"
                  % (j, sr, 2 * len(n), 50 * sr // len(n), niv, sx_, 2 * len(n), 50 * sx_ // len(n), niv, sum(b < a for a, b in n)))
            for l, (a, b) in zip(lignes, n):
                if b < a:
                    print("      - %s\n        defaut : %s\n        %-7s: %s" % (l["texte"][:70], l["ref"][:90], niv, l["x"][:90]))


if __name__ == "__main__":
    act, chap = sys.argv[1], sys.argv[2]
    juges = (sys.argv[sys.argv.index("--juges") + 1] if "--juges" in sys.argv else "deepseek,kimi").split(",")
    lancer(chap) if act == "lancer" else juger(chap, juges)
