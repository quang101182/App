# -*- coding: utf-8 -*-
"""R12 + R13 (27/09 -- Quang 12h21 : « beaucoup de textes restes en anglais […] des endroits ou il n'y a pas de dialogue » ;
« l'idee, c'est que l'application soit capable de faire les choses correctement ») -- patch des SCRIPTS (pas de l'app) :

traduire_chapitre.py 2.2.0 (R12) : une page ou le detecteur local ne trouve AUCUNE zone n'est plus sautee -- elle est lue par
  le modele quand meme (tout son texte passe par « hors zones »). Mesure du 27/09 : 15 pages sur 29 d'un webtoon enregistrees
  « 0 bulle » alors qu'elles etaient pleines d'anglais = exactement les 15 pages ou YOLO rendait 0 zone. Chaque page porte
  « lue » ; stats « pages_sans_zone ».
traduire_chapitre.py 2.2.0 + dialogues.py 1.12.0 (R13) : UNE regle `page_lue` -- une page jamais lue n'est pas « traduite »
  (lue = True ; ancien format : au moins une bulle). traduction_etat() ne compte que les pages lues (+ « non_lues ») ;
  dialogues.py --traduire retraduit les pages non lues. Les traductions EXISTANTES en profitent sans rien refaire a la main.
Rejouable : python scripts_patch_r12_r13.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")


def patcher(nom, reps, marque):
    p = os.path.join(D, nom)
    s = open(p, encoding="utf-8", newline="").read()
    if marque in s:
        print(nom, ": deja applique"); return
    N = "\r\n" if "\r\n" in s else "\n"
    for a, b in reps:
        a, b = a.replace("\n", N), b.replace("\n", N)
        assert s.count(a) == 1, (nom, a[:70], s.count(a))
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(s)
    print(nom, ": ok")


patcher("traduire_chapitre.py", [
    ('VERSION = "2.1.0"', 'VERSION = "2.2.0"   # 2.2.0 (R12/R13, 27/09) : aucune page sautee (0 zone detectee -> lue quand meme) ; « lue » par page'),
    # le modele est prevenu quand il n'y a aucune bulle decoupee : tout va dans « hors_zones »
    ('''    for t in texts:
        content.append({"type": "text", "text": "BULLE %d" % t["id"]})''',
     '''    if not texts:                                   # 2.2.0 (R12) : le detecteur n'a rien trouve -> le modele lit TOUTE la page
        content.append({"type": "text", "text": "AUCUNE BULLE DECOUPEE sur cette page (le detecteur n'a rien trouve) : "
                        "\\"bulles\\" = [] et TOUT texte lisible (bulles, encadres, pensees) va dans \\"hors_zones\\", avec sa box."})
    for t in texts:
        content.append({"type": "text", "text": "BULLE %d" % t["id"]})'''),
    # la regle unique « page lue »
    ('''def traduction_etat(cd, lg="fr"):''',
     '''def page_lue(x):
    """2.2.0 (R13) : une page de traduction.json a-t-elle VRAIMENT ete lue par le modele ? « lue » si present ; sinon (fichier
    d'avant 2.2.0) au moins une bulle -- avant 2.2.0, une page sans zone detectee n'etait jamais envoyee au modele (27/09 :
    15 pages sur 29 d'un webtoon). MEME regle dans dialogues.py et le serveur (_trad_etat)."""
    return bool(x.get("lue")) if "lue" in x else bool(x.get("bulles"))


def traduction_etat(cd, lg="fr"):'''),
    ('''    pages = sorted(x["page"] for x in t.get("pages") or [])
    total = t.get("pages_chapitre") or len(pages)
    return {"complete": bool(t.get("complete", True)), "pages": pages, "total": total,''',
     '''    pages = sorted(x["page"] for x in t.get("pages") or [] if page_lue(x))              # 2.2.0 (R13) : LUES seulement
    total = t.get("pages_chapitre") or len(pages)
    return {"complete": bool(t.get("complete", True)) and len(pages) >= total, "pages": pages, "total": total,
            "non_lues": sorted(x["page"] for x in t.get("pages") or [] if not page_lue(x)),'''),
    # la boucle : plus de page sautee
    ('''        stats["bulles"] += len(texts)
        lignes, rendu, trace = [], im, None
        if texts:
            HORS_ZONES[:] = []''',
     '''        stats["bulles"] += len(texts)
        lignes, rendu, trace = [], im, None
        lue = (avant.get(p["num"]) or {}).get("lue", True) if a.rerendu else False     # 2.2.0 (R12)
        if not texts:
            stats["pages_sans_zone"] = stats.get("pages_sans_zone", 0) + 1
        if texts or not a.rerendu:                       # 2.2.0 (R12) : 0 zone detectee -> la page est LUE quand meme
            HORS_ZONES[:] = []'''),
    ('''                    tr, trace = traduire_avec_relais(im, texts, a.engine, a.langue, stats, relais)
''', '''                    tr, trace = traduire_avec_relais(im, texts, a.engine, a.langue, stats, relais)
                    lue = True
'''),
    ('''                stats.setdefault("moderation", []).append({"page": p["num"], "moteur": e.moteur, "motif": e.motif})
                tr = {}''', '''                stats.setdefault("moderation", []).append({"page": p["num"], "moteur": e.moteur, "motif": e.motif})
                tr, lue = {}, True                         # lue et REFUSEE : l'alerte le dit, ne pas la repayer en boucle'''),
    ('''        res["pages"].append(dict({"page": p["num"], "source": p["file"], "file": f, "bulles": lignes},''',
     '''        res["pages"].append(dict({"page": p["num"], "source": p["file"], "file": f, "bulles": lignes, "lue": lue},'''),
    ('''    res["complete"] = len({x["page"] for x in res["pages"]}) >= total''',
     '''    res["complete"] = len({x["page"] for x in res["pages"] if page_lue(x)}) >= total     # 2.2.0 (R13)'''),
], "def page_lue(")

patcher("dialogues.py", [
    ('VERSION = "1.11.0"', 'VERSION = "1.12.0"  # 1.12.0 (R13, 27/09) : une page de traduction jamais LUE par le modele est retraduite (--traduire) ;'),
    ('''    faites = {p["page"] for p in tr.get("pages") or []}
    manq = [n for n in voulues if n not in faites]''',
     '''    # 1.12.0 (R13) : MEME regle que traduire_chapitre.page_lue -- lue si « lue », sinon (avant 2.2.0) au moins une bulle
    faites = {p["page"] for p in tr.get("pages") or [] if (bool(p.get("lue")) if "lue" in p else bool(p.get("bulles")))}
    manq = [n for n in voulues if n not in faites]'''),
], "1.12.0 (R13")
