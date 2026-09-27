# -*- coding: utf-8 -*-
"""R19 (27/09) -- dialogues.py 1.15.0 : la distribution AUTOMATIQUE ne choisit que des voix 100 % FRANCAISES (bibliotheque
publique ElevenLabs, language=fr, les plus utilisees, ouvertes a tous) ; repli sur le catalogue du compte seulement si la
bibliotheque ne repond pas. Les voix se choisissent a la main parmi toutes (/manga/el_voix, francaises d'abord). Mesure 27/09 :
voix de bibliotheque utilisable directement par son id (TTS 200), sans ajout au compte. Les personnages DEJA distribues gardent
leur voix (en changer = repayer leurs repliques : decision de Quang, ecran ✏). Suppose scripts_patch_r17.py.
Rejouable : python scripts_patch_r19.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
p = os.path.join(D, "dialogues.py")
s = open(p, encoding="utf-8", newline="").read()
if "def voix_francaises(" in s:
    print("deja applique"); sys.exit(0)
if 'VERSION = "1.14.0"' not in s:
    print("ERREUR : appliquer d'abord scripts_patch_r17.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.14.0"', 'VERSION = "1.15.0"  # 1.15.0 (R19, 27/09) : distribution automatique en voix 100 % FRANCAISES ;')
rep('''def catalogue_el():''', '''def voix_francaises():
    """1.15.0 (R19) : les voix FRANCAISES de la bibliotheque publique ElevenLabs ([] si elle ne repond pas)."""
    import urllib.request
    try:
        r = urllib.request.Request(nc.GATEWAY + "/api/elevenlabs/v1/shared-voices?page_size=100&language=fr&sort=cloned_by_count",
                                   headers={"Authorization": "Bearer " + nc.SECRET, "User-Agent": "manga-studio/dialogues-" + VERSION})
        v = json.load(urllib.request.urlopen(r, timeout=30)).get("voices") or []
    except Exception as e:
        log("  bibliotheque de voix francaises illisible (%s) : catalogue du compte" % str(e)[:120])
        return []
    out, vus = [], set()
    for x in v:
        if not x.get("free_users_allowed", True) or x.get("gender") not in ("male", "female") or x.get("voice_id") in vus:
            continue
        vus.add(x["voice_id"])
        n = x.get("name") or ""
        out.append({"id": x["voice_id"], "nom": n.split(" - ")[0].strip(), "genre": x["gender"], "age": x.get("age") or "?",
                    "desc": ((n.split(" - ", 1)[1] if " - " in n else "") or x.get("descriptive") or "")[:60], "fr": True})
    return out


def catalogue_el():''')
rep('''    cat = catalogue_el()''', '''    cat = voix_francaises() or catalogue_el()                  # 1.15.0 (R19) : 100 % francaises, sinon le compte''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
