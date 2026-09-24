"""ESSAI (24/09) : voix de narration LOCALE (Chatterbox multilingue, GPU) contre la voix actuelle (Gemini « Charon »).

Prend 3 pages narrees d'un chapitre (narration.json + pNNN.mp3 existants), regenere le MEME texte en local :
  A. voix francaise par defaut ;  B. voix CLONEE sur un extrait de la narration actuelle (meme timbre).
Ecrit dans --out : pNNN_gemini.mp3 (copie), pNNN_local_defaut.wav, pNNN_local_clone.wav + temps de calcul.
Ne modifie rien. A lancer avec le venv TTS (sur C:) :
  C:/Users/quang/AppData/Local/manga-tts/venv/Scripts/python.exe essai_tts_local.py one-punch-man/ch_1 --out DIR
"""
import argparse, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre"); ap.add_argument("--out", required=True); ap.add_argument("--tag", default="gemini-charon")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    nd = os.path.join(SRC, a.chapitre, "narration", a.tag)
    n = json.load(open(os.path.join(nd, "narration.json"), encoding="utf-8"))
    pages = [p for p in n["pages"] if (p.get("narration") or "").strip() and p.get("audio") and os.path.isfile(os.path.join(nd, os.path.basename(p["audio"])))]
    pages = sorted(pages, key=lambda p: -len(p["narration"]))[:a.n]
    import torch, torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    t0 = time.time(); m = ChatterboxMultilingualTTS.from_pretrained(device="cuda"); print("modele charge en %.0f s" % (time.time() - t0))
    ref = os.path.join(nd, os.path.basename(pages[0]["audio"]))
    for p in pages:
        num = "p%03d" % p["page"]; txt = p["narration"]
        shutil.copy2(os.path.join(nd, os.path.basename(p["audio"])), os.path.join(a.out, num + "_gemini.mp3"))
        for nom, kw in (("defaut", {}), ("clone", {"audio_prompt_path": ref})):
            t0 = time.time()
            wav = m.generate(txt, language_id="fr", **kw)
            dt = time.time() - t0
            f = os.path.join(a.out, "%s_local_%s.wav" % (num, nom))
            import soundfile as sf                       # torchaudio 2.11 exige torchcodec pour save()
            sf.write(f, wav.squeeze().float().cpu().numpy(), m.sr)
            dur = wav.shape[-1] / m.sr
            print("%s %-6s : %4.1f s d'audio en %4.1f s (%.1fx temps reel) | %d car." % (num, nom, dur, dt, dur / dt, len(txt)))
        print("   texte :", txt[:140])


if __name__ == "__main__":
    main()
