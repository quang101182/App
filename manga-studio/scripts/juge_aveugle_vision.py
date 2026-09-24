# -*- coding: utf-8 -*-
"""Juge A L'AVEUGLE qui VOIT la page (24/09/2026) : deux narrations du meme chapitre, laquelle est la plus fidele ?

Pour chaque page narree par les deux runs : l'image + la narration 1 + la narration 2 (ordre tire au sort, les tags ne
sont jamais montres). Le juge dit laquelle est la plus fidele (ou egal) et classe l'erreur de chacune : aucune |
mineure (embellissement sans consequence) | grave (contresens, mauvais personnage, evenement invente). Un juge qui ne
lit que du texte ne peut pas verifier la fidelite a une image : ici il la voit.
Juges : gemini (reflexion par DEFAUT, quel que soit MANGA_GEMINI_REFLEXION) et kimi (K3, vision).
Usage : python juge_aveugle_vision.py one-punch-man/ch_2 banc-reflex-defaut banc-reflex-minimal [--juges gemini,kimi]
"""
import base64, json, os, random, sys
os.environ["MANGA_GEMINI_REFLEXION"] = ""                  # le juge garde toute sa reflexion
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import narrate_chapter as nc
nc.SECRET = nc._secret()

SYS = ("Tu es un correcteur de FIDELITE de recaps manga. Tu vois la page et deux narrations ecrites pour elle. Juge "
       "uniquement la fidelite a CE QUI EST SUR LA PAGE (qui fait quoi, qui dit quoi, qui est present). Erreur 'grave' : "
       "contresens, action ou replique attribuee au mauvais personnage, personnage absent donne comme present, evenement "
       "invente qui change l'histoire. 'mineure' : embellissement d'ambiance sans consequence. Omettre un detail secondaire "
       "n'est pas une erreur. Reponds UNIQUEMENT en JSON : {\"plus_fidele\":\"1|2|egal\",\"erreur_1\":\"aucune|mineure|grave\","
       "\"erreur_2\":\"aucune|mineure|grave\",\"raison\":\"<une phrase>\"}")


def main():
    chap, ta, tb = sys.argv[1:4]
    juges = (sys.argv[sys.argv.index("--juges") + 1] if "--juges" in sys.argv else "gemini,kimi").split(",")
    cd = os.path.join(nc.SOURCES, chap)
    lire = lambda t: json.load(open(os.path.join(cd, "narration", t, "narration.json"), encoding="utf-8"))
    A, B = lire(ta), lire(tb)
    pb = {p["page"]: p for p in B["pages"]}
    paires = [(p, pb[p["page"]]) for p in A["pages"] if p["page"] in pb and (p.get("narration") or "").strip()
              and (pb[p["page"]].get("narration") or "").strip()]
    fiche = lambda n: ", ".join("%s (%s)" % (x.get("nom"), x.get("qui")) for x in n.get("personnages") or [])
    rnd = random.Random(11)
    for juge in juges:
        tot = {ta: {"grave": 0, "mineure": 0, "aucune": 0, "gagne": 0}, tb: {"grave": 0, "mineure": 0, "aucune": 0, "gagne": 0}, "egal": 0}
        cout, graves = 0.0, []
        for pa, pbb in paires:
            inv = rnd.random() < 0.5
            n1, n2 = (pbb, pa) if inv else (pa, pbb)
            t1, t2 = (tb, ta) if inv else (ta, tb)
            img = base64.b64encode(nc.page_jpeg(os.path.join(cd, pa["file"]))).decode()
            txt = ("Personnages connus (narration 1) : %s\nPersonnages connus (narration 2) : %s\n\nNARRATION 1 : %s\n\nNARRATION 2 : %s"
                   % (fiche(A if t1 == ta else B), fiche(A if t2 == ta else B), n1["narration"], n2["narration"]))
            content = [{"type": "text", "text": txt}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img}}]
            try:
                r, u = nc.appel_vision(juge, SYS, content, 8000 if juge == "gemini" else 16000)
                cout += nc.cout(nc.ENGINES[juge][1], u)
                v = nc.parse_json(r)
            except Exception as e:
                print("  p.%s : juge %s illisible (%s)" % (pa["page"], juge, str(e)[:80])); continue
            for t, k in ((t1, "erreur_1"), (t2, "erreur_2")):
                e = v.get(k) if v.get(k) in ("grave", "mineure", "aucune") else "aucune"
                tot[t][e] += 1
                if e == "grave":
                    graves.append("p.%s %s : %s" % (pa["page"], t, v.get("raison", "")[:160]))
            g = v.get("plus_fidele")
            if g in ("1", "2"):
                tot[t1 if g == "1" else t2]["gagne"] += 1
            else:
                tot["egal"] += 1
        __import__("depenses").noter("essai", chap, "juge-aveugle " + ta + " vs " + tb, juge, cout)   # une depense reste une depense
        print("\nJUGE %s (%d pages, %.3f $)" % (juge, len(paires), cout))
        for t in (ta, tb):
            print("  %-22s graves %2d · mineures %2d · aucune %2d · plus fidele sur %2d page(s)"
                  % (t, tot[t]["grave"], tot[t]["mineure"], tot[t]["aucune"], tot[t]["gagne"]))
        print("  egalite sur %d page(s)" % tot["egal"])
        for g in graves:
            print("   - " + g)


if __name__ == "__main__":
    main()
