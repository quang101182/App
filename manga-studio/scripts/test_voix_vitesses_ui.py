# -*- coding: utf-8 -*-
"""Banc v2.21.0 (S7 + demandes Quang 24/09 20h08) : voix de l'application secondaire et vitesses separees.

App reelle (Edge sans fenetre), n'ecrit rien cote serveur (la narration est refusee avant de partir) :
1. principale : la liste des voix est INCHANGEE (les 8 d'avant), en ligne comme sur le PC ;
2. secondaire : en ligne = Aoede, Despina, Leda, Sulafat ; sur le PC = Aoede@1.0, Leda@1.0, Kore@0.5, Leda@0.5 ;
   l'apercu d'une voix « avec ton » vise le bon fichier et il existe ;
3. serveur : « Voix@ton » accepte, un ton hors bornes refuse ;
4. vitesses : une memoire EN LIGNE et une SUR LE PC, separees, reprises selon la narration ouverte (dans les deux
   applications, chacune la sienne). La memoire de vitesse de Quang est restauree a la fin.
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []
AVANT = ["Charon", "Fenrir", "Orus", "Puck", "Algenib", "Kore", "Aoede", "Leda"]


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""), flush=True)


def post(port, chemin, corps):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, chemin), data=json.dumps(corps).encode(),
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=30))


print("3. serveur")
for port in (8190, 8192):
    r = post(port, "/manga/narrate", {"d": "zz-inexistant/ch_1", "engine": "gemini", "voice": "Leda@1.0", "tts": "local"})
    check("%d : « Leda@1.0 » accepte (refus pour le chapitre, pas pour la voix)" % port, "voix" not in (r.get("error") or ""), r)
    r = post(port, "/manga/narrate", {"d": "zz-inexistant/ch_1", "engine": "gemini", "voice": "Leda@9", "tts": "local"})
    check("%d : ton hors bornes refuse" % port, r.get("error") == "voix invalide", r)

opts = "() => [...document.getElementById('narrVoice').options].map(o => o.value)"
with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="msedge", headless=True)
    for port, nom in ((8190, "principale"), (8192, "secondaire")):
        print("%s (%d)" % (nom, port))
        pg = nav.new_page(viewport={"width": 360, "height": 800}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=%s" % (port, KEY)); pg.wait_for_timeout(3000)
        memo = pg.evaluate("() => [localStorage.getItem('manga_vit_cloud'), localStorage.getItem('manga_vit_local')]")
        mode0 = pg.evaluate("MODE")
        listes = {}
        for m in ("cloud", "pc"):
            pg.evaluate("m => { MODE = m; modeMaj(); }", m); pg.wait_for_timeout(200)
            listes[m] = pg.evaluate(opts)
        pg.evaluate("m => { MODE = m; modeMaj(); }", mode0)
        if nom == "principale":
            check("voix inchangees en ligne", listes["cloud"] == AVANT, listes["cloud"])
            check("voix inchangees sur le PC", listes["pc"] == AVANT, listes["pc"])
        else:
            check("en ligne : Aoede, Despina, Leda, Sulafat", listes["cloud"] == ["Aoede", "Despina", "Leda", "Sulafat"], listes["cloud"])
            check("sur le PC : Aoede@1.0, Leda@1.0, Kore@0.5, Leda@0.5", listes["pc"] == ["Aoede@1.0", "Leda@1.0", "Kore@0.5", "Leda@0.5"], listes["pc"])
            pg.evaluate("() => { MODE = 'pc'; modeMaj(); $('narrVoice').value = 'Aoede@1.0'; jouerApercu(); }"); pg.wait_for_timeout(800)
            src = pg.evaluate("() => APERCU.src")
            code = urllib.request.urlopen(urllib.request.Request(src if "_k=" in src else src, headers={"Authorization": "Bearer " + KEY})).status
            from urllib.parse import urlparse, parse_qs
            cible = (parse_qs(urlparse(src).query).get("p") or [urlparse(src).path])[0]
            check("apercu d'une voix avec ton : _apercus/Aoede.mp3, present", cible.endswith("_apercus/Aoede.mp3") and code == 200,
                  (cible, code))                                  # jamais l'adresse entiere : elle porte la cle (_k=)
            pg.evaluate("m => { MODE = m; modeMaj(); }", mode0)
        # vitesses separees
        v = pg.evaluate("""() => { const r = [];
          LEC.n = {tts: 'local'}; localStorage.removeItem('manga_vit_local'); localStorage.removeItem('manga_vit_cloud');
          vitAppliquer(); r.push($('lecVit').value);                                         // defaut local = 1
          $('lecVit').value = '1.3'; $('lecVit').onchange();                                  // Quang regle 1,3 en local
          LEC.n = {tts: 'cloud'}; vitAppliquer(); r.push($('lecVit').value);                   // defaut en ligne = 1,15
          $('lecVit').value = '1.1'; $('lecVit').onchange();                                  // 1,1 en ligne
          LEC.n = {tts: 'local'}; vitAppliquer(); r.push($('lecVit').value);                   // le local a garde 1,3
          LEC.n = {tts: 'cloud'}; vitAppliquer(); r.push($('lecVit').value, $('lecAudio').playbackRate);
          LEC.n = null; return r; }""")
        check("vitesses : defauts 1 (PC) / 1,15 (en ligne), puis chacune garde la sienne", v == ["1", "1.15", "1.3", "1.1", 1.1], v)
        pg.evaluate("m => { m[0] === null ? localStorage.removeItem('manga_vit_cloud') : localStorage.setItem('manga_vit_cloud', m[0]);"
                    " m[1] === null ? localStorage.removeItem('manga_vit_local') : localStorage.setItem('manga_vit_local', m[1]); }", memo)
        check("aucune erreur JavaScript", not errs, errs[:2])
        pg.close()
    nav.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
