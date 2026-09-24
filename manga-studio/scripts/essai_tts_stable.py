"""ESSAI (24/09) : voix locale STABLE -- phrase par phrase, graine fixe, timbre clone sur la voix choisie par Quang
(p009_local_defaut.wav). Remarque Quang : p024 « horrible, timbre different, accelere » avec les memes parametres.
Mesure le debit (caracteres/s) de chaque page : il doit etre homogene. Ne modifie rien.
"""
import json, os, re, sys, time
import numpy as np, soundfile as sf, torch
HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"C:/Users/quang/Documents/MangaStudio-donnees/essais_voix_24-09"
ND = os.path.normpath(os.path.join(HERE, "..", "sources", "one-punch-man", "ch_1", "narration", "gemini-charon"))
REF = os.path.join(E, "p009_local_defaut.wav")
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
n = json.load(open(os.path.join(ND, "narration.json"), encoding="utf-8"))
for num in (9, 20, 24):
    txt = [p for p in n["pages"] if p["page"] == num][0]["narration"]
    phrases = [x.strip() for x in re.split(r"(?<=[.!?…])\s+", txt) if x.strip()]
    morceaux, t0 = [], time.time()
    for i, ph in enumerate(phrases):
        torch.manual_seed(1234 + i)
        w = m.generate(ph, language_id="fr", audio_prompt_path=REF, temperature=0.6, cfg_weight=0.5, exaggeration=0.5)
        morceaux += [w.squeeze().float().cpu().numpy(), np.zeros(int(0.25 * m.sr), np.float32)]
    audio = np.concatenate(morceaux)
    f = os.path.join(E, "p%03d_local_stable.wav" % num); sf.write(f, audio, m.sr)
    d = len(audio) / m.sr
    print("p%03d : %d phrases, %.1f s d'audio, %.1f car/s, calcul %.1f s" % (num, len(phrases), d, len(txt) / d, time.time() - t0))
