# -*- coding: utf-8 -*-
"""Patch du proxy : AVANCEMENT d'une capture en serie dans /manga/activite (Manga Studio v2.53.0, 25/09/2026).

Constat (Quang 25/09 12h25, capture reprise au ch.23) : « calcul du temps restant… » affiche EN PERMANENCE. Le serveur
n'envoyait que le nombre de pages du chapitre en cours, total VIDE -> aucun temps restant possible. Desormais, pour une
capture EN SERIE : fait = chapitres termines, total = chapitres demandes (suite + 1, ou jusqu'au N depuis le depart),
etape = « ch. N », reste_s = duree ecoulee / chapitres faits x chapitres restants (des le 1er chapitre fini).
Une capture d'UN chapitre garde son compte de pages (total inconnu d'avance). Rejouable ; fins de ligne conservees.
Usage : python patch_capture_avancement.py <chemin du proxy>
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in s else "\n"
if "_capture_avancement(fs)" in s:
    print("deja patche"); sys.exit(0)
A = ('            out.append({"type": "capture", "titre": fs.get("titre"), "chapitre": str(fs.get("chapitre") or ""),' + NL
     + '                        "fait": fs.get("pages"), "total": None, "d": None})' + NL)
B = ('            out.append(_capture_avancement(fs))            # v2.53.0 : en serie -> chapitres faits / demandes + reste' + NL)
F = NL.join([
    'def _capture_avancement(fs):',
    '    """Manga Studio v2.53.0 : la ligne « capture » de l\'activite. En SERIE : avancement en CHAPITRES et temps restant mesure."""',
    '    it = {"type": "capture", "titre": fs.get("titre"), "chapitre": str(fs.get("chapitre") or ""),',
    '          "fait": fs.get("pages"), "total": None, "d": None}',
    '    try:',
    '        suite, jusqua = int(fs.get("suite") or 0), str(fs.get("jusqua") or "")',
    '        if not (suite or jusqua):',
    '            return it',
    '        dep = float(fs.get("chapitre_depart"))',
    '        total = suite + 1 if suite else max(1, int(float(jusqua) - dep) + 1)',
    '        faits = min(len(fs.get("dossiers") or []), total)',
    '        it.update(fait=faits, total=total, etape="ch. %s" % (fs.get("chapitre") or "?"), pages=fs.get("pages"))',
    '        if faits >= 1 and fs.get("duree_s"):',
    '            it["reste_s"] = round(float(fs["duree_s"]) / faits * max(0, total - faits))',
    '    except (TypeError, ValueError):',
    '        pass',
    '    return it',
    '', '', ''])
A2 = "def manga_activite():" + NL
for a in (A, A2):
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:60]))
s = s.replace(A, B, 1).replace(A2, F + A2, 1)
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
