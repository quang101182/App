# -*- coding: utf-8 -*-
"""Banc v2.6.0 (B1 + B2) : fiche de serie fiable + genres, bibliotheque personnelle (masquees / ouvertes).
Series de TEST creees PAR LE BANC (2 pages chacune), supprimees ensuite : zz-bib-claymore (serie.json de Claymore),
zz-bib-blackjack (pas de serie.json, titre « Black Jack ni Yoroshiku »), zz-bib-pepper (pas sur MangaDex).
Remet _bibliotheque.json dans son etat d'avant. Usage : python test_bibliotheque_api.py [port]
"""
import json, os, sys, urllib.request
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
S = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=120) as x:
        return json.load(x)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_outils as bo
BIB = os.path.join(S, "_bibliotheque.json")
avant = open(BIB, encoding="utf-8").read() if os.path.isfile(BIB) else None
bo.copier_serie("claymore", "zz-bib-claymore", ["ch_1"], pages_max=2, avec=("serie.json",))
bo.copier_serie("black-jack-ni-yoroshiku", "zz-bib-blackjack", ["ch_1"], pages_max=2, avec=())
bo.copier_serie("pepper-carrot", "zz-bib-pepper", ["ch_6"], pages_max=2, avec=())
try:
    # --- B1
    r = api("/manga/serie_infos", {"slug": "zz-bib-claymore"})
    check("Claymore : meme identite MangaDex qu'avant (id reutilise)", r.get("mangadex_id") == "be8fe64b-37da-4fba-b14d-603aba19be1f", r.get("mangadex_id"))
    check("Claymore : genres et public", "Action" in (r.get("genres") or []) and "Horror" in r["genres"] and r.get("public") == "shounen",
          (r.get("genres"), r.get("themes"), r.get("public")))
    check("Claymore : tomes et dates toujours la", r.get("annee_debut") == 2001 and str(r.get("tomes_total")) == "27")
    r = api("/manga/serie_infos", {"slug": "zz-bib-blackjack"})
    check("Black Jack : la BONNE serie (Give My Regards to Black Jack), pas la 1re trouvee ni la suite « Shin- »",
          r.get("mangadex_id") == "9fca3c19-ac41-4ebf-8735-f4e3becc2b3e", (r.get("mangadex_id"), r.get("titre_mangadex"), r.get("error")))
    check("Black Jack : genres", bool(r.get("genres")), r.get("genres"))
    r = api("/manga/serie_infos", {"slug": "zz-bib-pepper"})
    check("Pepper&Carrot (absent de MangaDex) : erreur claire, AUCUNE fiche ecrite",
          r.get("error") and not os.path.isfile(os.path.join(S, "zz-bib-pepper", "serie.json")), r.get("error", "")[:120])
    # --- B2
    b = api("/manga/bibliotheque")
    check("bibliotheque lisible", isinstance(b.get("masquees"), list) and isinstance(b.get("ouvertes"), dict))
    check("masquer", "zz-bib-pepper" in api("/manga/bibliotheque", {"action": "masquer", "slug": "zz-bib-pepper"})["masquees"])
    check("masquer 2 fois = une seule fois", api("/manga/bibliotheque", {"action": "masquer", "slug": "zz-bib-pepper"})["masquees"].count("zz-bib-pepper") == 1)
    check("... relu tel quel", "zz-bib-pepper" in api("/manga/bibliotheque")["masquees"])
    check("afficher", "zz-bib-pepper" not in api("/manga/bibliotheque", {"action": "afficher", "slug": "zz-bib-pepper"})["masquees"])
    check("ouverte = horodatage", api("/manga/bibliotheque", {"action": "ouverte", "slug": "zz-bib-claymore"})["ouvertes"].get("zz-bib-claymore", 0) > 1.7e9)
    check("slug invalide refuse", "error" in api("/manga/bibliotheque", {"action": "masquer", "slug": "../x"}))
    check("serie inexistante refusee", "error" in api("/manga/bibliotheque", {"action": "masquer", "slug": "n-existe-pas"}))
    check("action inconnue refusee", "error" in api("/manga/bibliotheque", {"action": "supprimer", "slug": "zz-bib-claymore"}))
    check("sources/<serie>/serie.json intact (rien d'autre n'y est ecrit)", "masquee" not in open(os.path.join(S, "zz-bib-claymore", "serie.json"), encoding="utf-8").read())
finally:
    for x in ("zz-bib-claymore", "zz-bib-blackjack", "zz-bib-pepper"):
        bo.supprimer_serie(x)
    if avant is None:
        if os.path.isfile(BIB):
            os.remove(BIB)
    else:
        open(BIB, "w", encoding="utf-8").write(avant)
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
