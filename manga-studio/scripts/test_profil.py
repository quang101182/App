# -*- coding: utf-8 -*-
"""Banc des routes PROFIL + LOT (Manga Studio v2.4.0, etape 27 phase 2).

Usage : python test_profil.py [port]     (8191 = copie patchee, 8190 = proxy reel)
Cree sources/banc-profil/ et banc-profil-2/ (1 chapitre de 3 pages copie d'OPM 298, VO vi). Le defaut general
(sources/_profil_defaut.json) est SAUVE avant et RESTAURE apres (la config reelle de Quang n'est jamais perdue).
Verifie : profil par defaut d'une serie neuve, enregistrement normalise, « en faire mes reglages par defaut »
(sans « actif »), une AUTRE serie neuve le recoit, « reprendre mes defauts », refus des lots invalides, puis un LOT
REEL (Gemini, 3 pages, sans video, ~0,05 $) visible dans /manga/activite, fini, relance = rien a faire.
"""
import json, os, shutil, sys, time, urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8191
BASE = "http://127.0.0.1:%d" % PORT
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
DEF = os.path.join(SRC, "_profil_defaut.json")
B1, B2 = os.path.join(SRC, "banc-profil"), os.path.join(SRC, "banc-profil-2")
OK, KO = [], []


def api(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def serie_banc(dossier):
    shutil.rmtree(dossier, ignore_errors=True)
    cs, cd = os.path.join(SRC, "one-punch-man", "ch_298"), os.path.join(dossier, "ch_1")
    os.makedirs(cd)
    man = json.load(open(os.path.join(cs, "manifest.json"), encoding="utf-8"))
    man.update(pages=man["pages"][1:4], chapter="1", slug=os.path.basename(dossier), title=os.path.basename(dossier))
    for p in man["pages"]:
        shutil.copy(os.path.join(cs, p["file"]), os.path.join(cd, p["file"]))
    json.dump(man, open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    sauve = open(DEF, "rb").read() if os.path.isfile(DEF) else None
    serie_banc(B1); serie_banc(B2)
    try:
        if os.path.isfile(DEF):
            os.remove(DEF)
        r = api("/manga/suivi?serie=banc-profil")
        check("série neuve : pas de profil propre", r.get("a_profil") is False, r.get("a_profil"))
        check("série neuve : profil = défaut", r.get("config") == r.get("defaut"), r.get("config"))
        check("plan : 1 chapitre, narration à faire", len(r.get("plan") or []) == 1 and r["plan"][0]["etapes"]["narration"] == "faire")
        check("estimation > 0", (r.get("estimation") or {}).get("cout", 0) > 0, r.get("estimation"))

        cfg = dict(r["config"], moteur="gemini", voix="Aoede", traduction="fr", actif=True, video=False)
        cfg["reglages_video"] = dict(cfg["reglages_video"], vitesse=1.2)
        api("/manga/suivi", dict(cfg, serie="banc-profil"))
        r = api("/manga/suivi?serie=banc-profil")
        c = r.get("config") or {}
        check("enregistré : profil propre", r.get("a_profil") is True)
        check("enregistré : gemini / Aoede / fr / vitesse 1,2", (c.get("moteur"), c.get("voix"), c.get("traduction"),
              c.get("reglages_video", {}).get("vitesse")) == ("gemini", "Aoede", "fr", 1.2), c)
        api("/manga/suivi", dict(cfg, serie="banc-profil", traduction="xx", moteur="pixtral"))
        c = api("/manga/suivi?serie=banc-profil")["config"]
        check("valeurs inconnues normalisées (traduction xx → aucune, pixtral → kimi)", c["traduction"] == "" and c["moteur"] == "kimi", c)
        api("/manga/suivi", dict(cfg, serie="banc-profil"))

        r = api("/manga/profil_defaut", {"serie": "banc-profil", "action": "depuis_serie"})
        d = r.get("defaut") or {}
        check("« en faire mes réglages par défaut » : copié", (d.get("moteur"), d.get("voix"), d.get("traduction")) == ("gemini", "Aoede", "fr"), d)
        check("… sans « actif » (la nuit se règle par série)", d.get("actif") is False)
        check("GET /manga/profil_defaut = pareil", api("/manga/profil_defaut").get("defaut") == d)
        r2 = api("/manga/suivi?serie=banc-profil-2")
        check("une AUTRE série neuve reçoit ces défauts", r2.get("a_profil") is False and r2["config"]["voix"] == "Aoede"
              and r2["config"]["traduction"] == "fr", r2.get("config"))

        api("/manga/suivi", dict(cfg, serie="banc-profil", voix="Fenrir"))
        r = api("/manga/profil_defaut", {"serie": "banc-profil", "action": "vers_serie"})
        check("« reprendre mes défauts » : voix remise à Aoede, « actif » gardé",
              r["config"]["voix"] == "Aoede" and r["config"]["actif"] is True, r.get("config"))

        check("lot refusé : chapitre d'une autre série", "error" in api("/manga/suivi_lancer",
              {"serie": "banc-profil", "lot": True, "chapitres": ["one-punch-man/ch_298"]}))
        check("lot refusé : sans série", "error" in api("/manga/suivi_lancer", {"lot": True}))

        # LOT REEL : gemini, fr, karaoke, pas de video (3 pages)
        api("/manga/suivi", dict(cfg, serie="banc-profil", actif=False))
        r = api("/manga/suivi_lancer", {"serie": "banc-profil", "lot": True, "chapitres": ["banc-profil/ch_1"]})
        check("lot lancé", r.get("ok"), r)
        vu_lot, t0 = [], time.time()
        while time.time() - t0 < 900:
            items = [x for x in api("/manga/activite").get("items") or [] if x.get("type") == "lot"]
            if items:
                vu_lot.append(items[0].get("etape"))
            p = api("/manga/suivi?serie=banc-profil")["passage"]
            if p.get("etat") in ("fini", "echec", "interrompu") and time.time() - t0 > 5:
                break
            time.sleep(3)
        check("activité : l'item « lot » suit les étapes", "narration" in vu_lot and "traduction" in vu_lot, sorted(set(x for x in vu_lot if x)))
        p = api("/manga/suivi?serie=banc-profil")
        check("lot fini, 1 fait, 0 erreur", p["passage"].get("etat") == "fini" and len(p["passage"].get("fait") or []) == 1
              and not p["passage"].get("erreurs"), {k: p["passage"].get(k) for k in ("etat", "fait", "erreurs")})
        check("après le lot : plus rien à faire", not [x for x in p.get("plan") or [] if x["a_faire"]], [x["etapes"] for x in p.get("plan") or []])
    finally:
        if sauve is None:
            try: os.remove(DEF)
            except OSError: pass
        else:
            open(DEF, "wb").write(sauve)
        shutil.rmtree(B1, ignore_errors=True); shutil.rmtree(B2, ignore_errors=True)
    check("défaut général restauré", (open(DEF, "rb").read() if os.path.isfile(DEF) else None) == sauve)
    print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
    return 0 if not KO else 1


if __name__ == "__main__":
    sys.exit(main())
