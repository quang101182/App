# -*- coding: utf-8 -*-
"""dialogues.py 1.21.1 -> 1.22.0 (27/09, Quang 18h10 : « la solution parait evidente ») -- une bulle ENTOUREE par Quang
(verification des bulles) sur une page TRADUITE est traduite et REECRITE en francais sur l'image de la page, avant la
preparation : lue sur la page d'ORIGINE (traduire_chapitre.traduire_page, meme prompt que la traduction), effacee et posee
sur la page TRADUITE (nettoyer + poser_texte, memes fonctions et reglages), ajoutee a traduction.json (« ajout »: true).
La preparation la lit alors comme toute bulle traduite. Copie de traduction.json avant la 1re modification. Cout inscrit
au journal des depenses. Idempotent (une zone deja presente n'est pas refaite). Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.22.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.21.1"  #', 'VERSION = "1.22.0"  # 1.22.0 (27/09) : bulle ENTOUREE sur une page traduite -> traduite et REECRITE en francais sur la page ;  #')
FN = r'''

def traduire_ajouts(chap_dir, dd, a, voulues):
    """1.22.0 : les bulles ajoutees par Quang sur des pages TRADUITES -> traduites et posees sur l'image, puis ajoutees a
    traduction.json. Retourne le nombre de bulles posees. Sans verification / sans traduction : rien."""
    verif = lire_json(os.path.join(dd, "bulles_verifiees.json")) or {}
    tf = os.path.join(chap_dir, "traduction", "fr", "traduction.json")
    tr = lire_json(tf)
    if not tr or not verif.get("pages"):
        return 0
    trp = {p["page"]: p for p in tr.get("pages") or []}
    man = lire_json(os.path.join(chap_dir, "manifest.json")) or {}
    fich = [os.path.basename(q.get("file") or "") for q in man.get("pages") or []]
    faites, st, pages_touchees = 0, {"tokens_in": 0, "tokens_out": 0, "cout": 0.0}, []
    for k, v in sorted(verif["pages"].items(), key=lambda kv: int(kv[0])):
        n = int(k)
        p = trp.get(n)
        if n not in voulues or not p or p.get("bulles") is None or not (0 < n <= len(fich)):
            continue
        nouveaux = [z for z in v.get("ajouts") or [] if not any(iou(z["box"], b["box"]) >= 0.5 for b in p["bulles"] if b.get("box"))]
        if not nouveaux:
            continue
        import ingest_page as ip
        import traduire_chapitre as tc
        img_t = os.path.join(chap_dir, "traduction", "fr", p.get("file") or "page_%03d.png" % n)
        if not os.path.isfile(img_t):
            continue
        texts = [dict(z["box"], id=int(z["id"]), conf=1.0) for z in nouveaux]
        try:
            lu = tc.traduire_page(ip.load_page(os.path.join(chap_dir, fich[n - 1])), texts, "gemini", "fr", st)
        except Exception as e:
            log("  page %d : bulle(s) ajoutee(s) non traduite(s) (%s) -- lue(s) a la preparation" % (n, str(e)[:120]))
            continue
        a_poser = [(t, lu.get(t["id"]) or {}) for t in texts if ((lu.get(t["id"]) or {}).get("trad") or "").strip()]
        if not a_poser:
            continue
        rendu, net = tc.nettoyer(ip.load_page(img_t), [t for t, _ in a_poser])
        etats = {x.get("id"): x.get("etat") for x in net}
        for t, b in a_poser:
            etat, c = etats.get(t["id"]), t.get("clean")
            if etat == "bulle" and c and c["w"] * c["h"] > 6 * t["w"] * t["h"]:
                etat, c = "case", None
            boite = c if etat == "bulle" and c else {q: t[q] for q in ("x", "y", "w", "h")}
            r = tc.poser_texte(rendu, boite, b["trad"].strip(), etat == "bulle") if (etat == "bulle" or (etat and "boite" in etat)) else {}
            typ = b.get("type") if b.get("type") in ("dialogue", "narration") else "dialogue"
            p["bulles"].append(dict({"id": t["id"], "box": {q: round(t[q], 4) for q in ("x", "y", "w", "h")}, "type": typ,
                                     "texte": (b.get("texte") or "").strip(), "trad": b["trad"].strip(), "effacement": etat or "non effacee",
                                     "ajout": True}, **{q: r[q] for q in ("taille", "lignes", "tient") if q in r}))
            faites += 1
        if not os.path.isfile(img_t + ".avant_ajouts"):
            import shutil as _sh
            _sh.copy2(img_t, img_t + ".avant_ajouts")
        rendu.save(img_t)
        pages_touchees.append(n)
        log("  page %d : %d bulle(s) ajoutee(s) traduite(s) et posee(s)" % (n, len(a_poser)))
    if faites:
        if not os.path.isfile(tf + ".avant_ajouts"):
            import shutil as _sh
            _sh.copy2(tf, tf + ".avant_ajouts")
        ecrire_json(tf, tr)
        depenses.noter("dialogues", a.chap, "traduction des bulles ajoutees", "gemini", round(st["cout"], 5), pages=pages_touchees)
    return faites

'''
rep("\n\ndef cmd_preparer(a):", FN.replace("\n", N) + "\ndef cmd_preparer(a):")
rep('''    tr = source_bulles(chap_dir, a.pages)
    if not tr:
        print("ARRET : pas de traduction francaise pour %s -- traduis d'abord ce chapitre en francais" % a.chap)
        return 3''',
    '''    try:                                                                   # 1.22.0 : bulles entourees -> traduites sur la page
        _tr0 = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
        traduire_ajouts(chap_dir, dd, a, set(nc_plage(a.pages, [p["page"] for p in _tr0.get("pages") or []])))
    except Exception as e:
        log("  bulles ajoutees : traduction sur la page impossible (%s) -- elles seront lues a la preparation" % str(e)[:160])
    tr = source_bulles(chap_dir, a.pages)
    if not tr:
        print("ARRET : pas de traduction francaise pour %s -- traduis d'abord ce chapitre en francais" % a.chap)
        return 3''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.22.0")
