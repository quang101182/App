# -*- coding: utf-8 -*-
"""Banc v2.12.0 (4-undecies) : INTERROMPRE un lot / une narration seule, puis REPRENDRE -- sans reseau, sans rien payer.

Tout se passe dans un dossier jetable : suivi_nuit / interruption / reglages sont rediriges (SRC, etat, journal,
_reglages.json). Les « etapes » sont de vrais processus python qui dorment ; on verifie qu'ils meurent.
  A. lot de 4 chapitres : ch.1 fini, ch.2 en echec, ch.3 COUPE pendant la voix (analyse payee), ch.4 pas commence
     -> processus tues, etat « interrompu », bilan exact, progress.json marque, analyse gardee + son dossier (tag).
  B. narration lancee seule -> tuee, marquee, analyse pas finie = « pas gardee ».
  C. reprise : le chapitre coupe relit l'analyse de SON dossier d'origine (--reuse-vision gemini-charon) meme si le
     mode est passe en 🖥 (nouveau dossier -local) et meme en « refaire » ; un autre chapitre ne la reprend pas.
  D. mode relu a CHAQUE chapitre : l'interrupteur change entre deux chapitres -> le suivant part en --tts local.
Usage : python scripts/test_interruption.py   (exit 0 = vert)
"""
import json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="banc_interruption_")
os.environ["MANGA_REGLAGES"] = os.path.join(TMP, "_reglages.json")
import reglages, suivi_nuit as sn, interruption as itr
SRC = os.path.join(TMP, "sources")
sn.SRC, sn.DIR = SRC, os.path.join(SRC, "_suivi")
sn.ETAT, sn.JOURNAL = os.path.join(sn.DIR, "etat.json"), os.path.join(sn.DIR, "journal.jsonl")
itr.SRC = SRC
itr._suivi = lambda: sn
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def dormeur():
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], creationflags=itr.CREATE)


def ecrire(f, obj):
    os.makedirs(os.path.dirname(f), exist_ok=True)
    json.dump(obj, open(f, "w", encoding="utf-8"))


def chapitre(n):
    cd = os.path.join(SRC, "banc", "ch_%d" % n)
    ecrire(os.path.join(cd, "manifest.json"), {"chapter": str(n), "title": "banc", "pages": [{"file": "p%d.jpg" % i} for i in range(3)]})
    return cd


