# -*- coding: utf-8 -*-
"""Apercus des voix de narration (Manga Studio v1.76.0, demande Quang 21/09 : « un petit bouton play/stop
pour ecouter a quoi la voix ressemble AVANT de generer »).

Genere UNE FOIS sources/_apercus/<Voix>.mp3 par le MEME chemin que la narration (Chirp 3 HD fr-FR via le
gateway, meme vitesse). ~130 caracteres par voix = ~0,004 $ la voix. Le dossier commence par "_" : la
bibliotheque l'ignore. Relancer avec --force pour regenerer (nouvelle phrase, nouvelle vitesse).

Usage : python voix_apercus.py [--force]
"""
import base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narrate_chapter as nc

PHRASE = ("Le village retient son souffle. La guerrière aux yeux d'argent dégaine son épée : "
          "cette fois, le monstre n'a plus nulle part où se cacher.")
VOIX = ["Charon", "Fenrir", "Orus", "Puck", "Algenib", "Kore", "Aoede", "Leda"]   # = la liste VOIX de l'app
VOIX = [v for v in os.environ.get("MANGA_VOIX", "").split(",") if v.strip()] or VOIX   # S7 : voix de l'application secondaire
RATE = 1.05                                                                      # = defaut de narrate_chapter


def main():
    nc.SECRET = nc._secret()
    out = os.path.join(nc.SOURCES, "_apercus")
    os.makedirs(out, exist_ok=True)
    force, faits = "--force" in sys.argv, 0
    for v in VOIX:
        f = os.path.join(out, v + ".mp3")
        if os.path.isfile(f) and not force:
            continue
        r = nc.post("/api/gcptts/v1/text:synthesize", {
            "input": {"text": PHRASE}, "voice": {"languageCode": "fr-FR", "name": "fr-FR-Chirp3-HD-" + v},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": RATE}}, timeout=90)
        with open(f, "wb") as fh:
            fh.write(base64.b64decode(r["audioContent"]))
        faits += 1
        print("%-8s %6d octets  %.1f s" % (v, os.path.getsize(f), nc.duree_mp3(f) or 0))
    print("%d apercu(s) genere(s), cout ~%.3f $" % (faits, faits * len(PHRASE) * nc.PRIX_TTS_CHAR))


if __name__ == "__main__":
    main()
