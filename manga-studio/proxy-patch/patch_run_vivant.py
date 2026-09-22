# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : une tache est « en cours » tant que SON PROCESSUS vit (Manga Studio v1.91.0, 22/09/2026).

Bug trouve le 22/09 a 05h50 : apres une relance du proxy, une narration etait jugee vivante si sa progression avait
bouge il y a < 3 min. Or un lot Kimi K3 de 2 pages prend jusqu'a 4 min (timeout 240 s + reessais) : a 219 s
d'immobilite, une narration qui TRAVAILLAIT allait s'afficher « echec » (et la suppression du chapitre n'etait
plus bloquee). Maintenant : narrate / traduire / karaoke ecrivent leur PID dans progress.json -> le proxy demande a
Windows si ce processus existe encore (_pid_vivant EXISTANT de Generate Studio v7.28, reutilise : le redefinir
l'aurait remplace pour tout le proxy) et depuis moins d'1 h (contre un PID recycle) ; sans PID (runs lances avant
v1.91), repli sur 10 min au lieu de 3. Les 4 regles « < 180 » passent par _run_vivant().
Rejouable : python patch_run_vivant.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def _pid_vivant(" not in s:
    raise SystemExit("_pid_vivant (Generate Studio v7.28) introuvable : ne pas le recreer ici")
if "def _run_vivant(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def _manga_src_safe(rel):''',
    '''def _run_vivant(pr):
    """Une tache (narration, traduction, karaoke) tourne-t-elle encore ? pr = son progress.json. (v1.91.0)"""
    if not pr or pr.get("fini") or pr.get("etape") == "fini":
        return False
    age = time.time() - float(pr.get("t") or 0)
    if pr.get("pid"):
        return age < 3600 and _pid_vivant(pr["pid"])
    return age < 600                                         # run lance avant v1.91 (sans PID) : 10 min de repli


def _manga_src_safe(rel):''')
rep('''                if pr.get("etape") != "fini" and time.time() - float(pr.get("t") or 0) < 180:''',
    '''                if _run_vivant(pr):''')
rep('''        return not pr.get("fini") and time.time() - float(pr.get("t") or 0) < 180''',
    '''        return _run_vivant(pr)''')
rep('''            it.get("progress") and not it["progress"].get("fini") and time.time() - float(it["progress"].get("t") or 0) < 180)''',
    '''            _run_vivant(it.get("progress")))''')
rep('''                it["running"] = time.time() - float(it.get("progress", {}).get("t") or 0) < 180''',
    '''                it["running"] = _run_vivant(it.get("progress"))''')
open(p, "w", encoding="utf-8").write(s)
print("patch run vivant OK")
