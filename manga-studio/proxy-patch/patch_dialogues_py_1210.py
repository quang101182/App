# -*- coding: utf-8 -*-
"""dialogues.py 1.20.0 -> 1.21.0 (27/09, Quang 17h51 : « oui go ») -- commande « tout » : preparation (sauf --sans-preparation),
ARRET avant les voix si l'IA a un DOUTE (replique « a traiter », personnage « inconnu », doublon probable) -> progress
etape « doute » + code 5 ; sinon voix (arret net au quota : code 4) puis video de la portee. Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.21.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.20.0"  #', 'VERSION = "1.21.0"  # 1.21.0 (27/09) : commande « tout » (preparer -> ARRET si doute -> voix -> video) ;  #')
FN = r'''

def doutes(doc, distrib, plage):
    """1.21.0 : ce qui doit passer par ✏ AVANT de payer des voix, dans la portee : repliques « a traiter », personnage
    « inconnu » (lues), doublons probables de la distribution."""
    pv = set(nc_plage(plage, sorted({x["page"] for x in doc.get("repliques") or []}))) if plage else None
    reps = [x for x in doc.get("repliques") or [] if (pv is None or x["page"] in pv)]
    trait = [x["cle"] for x in reps if x.get("a_traiter") and not ((x.get("corrige") or {}).get("qui"))]
    inconnu = [x["cle"] for x in reps if x.get("lire") and (x.get("qui") or "inconnu") == "inconnu"]
    dbl = [g for g in distrib.get("doublons") or [] if g.get("garder") and g.get("avec")]
    return trait, inconnu, dbl


def cmd_tout(a):
    """1.21.0 : tout d'un coup, avec UN arret humain possible : avant les voix, si l'IA doute."""
    chap_dir, serie_dir, dd = chemins(a.chap)
    if not getattr(a, "sans_preparation", False):
        rc = cmd_preparer(a)
        if rc:
            return rc
    doc = lire_json(os.path.join(dd, "dialogues.json"))
    if not doc:
        print("ARRET : chapitre pas encore prepare"); return 3
    trait, inconnu, dbl = doutes(doc, distribution(serie_dir), a.pages)
    if trait or inconnu or dbl:
        motif = "; ".join(t for t in (
            ("%d replique(s) a traiter" % len(trait)) if trait else "",
            ("%d replique(s) sans personnage reconnu" % len(inconnu)) if inconnu else "",
            ("%d doublon(s) probable(s) de personnage" % len(dbl)) if dbl else "") if t)
        nc.PROGRESS = os.path.join(dd, "progress.json")
        nc.progres("doute", 0, 0, fini=True, arret=motif, cles=(trait + inconnu)[:40])
        log("ARRET avant les voix (doute de l'IA) : %s -- a regler dans ✏, puis relancer" % motif)
        return 5
    rc = cmd_voix(a)
    if rc:
        return rc
    return cmd_video(a)

'''
rep("\n\ndef cmd_preparer(a):", FN.replace("\n", N) + "\ndef cmd_preparer(a):")
rep('''    de = sp.add_parser("detecter"); de.add_argument("chap"); de.add_argument("--pages", default="")     # 1.19.0 (R30)''',
    '''    de = sp.add_parser("detecter"); de.add_argument("chap"); de.add_argument("--pages", default="")     # 1.19.0 (R30)
    to = sp.add_parser("tout"); to.add_argument("chap"); to.add_argument("--pages", default="")         # 1.21.0
    to.add_argument("--traduire", action="store_true"); to.add_argument("--sans-preparation", action="store_true", dest="sans_preparation")''')
rep('''    if a.cmd == "detecter":
        return cmd_detecter(a)''', '''    if a.cmd == "detecter":
        return cmd_detecter(a)
    if a.cmd == "tout":
        return cmd_tout(a)''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.21.0")
