# -*- coding: utf-8 -*-
"""v2.99.2 (27/09, Quang 16h34, capture PC 1362 px) : (1) le fil d'Ariane (v2.96.0) partait du BORD GAUCHE de la fenetre sur
grand ecran, hors de la colonne de l'app (760 px) -> aligne sur elle ; (2) doublon « ← Noritaka » / « ← Toutes les series » :
le bandeau (R25) ET le bouton retour de l'ecran l'un sous l'autre -> le bouton d'origine est masque TANT QUE le bandeau le
remplace (regle liee a body[data-ou-masque], survit aux re-rendus), et le bandeau peut toujours le declencher. Suppose v2.99.1."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.99.2" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v2.99.1" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_2991_oublier.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.99.1</title>", "<title>Manga Studio v2.99.2</title>")
rep('<span class="ver" id="verBadge">v2.99.1</span>', '<span class="ver" id="verBadge">v2.99.2</span>')
rep('const VERSION = "2.99.1";', 'const VERSION = "2.99.2";   // v2.99.2 : fil d Ariane dans la colonne de l app (grand ecran) ; plus de double bouton retour sous le bandeau')
rep(".ou-fil[hidden],.ou-bande[hidden]{display:none}",
    ".ou-fil[hidden],.ou-bande[hidden]{display:none}" + N
    + ".ou-fil{max-width:760px;margin:0 auto;box-sizing:border-box;padding-left:14px;padding-right:14px}   /* v2.99.2 : dans la colonne de l'app */" + N
    + "body[data-ou-masque=vidFermer] #vidFermer,body[data-ou-masque=dlgsFermer] #dlgsFermer,body[data-ou-masque=btnLibBack] #btnLibBack{display:none !important}   /* v2.99.2 : le bandeau le remplace */")
rep("""  fil.hidden = bande.hidden = !e; if (!e) return;""",
    """  fil.hidden = bande.hidden = !e; document.body.dataset.ouMasque = e ? e.retId || "" : "";   /* PAS data-ou-ret : closest("[data-ou-ret]") le prendrait pour le bouton du bandeau */ if (!e) return;   // v2.99.2""")
rep("""function ouCliquer(id){ const b = document.getElementById(id); if (b && b.offsetParent !== null) b.click(); }""",
    """function ouCliquer(id){ const b = document.getElementById(id); if (b && (b.offsetParent !== null || document.body.dataset.ouMasque === id)) b.click(); }   // v2.99.2 : masque par le bandeau""")
# (3) Quang 16h36 : « ✓ Voix » gris (bouton desactive : plus rien a generer) alors que Prepare / Video sont verts
rep("""    $("dlgVoix").textContent = p.a_faire ? "🔊 Voix (" + p.a_faire + ")" : x.faites ? "✓ Voix" : "🔊 Voix";""",
    """    $("dlgVoix").textContent = p.a_faire ? "🔊 Voix (" + p.a_faire + ")" : x.faites ? "✓ Voix" : "🔊 Voix";
    $("dlgVoix").classList.toggle("dpl-fait", !p.a_faire && !!x.faites);   // v2.99.2 : fait = vert, meme desactive""")
rep(".dpl-etapes .dpl-fait{", ".dpl-etapes .btn.dpl-fait:disabled{opacity:1}   /* v2.99.2 */" + N + ".dpl-etapes .dpl-fait{")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v2.99.2")