try:
    reglages.ecrire(mode="cloud")
    for n in (1, 2, 3, 4):
        chapitre(n)
    time.sleep(1.1)
    # --- A. un lot en cours, coupe pendant la voix du ch.3
    lot, etape = dormeur(), dormeur()
    nd = os.path.join(SRC, "banc", "ch_3", "narration", "gemini-charon")
    ecrire(os.path.join(nd, "vision.json"), {"pages": [{"p": 1}, {"p": 2}, {"p": 3}]})       # analyse payee
    ecrire(os.path.join(nd, "progress.json"), {"etape": "voix", "fait": 1, "total": 3, "t": time.time(), "pid": etape.pid})
    debut = time.time() - 5
    sn.ecrire_etat({"etat": "en cours", "pid": lot.pid, "debut": debut, "serie": "banc", "refaire": True,
                    "file": ["banc/ch_1", "banc/ch_2", "banc/ch_3", "banc/ch_4"],
                    "fait": [{"d": "banc/ch_1", "num": "1"}], "erreurs": [{"d": "banc/ch_2", "num": "2"}],
                    "en_cours": {"d": "banc/ch_3", "num": "3", "etape": "narration", "pid": etape.pid,
                                 "etapes": {"narration": "faire", "karaoke": "faire"}}})
    # --- B. une narration seule sur ch.4 (analyse pas finie)
    seule = dormeur()
    nd4 = os.path.join(SRC, "banc", "ch_4", "narration", "kimi-leda")
    ecrire(os.path.join(nd4, "progress.json"), {"etape": "vision", "fait": 1, "total": 3, "t": time.time(), "pid": seule.pid})
    b = itr.interrompre("banc")
    time.sleep(0.5)
    check("A. processus du lot + de l'étape tués", lot.poll() is not None and etape.poll() is not None)
    e = sn.lire_etat()
    check("A. état « interrompu »", e.get("etat") == "interrompu" and e.get("en_cours") is None, e.get("etat"))
    L = b["lot"] or {}
    check("A. bilan : finis ch.1, échec ch.2", L.get("finis") == ["1"] and L.get("erreurs") == ["2"], L)
    c = L.get("coupe") or {}
    check("A. bilan : ch.3 coupé à l'étape narration", c.get("d") == "banc/ch_3" and c.get("etape") == "narration", c)
    check("A. analyse payée GARDÉE + son dossier", c.get("analyse_gardee") is True and c.get("tag") == "gemini-charon", c)
    check("A. bilan : ch.4 pas commencé", L.get("restants") == ["banc/ch_4"] and L.get("restants_num") == ["4"], L.get("restants"))
    pr = json.load(open(os.path.join(nd, "progress.json"), encoding="utf-8"))
    check("A. progress.json du ch.3 dit « interrompu »", pr.get("etape") == "interrompu", pr.get("etape"))
    check("A. journal : ligne « interruption »", '"interruption"' in open(sn.JOURNAL, encoding="utf-8").read())
    check("B. narration seule tuée", seule.poll() is not None)
    s4 = [x for x in b["seuls"] if x["d"] == "banc/ch_4"]
    check("B. bilan : narration seule, analyse pas gardée", len(s4) == 1 and s4[0]["type"] == "narration" and s4[0]["analyse_gardee"] is False, s4)
    check("rien de non arrêté", not b["non_arretes"], b["non_arretes"])
    b2 = itr.interrompre("banc")
    check("2e interruption à vide : ne touche à rien", b2["lot"] is None and not b2["seuls"], b2)

    # --- C / D. la reprise, avec « lancer » remplace par un espion (aucun process, aucun appel)
    appels = []

    def espion(cmd, log, etat, etape_):
        appels.append((etape_, cmd))
        return 1                                            # « echec » : on ne regarde que ce qui AURAIT ete lance
    sn.lancer = espion
    reglages.ecrire(mode="pc")                             # Quang a bascule en 🖥 entre-temps
    old = sn.lire_etat()
    reprise_de = dict(old["interruption"]["coupe"], debut=old["debut"])
    cfg = dict(sn.DEFAUT_INTEGRE, moteur="gemini", voix="Charon", voix_moteur="cloud", karaoke=False, precedemment=False, video=False)
    ch = {c_["d"]: c_ for c_ in sn.chapitres("banc")}
    et = {}
    sn.traiter_chapitre(ch["banc/ch_3"], cfg, True, et, False, reprise_de)
    n1 = [c_ for e_, c_ in appels if e_ == "narration"][0]
    check("C. reprise du ch.3 : --reuse-vision gemini-charon (dossier d'origine)", n1[-2:] == ["--reuse-vision", "gemini-charon"], n1[-4:])
    check("D. mode relu : --tts local + dossier -local", "--tts" in n1 and n1[n1.index("--tts") + 1] == "local" and "gemini-charon-local" in n1, n1)
    check("D. l'état du chapitre note le mode 🖥", et.get("en_cours", {}).get("mode") == "pc")
    appels.clear(); reglages.ecrire(mode="cloud")
    sn.traiter_chapitre(ch["banc/ch_4"], cfg, True, et, False, reprise_de)
    n2 = [c_ for e_, c_ in appels if e_ == "narration"][0]
    check("C. un AUTRE chapitre ne reprend pas l'analyse du coupé (refaire)", "--reuse-vision" not in n2, n2[-4:])
    check("D. rebasculé ☁ -> --tts cloud", n2[n2.index("--tts") + 1] == "cloud")
finally:
    shutil.rmtree(TMP, ignore_errors=True)
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
