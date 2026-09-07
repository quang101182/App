# -*- coding: utf-8 -*-
"""Calibration du declencheur du mode CROISE.

Question : a partir de quel ratio Gemini/Groq faut-il considerer que Gemini a
DECROCHE sur un chunk, et basculer sur Groq ?

Le declencheur actuel (Gemini rend VIDE) ne couvre que le cas extreme. On mesure
donc, sur des extraits reels de regimes differents, le ratio de CARACTERES entre
les deux moteurs -- et pas le nombre de blocs, qui differe structurellement
(Gemini fabrique ses blocs depuis les mots, Groq rend ses propres segments).

Appelle exactement les memes endpoints que fly-ffmpeg/src/server.js.
"""
import io, os, re, sys, json, base64, subprocess, tempfile, time
import requests
from secret import worker_secret

GW = "https://api-gateway.quang101182.workers.dev"
GROQ_MODEL = "whisper-large-v3-turbo"
GEMINI_MODEL = "gemini-3.5-transcribe"
DUREE = 360          # 6 min = un chunk Gemini (11 Mo de PCM)

def extraire_wav(src, debut, sortie):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(debut), "-t", str(DUREE),
                    "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", sortie], check=True)
    return sortie

def texte_groq(wav, secret):
    with open(wav, "rb") as f:
        r = requests.post(GW + "/api/groq",
            headers={"Authorization": "Bearer " + secret,
                     "X-Api-Path": "/openai/v1/audio/transcriptions"},
            files={"file": (os.path.basename(wav), f, "audio/wav")},
            data={"model": GROQ_MODEL, "response_format": "verbose_json",
                  "timestamp_granularities[]": "segment"}, timeout=600)
    if not r.ok:
        return None, f"HTTP {r.status_code}"
    d = r.json()
    segs = d.get("segments") or []
    return "".join((s.get("text") or "").strip() for s in segs), f"{len(segs)} segs"

def texte_gemini(wav, secret):
    b64 = base64.b64encode(open(wav, "rb").read()).decode("ascii")
    body = {"model": GEMINI_MODEL,
            "input": [{"type": "audio", "mime_type": "audio/wav", "data": b64}],
            "generation_config": {"transcription_config": {
                "mode": {"type": "verbatim", "timestamp_granularities": ["word"]}}}}
    r = requests.post(GW + "/api/gemini/v1beta/interactions",
        headers={"Authorization": "Bearer " + secret,
                 "Content-Type": "application/json"}, json=body, timeout=900)
    if not r.ok:
        return None, f"HTTP {r.status_code}: {r.text[:120]}"
    d = r.json()
    mots = []
    for st in d.get("steps") or []:
        for c in st.get("content") or []:
            for an in c.get("annotations") or []:
                if an.get("type") == "word_info":
                    mots.append(an.get("text") or "")
    return "".join(m.strip() for m in mots), f"{len(mots)} mots"

# ── Le corpus vit DANS UN FICHIER LOCAL, jamais dans le code ────────────────
# `corpus.json` est gitignore : il designe des fichiers de la bibliotheque
# personnelle, qui n'ont rien a faire dans un depot public. Format attendu :
#   [{"etiquette": "cjk-1", "regime": "dialogue CJK reel",
#     "chemin": "D:/.../fichier.mp4", "offset_s": 600}, ...]
# Viser au moins deux regimes differents : un ou le moteur teste est cense
# exceller, un ou il est cense echouer. Sans cela on ne mesure pas un
# discriminant, on mesure un seul point.
CORPUS_PAR_DEFAUT = [
    {"etiquette": "exemple", "regime": "a decrire",
     "chemin": "chemin/vers/une/video.mp4", "offset_s": 0},
]


def charger_corpus():
    import json
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "corpus.json"), encoding="utf-8") as f:
            return [(c["etiquette"], c["regime"], c["chemin"], c.get("offset_s", 0))
                    for c in json.load(f)]
    except FileNotFoundError:
        print("⚠️  corpus.json absent — cree-le a cote de ce script "
              "(voir CORPUS_PAR_DEFAUT pour le format).")
        return []


if __name__ == "__main__":
    secret = worker_secret()
    lignes = []
    for etiq, regime, src, off in charger_corpus():
        if not os.path.exists(src):
            print(f"{etiq:9s} SOURCE ABSENTE — ignore"); continue
        wav = f"cal_{etiq}.wav"
        try:
            extraire_wav(src, off, wav)
        except Exception as e:
            print(f"{etiq:9s} extraction impossible : {e}"); continue
        taille = os.path.getsize(wav)
        tg, ig = texte_groq(wav, secret)
        time.sleep(4)                      # throttling Groq
        tge, ige = texte_gemini(wav, secret)
        os.remove(wav)
        if tg is None or tge is None:
            print(f"{etiq:9s} ECHEC groq={ig} gemini={ige}"); continue
        ratio = (len(tge) / len(tg)) if len(tg) else None
        lignes.append({"etiquette": etiq, "regime": regime,
                       "wav_Mo": round(taille/1048576, 1),
                       "groq_car": len(tg), "gemini_car": len(tge),
                       "ratio": round(ratio, 3) if ratio is not None else None,
                       "groq_info": ig, "gemini_info": ige})
        print(f"{etiq:9s} [{regime:24s}] groq {len(tg):5d} car ({ig:9s}) · "
              f"gemini {len(tge):5d} car ({ige:9s}) · ratio {ratio:.2f}", flush=True)
    json.dump(lignes, open("calibration_croise.json", "w"), indent=2, ensure_ascii=False)
    print("\n--- classement par ratio croissant ---")
    for l in sorted(lignes, key=lambda x: x["ratio"] if x["ratio"] is not None else 9):
        print(f"  {l['ratio']:.2f}  {l['etiquette']:9s} {l['regime']}")
