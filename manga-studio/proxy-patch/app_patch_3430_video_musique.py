# -*- coding: utf-8 -*-
"""v3.4.3 (27/09, Quang 19h15) : (1) « ✓ Video » ne disait pas qu'on pouvait la LANCER -> une video prete s'affiche
« ▶ Video » (vert, comme « ▶ Lire ») ; (2) musique changee (morceau ajoute / retire, musique activee / coupee) -> la video
du chapitre ouvert passe « a refaire » (comme la narration) : dlgVideos compare la musique ENREGISTREE dans la fiche de la
video (dialogues.py 1.24.0) a celle d'aujourd'hui (MUS_ON + MUS.effectif). Suppose v3.4.2. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.4.3" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.4.2" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3420_pourcentages.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)
rep("<title>Manga Studio v3.4.2</title>", "<title>Manga Studio v3.4.3</title>")
rep('<span class="ver" id="verBadge">v3.4.2</span>', '<span class="ver" id="verBadge">v3.4.3</span>')
rep('const VERSION = "3.4.2";', 'const VERSION = "3.4.3";   // v3.4.3 : video prete = « ▶ Video » ; musique changee = video a refaire')
rep("""  if (doc && doc.video && !out.tout && p && p.video && p.video !== "absente") out.tout = { v: doc.video, etat: p.video };
  return out;
}""", """  if (doc && doc.video && !out.tout && p && p.video && p.video !== "absente") out.tout = { v: doc.video, etat: p.video };
  if (doc && DLG.e && doc === DLG.e.doc && typeof MUS !== "undefined" && MUS){     // v3.4.3 : la musique a-t-elle change ?
    const voulu = (MUS_ON ? (MUS.effectif || []) : []).slice().sort().join("|");
    Object.values(out).forEach(x => { const eu = ((x.v.musique || {}).noms || []).slice().sort().join("|");
      if (x.etat === "a_jour" && eu !== voulu){ x.etat = "perimee"; x.musique = true; } });
  }
  return out;
}""")
rep("""    $("dlgVid").textContent = vv ? "✓ Vidéo" : x.v ? "🎬 Mettre à jour" : "🎬 Vidéo";""",
    """    $("dlgVid").textContent = vv ? "▶ Vidéo" : x.v ? (x.v.musique ? "🎬 Refaire (musique)" : "🎬 Mettre à jour") : "🎬 Vidéo";   // v3.4.3""")
rep("""    $("dlgVid").classList.toggle("dpl-fait", !!vv);""",
    """    $("dlgVid").classList.toggle("dpl-fait", false); $("dlgVid").classList.toggle("dpl-pret", !!vv);   // v3.4.3 : un BOUTON qui se lance""")
rep(".dpl-etapes .dpl-fait{", ".dpl-etapes .btn.dpl-pret{color:var(--ok);border-color:#3fbf7f;font-weight:700}   /* v3.4.3 */" + N + ".dpl-etapes .dpl-fait{")
rep("""'<span class="dpl-chip ' + (x.v.etat === "perimee" ? "warn" : "ok") + '">🎬 ' + (x.v.etat === "perimee" ? "à refaire" : x.v.v.duree ? Math.round(x.v.v.duree) + " s" : "prête") + "</span>\"""",
    """'<span class="dpl-chip ' + (x.v.etat === "perimee" ? "warn" : "ok") + '">🎬 ' + (x.v.etat === "perimee" ? (x.v.musique ? "à refaire (musique)" : "à refaire") : x.v.v.duree ? Math.round(x.v.v.duree) + " s" : "prête") + "</span>\"""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.4.3")
