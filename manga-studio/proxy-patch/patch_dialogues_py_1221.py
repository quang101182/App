# -*- coding: utf-8 -*-
"""dialogues.py 1.22.0 -> 1.22.1 (27/09, essai REEL sur copie) : une bulle entouree est souvent du texte posé sur le FOND de
la case, sans contour : l'effacement standard (clean_bubbles) prenait TOUTE la case pour une bulle et la blanchissait
(dessin efface), puis n'ecrivait rien. Desormais : effacement LIMITE AUX LETTRES (traduire_chapitre.boite_lettres, qui ne
repond que pour du texte net sur fond clair) puis texte pose dans cette boite ; sinon l'image n'est PAS touchee (la
replique est quand meme lue en francais). Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.22.1"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)
rep('VERSION = "1.22.0"  #', 'VERSION = "1.22.1"  # 1.22.1 (27/09) : bulle entouree effacee LETTRES SEULES (jamais la case entiere) ;  #')
rep('''        rendu, net = tc.nettoyer(ip.load_page(img_t), [t for t, _ in a_poser])
        etats = {x.get("id"): x.get("etat") for x in net}
        for t, b in a_poser:
            etat, c = etats.get(t["id"]), t.get("clean")
            if etat == "bulle" and c and c["w"] * c["h"] > 6 * t["w"] * t["h"]:
                etat, c = "case", None
            boite = c if etat == "bulle" and c else {q: t[q] for q in ("x", "y", "w", "h")}
            r = tc.poser_texte(rendu, boite, b["trad"].strip(), etat == "bulle") if (etat == "bulle" or (etat and "boite" in etat)) else {}''',
    '''        from PIL import ImageDraw
        rendu = ip.load_page(img_t).convert("RGB")
        W, H = rendu.size
        for t, b in a_poser:
            serre = tc.boite_lettres(rendu, t)                         # texte net sur fond clair, sinon None
            if serre:
                ImageDraw.Draw(rendu).rectangle([int(serre["x"] * W), int(serre["y"] * H), int((serre["x"] + serre["w"]) * W),
                                                 int((serre["y"] + serre["h"]) * H)], fill=(255, 255, 255))
                r, etat = tc.poser_texte(rendu, serre, b["trad"].strip(), False), "lettres seules"
            else:
                r, etat = {}, "non effacee (fond charge : image laissee telle quelle)"''')
rep('''                                     "texte": (b.get("texte") or "").strip(), "trad": b["trad"].strip(), "effacement": etat or "non effacee",''',
    '''                                     "texte": (b.get("texte") or "").strip(), "trad": b["trad"].strip(), "effacement": etat,''')
rep('''        log("  page %d : %d bulle(s) ajoutee(s) traduite(s) et posee(s)" % (n, len(a_poser)))''',
    '''        log("  page %d : %d bulle(s) ajoutee(s) traduite(s) (%s)" % (n, len(a_poser), ", ".join(x.get("effacement", "") for x in p["bulles"][-len(a_poser):])))''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.22.1")
