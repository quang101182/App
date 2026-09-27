# -*- coding: utf-8 -*-
"""Manga Studio v3.5.0 -- 16e patch serveur (27/09, S4 « Qui parle ? », maquette_qui_parle_v1 validee 20h38) :
/manga/dialogues_verif GARDE « qui » (nom, 40 car. max) sur les entrees « ordre » / « ajouts » ; et sur les pages DEJA preparees,
l'attribution est appliquee TOUT DE SUITE a la replique (exactement comme une correction ✏ : qui + corrige.qui), gratuitement,
sans refaire la preparation. Pas applique si un travail tourne sur le chapitre (la preparation suivante le prendra : dialogues.py
>= 1.27.0 impose « qui »). Appariement = celui de dialogues.py (meme n° et zone proche, meme zone, ou bulle dans le trace).
Suppose patch_dialogues_15. Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _dlg_verif_qui(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_dialogues_verif(d, pages):''', '''def _dlg_iou(a, b):
    x1, y1, x2, y2 = max(a["x"], b["x"]), max(a["y"], b["y"]), min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    i = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    u = a["w"] * a["h"] + b["w"] * b["h"] - i
    return i / u if u > 0 else 0.0


def _dlg_couvre(g, p):
    x1, y1, x2, y2 = max(g["x"], p["x"]), max(g["y"], p["y"]), min(g["x"] + g["w"], p["x"] + p["w"]), min(g["y"] + g["h"], p["y"] + p["h"])
    a = p["w"] * p["h"]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1) / a if a > 0 else 0.0


def _dlg_verif_qui(base, d, entrees):
    """S4 (v3.5.0) : les « qui » de la verification -> repliques DEJA preparees (comme une correction ✏). -> nombre applique."""
    if _dlg_vivant(d):
        return 0
    f = os.path.join(base, "dialogues", "dialogues.json")
    doc = _dlg_lire(f)
    if not doc:
        return 0
    n = 0
    for k, e in entrees.items():
        reps = [x for x in doc.get("repliques") or [] if x.get("page") == int(k) and isinstance(x.get("box"), dict)]
        for r in e.get("ordre") or []:
            q = r.get("qui")
            if not q:
                continue
            x = next((y for y in reps if y.get("id") == r["id"] and _dlg_iou(y["box"], r["box"]) >= 0.2), None)
            if x is None:
                c = sorted(((_dlg_iou(y["box"], r["box"]), y) for y in reps), key=lambda t: -t[0])
                x = c[0][1] if c and c[0][0] >= 0.5 else None
            if x is None:
                c = sorted(((_dlg_couvre(r["box"], y["box"]), y) for y in reps), key=lambda t: -t[0])
                x = c[0][1] if c and c[0][0] >= 0.8 else None
            if x is not None and (x.get("qui") != q or (x.get("corrige") or {}).get("qui") != q):
                x["qui"] = q
                x.setdefault("corrige", {})["qui"] = q
                n += 1
    if n:
        doc["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _dlg_ecrire(f, doc)
    return n


def manga_dialogues_verif(d, pages):''')

rep('''                if bx is None or i is None:
                    return {"error": "zone invalide (%s, page %s)" % (cle, k)}
                l.append({"id": i, "box": bx})''',
    '''                if bx is None or i is None:
                    return {"error": "zone invalide (%s, page %s)" % (cle, k)}
                q = (r or {}).get("qui")                                    # S4 (v3.5.0) : qui parle, choisi par Quang
                q = q.strip()[:40] if isinstance(q, str) and cle != "exclues" else ""
                l.append(dict({"id": i, "box": bx}, **({"qui": q} if q else {})))''')

rep('''        e["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        doc["pages"][str(int(k))] = e
    os.makedirs(os.path.dirname(f), exist_ok=True)
    _dlg_ecrire(f, doc)
    return {"ok": True, "pages": sorted(int(k) for k in pages)}''',
    '''        e["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        doc["pages"][str(int(k))] = e
    os.makedirs(os.path.dirname(f), exist_ok=True)
    _dlg_ecrire(f, doc)
    try:
        nq = _dlg_verif_qui(base, d, {k: doc["pages"][str(int(k))] for k in pages})
    except Exception as ex:
        print("[dialogues] qui de la verification non applique : %s" % ex)
        nq = 0
    return {"ok": True, "pages": sorted(int(k) for k in pages), "qui_appliques": nq}''')

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
