# -*- coding: utf-8 -*-
"""Manga Studio v2.99.1 -- mode Dialogues, 11e patch serveur (Quang 27/09 16h26 : « oui go » pour « 🗑 Oublier cette plage »,
maquette_dialogues_compact_v1 A3). Route POST /manga/dialogues_oublier {d, portee} (portee = « a-b » ou « tout »).
RIEN n'est efface : copie du fichier avant (dialogues.json.avant_oubli_<horodatage>), repliques des pages oubliees RANGEES
dans doc["oubliees"], video deplacee dans dialogues/video/_oubliees/. Une page encore couverte par une AUTRE plage garde ses
repliques. Refus si les dialogues du chapitre tournent. Rejouable : python patch_dialogues_11.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def manga_dialogues_oublier(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"

FN = '''

def _dlg_oublier_doc(doc, k):
    """v2.99.1 : retire la plage k du document (pur, testable) -> (doc, [videos a ranger]). Rien n'est perdu : « oubliees »."""
    import re as _re
    m = _re.match(r"^(\\d+)(?:-(\\d+))?$", k or "")
    if k != "tout" and not m:
        raise ValueError("plage invalide")
    a, b = (1, 10 ** 9) if k == "tout" else (int(m.group(1)), int(m.group(2) or m.group(1)))
    autres = []
    for x in doc.get("portees") or []:
        mx = _re.match(r"^(\\d+)(?:-(\\d+))?$", str(x))
        if mx and str(x) != k:
            autres.append((int(mx.group(1)), int(mx.group(2) or mx.group(1))))
    garde = lambda n: any(u <= n <= v for u, v in autres)
    part = lambda n: a <= n <= b and not garde(n)
    t = time.strftime("%Y-%m-%dT%H:%M:%S")
    parties = [dict(x, oubliee=t, plage=k) for x in doc.get("repliques") or [] if part(int(x.get("page") or 0))]
    doc["repliques"] = [x for x in doc.get("repliques") or [] if not part(int(x.get("page") or 0))]
    doc["oubliees"] = (doc.get("oubliees") or []) + parties
    if doc.get("pages_vues"):
        doc["pages_vues"] = [n for n in doc["pages_vues"] if not part(int(n))]
    doc["portees"] = [x for x in doc.get("portees") or [] if str(x) != k]
    vids = []
    if k in (doc.get("videos") or {}):
        vids.append(doc["videos"].pop(k))
    if k == "tout" and doc.get("video"):
        vids.append(doc.pop("video"))
    return doc, vids


def manga_dialogues_oublier(d, k):
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    if _dlg_vivant(d):
        return {"error": "les dialogues de ce chapitre sont en cours : arrête-les d'abord"}
    dd = os.path.join(base, "dialogues")
    f = os.path.join(dd, "dialogues.json")
    doc = _dlg_lire(f)
    if not doc:
        return {"error": "rien de préparé dans ce chapitre"}
    try:
        shutil.copy2(f, f + ".avant_oubli_" + time.strftime("%Y%m%d_%H%M%S"))
        doc, vids = _dlg_oublier_doc(doc, str(k or ""))
    except ValueError as e:
        return {"error": str(e)}
    ranges = []
    for v in vids:
        src = os.path.normpath(os.path.join(MANGA_SOURCES, str(v.get("fichier") or "")))
        if src.startswith(MANGA_SOURCES) and os.path.isfile(src):
            dst_dir = os.path.join(dd, "video", "_oubliees")
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, os.path.join(dst_dir, time.strftime("%Y%m%d_%H%M%S_") + os.path.basename(src)))
            ranges.append(os.path.basename(src))
    _dlg_ecrire(f, doc)
    return {"ok": True, "repliques": len([x for x in doc.get("oubliees") or [] if x.get("plage") == k]), "videos": ranges}
'''.replace("\n", NL)

a = "def manga_dialogues_arreter(d):" + NL
if s.count(a) != 1:
    raise SystemExit("ancre fonction introuvable (%d)" % s.count(a))
i = s.index(a)
s = s[:i] + FN.lstrip(NL) + NL + NL + s[i:]

r = '''            elif self.path == "/manga/dialogues_arreter":
                self._json(200, manga_dialogues_arreter(str(data.get("d") or "")))
'''.replace("\n", NL)
if s.count(r) != 1:
    raise SystemExit("ancre route introuvable (%d)" % s.count(r))
s = s.replace(r, r + '''            elif self.path == "/manga/dialogues_oublier":      # Manga Studio v2.99.1
                self._json(200, manga_dialogues_oublier(str(data.get("d") or ""), str(data.get("portee") or "")))
'''.replace("\n", NL))
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
