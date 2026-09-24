"""Voix LOCALE de narration (feuille de route 4-nonies, etape 1 -- 24/09/2026).

Chatterbox multilingue sur la carte graphique, methode « stable » validee a l'oreille par Quang le 24/09 : phrase par
phrase, graine fixe par phrase, timbre CLONE sur l'extrait de la voix choisie (sources/_apercus/<Voix>.mp3).
Sans ca, memes parametres = timbre qui change et debit jusqu'a 21,6 car/s (« horrible », p024).

Tourne dans le venv voix (sur C:) : C:/Users/quang/AppData/Local/manga-tts/venv/Scripts/python.exe
  entree  : --jobs fichier.json = [{"id": "p001", "texte": "..."}, ...]
  sortie  : <out>/<id>.mp3 + une ligne JSON par morceau sur stdout ({"id", "dur", "s"}), puis {"fin": ...}
  code 3  : carte graphique occupee trop longtemps (ComfyUI / Generate Studio) -- rien n'est produit
Avant de charger le modele : attend que la carte soit LIBRE (memoire et file ComfyUI), sans se battre avec elle.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

VERSION = "1.2.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
APERCUS = os.path.join(SRC, "_apercus")
MEMOIRE_MIN_MO = 5000          # Chatterbox multilingue : ~4 Go mesures en generation
COMFY = "http://127.0.0.1:8188/queue"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def dit(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def etat_gpu():
    """-> (memoire libre en Mo, file ComfyUI occupee ?). None si nvidia-smi est absent."""
    try:
        libre = int(subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=15).stdout.split()[0])
    except Exception:
        libre = None
    try:
        q = json.load(urllib.request.urlopen(COMFY, timeout=3))
        comfy = bool(q.get("queue_running") or q.get("queue_pending"))
    except Exception:
        comfy = False                                           # ComfyUI eteint = rien en cours
    return libre, comfy


def attendre_gpu(max_s):
    t0, dernier = time.time(), 0
    while True:
        libre, comfy = etat_gpu()
        if (libre is None or libre >= MEMOIRE_MIN_MO) and not comfy:
            dit(gpu="libre", memoire_libre_mo=libre, attente_s=round(time.time() - t0))
            return True
        if time.time() - t0 > max_s:
            dit(gpu="occupee", memoire_libre_mo=libre, comfyui=comfy, abandon_apres_s=round(time.time() - t0))
            return False
        if time.time() - dernier > 60:
            dit(gpu="attente", memoire_libre_mo=libre, comfyui=comfy)
            dernier = time.time()
        time.sleep(10)


def phrases(txt):
    return [x.strip() for x in re.split(r"(?<=[.!?…])\s+", txt) if x.strip()]


def main():
    try: __import__("declaration_gpu").declarer("voix")      # v2.13.0 : sa part de la VRAM, pour la jauge ventilee
    except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True); ap.add_argument("--voix", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--attente-max", type=int, default=1800, help="secondes d'attente d'une carte libre (defaut 30 min)")
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--debit", type=float, default=17.4,
                    help="v1.1.0 : debit vise en caracteres/s (17,4 = voix en ligne Charon mesuree sur OPM ch.1) ; 0 = naturel")
    a = ap.parse_args()
    ref = os.path.join(APERCUS, a.voix + ".mp3")
    if not re.match(r"^[A-Z][a-z]{2,15}$", a.voix) or not os.path.isfile(ref):
        dit(erreur="voix locale inconnue : %s (extraits disponibles : %s)" % (a.voix, ", ".join(
            sorted(f[:-4] for f in os.listdir(APERCUS) if f.endswith(".mp3")))))
        return 2
    jobs = json.load(open(a.jobs, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    if not attendre_gpu(a.attente_max):
        return 3
    import numpy as np, soundfile as sf, torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    t0 = time.time()
    m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    dit(modele="chatterbox-multilingue", voix=a.voix, charge_s=round(time.time() - t0, 1), version=VERSION)
    total_s, total_dur = 0.0, 0.0
    for j in jobs:
        t = time.time(); morceaux = []
        for i, ph in enumerate(phrases(j["texte"])):
            torch.manual_seed(1234 + i)
            w = m.generate(ph, language_id=a.langue, audio_prompt_path=ref, temperature=a.temperature)
            morceaux += [w.squeeze().float().cpu().numpy(), np.zeros(int(0.25 * m.sr), np.float32)]
        if not morceaux:
            continue
        wav = os.path.join(a.out, j["id"] + ".wav")
        sf.write(wav, np.concatenate(morceaux[:-1]), m.sr)
        mp3 = os.path.join(a.out, j["id"] + ".mp3")
        dur0 = sum(len(x) for x in morceaux[:-1]) / m.sr
        # v1.1.0 (Quang 24/09 : « j'aime bien regler la voix a 1,15 ») : la voix locale parle ~20 % plus lentement que
        # l'en-ligne -> tempo ramene au MEME debit (sans changer la hauteur), borne 0,9-1,35 ; le 1,15x de la video
        # donne alors le meme rythme qu'avec la voix en ligne
        k = 1.0 if not a.debit else min(1.35, max(0.9, a.debit / (len(j["texte"]) / max(dur0, 0.1))))
        filtre = ["-filter:a", "atempo=%.3f" % k] if abs(k - 1) > 0.02 else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav] + filtre + ["-b:a", "128k", mp3], check=True)
        os.remove(wav)
        dur = dur0 / k if filtre else dur0
        dt = time.time() - t
        total_s += dt; total_dur += dur
        dit(id=j["id"], dur=round(dur, 2), s=round(dt, 1), car=len(j["texte"]), car_s=round(len(j["texte"]) / max(dur, 0.1), 1),
            tempo=round(k, 3))
    dit(fin=True, morceaux=len(jobs), audio_s=round(total_dur, 1), calcul_s=round(total_s, 1),
        temps_reel=round(total_dur / max(total_s, 0.1), 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
