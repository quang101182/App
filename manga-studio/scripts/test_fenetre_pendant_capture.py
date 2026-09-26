# -*- coding: utf-8 -*-
"""Banc 26/09/2026 : gestes de FENETRE autorises pendant une capture (patch_pilote_fenetre_capture + cdp_mini en_capture).
A lancer PENDANT une vraie capture de l'application (port 8190 par defaut). Verifie : taille sure = accepte ; ranger (place
retenue assez grande) = accepte ; fermer = REFUSE ; ranger avec une place retenue TROP PETITE = REFUSE et la fenetre ne bouge
pas ; un clic dans la page = toujours REFUSE ; la capture tourne toujours. fenetre.json (place retenue de Quang) est sauvegarde
octet pour octet et RESTAURE a la fin, quoi qu'il arrive.
Usage : python test_fenetre_pendant_capture.py [port]
"""
import json, os, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
CONF = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "manga-fetch", "fenetre.json")
def api(ch, corps=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, ch), data=json.dumps(corps).encode() if corps is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:220] if detail else ""), flush=True)

st = api("/manga/fetch_status")
if st.get("etat") != "en cours":
    print("pas de capture en cours : banc sans objet"); sys.exit(2)
print("capture :", st.get("titre"), "ch.", st.get("chapitre"), "pages", st.get("pages"))
o = (api("/manga/pilote_onglets").get("onglets") or [None])[0]
if not o: print("fenetre de capture introuvable"); sys.exit(2)
pil = lambda action, **kw: api("/manga/pilote", dict({"id": o["id"], "action": action}, **kw))
sauve = open(CONF, "rb").read() if os.path.exists(CONF) else None
try:
    r = pil("fenetre_etat"); b0 = r.get("bounds")
    check("état de la fenêtre lisible pendant la capture", r.get("ok"), {k: r.get(k) for k in ("interieur", "assez_grande")})
    r = pil("fenetre_taille")
    check("« Taille sûre » ACCEPTÉE pendant la capture", r.get("ok") and r.get("assez_grande"), r.get("error") or r.get("interieur"))
    r = pil("fenetre_ranger")
    check("« Ranger » ACCEPTÉ (place retenue assez grande)", r.get("ok") and r.get("assez_grande"), r.get("error") or r.get("bounds"))
    b1 = pil("fenetre_etat").get("bounds")
    r = pil("fenetre_fermer")
    check("« Fermer la fenêtre » REFUSÉ pendant la capture", bool(r.get("error")) and not r.get("ok"), r.get("error"))
    r = pil("clic", x=0.5, y=0.5)
    check("clic dans la page REFUSÉ pendant la capture", "capture est en cours" in (r.get("error") or ""), r.get("error"))
    if sauve is not None:                                             # place retenue TROP PETITE, le temps d'un appel
        c = json.loads(sauve.decode("utf-8")); c["place"] = dict(c["place"], width=400, height=300)
        open(CONF, "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=1))
        r = pil("fenetre_ranger")
        b2 = pil("fenetre_etat").get("bounds")
        check("« Ranger » vers une place TROP PETITE : REFUSÉ, la fenêtre ne bouge pas",
              bool(r.get("error")) and "trop petite" in r["error"] and b2 == b1, (r.get("error"), b1, b2))
finally:
    if sauve is not None: open(CONF, "wb").write(sauve)
check("place retenue de Quang restaurée à l'octet", sauve is None or open(CONF, "rb").read() == sauve)
time.sleep(3); st2 = api("/manga/fetch_status")
check("la capture tourne toujours (ou s'est finie normalement)", st2.get("etat") in ("en cours", "fini"), {k: st2.get(k) for k in ("etat", "pages")})
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
