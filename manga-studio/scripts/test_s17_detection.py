# -*- coding: utf-8 -*-
"""Banc S17 (28/09/2026, dialogues.py 1.30.0) : la DETECTION lit le texte de chaque zone (RapidOCR, local, gratuit) pour que les
petits cris soient reconnus avant toute traduction. VRAIE commande `dialogues.py detecter`, dans le venv de la detection, sur une
COPIE de quelques pages (dossier temporaire ; la source n'est jamais modifiee).
Controles : chaque zone porte « lu » ; au moins N cris reconnus ; aucune zone lue comme une vraie phrase (>= 4 mots) prise pour un
cri ; journal « zone(s) lue(s) ». Sabotage : --dialogues dialogues.py.bak-1290 (1.29.0) -> ROUGE.
Usage : python test_s17_detection.py <dossier du chapitre> <plage, ex. 20-22> [--min-cris 5] [--dialogues autre_dialogues.py]"""
import json, os, re, shutil, subprocess, sys, tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
args = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith("--") and sys.argv[i - 1] not in ("--min-cris", "--dialogues")]
CH, PL = os.path.abspath(args[0]), args[1]
PAGES = list(range(int(PL.split("-")[0]), int(PL.split("-")[-1]) + 1))
MIN = int(sys.argv[sys.argv.index("--min-cris") + 1]) if "--min-cris" in sys.argv else 1
DLG = os.path.abspath(sys.argv[sys.argv.index("--dialogues") + 1]) if "--dialogues" in sys.argv else os.path.join(ICI, "dialogues.py")
PY = os.environ.get("MANGA_PY", r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail != "" else ""), flush=True)


T = tempfile.mkdtemp(prefix="s17_")
try:
    dst = os.path.join(T, "zz-banc", "ch_1")
    os.makedirs(dst)
    man = json.load(open(os.path.join(CH, "manifest.json"), encoding="utf-8"))
    json.dump(man, open(os.path.join(dst, "manifest.json"), "w", encoding="utf-8"))
    for n, q in enumerate(man["pages"], 1):
        f = os.path.join(dst, q["file"])
        shutil.copy2(os.path.join(CH, q["file"]), f) if n in PAGES else open(f, "wb").close()
    run = DLG
    if DLG != os.path.join(ICI, "dialogues.py"):                  # sabotage : l'ancienne version, lancee depuis ce dossier
        run = os.path.join(ICI, "_banc_dialogues_s17.py"); shutil.copy2(DLG, run)
    r = subprocess.run([PY, run, "detecter", "zz-banc/ch_1", "--pages", PL], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=dict(os.environ, MANGA_SOURCES_DIR=T, PYTHONIOENCODING="utf-8"), timeout=900)
    if run != DLG:
        os.remove(run)
    journal = r.stdout + r.stderr
    print("  code", r.returncode, "|", " / ".join(l.strip() for l in journal.splitlines() if "zone(s) lue(s)" in l or "detection :" in l)[:300])
    det = json.load(open(os.path.join(dst, "dialogues", "detection.json"), encoding="utf-8"))["pages"]
    sys.path.insert(0, ICI)
    import dialogues as d
    zones = [(p, b) for p in det for b in det[p]["bulles"]]
    check("detection faite sur les %d page(s)" % len(PAGES), sorted(map(int, det)) == sorted(PAGES) and zones, sorted(det))
    check("chaque zone porte le texte lu (« lu »)", zones and all("lu" in b for _, b in zones), sum("lu" in b for _, b in zones))
    cris = [b["lu"] for _, b in zones if b.get("lu") and d.est_gimmick(b["lu"])]
    phrases = [b["lu"] for _, b in zones if b.get("lu") and len(re.findall(r"[A-Za-z]+", b["lu"])) >= 4]
    check("au moins %d petit(s) cri(s) reconnu(s)" % MIN, len(cris) >= MIN, cris[:12])
    check("aucune phrase (>= 4 mots) prise pour un cri", not any(d.est_gimmick(t) for t in phrases), phrases[:4])
    check("journal : zones lues, cris, illisibles par page", "zone(s) lue(s)" in journal)
    print("  zones %d, cris %d, illisibles %d" % (len(zones), len(cris), sum(1 for _, b in zones if b.get("lu") == "")))
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT %s : %d/%d" % ("VERT" if not KO else "ROUGE", len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
