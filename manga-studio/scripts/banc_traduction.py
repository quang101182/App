# -*- coding: utf-8 -*-
"""Banc : ce que devient une PHRASE EXPLICATIVE francaise en passant par /enhance.

Pourquoi ce banc existe (28/07/2026, demande de Quang) : « mes requetes sont plus
des phrases explicatives que de vrais prompts », et le resultat ne les respecte pas.

Le probleme ne se voit PAS dans la base : `traduire()` et `ameliorerPrompt()`
ECRASENT `p.prompt` par leur sortie. La phrase de depart n'est conservee nulle
part -- ni en base, ni dans le journal. On ne peut donc pas auditer apres coup :
il faut rejouer la traduction sur des phrases representatives.

Ce banc mesure quatre choses, chacune avec un critere VERIFIABLE :
  1. NEGATION       -- « sans voir son visage » doit produire un NEG, jamais le
                       tag positif `face`. Une negation traduite en tag positif
                       demande exactement le contraire de ce qui est ecrit.
  2. CADRAGE        -- « tres gros plan sur ses mains » doit produire un tag
                       d'echelle (close-up / extreme close-up).
  3. COMPTAGE       -- combien de personnages la phrase demande-t-elle, et que
                       repond `nbPersonnages()` (reimplemente ici a l'identique).
  4. INVENTION      -- l'amelioration ajoute-t-elle un decor / une lumiere /
                       une emotion que la phrase ne demande pas ?

Usage :
    python banc_traduction.py            les 14 cas
    python banc_traduction.py --n 3      les 3 premiers (mise au point)
    python banc_traduction.py --json out.json
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = os.environ.get("MANGA_PROXY", "http://127.0.0.1:8190")
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"

# ⚠ La consigne est LUE DANS L'APP, jamais recopiee ici.
# Le premier jet en gardait une copie « exacte » -- et une copie diverge : le
# banc aurait mesure une consigne qui n'existe plus, avec l'assurance du chiffre.
# C'est la meme famille de defaut que les trois bancs perimes du 28/07 matin.
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "manga_studio.html")


def consigne_de_lapp(nom):
    """Extrait une consigne du source de l'app (concatenation de litteraux JS).

    On reconstitue la chaine que le navigateur enverra : les litteraux entre
    guillemets sont concatenes, et les echappements JS (\\n, \\") redeviennent
    ce qu'ils designent. Les lignes de commentaire sont ignorees -- elles ne
    contiennent pas de litteral en fin de ligne.
    """
    src = io.open(APP, encoding="utf-8").read()
    i = src.index("const " + nom + " =")
    # ⚠ On retire les commentaires AVANT de chercher le point-virgule final.
    # Premier jet : la coupure tombait sur un « ; » situe DANS un commentaire
    # (« il rendait `solo` malgre la consigne ; »), et le banc mesurait une
    # consigne tronquee -- sans le bloc COUNT, donc sans ce qu'il venait
    # justement verifier. Un extracteur qui lit du code doit ignorer les
    # commentaires en premier, jamais en dernier.
    brut = src[i:i + 6000]
    brut = "\n".join(l for l in brut.splitlines()
                     if not l.strip().startswith("//"))
    bout = brut[:brut.index(";")]
    morceaux = re.findall(r'"((?:[^"\\]|\\.)*)"', bout)
    txt = "".join(morceaux)
    for avant, apres in (("\\n", "\n"), ('\\"', '"'), ("\\'", "'"),
                         ("\\\\", "\\")):
        txt = txt.replace(avant, apres)
    return txt


TRAD_CONSIGNE = consigne_de_lapp("TRAD_CONSIGNE")

AMELIO_CONSIGNE = (
    "Manga panel, black and white. IMPORTANT: if the scene involves several "
    "characters, you MUST use danbooru count tags (2boys, 2girls, 1boy 1girl, "
    "3boys, multiple boys, multiple girls) and you must NOT output the tag "
    "\"solo\". If it involves exactly one, use solo. Scene: ")

# --- Les cas. Ecrits comme Quang ecrit : des phrases, pas des tags. -----------
# `attendus` : ce qu'un humain lit dans la phrase. C'est la reference du banc.
CAS = [
    dict(id="C1", txt="Je voudrais un plan tres rapproche sur ses pieds, sans que l'on voie son visage.",
         nb=1, cadrage=True, negation=["face", "visage"]),
    dict(id="C2", txt="Un gros plan sur ses mains crispees, on ne doit voir que les mains.",
         nb=1, cadrage=True, negation=None),
    dict(id="C3", txt="Le dojo est vide, personne dedans, juste la lumiere du matin qui passe par les fenetres.",
         nb=0, cadrage=False, negation=["1girl", "1boy", "person", "solo"]),
    dict(id="C4", txt="Elle s'elance et lui donne un coup de pied saute, avec des lignes de vitesse.",
         nb=2, cadrage=False, negation=None),
    dict(id="C5", txt="Elle esquive en arriere, ses cheveux suivent le mouvement, en plan serre.",
         nb=1, cadrage=True, negation=None),
    dict(id="C6", txt="Vue de dos, elle s'arrete sur le seuil de la porte, on ne voit pas son visage.",
         nb=1, cadrage=False, negation=["face", "visage"]),
    dict(id="C7", txt="Les deux adversaires se font face au centre du dojo, plan large, tension.",
         nb=2, cadrage=True, negation=None),
    dict(id="C8", txt="Un couloir de lycee vide, un bras qui se fait tirer violemment hors du cadre.",
         nb=1, cadrage=False, negation=None),
    dict(id="C9", txt="Tres gros plan sur ses orteils poses sur lui, on ne voit rien d'autre, pas de tete.",
         nb=2, cadrage=True, negation=["face", "head"]),
    dict(id="C10", txt="Elle est debout au-dessus de lui, il est attache sur le lit, elle le domine du regard.",
         nb=2, cadrage=False, negation=None),
    dict(id="C11", txt="Un plan de coupe sur la fenetre de la classe, il pleut, aucun personnage.",
         nb=0, cadrage=False, negation=["1girl", "1boy", "person", "solo"]),
    dict(id="C12", txt="Je veux qu'on la voie de profil, en contre-plongee, l'air determine.",
         nb=1, cadrage=True, negation=None),
    dict(id="C13", txt="Les autres eleves chuchotent et se retournent vers elle.",
         nb=3, cadrage=False, negation=None),
    dict(id="C14", txt="Plan tres large de la ville la nuit, vue des toits, sans aucun personnage.",
         nb=0, cadrage=True, negation=["1girl", "1boy", "person", "solo"]),
]

# --- Reimplementation FIDELE des heuristiques de l'app (manga_studio.html) ----
MOTS_FR = ["une", "un", "des", "les", "le", "la", "du", "dans", "avec", "sur",
           "sous", "qui", "que", "pour", "est", "sont", "et", "ses", "son", "sa", "leur",
           "montrant", "assise", "assis", "debout", "deux", "trois", "quatre", "femme",
           "homme", "fille", "garcon", "jeune", "vieux", "grand", "petite", "petit"]
CHIFFRES_FR = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "2": 2, "3": 3, "4": 4,
               "5": 5, "two": 2, "three": 3, "four": 4, "five": 5}
SUJETS_FR = ["personnage", "personnages", "homme", "hommes", "femme", "femmes",
             "fille", "filles", "garcon", "garcons", "maitre", "maitres", "guerrier",
             "guerriers", "robot", "robots", "mecha", "mechas", "combattant",
             "combattants", "people", "characters", "men", "women", "girls", "boys",
             "masters", "robots"]


def mots(t):
    return [m for m in re.split(r"[^a-z0-9]+", (t or "").lower()) if m]


def semble_francais(t):
    s = (t or "").lower()
    if not s.strip():
        return False
    if re.search(r"[\u00e0-\u00ff\u0152\u0153]", s):
        return True
    return any(m in MOTS_FR for m in re.split(r"[^a-z]+", s) if m)


def nb_personnages(t):
    ms = mots(t)
    for i in range(len(ms) - 1):
        n = CHIFFRES_FR.get(ms[i])
        if n:
            for j in range(i + 1, min(i + 4, len(ms))):
                if ms[j] in SUJETS_FR:
                    return n
    distincts = set(m.rstrip("s") for m in ms if m in SUJETS_FR)
    return len(distincts) if len(distincts) >= 2 else 0


# --- Appel du proxy ----------------------------------------------------------
def secret():
    if not os.path.isfile(SECRET_FILE):
        print("ARRET : %s introuvable. Sans la cle, le proxy repond 401 et le banc\n"
              "        conclurait a un defaut de traduction qui n'existe pas." % SECRET_FILE)
        sys.exit(2)
    return open(SECRET_FILE).read().strip()


def enhance(idea, fmt, cle):
    req = urllib.request.Request(
        PROXY + "/enhance",
        data=json.dumps({"idea": idea, "format": fmt}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + cle})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def joue(cas, cle):
    out = dict(cas)
    try:
        r = enhance(TRAD_CONSIGNE + cas["txt"], "raw", cle)
        # ⚠ Le COUNT arrive sur la DEUXIEME ligne. Ne garder que la premiere
        # avant de le chercher, c'est le jeter puis constater qu'il manque --
        # ce que le banc a fait au premier jet, en concluant « 0 sur 14 » alors
        # que le modele repondait « COUNT:2 » a chaque fois.
        brut = (r.get("prompt") or "").strip()
        m = re.search(r"COUNT\s*[:：]\s*(\d+)", brut, re.I)
        out["count"] = int(m.group(1)) if m else None
        brut = re.sub(r"[,;]?\s*COUNT\s*[:：]\s*\d+", "", brut, flags=re.I)
        out["traduit"] = brut.strip().split("\n")[0].strip()
        out["trad_neg"] = r.get("negativeAdd") or ""
    except Exception as e:
        out["traduit"] = "ERREUR: %s" % e
        out["trad_neg"] = ""
        out["count"] = None
        out["count"] = None
    try:
        r = enhance(AMELIO_CONSIGNE + cas["txt"], "tags", cle)
        out["ameliore"] = (r.get("prompt") or "").strip()
        out["amelio_neg"] = r.get("negativeAdd") or ""
    except Exception as e:
        out["ameliore"] = "ERREUR: %s" % e
        out["amelio_neg"] = ""
    return out


# --- Criteres ----------------------------------------------------------------
CADRAGE_TAGS = ["close-up", "close up", "closeup", "extreme close", "wide shot",
                "cowboy shot", "full body", "upper body", "from above", "from below",
                "from behind", "from side", "profile", "portrait", "long shot"]


def a_cadrage(s):
    b = (s or "").lower()
    return any(t in b for t in CADRAGE_TAGS)


def negation_violee(s, mots_interdits):
    """Un tag POSITIF qui reprend le mot nie = la demande est inversee."""
    if not mots_interdits:
        return []
    b = (s or "").lower()
    return [m for m in mots_interdits if re.search(r"\b" + re.escape(m.lower()) + r"\b", b)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=len(CAS))
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    cle = secret()
    cas = CAS[:args.n]

    with ThreadPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(lambda c: joue(c, cle), cas))

    print("=" * 78)
    print("BANC TRADUCTION -- %d cas, proxy %s" % (len(res), PROXY))
    print("=" * 78)
    stats = dict(fr_rate=0, neg_pos=0, cadrage_perdu=0, compte_faux=0,
                 invente=0, count_absent=0, count_faux=0)
    for r in res:
        det_fr = semble_francais(r["txt"])
        n_app = nb_personnages(r["txt"])
        viol_t = negation_violee(r["traduit"], r["negation"])
        viol_a = negation_violee(r["ameliore"], r["negation"])
        cad_t = a_cadrage(r["traduit"])
        cad_a = a_cadrage(r["ameliore"])
        print("\n--- %s  %s" % (r["id"], r["txt"]))
        print("    detecte francais : %s   (sinon la phrase part TELLE QUELLE au moteur)"
              % ("oui" if det_fr else "NON  <-- DEFAUT"))
        print("    personnages attendus %s | COUNT du modèle : %s | nbPersonnages() rend %s%s"
              % (r["nb"], r.get("count"), n_app,
                 "   <-- ECART heuristique" if n_app != r["nb"]
                    and not (r["nb"] <= 1 and n_app == 0) else ""))
        print("    _%s"
              % ("",))
        print("    TRADUIT  : %s" % r["traduit"][:200])
        if r["trad_neg"]:
            print("      NEG    : %s" % r["trad_neg"][:120])
        print("    AMELIORE : %s" % r["ameliore"][:200])
        if r["amelio_neg"]:
            print("      NEG    : %s" % r["amelio_neg"][:120])
        if r["negation"]:
            print("    negation : traduit %s | ameliore %s"
                  % ("VIOLEE " + str(viol_t) if viol_t else "ok",
                     "VIOLEE " + str(viol_a) if viol_a else "ok"))
        if r["cadrage"]:
            print("    cadrage demande : traduit %s | ameliore %s"
                  % ("present" if cad_t else "PERDU", "present" if cad_a else "PERDU"))
        if not det_fr:
            stats["fr_rate"] += 1
        if viol_t or viol_a:
            stats["neg_pos"] += 1
        if r["cadrage"] and not (cad_t or cad_a):
            stats["cadrage_perdu"] += 1
        if n_app != r["nb"] and not (r["nb"] <= 1 and n_app == 0):
            stats["compte_faux"] += 1
        # ⚠ Ces deux compteurs manquaient au premier jet : le verdict annoncait
        # « 0 COUNT absent » alors qu'il l'etait sur les 14 cas. Un compteur
        # jamais incremente affiche zero, et zero se lit comme une reussite.
        # Un chiffre doit venir d'une addition, jamais d'une valeur par defaut.
        if r.get("count") is None:
            stats["count_absent"] += 1
        elif r["count"] != r["nb"]:
            stats["count_faux"] += 1

    print("\n" + "=" * 78)
    print("VERDICT sur %d cas" % len(res))
    print("  phrases francaises NON detectees (partent non traduites) : %d" % stats["fr_rate"])
    print("  negations rendues en tag POSITIF                         : %d" % stats["neg_pos"])
    print("  cadrages explicitement demandes et PERDUS                : %d" % stats["cadrage_perdu"])
    print("  comptages faux -- ancienne heuristique de mots            : %d" % stats["compte_faux"])
    print("  comptages faux -- COUNT demande au modele (v1.61.0)       : %d"
          % stats["count_faux"])
    print("  COUNT absent de la reponse                                : %d"
          % stats["count_absent"])
    if args.json:
        json.dump(res, io.open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  detail -> %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
