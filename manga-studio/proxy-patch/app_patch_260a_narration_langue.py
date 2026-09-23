# -*- coding: utf-8 -*-
"""Manga Studio v2.6.0, etape N1 (23/09/2026) : choisir la LANGUE de la narration dans l'app (francais / anglais).
Le proxy (patch_narration_langue.py) nomme alors « moteur-voix-en » : la narration francaise n'est jamais ecrasee.
« Autre voix » garde la langue de la narration d'origine. Choix memorise par appareil.
Rejouable : python app_patch_260a_narration_langue.py <manga_studio.html>.
"""
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if 'id="narrLangue"' in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''        <div style="width:110px"><label>Pages</label><input id="narrPages" placeholder="toutes" title="ex. 1-20 ; vide = tout le chapitre"></div>''',
    '''        <div style="width:118px"><label>Langue</label><select id="narrLangue" title="langue de la narration (le texte ET la voix)">
          <option value="fr">Français</option><option value="en">Anglais</option></select></div>
        <div style="width:110px"><label>Pages</label><input id="narrPages" placeholder="toutes" title="ex. 1-20 ; vide = tout le chapitre"></div>''')
rep('''  const body = { d: CHAP_OPEN, engine: $("narrEngine").value, voice: $("narrVoice").value, pages: $("narrPages").value.trim() };''',
    '''  const body = { d: CHAP_OPEN, engine: $("narrEngine").value, voice: $("narrVoice").value, pages: $("narrPages").value.trim(),
                 langue: $("narrLangue").value };                                          // v2.6.0 (N1)''')
rep('''      const r = await api("/manga/narrate", { d: CHAP_OPEN, engine: n.engine, voice: voix, reuse: n.tag });''',
    '''      const r = await api("/manga/narrate", { d: CHAP_OPEN, engine: n.engine, voice: voix, reuse: n.tag, langue: n.langue || "fr" });''')
rep('''/* ----- v1.96.0 : chapitre precedent / suivant (meme serie, ordre des numeros) ----- */''',
    '''// v2.6.0 (N1) : la langue de narration choisie est gardee sur cet appareil
try { const l = localStorage.getItem("manga_narr_langue"); if (l === "fr" || l === "en") $("narrLangue").value = l; } catch {}
$("narrLangue").onchange = () => { try { localStorage.setItem("manga_narr_langue", $("narrLangue").value); } catch {} };

/* ----- v1.96.0 : chapitre precedent / suivant (meme serie, ordre des numeros) ----- */''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
