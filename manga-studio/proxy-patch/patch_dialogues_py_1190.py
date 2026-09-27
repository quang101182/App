# -*- coding: utf-8 -*-
"""dialogues.py 1.18.0 -> 1.19.0 (R30, maquette_verif_bulles_v1 validee 27/09 17h17)."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.19.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.18.0"  #', 'VERSION = "1.19.0"  # 1.19.0 (R30, 27/09) : 🔍 bulles VERIFIEES par Quang avant la preparation (exclues, ajoutees, ORDRE) + commande « detecter » (gratuite) ;  #')

FN = r'''

# ---------------------------------------------------------------- 1.19.0 (R30) : bulles verifiees par Quang
def iou(a, b):
    x1, y1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x2, y2 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    uni = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / uni if uni > 0 else 0.0


def apparier(ref, bulles):
    """La bulle de la source qui correspond a une entree verifiee : meme zone (IoU >= 0.5), sinon meme id si la zone est proche."""
    best, bi = None, 0.0
    for b in bulles:
        v = iou(ref["box"], b["box"])
        if v > bi:
            best, bi = b, v
    if bi >= 0.5:
        return best
    same = [b for b in bulles if b["id"] == ref.get("id")]
    return same[0] if same and iou(ref["box"], same[0]["box"]) >= 0.2 else None


def appliquer_verif(page, bulles, verif):
    """bulles de la page (deja filtrees) + la verification de Quang -> liste dans SON ordre, exclues retirees, ajouts (lus sur
    l'image par Gemini, comme une page deja en VF). Sans verification : inchangee. Chaque bulle recoit « ordre »."""
    v = ((verif or {}).get("pages") or {}).get(str(page))
    if not v:
        return bulles
    ex = [apparier(r, bulles) for r in v.get("exclues") or []]
    ids_ex = {id(b) for b in ex if b is not None}
    reste = [b for b in bulles if id(b) not in ids_ex]
    for k, z in enumerate(v.get("ajouts") or []):
        if not any(iou(z["box"], b["box"]) >= 0.5 for b in reste):
            reste.append({"id": int(z.get("id") or 900 + k), "type": "dialogue", "box": {q: round(float(z["box"][q]), 4) for q in ("x", "y", "w", "h")},
                          "trad": "", "a_lire": True, "ajout": True})
    rang = {}
    for i, r in enumerate(v.get("ordre") or []):
        b = next((x for x in reste if x.get("ajout") and x["id"] == r.get("id") and iou(r["box"], x["box"]) >= 0.5), None) or apparier(r, reste)
        if b is not None and id(b) not in rang:
            rang[id(b)] = i
    base = len(rang)
    for b in sorted(reste, key=lambda x: x["id"]):
        b["ordre"] = rang.get(id(b), base + b["id"] / 10000.0)
    return sorted(reste, key=lambda x: x["ordre"])


def rang(x):
    """Cle de tri d'une replique dans sa page : l'ordre verifie par Quang s'il existe, sinon le n° de detection."""
    o = x.get("ordre")
    return o if o is not None else (x.get("id") or 0)


def cmd_detecter(a):
    """Detection SEULE (gratuite, sur le PC) des pages demandees qui ne sont PAS encore traduites -> dialogues/detection.json.
    Memes fonction et seuils que la traduction (traduire_chapitre.zones_texte) : ses n° correspondent aux siens."""
    chap_dir, serie_dir, dd = chemins(a.chap)
    os.makedirs(dd, exist_ok=True)
    nc.PROGRESS = os.path.join(dd, "progress.json")
    import ingest_page as ip
    import traduire_chapitre as tc
    man = lire_json(os.path.join(chap_dir, "manifest.json")) or {}
    fichiers = [os.path.basename(q.get("file") or "") for q in man.get("pages") or []]
    tr = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
    deja = {p["page"] for p in tr.get("pages") or [] if p.get("bulles") is not None}
    voulues = [n for n in nc_plage(a.pages, list(range(1, len(fichiers) + 1))) if n not in deja]
    f = os.path.join(dd, "detection.json")
    doc = lire_json(f) or {"pages": {}}
    for k, n in enumerate(voulues):
        nc.progres("detection", k, len(voulues))
        img = os.path.join(chap_dir, fichiers[n - 1])
        if not os.path.isfile(img):
            continue
        try:                                             # une image illisible ne bloque pas les autres pages
            texts = tc.zones_texte(ip.load_page(img), 0.25)
        except Exception as e:
            log("  page %d : detection impossible (%s)" % (n, str(e)[:120]))
            texts = []
        doc["pages"][str(n)] = {"file": fichiers[n - 1], "bulles": [{"id": t["id"], "box": {q: round(t[q], 4) for q in ("x", "y", "w", "h")}} for t in texts]}
    doc["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ecrire_json(f, doc)
    nc.progres("detection", len(voulues), len(voulues), fini=True)
    print("detection : %d page(s)" % len(voulues))
    return 0

'''
rep("\n\ndef cmd_preparer(a):", FN.replace("\n", N) + "\ndef cmd_preparer(a):")

rep('''            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and (not b.get("ecarte") or ecarte_pour_image(b))
                                   and ((b.get("trad") or "").strip() or b.get("a_lire"))], key=lambda b: b["id"])''',
    '''            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and (not b.get("ecarte") or ecarte_pour_image(b))
                                   and ((b.get("trad") or "").strip() or b.get("a_lire"))], key=lambda b: b["id"])
            p["_bulles"] = appliquer_verif(p["page"], p["_bulles"], verif)      # 1.19.0 (R30) : exclues / ajouts / ORDRE de Quang''')
rep('''    voulues = set(nc_plage(a.pages, [p["page"] for p in tr["pages"]]))''',
    '''    voulues = set(nc_plage(a.pages, [p["page"] for p in tr["pages"]]))
    verif = lire_json(os.path.join(dd, "bulles_verifiees.json"))              # 1.19.0 (R30)''')
rep('''                    "box": b["box"], "contour": contour_bulle(img, b["box"]),''',
    '''                    "box": b["box"], "contour": contour_bulle(img, b["box"]), "ordre": b.get("ordre", b["id"]),''')
rep('''           "repliques": sorted(par_cle.values(), key=lambda x: (x["page"], x["id"]))}''',
    '''           "repliques": sorted(par_cle.values(), key=lambda x: (x["page"], rang(x)))}''')
rep('''    etapes.sort(key=lambda x: (x["page"], x.get("id") or 0))''',
    '''    etapes.sort(key=lambda x: (x["page"], rang(x) if not x.get("vide") else -1))     # 1.19.0 : l'ordre verifie''')
rep('''    lo = sp.add_parser("lot"); lo.add_argument("serie");''',
    '''    de = sp.add_parser("detecter"); de.add_argument("chap"); de.add_argument("--pages", default="")     # 1.19.0 (R30)
    lo = sp.add_parser("lot"); lo.add_argument("serie");''')
rep('''    if a.cmd == "lot":
        return cmd_lot(a)''', '''    if a.cmd == "lot":
        return cmd_lot(a)
    if a.cmd == "detecter":
        return cmd_detecter(a)''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.19.0")
