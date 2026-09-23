# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : narration dans une AUTRE LANGUE depuis l'app (Manga Studio v2.6.0, etape N1, 23/09/2026).

Remontee de la session Video Studio (23/09), confirmee dans le code : manga_narrate imposait l'etiquette « moteur-voix »
et ne transmettait jamais --langue a narrate_chapter.py -> impossible de narrer en anglais depuis l'app ; et ajouter la
langue SANS changer l'etiquette aurait ECRASE la narration francaise (meme dossier narration/<tag>/).
Desormais : `langue` accepte (liste blanche = LANGUES_NARR de narrate_chapter.py : fr, en), etiquette
« moteur-voix-<langue> » hors francais (la regle du script, v2.0.0), et la liste des narrations dit leur langue.
Rejouable : python patch_narration_langue.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "# v2.6.0 : langue de narration" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_narrate(d, engine, voice, pages="", reuse=""):''',
    '''_NARR_LANGUES = ("fr", "en")                     # v2.6.0 : langue de narration = LANGUES_NARR de narrate_chapter.py


def manga_narrate(d, engine, voice, pages="", reuse="", langue="fr"):''')
rep('''    tag = "%s-%s" % (engine, voice.lower())
    if reuse and not _RE_TAG.match(reuse):''',
    '''    langue = langue or "fr"
    if langue not in _NARR_LANGUES:
        return {"error": "langue de narration inconnue"}
    # v2.6.0 : langue de narration -- hors francais, l'etiquette porte la langue (sinon l'anglais ECRASAIT le francais)
    tag = "%s-%s" % (engine, voice.lower()) + ("" if langue == "fr" else "-" + langue)
    if reuse and not _RE_TAG.match(reuse):''')
rep('''    if reuse: cmd += ["--reuse-vision", reuse]
    lg = open(os.path.join(td, "run.log"), "w", encoding="utf-8")''',
    '''    if reuse: cmd += ["--reuse-vision", reuse]
    if langue != "fr": cmd += ["--langue", langue]
    lg = open(os.path.join(td, "run.log"), "w", encoding="utf-8")''')
rep('''                    it.update(etat="fini", engine=n.get("engine"), model=n.get("model"), voice=n.get("voice"),''',
    '''                    it.update(etat="fini", engine=n.get("engine"), model=n.get("model"), voice=n.get("voice"),
                              langue=n.get("langue") or "fr",''')
rep('''                self._json(200, manga_narrate(data.get("d") or "", data.get("engine") or "",
                                              data.get("voice") or "", str(data.get("pages") or ""),
                                              data.get("reuse") or ""))''',
    '''                self._json(200, manga_narrate(data.get("d") or "", data.get("engine") or "",
                                              data.get("voice") or "", str(data.get("pages") or ""),
                                              data.get("reuse") or "", data.get("langue") or "fr"))''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
