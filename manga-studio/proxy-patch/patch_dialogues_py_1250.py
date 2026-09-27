# -*- coding: utf-8 -*-
"""dialogues.py 1.24.0 -> 1.25.0 (27/09, Quang 19h11 : abonnement Creator pris, « l'information des couts sera fausse »)
-- le cout des voix etait une ESTIMATION (len x 0,28). Desormais : credits REELLEMENT consommes = solde ElevenLabs avant /
apres (meme forfait) ; l'estimation ne sert que si la lecture echoue. Chaque mesure recale le tarif (credits / caractere,
moyenne glissante) garde dans sources/_elevenlabs_tarif.json : les annonces de cout suivent le forfait. Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.25.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)
rep('VERSION = "1.24.0"  #', 'VERSION = "1.25.0"  # 1.25.0 (27/09) : cout des voix MESURE (solde avant / apres), tarif recale a chaque mesure ;  #')
rep('''def cout_el(envoye):
    return max(1, round(len(envoye) * TARIF_V3))''',
    '''def tarif_el():
    """1.25.0 : credits / caractere MESURE (sources/_elevenlabs_tarif.json), sinon TARIF_V3."""
    t = (lire_json(os.path.join(SOURCES, "_elevenlabs_tarif.json")) or {}).get("par_car")
    return float(t) if t and 0.01 < float(t) < 5 else TARIF_V3


def recaler_tarif(credits, caracteres):
    """1.25.0 : une mesure reelle (credits consommes pour N caracteres envoyes) -> moyenne glissante du tarif."""
    if credits <= 0 or caracteres < 20:
        return
    f = os.path.join(SOURCES, "_elevenlabs_tarif.json")
    d = lire_json(f) or {}
    mesure = credits / float(caracteres)
    anc, n = d.get("par_car"), int(d.get("mesures") or 0)
    d["par_car"] = round(mesure if not anc else (anc * min(n, 9) + mesure) / (min(n, 9) + 1), 4)
    d["mesures"] = n + 1
    d["derniere"] = {"credits": credits, "caracteres": caracteres, "par_car": round(mesure, 4), "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ecrire_json(f, d)


def cout_el(envoye):
    return max(1, round(len(envoye) * tarif_el()))''')
rep('''    depenses.noter_credits("dialogues", a.chap, "voix", "elevenlabs", credits, repliques=faits)
    depenses.noter("dialogues", a.chap, "balises", "deepseek", round(stats.get("cout_balises", 0.0), 5))
    solde2 = el_solde()''',
    '''    time.sleep(2)                                                          # 1.25.0 : le compteur ElevenLabs suit en ~1 s
    solde2 = el_solde()
    estime = credits
    if faits and solde and solde2 and solde2.get("limite") == solde.get("limite") and solde2["utilises"] >= solde["utilises"]:
        reel = solde2["utilises"] - solde["utilises"]
        if reel > 0:
            recaler_tarif(reel, stats.get("_car_envoyes", 0))
            credits = reel
            log("  credits MESURES : %d (estimation : %d)" % (reel, estime))
    depenses.noter_credits("dialogues", a.chap, "voix", "elevenlabs", credits, repliques=faits)
    depenses.noter("dialogues", a.chap, "balises", "deepseek", round(stats.get("cout_balises", 0.0), 5))''')
rep('''                credits += cout_el(envoye)''',
    '''                credits += cout_el(envoye)
                stats["_car_envoyes"] = stats.get("_car_envoyes", 0) + len(envoye)     # 1.25.0 : pour recaler le tarif''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.25.0")
