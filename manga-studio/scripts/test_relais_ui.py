# -*- coding: utf-8 -*-
"""Banc v2.43.0 : interrupteur « 🔁 Relais auto si moderation » (menu ⋯) sur l'APP REELLE, 1280 + 360 px. Bascule le
reglage cote serveur puis REMET l'etat d'origine. Usage : python test_relais_ui.py [port]"""
import os, json, urllib.request
import sys
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
from playwright.sync_api import sync_playwright
KEY=open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"),encoding="utf-8").read().strip()
def srv():
    r=urllib.request.Request("http://127.0.0.1:"+PORT+"/manga/reglages",headers={"Authorization":"Bearer "+KEY})
    return json.loads(urllib.request.urlopen(r,timeout=20).read())
avant=srv(); print("serveur avant :", avant.get("mode"), avant.get("relais_moderation"))
ok=[]
with sync_playwright() as p:
    b=p.chromium.launch(channel="msedge",headless=True)
    for w in (1280,360):
        pg=b.new_page(viewport={"width":w,"height":820},is_mobile=w<400,has_touch=w<400); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)))
        pg.goto("http://127.0.0.1:"+PORT+"/manga#k="+KEY); pg.wait_for_timeout(3500)
        pg.click("#hdrPlus"); pg.wait_for_timeout(200)
        vis=pg.evaluate("()=>$('hdrRelais').checkVisibility()"); etat=pg.evaluate("()=>$('hdrRelais').checked")
        ok.append(("%d visible"%w, vis)); ok.append(("%d = serveur"%w, etat==avant["relais_moderation"]))
        mp=pg.eval_on_selector(".hdr-plus .menu-pan","e=>{const r=e.getBoundingClientRect();return [r.left,r.right]}"); ok.append(("%d menu dans l'ecran"%w, mp[0]>=0 and mp[1]<=w+0.5))
        pg.click("label.menu-ligne:has(#hdrRelais)"); pg.wait_for_timeout(800)
        s1=srv(); ok.append(("%d clic -> serveur bascule"%w, s1["relais_moderation"]!=avant["relais_moderation"] and s1["mode"]==avant["mode"]))
        ok.append(("%d menu reste ouvert"%w, pg.evaluate("()=>!document.querySelector('.hdr-plus .menu-pan').hidden")))
        if w==1280: pg.screenshot(path=os.environ["TEMP"]+"/relais_menu.png")
        pg.click("label.menu-ligne:has(#hdrRelais)"); pg.wait_for_timeout(800)
        s2=srv(); ok.append(("%d reclic -> etat d'origine"%w, s2["relais_moderation"]==avant["relais_moderation"]))
        ok.append(("%d erreurs JS"%w, not errs))
        pg.close()
    b.close()
for n,v in ok: print(("[OK] " if v else "[KO] ")+n)
print("serveur apres :", srv().get("relais_moderation"))

# v2.44.0 : Pixtral hors des choix de moteur ; la TRACE d'une page s'affiche dans le lecteur
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True); pg = b.new_page()
    pg.goto("http://127.0.0.1:" + PORT + "/manga#k=" + KEY); pg.wait_for_timeout(3000)
    opts = pg.evaluate("() => [...$('narrEngine').options].map(o => o.value)")
    print(("[OK] " if "pixtral" not in opts else "[KO] ") + "Pixtral retiré des choix de moteur " + str(opts))
    t1 = pg.evaluate("() => traceTxt({ trace: { lu_par: 'kimi', refuse_par: [{ moteur: 'gemini' }], comment: 'relais automatique' } })")
    t2 = pg.evaluate("() => traceTxt({ trace: { lu_par: null, refuse_par: [{ moteur: 'gemini' }, { moteur: 'kimi' }, { moteur: 'pixtral' }], comment: 'mise de côté (alerte)' } })")
    t3 = pg.evaluate("() => traceTxt({})")
    print(("[OK] " if "lue par Kimi" in t1 and "Gemini" in t1 else "[KO] ") + "trace relais : " + t1)
    print(("[OK] " if "non lue" in t2 and "Pixtral" in t2 and "alerte" in t2 else "[KO] ") + "trace mise de côté : " + t2)
    print(("[OK] " if t3 == "" else "[KO] ") + "page sans trace : rien d'affiché")
    b.close()
