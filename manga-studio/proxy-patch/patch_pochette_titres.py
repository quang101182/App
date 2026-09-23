# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : « Pochette officielle » essaie TOUS les titres connus de la serie (Manga Studio v2.6.1, 23/09/2026).

Quang (13h43, capture) : « Pochette officielle » sur Solo Leveling Ragnarok -> « pochette : HTTP Error 404: Not Found ».
Mesure : AniList repond 404 quand le titre ne trouve rien ; le titre de la serie porte une faute (« Solo Levelng -
Ragnarok ») et le titre MangaDex aussi echoue (« ... (Pre-serialization) »), mais un titre ALTERNATIF deja connu
(serie.json : « Solo Leveling: Ragnarok ») trouve du premier coup. Desormais : titre demande, puis titre MangaDex, puis
titres alternatifs (ecriture latine d'abord), le 1er qui trouve gagne ; sinon un message clair avec les titres essayes.
Rejouable : python patch_pochette_titres.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "# v2.6.1 : pochette, tous les titres" in s:
    print("deja patche"); sys.exit(0)
a = '''        if src == "anilist":
            titre = (data.get("titre") or slug.replace("-", " ")).strip()
            q = json.dumps({"query": "query($s:String){Media(search:$s,type:MANGA){title{romaji english}"
                                     " coverImage{extraLarge}}}", "variables": {"s": titre}}).encode()
            req = urllib.request.Request("https://graphql.anilist.co", data=q, headers={
                "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "manga-studio"})
            with urllib.request.urlopen(req, timeout=20) as r:
                m = (json.load(r).get("data") or {}).get("Media")
            if not m or not (m.get("coverImage") or {}).get("extraLarge"):
                return {"error": "aucune pochette trouvee sur AniList pour : " + titre}'''
b = '''        if src == "anilist":
            # v2.6.1 : pochette, tous les titres -- AniList repond 404 si rien ne correspond (titre a faute de frappe)
            titre = (data.get("titre") or slug.replace("-", " ")).strip()
            si = _serie_json(slug)
            essais = []
            for t in [titre, si.get("titre_mangadex")] + sorted(si.get("titres_alt") or [], key=lambda x: not str(x).isascii()):
                t = (t or "").strip()
                if t and t not in essais:
                    essais.append(t)
            m = None
            for t in essais[:8]:
                q = json.dumps({"query": "query($s:String){Media(search:$s,type:MANGA){title{romaji english}"
                                         " coverImage{extraLarge}}}", "variables": {"s": t}}).encode()
                req = urllib.request.Request("https://graphql.anilist.co", data=q, headers={
                    "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "manga-studio"})
                try:
                    with urllib.request.urlopen(req, timeout=20) as r:
                        m = (json.load(r).get("data") or {}).get("Media")
                except urllib.error.HTTPError as e:
                    if e.code != 404:
                        raise
                    m = None
                if m and (m.get("coverImage") or {}).get("extraLarge"):
                    break
                m = None
            if not m:
                return {"error": "aucune pochette trouvee sur AniList (titres essayes : " + " ; ".join(essais[:8]) + ")"}'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable (%d)" % s.count(a))
s = s.replace(a, b)
open(p, "w", encoding="utf-8").write(s)
print("patche")
