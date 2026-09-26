# -*- coding: utf-8 -*-
"""Banc dialogues.py lot (D4-bis, ROADMAP 4-septdecies) -- HORS LIGNE : preparer/voix simules, dossier temporaire.
A. ch.1 · ch.2 (non traduit) · ch.3 · ch.4, action « tout », quota epuise au ch.3 : ordre respecte, ch.2 saute, ARRET au ch.3
   (ch.4 jamais touche), etat « arrete » + motif
B. reprise : ch.1 deja prepare -> pas repaye ; voix reprises ; ch.4 fait ; etat « fini »
C. portee : ch.1 a ch.1 = un seul chapitre
D. MUTATION : quota qui ne coupe pas le lot -> ROUGE
Usage : python test_dialogues_lot.py
"""
import json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
T = tempfile.mkdtemp(prefix="banc_dlot_")
os.environ.update(MANGA_SOURCES_DIR=T, MANGA_DEPENSES=os.path.join(T, "_d.jsonl"), MANGA_ALERTES=os.path.join(T, "_a.json"))
sys.path.insert(0, HERE)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""))


def decor():
    shutil.rmtree(os.path.join(T, "s"), ignore_errors=True)
    for n in (1, 2, 3, 4):
        ch = os.path.join(T, "s", "ch_%d" % n)
        os.makedirs(ch)
        json.dump({"chapter": str(n)}, open(os.path.join(ch, "manifest.json"), "w"))
        if n != 2:
            os.makedirs(os.path.join(ch, "traduction", "fr"))
            open(os.path.join(ch, "traduction", "fr", "traduction.json"), "w").write("{}")


def charger(patch=None):
    src = open(os.path.join(HERE, "dialogues.py"), encoding="utf-8").read()
    for a, b in (patch or []):
        assert a in src, a[:60]
        src = src.replace(a, b)
    m = types.ModuleType("dlot")
    m.__file__ = os.path.join(HERE, "dialogues.py")
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    m.APPELS = []

    def prep(a):
        m.APPELS.append(("preparer", a.chap))
        dd = os.path.join(T, a.chap.replace("/", os.sep), "dialogues")
        os.makedirs(dd, exist_ok=True)
        open(os.path.join(dd, "dialogues.json"), "w").write('{"repliques": []}')
        return 0

    def voix(a):
        m.APPELS.append(("voix", a.chap))
        return m.CODE_QUOTA if a.chap in m.QUOTA else 0
    m.cmd_preparer, m.cmd_voix, m.QUOTA = prep, voix, set()
    return m


def lot(m, de, a_, action="tout"):
    return m.cmd_lot(types.SimpleNamespace(serie="s", de=de, a=a_, action=action))


def scenario(m):
    k0 = len(KO)
    decor()
    m.APPELS.clear(); m.QUOTA = {"s/ch_3"}
    code = lot(m, 1, 4)
    e = json.load(open(os.path.join(T, "s", "dialogues_lot.json"), encoding="utf-8"))
    et = {c["ch"]: c["etat"] for c in e["chapitres"]}
    check("A. code 4 (quota)", code == 4, code)
    check("A. ordre : ch_1 prep+voix, ch_3 prep+voix, rien apres", m.APPELS == [("preparer", "s/ch_1"), ("voix", "s/ch_1"),
          ("preparer", "s/ch_3"), ("voix", "s/ch_3")], m.APPELS)
    check("A. ch_2 non traduit saute, ch_4 en attente", et.get("ch_2") == "non traduit" and et.get("ch_4") == "attente", et)
    check("A. etat arrete + motif", e["etat"] == "arrete" and "quota" in (e.get("arret") or ""), e.get("arret"))
    m.APPELS.clear(); m.QUOTA = set()
    code = lot(m, 1, 4)
    e = json.load(open(os.path.join(T, "s", "dialogues_lot.json"), encoding="utf-8"))
    check("B. reprise : aucun chapitre deja prepare repaye", ("preparer", "s/ch_1") not in m.APPELS and ("preparer", "s/ch_3") not in m.APPELS, m.APPELS)
    check("B. reprise : ch_4 prepare + voix, etat fini", ("preparer", "s/ch_4") in m.APPELS and ("voix", "s/ch_4") in m.APPELS and e["etat"] == "fini" and code == 0)
    m.APPELS.clear()
    lot(m, 1, 1, "voix")
    check("C. portee ch.1 seul", m.APPELS == [("voix", "s/ch_1")], m.APPELS)
    return len(KO) == k0


print("=== A-C")
scenario(charger())
print("=== D. mutation")
a0, o0 = len(KO), len(OK)
vert = scenario(charger([('; code = CODE_QUOTA\n                    break', '; code = CODE_QUOTA\n                    continue')]))
del KO[a0:]; del OK[o0:]
check("D. mutation « quota qui ne coupe pas le lot » detectee", not vert)
shutil.rmtree(T, ignore_errors=True)
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
