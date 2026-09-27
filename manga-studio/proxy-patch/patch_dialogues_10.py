# -*- coding: utf-8 -*-
"""Manga Studio v2.88.0 -- mode Dialogues, 10e patch serveur (R19, Quang 27/09 13h14 : « ca fait vraiment moche quand c'est
anglophone […] les voix privilegiees doivent etre 100 % francaises, les autres restent optionnelles ») : /manga/el_voix rend
d'ABORD les voix FRANCAISES de la bibliotheque publique ElevenLabs (language=fr, les plus utilisees, ouvertes a tous), marquees
« fr », PUIS les voix du compte (les 25 voix par defaut d'ElevenLabs, anglophones de naissance), marquees fr=false.
Mesure 27/09 : une voix de la bibliotheque s'utilise DIRECTEMENT par son id (TTS 200) -- aucun ajout au compte, aucun
emplacement (le compte n'en a que 3). Cache 1 h comme avant. Rejouable : python patch_dialogues_10.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "shared-voices?page_size=100&language=fr" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
a = '''    try:
        out = []
        for x in _el_get("/api/elevenlabs/v1/voices").get("voices") or []:
            lb = x.get("labels") or {}
            n = x.get("name") or ""
            out.append({"id": x.get("voice_id"), "nom": n.split(" - ")[0].strip(), "genre": lb.get("gender") or "?",
                        "age": lb.get("age") or "?", "desc": (n.split(" - ", 1)[1] if " - " in n else "") or lb.get("descriptive") or ""})
'''.replace("\n", NL)
b = '''    try:
        out, vus = [], set()
        try:                                             # v2.88.0 (R19) : les voix FRANCAISES d'abord (bibliotheque publique)
            for x in _el_get("/api/elevenlabs/v1/shared-voices?page_size=100&language=fr&sort=cloned_by_count").get("voices") or []:
                n = x.get("name") or ""
                if not x.get("free_users_allowed", True) or x.get("gender") not in ("male", "female") or x.get("voice_id") in vus:
                    continue
                vus.add(x.get("voice_id"))
                out.append({"id": x.get("voice_id"), "nom": n.split(" - ")[0].strip(), "genre": x.get("gender"), "age": x.get("age") or "?",
                            "desc": ((n.split(" - ", 1)[1] if " - " in n else "") or x.get("descriptive") or "")[:60]
                                    + (" · " + x["accent"] if x.get("accent") and x["accent"] != "standard" else ""),
                            "fr": True})
        except Exception:
            pass
        for x in _el_get("/api/elevenlabs/v1/voices").get("voices") or []:
            if x.get("voice_id") in vus:                 # une voix de bibliotheque UTILISEE est rangee au compte par EL (27/09)
                continue
            lb = x.get("labels") or {}
            n = x.get("name") or ""
            out.append({"id": x.get("voice_id"), "nom": n.split(" - ")[0].strip(), "genre": lb.get("gender") or "?",
                        "age": lb.get("age") or "?", "desc": (n.split(" - ", 1)[1] if " - " in n else "") or lb.get("descriptive") or "",
                        "fr": False})
'''.replace("\n", NL)
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
