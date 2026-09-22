# -*- coding: utf-8 -*-
"""Banc de la CHAINE (suivi_nuit.py v2.4.0, etape 27) : un lot REEL, de la capture brute a la video.

Cree sources/banc-lot/ (2 chapitres de 3 pages copies d'OPM 298 et 299, VO vietnamienne, manifestes gardes : la langue
se detecte par MangaDex), un profil Gemini + Charon + traduction fr + karaoke + « Precedemment » + video, puis :
  1. plan a sec : 2 chapitres, toutes les etapes « faire » (sauf Precedemment du 1er : premier chapitre) ;
  2. le lot pour de vrai (--declencheur lot) : narration avec voix, mots du karaoke, traduction fr, ouverture du ch.2,
     2 videos fabriquees par la file du proxy (8190) ;
  3. relance : « rien a faire » (tout est saute : idempotence) ;
  4. plan --refaire : tout redevient « faire » ; plan avec traduction « vi » : sautee (« deja en vi »).
~0,15 $ (Gemini, 6 pages). Tout est efface a la fin (dossier, file video).
Usage : python test_chaine.py
"""
import json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
BANC = os.path.join(SRC, "banc-lot")
PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"
OK, KO = [], []
sys.path.insert(0, HERE)


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def chaine(*args, timeout=3600):
    r = subprocess.run([PY, os.path.join(HERE, "suivi_nuit.py"), "--serie", "banc-lot", "--declencheur", "lot"] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, r.stdout + r.stderr


def prepare():
    shutil.rmtree(BANC, ignore_errors=True)
    for i, src in ((1, "one-punch-man/ch_298"), (2, "one-punch-man/ch_299")):
        cs, cd = os.path.join(SRC, src), os.path.join(BANC, "ch_%d" % i)
        os.makedirs(cd)
        man = json.load(open(os.path.join(cs, "manifest.json"), encoding="utf-8"))
        pages = man["pages"][1:4]                      # la page 1 = credits du traducteur
        for p in pages:
            shutil.copy(os.path.join(cs, p["file"]), os.path.join(cd, p["file"]))
        man.update(pages=pages, chapter=str(i), slug="banc-lot", title="banc lot")
        json.dump(man, open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"actif": False, "moteur": "gemini", "voix": "Charon", "traduction": "fr", "karaoke": True,
               "precedemment": True, "video": True,
               "reglages_video": {"vitesse": 1.0, "sous": True, "karaoke": True, "musique": False, "volume": 25,
                                  "pages": "", "precedemment": True}},
              open(os.path.join(BANC, "suivi.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def nettoie_file():
    fd = os.path.join(SRC, "_videos_file")
    for f in (os.listdir(fd) if os.path.isdir(fd) else []):
        if f.endswith(".json") and not f.startswith("_"):
            try:
                if json.load(open(os.path.join(fd, f), encoding="utf-8")).get("d", "").startswith("banc-lot/"):
                    for x in (f, f[:-5] + ".log"):
                        try: os.remove(os.path.join(fd, x))
                        except OSError: pass
            except Exception:
                pass


def main():
    prepare()
    try:
        import suivi_nuit as sn
        pl = sn.plan_serie("banc-lot", detecter_langue=True)
        check("plan : 2 chapitres à faire", [p["num"] for p in pl if p["a_faire"]] == ["1", "2"], [p["etapes"] for p in pl])
        check("plan : ch.1 tout à faire sauf « Précédemment » (premier)",
              pl[0]["etapes"] == {"narration": "faire", "karaoke": "faire", "traduction": "faire", "precedemment": "non", "video": "faire"},
              pl[0]["etapes"])
        check("plan : ch.2 tout à faire", all(v == "faire" for v in pl[1]["etapes"].values()), pl[1]["etapes"])
        check("plan : estimation > 0", sum(p["cout"] for p in pl) > 0, sum(p["cout"] for p in pl))

        t0 = time.time()
        rc, out = chaine()
        print("  (lot : %d s)" % (time.time() - t0))
        check("lot : code 0", rc == 0, out[-300:])
        e = sn.lire_etat()
        check("lot : état fini, 2 faits, 0 erreur", e.get("etat") == "fini" and len(e.get("fait") or []) == 2 and not e.get("erreurs"),
              {k: e.get(k) for k in ("etat", "fait", "erreurs")})
        for i in (1, 2):
            cd = os.path.join(BANC, "ch_%d" % i)
            nf = os.path.join(cd, "narration", "gemini-charon", "narration.json")
            n = json.load(open(nf, encoding="utf-8")) if os.path.isfile(nf) else {"pages": []}
            voix = [p for p in n["pages"] if p.get("audio")]
            texte = [p for p in n["pages"] if (p.get("narration") or "").strip()]
            # une page sans texte a narrer (pleine page muette) n'a pas de voix : chaque page AVEC texte doit en avoir une
            check("ch.%d : narration avec voix sur chaque page qui a du texte" % i, voix and len(voix) == len(texte),
                  "%d voix / %d pages avec texte / %d pages" % (len(voix), len(texte), len(n["pages"])))
            check("ch.%d : karaoké calé" % i, all(p.get("mots") for p in voix), sum(1 for p in voix if p.get("mots")))
            check("ch.%d : traduction fr" % i, os.path.isfile(os.path.join(cd, "traduction", "fr", "traduction.json")))
        check("ch.2 : « Précédemment » fabriqué", os.path.isfile(os.path.join(BANC, "ch_2", "precedemment", "ouverture.json")))
        # videos : la file du proxy les fabrique (pas d'attente dans la chaine) -> on attend ici, 15 min max
        fin = time.time() + 900
        while time.time() < fin and not all(os.path.isfile(os.path.join(BANC, "ch_%d" % i, "video", "gemini-charon.mp4")) for i in (1, 2)):
            time.sleep(10)
        for i in (1, 2):
            vj = os.path.join(BANC, "ch_%d" % i, "video", "gemini-charon.json")
            v = json.load(open(vj, encoding="utf-8")) if os.path.isfile(vj) else {}
            check("ch.%d : vidéo fabriquée, pages traduites (fr)" % i, bool(v) and (v.get("reglages") or {}).get("pages") == "fr",
                  (v.get("reglages") or {}).get("pages"))

        rc, out = chaine()
        check("relance : rien à faire (tout est sauté)", rc == 0 and "rien a faire" in out, out[-200:])
        pl = sn.plan_serie("banc-lot", refaire=True)
        check("--refaire : tout redevient à faire", all(p["etapes"]["narration"] == "faire" and p["etapes"]["video"] == "faire" for p in pl))
        cfg = sn.profil("banc-lot")[0]; cfg["traduction"] = "vi"
        pl = sn.plan_serie("banc-lot", cfg=cfg)
        check("traduction vers la langue d'origine (vi) : sautée", all(p["etapes"]["traduction"] == "non" and "vi" in p["pourquoi"].get("traduction", "") for p in pl),
              [p["pourquoi"] for p in pl])
    finally:
        nettoie_file()
        shutil.rmtree(BANC, ignore_errors=True)
    print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
    return 0 if not KO else 1


if __name__ == "__main__":
    sys.exit(main())
