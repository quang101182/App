# -*- coding: utf-8 -*-
"""MESURE (lecture seule) : combien de temps une page en BANDE DEFILANTE met-elle vraiment a charger ses images apres chaque
pas de defilement ? Avant toute optimisation de manga-fetch (attente FIXE de 1,2 s par pas aujourd'hui) -- 25/09/2026.

Ouvre l'adresse dans un NOUVEL onglet de la fenetre de capture (port CDP), rejoue le defilement de manga-fetch (70 % d'ecran),
et chronometre, a chaque pas, le temps jusqu'a ce que toutes les images de page VISIBLES soient chargees (plafond 5 s).
Ne capture rien, n'ecrit rien dans l'app ; referme son onglet a la fin. Aucune donnee de la page n'est affichee (sauf l'hote).
Usage : python mesure_chargement_bande.py <port CDP> <adresse> [<adresse>…]
"""
import json, sys, time, urllib.request
from urllib.parse import urlparse, quote
sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
import cdp_mini

PORT = sys.argv[1]
ETAT = r"""(() => {
  const bloc = document.querySelector('[data-mesure-defile]');
  const imgs = [...document.images].filter(i => i.getBoundingClientRect().width >= 180
      && !i.closest('#comments, .comments, .comment, [id^="comment"], .disqus, #disqus_thread'));
  const ok = i => i.complete && i.naturalWidth > 0 && !(i.currentSrc || i.src || '').startsWith('data:');
  // v2 : TOUTES les images placees a l'ecran, meme de taille nulle (une image pas encore chargee n'a souvent pas de taille)
  const toutes = [...document.images].filter(i => !i.closest('#comments, .comments, .comment, [id^="comment"], .disqus, #disqus_thread'));
  const vis = toutes.filter(i => { const r = i.getBoundingClientRect(); return r.bottom >= 0 && r.top <= innerHeight && r.width >= (r.height ? 180 : 0); });
  const pos = bloc ? [bloc.scrollTop, bloc.scrollHeight, bloc.clientHeight] : [scrollY, document.documentElement.scrollHeight, innerHeight];
  return JSON.stringify({ n: imgs.length, charges: imgs.filter(ok).length, vis: vis.length, visOk: vis.filter(ok).length, pos });
})()"""
BLOC = r"""(() => { let best = null, bh = 0;
  for (const el of document.querySelectorAll('*')) { const oy = getComputedStyle(el).overflowY;
    if ((oy !== 'auto' && oy !== 'scroll') || el === document.body || el === document.documentElement || el.clientHeight < innerHeight * 0.5) continue;
    if (el.scrollHeight > bh && el.scrollHeight > el.clientHeight * 2.5) { bh = el.scrollHeight; best = el; } }
  if (best && best.scrollHeight >= document.documentElement.scrollHeight) { best.setAttribute('data-mesure-defile', '1'); return true; } return false; })()"""
PAS = r"""(() => { const e = document.querySelector('[data-mesure-defile]'); if (e) e.scrollBy(0, e.clientHeight * 0.7); else window.scrollBy(0, innerHeight * 0.7); })()"""


def mesurer(url):
    t = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%s/json/new?%s" % (PORT, quote(url, safe=":/?=&%#")), method="PUT")))
    try:
        with cdp_mini.Onglet(t["webSocketDebuggerUrl"], timeout=30) as o:
            ev = lambda js: o.cmd("Runtime.evaluate", expression=js, returnByValue=True)["result"].get("value")
            o.cmd("Network.enable"); o.cmd("Network.setCacheDisabled", cacheDisabled=True)   # v2 : AUCUN cache (chapitres deja captures)
            o.cmd("Page.reload", ignoreCache=True)
            time.sleep(8)                                              # chargement initial (comme un onglet ouvert a la main)
            clic = ev(r"""(() => { const b = [...document.querySelectorAll('button, a, [role=button]')].find(x =>
                /^(lire|read|commencer la lecture|start reading)/i.test((x.innerText || '').trim()) && x.getBoundingClientRect().width > 0);
                if (!b || [...document.images].some(i => i.naturalHeight >= 800)) return ''; b.click(); return (b.innerText || '').trim().slice(0, 30); })()""")
            if clic: print("   (accueil : clic sur « %s »)" % clic); time.sleep(4)
            h, stable = -1, 0
            while stable < 3:
                time.sleep(0.5); hh = json.loads(ev(ETAT))["pos"][1]; stable = stable + 1 if hh == h else 0; h = hh
            bloc = ev(BLOC); e0 = json.loads(ev(ETAT))
            attentes, plafonds, pas, prec, immobile = [], 0, 0, None, 0
            while pas < 3000:
                ev(PAS); pas += 1; t0 = time.time(); e = json.loads(ev(ETAT))
                calme, dernier = 0, (e["visOk"], e["pos"][1])
                while time.time() - t0 < 5:                            # tout ce qui est a l'ecran charge ET plus rien ne bouge 0,3 s
                    time.sleep(0.05); e = json.loads(ev(ETAT))
                    cle = (e["visOk"], e["pos"][1]); calme = calme + 1 if cle == dernier else 0; dernier = cle
                    if e["visOk"] >= e["vis"] and calme >= 6: break
                dt = time.time() - t0; attentes.append(dt); plafonds += dt >= 5
                if prec and e["pos"][:2] == prec: immobile += 1
                else: immobile = 0
                if immobile >= 2: break
                prec = e["pos"][:2]
            ef = json.loads(ev(ETAT))
    finally:
        try: urllib.request.urlopen("http://127.0.0.1:%s/json/close/%s" % (PORT, t["id"]))
        except Exception: pass
    a = sorted(attentes); med = a[len(a) // 2]; p95 = a[int(len(a) * 0.95)]
    print("%s : %d px, %d pas, bloc=%s | images a l'ouverture %d/%d chargees, a la fin %d/%d | attente par pas : mediane %.2f s, "
          "p95 %.2f s, max %.2f s, plafond 5 s atteint %d fois | aujourd'hui (1,2 s fixe) ~%.0f s -> adaptatif ~%.0f s"
          % (urlparse(url).hostname, ef["pos"][1], pas, bloc, e0["charges"], e0["n"], ef["charges"], ef["n"], med, p95, a[-1], plafonds,
             pas * 1.2, sum(max(x, 0.4) for x in a)))


for u in sys.argv[2:]:
    try: mesurer(u)
    except Exception as ex: print(urlparse(u).hostname, ": ERREUR", type(ex).__name__, str(ex)[:150])
