# -*- coding: utf-8 -*-
"""Banc S6 (compartiment, 24/09/2026) : discretion de l'application secondaire, app reelle (Edge sans fenetre).

Principale (8190) : RIEN ne change (jamais floutee ; Echap x2 sans effet).
Secondaire (8192) : floutee quand elle perd le focus, nette quand elle le reprend ; Echap x1 = rien ; Echap x2 (< 0,6 s)
= retour a la principale (sur le PC : la fenetre dediee se FERME ; sans fenetre dediee : l'adresse principale) ;
retour automatique apres l'inactivite (reglee a 3 s pour le banc), SAUF si un son joue.
Fin : la fenetre dediee de Quang est rouverte a sa place.
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
N, P = "http://127.0.0.1:8190/manga/", "http://127.0.0.1:8192/manga/"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""), flush=True)


def fen(action):
    r = urllib.request.Request(N.replace("/manga/", "/manga/espace_fenetre"), data=json.dumps({"action": action}).encode(),
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=40))


flou = lambda pg: pg.evaluate("() => document.body.classList.contains('esp-flou')")
SON = """() => { const n = 8000 * 10, b = new ArrayBuffer(44 + n), v = new DataView(b);   // 10 s de silence, WAV 8 bits
  const ecr = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  ecr(0, 'RIFF'); v.setUint32(4, 36 + n, true); ecr(8, 'WAVEfmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
  v.setUint16(22, 1, true); v.setUint32(24, 8000, true); v.setUint32(28, 8000, true); v.setUint16(32, 1, true);
  v.setUint16(34, 8, true); ecr(36, 'data'); v.setUint32(40, n, true); for (let i = 0; i < n; i++) v.setUint8(44 + i, 128);
  const a = document.createElement('audio'); a.id = 'bancSon'; a.loop = true; a.muted = true;
  a.src = URL.createObjectURL(new Blob([b], {type: 'audio/wav'})); document.body.appendChild(a);
  return a.play().then(() => !a.paused).catch(e => 'refus ' + e.message); }"""
try:
    with sync_playwright() as pw:
        nav = pw.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = nav.new_context(viewport={"width": 360, "height": 800})
        print("principale")
        pg = ctx.new_page(); pg.goto(N + "#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => window.dispatchEvent(new Event('blur'))"); pg.wait_for_timeout(200)
        check("principale : jamais floutee", not flou(pg))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150); pg.keyboard.press("Escape"); pg.wait_for_timeout(2000)
        check("principale : Echap x2 sans effet", pg.url.startswith(N) and "ESP_DISCRETION" and not pg.evaluate("ESP_DISCRETION"))
        print("secondaire")
        fen("ouvrir")
        ps = ctx.new_page(); ps.goto(P + "#k=" + KEY); ps.wait_for_timeout(3000)
        ps.evaluate("() => window.dispatchEvent(new Event('focus'))"); ps.wait_for_timeout(200)
        check("secondaire : nette avec le focus", not flou(ps))
        ps.evaluate("() => window.dispatchEvent(new Event('blur'))"); ps.wait_for_timeout(200)
        check("secondaire : FLOUTEE quand elle perd le focus", flou(ps))
        check("... le flou vise bien le contenu", ps.evaluate("() => getComputedStyle(document.querySelector('main')).filter").startswith("blur"))
        ps.evaluate("() => window.dispatchEvent(new Event('focus'))"); ps.wait_for_timeout(200)
        check("secondaire : nette a nouveau", not flou(ps))
        ps.keyboard.press("Escape"); ps.wait_for_timeout(1500)
        check("Echap x1 : rien", fen("etat").get("ouverte") and ps.url.startswith(P))
        ps.keyboard.press("Escape"); ps.wait_for_timeout(900); ps.keyboard.press("Escape"); ps.wait_for_timeout(1500)
        check("Echap x2 trop lents (> 0,6 s) : rien", fen("etat").get("ouverte"))
        ps.keyboard.press("Escape"); ps.wait_for_timeout(150); ps.keyboard.press("Escape"); ps.wait_for_timeout(4000)
        check("PANIQUE Echap x2 : la fenetre dediee se ferme", not fen("etat").get("ouverte"))
        ps.keyboard.press("Escape"); ps.wait_for_timeout(150); ps.keyboard.press("Escape"); ps.wait_for_timeout(4000)
        check("PANIQUE sans fenetre dediee : retour a l'adresse principale", ps.url.startswith(N), ps.url)
        print("retour automatique (inactivite reglee a 3 s)")
        pa = ctx.new_page(); pa.goto(P + "#k=" + KEY); pa.wait_for_timeout(1500)
        pa.evaluate("() => localStorage.setItem('esp_inactif_min', '0.05')"); pa.reload(); pa.wait_for_timeout(1500)
        r = pa.evaluate(SON)
        pa.wait_for_timeout(6000)
        check("un son joue : PAS de retour automatique", pa.url.startswith(P) and r is True, (r, pa.url))
        pa.evaluate("() => document.getElementById('bancSon').pause()"); pa.wait_for_timeout(5000)
        check("plus de son : retour automatique a la principale", pa.url.startswith(N), pa.url)
        pa.goto(P); pa.wait_for_timeout(800); pa.evaluate("() => localStorage.removeItem('esp_inactif_min')")
        nav.close()
finally:
    fen("ouvrir")                                          # la fenetre dediee de Quang, a sa place
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
