# -*- coding: utf-8 -*-
"""dialogues.py 1.23.0 -> 1.24.0 (27/09, Quang 18h57 : musique de fond optionnelle pour les Dialogues) -- la VIDEO des
Dialogues peut porter la musique de la serie : `video` / `tout` --musique '{"noms": [...], "volume": 0-100}'. MEME regle
que video_chapitre.py (playlist melangee a graine gardee, fondu 3 s, gain = volume x 0,4, -7 dB sous la voix, baisse
0,3 s / remonte ~2,5 s, pas de 100 ms comme musTick) ; mixage ffmpeg amix (voix intactes). Le choix est garde dans la
fiche de la video (« musique »). Sans --musique : video d'avant, a l'identique. Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.24.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.23.0"  #', 'VERSION = "1.24.0"  # 1.24.0 (27/09) : musique de fond de la serie dans la video des Dialogues (optionnelle) ;  #')
FN = r'''

def piste_musique(musique, serie_dir, segments, sortie):
    """1.24.0 : la musique de fond de la video des Dialogues, MEME regle que video_chapitre.mixer. segments = [(duree, parle)].
    Ecrit un WAV stereo de la duree totale (gain applique) ; None si aucun morceau."""
    import numpy as np, random, wave
    import video_chapitre as vc
    md = os.path.join(serie_dir, "musique")
    dispo = os.listdir(md) if os.path.isdir(md) else []
    fichiers = [os.path.join(md, f[0]) for f in ([x for x in dispo if os.path.splitext(x)[0] == nom] for nom in musique.get("noms") or []) if f]
    if not fichiers:
        return None
    SR, total = vc.SR, sum(d for d, _ in segments)
    N_ = int((total + 0.5) * SR)
    rnd = random.Random(musique.get("graine") or 1)
    seq, mus, t, k = [], np.zeros((N_, 2), np.float32), 0.0, 0
    while t < total + 1:
        if len(seq) <= k:
            tour = list(range(len(fichiers))); rnd.shuffle(tour)
            if len(fichiers) > 1 and seq and tour[0] == seq[-1]:
                tour.append(tour.pop(0))
            seq += tour
        x = vc.pcm(fichiers[seq[k]])
        d = len(x) / SR
        env = np.minimum(1.0, np.minimum(np.arange(len(x)) / SR / vc.FONDU, (d - np.arange(len(x)) / SR) / vc.FONDU)).clip(0, 1)
        i0 = int(t * SR); i1 = min(N_, i0 + len(x))
        if i1 > i0:
            mus[i0:i1] += x[: i1 - i0] * env[: i1 - i0, None]
        t += max(1.0, d - vc.FONDU); k += 1
    parle, t = np.zeros(int(total * 10) + 2, bool), 0.0
    for d, p in segments:
        if p:
            parle[int(t * 10): int((t + max(0.0, d - 0.4)) * 10) + 1] = True    # le silence de fin de replique (apad 0,4 s) laisse remonter
        t += d
    base = float(musique.get("volume", 25)) / 100 * vc.GAIN_MAX
    g, gains = 0.0, []
    for st in range(int((total + 1.2) * 10) + 1):
        cible = 0.0 if st / 10 >= total else base * (vc.DUCK if st < len(parle) and parle[st] else 1)
        g += max(-0.02, min(max(0.004, cible * 0.04), cible - g))
        gains.append(g)
    gain = np.interp(np.arange(N_) / SR, np.arange(len(gains)) / 10, np.array(gains)).astype(np.float32)
    mus = np.clip(mus * gain[:, None], -1, 1)
    with wave.open(sortie, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mus * 32767).astype("<i2").tobytes())
    return sortie

'''
rep("\n\ndef cmd_preparer(a):", FN.replace("\n", N) + "\ndef cmd_preparer(a):")
rep('''    base = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "i.txt"), "-f", "concat", "-safe", "0",
            "-i", os.path.join(tmp, "a.txt"), "-vf", "fps=30,format=yuv420p"]
    fin = ["-c:a", "copy", "-shortest", "-movflags", "+faststart", sortie]''',
    '''    base = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "i.txt"), "-f", "concat", "-safe", "0",
            "-i", os.path.join(tmp, "a.txt"), "-vf", "fps=30,format=yuv420p"]
    fin = ["-c:a", "copy", "-shortest", "-movflags", "+faststart", sortie]
    musique = json.loads(getattr(a, "musique", "") or "null") if getattr(a, "musique", "") else None     # 1.24.0
    piste = None
    if musique and musique.get("noms"):
        try:
            piste = piste_musique(musique, serie_dir, [(du, not x.get("vide")) for (_i, du), x in zip(imgs, etapes)], os.path.join(tmp, "musique.wav"))
        except Exception as e:
            log("  musique de fond impossible (%s) : video sans musique" % str(e)[:160])
    if piste:
        base = [x for x in base if x not in ("-vf", "fps=30,format=yuv420p")] + ["-i", piste, "-filter_complex",
                "[0:v]fps=30,format=yuv420p[v];[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[v]", "-map", "[a]"]
        fin = ["-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", sortie]''')
rep('''         "duree": nc.duree_mp3(sortie), "t": time.strftime("%Y-%m-%dT%H:%M:%S"), "portee": portee or "tout"}''',
    '''         "duree": nc.duree_mp3(sortie), "t": time.strftime("%Y-%m-%dT%H:%M:%S"), "portee": portee or "tout",
         "musique": ({"noms": musique.get("noms"), "volume": musique.get("volume")} if piste else None)}   # 1.24.0''')
rep('''                                                     "reglages": {"pages": "fr", "sous": True, "musique": False}})''',
    '''                                                     "reglages": {"pages": "fr", "sous": True, "musique": bool(piste)}})''')
rep('''    vi = sp.add_parser("video"); vi.add_argument("chap"); vi.add_argument("--pages", default="", help="1.10.0 : la video de cette portee seulement")''',
    '''    vi = sp.add_parser("video"); vi.add_argument("chap"); vi.add_argument("--pages", default="", help="1.10.0 : la video de cette portee seulement")
    vi.add_argument("--musique", default="", help="1.24.0 : JSON {noms, volume} -- musique de fond de la serie")''')
rep('''    to.add_argument("--traduire", action="store_true"); to.add_argument("--sans-preparation", action="store_true", dest="sans_preparation")''',
    '''    to.add_argument("--traduire", action="store_true"); to.add_argument("--sans-preparation", action="store_true", dest="sans_preparation")
    to.add_argument("--musique", default="")                                                             # 1.24.0''')
rep('''        subprocess.run(base + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"] + fin, check=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))''',
    '''        r2 = subprocess.run(base + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"] + fin, capture_output=True, text=True,
                            errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r2.returncode:                                                     # 1.24.0 : l'erreur d'ffmpeg dans le journal
            log("ECHEC ffmpeg (nvenc : %s) (x264 : %s)" % ((r.stderr or "")[-300:], (r2.stderr or "")[-300:]))
            raise RuntimeError("video : ffmpeg a echoue (voir le journal)")''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.24.0")
