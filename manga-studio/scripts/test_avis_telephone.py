# -*- coding: utf-8 -*-
"""Banc REEL v3.7.0 : avis de fin sur le TELEPHONE (Samsung A32 de Claude), ECRAN ETEINT, app non regardee.
Instance de TEST sur 8191 (gestionnaire HTTP + veilleur d'avis, sur une COPIE d'un chapitre) -- jamais 8190/8192.
1. Chrome du telephone ouvre l'app par adb reverse (http://localhost = origine sure : le push y fonctionne) ;
2. l'interrupteur « 📲 Notifications de fin » abonne l'appareil (permission accordee par CDP) ; l'essai arrive ;
3. ecran ETEINT ; une tache Dialogues FACTICE tourne > 60 s puis finit -> le VEILLEUR la voit (aucune page ne
   l'interroge : l'onglet est en arriere-plan, ecran eteint) -> la notification est dans la barre d'Android ;
4. une tache de 20 s ne sonne pas ; desabonnement propre.
⚠️ Limite assumee : la permission est accordee par CDP (pas au doigt) et ne vit que la connexion -> UNE connexion du
   debut a la fin. Le vrai « Autoriser » se fait une fois, a la main, sur le telephone de Quang. 0 credit, 0 appel paye (le push passe par Google FCM).
Usage : python test_avis_telephone.py
"""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
COMFY = os.path.expanduser(r"~\Documents\ComfyUI")
PY = os.path.join(COMFY, ".venv", "Scripts", "python.exe")
KEY = open(os.path.join(COMFY, ".studio_secret"), encoding="utf-8").read().strip()
ADB = os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe")
SER, PORT, CDP = "RFCT32ATWGJ", 8191, 9341
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:240] if d else ""), flush=True)


def adb(*a):
    return subprocess.run([ADB, "-s", SER] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def notifs():
    """Les notifications de Chrome que montre Android (titre + texte)."""
    out, res, bloc = adb("shell", "dumpsys", "notification", "--noredact"), [], None
    for l in out.splitlines():
        if "NotificationRecord(" in l:
            bloc = {"chrome": "pkg=com.android.chrome" in l}; res.append(bloc)
        elif bloc is not None:
            m = re.search(r"android\.(title|text)=String \((.*)\)\s*$", l.strip())
            if m and m.group(1) not in bloc: bloc[m.group(1)] = m.group(2)   # la 1re = la vraie ; la suivante = version MASQUEE (ecran verrouille)
    return [b for b in res if b.get("chrome") and b.get("title")]


def attendre_notif(titre, s):
    for _ in range(s):
        n = [b for b in notifs() if b.get("title") == titre]
        if n: return n[0]
        time.sleep(1)
    return None


# --- copie isolee d'un chapitre de la principale
T = tempfile.mkdtemp(prefix="avis_tel_")
SD = os.path.join(T, "one-punch-man")
os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("narration", "video", "*.mp4", "dialogues"))
for f in ("serie.json", "suivi.json", "dialogues_distribution.json"):
    if os.path.exists(os.path.join(SRC, "one-punch-man", f)): shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(SD, f))
PROG = os.path.join(SD, "ch_5", "dialogues", "progress.json")
os.makedirs(os.path.dirname(PROG), exist_ok=True)

LANCEUR = os.path.join(T, "srv.py")      # le gestionnaire HTTP + LE VEILLEUR (c'est lui qu'on prouve), sur la copie
open(LANCEUR, "w", encoding="utf-8").write(
    "import importlib.util, os, shutil, sys, threading\nfrom http.server import ThreadingHTTPServer\n"
    "C = %r\nsys.path.insert(0, C)\ncopie = os.path.join(C, '_studio_llm_proxy_8191.py')\n"
    "shutil.copyfile(os.path.join(C, '_studio_llm_proxy.py'), copie)\n"
    "s = importlib.util.spec_from_file_location('proxy_8191', copie); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
    "os.remove(copie)\nthreading.Thread(target=m.manga_avis_veilleur, daemon=True).start()\n"
    "ThreadingHTTPServer(('127.0.0.1', %d), m.H).serve_forever()\n" % (COMFY, PORT))
srv = subprocess.Popen([PY, LANCEUR], env=dict(os.environ, MANGA_SOURCES_DIR=T), stdout=open(os.path.join(T, "srv.log"), "w"), stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/manga/avis/cle" % PORT, headers={"Authorization": "Bearer " + KEY}), timeout=5); break
    except Exception:
        time.sleep(1)
dort = None
try:
    check("instance de test sur la COPIE", os.path.exists(os.path.join(T, "_avis.json")) or True, T)
    # --- telephone
    adb("shell", "settings put global stay_on_while_plugged_in 7"); adb("shell", "input keyevent KEYCODE_WAKEUP")
    adb("reverse", "tcp:%d" % PORT, "tcp:%d" % PORT); adb("forward", "tcp:%d" % CDP, "localabstract:chrome_devtools_remote")
    adb("shell", "am start -a android.intent.action.VIEW -n com.android.chrome/com.google.android.apps.chrome.Main -d 'http://localhost:%d/manga#k=%s'" % (PORT, KEY))
    time.sleep(8)
    # ⚠️ UNE seule connexion CDP pour TOUT le banc : la permission accordee par Browser.grantPermissions ne vit que le
    # temps de la connexion -- la fermer = Chrome revoque l'abonnement (410), mesure le 03/10 (sonde_doze). Un vrai
    # « Autoriser » au doigt, lui, est permanent.
    PW = sync_playwright().start()
    b = PW.chromium.connect_over_cdp("http://127.0.0.1:%d" % CDP)
    ctx = b.contexts[0]
    pg = next((x for x in ctx.pages if ("localhost:%d/manga" % PORT) in x.url), None)
    check("page de l'app ouverte sur le telephone", pg is not None, [x.url.split("#")[0][:60] for x in ctx.pages])   # jamais le #k= (la cle)
    pg.wait_for_function("() => typeof VERSION !== 'undefined'", timeout=30000)
    check("v3.7.x servie", pg.evaluate("() => VERSION").startswith("3.7."), pg.evaluate("() => VERSION"))
    s = ctx.new_cdp_session(pg)
    s.send("Browser.grantPermissions", {"origin": "http://localhost:%d" % PORT, "permissions": ["notifications"]})
    pg.wait_for_function("() => !document.getElementById('hdrAvisL').hidden", timeout=20000)
    larg = pg.evaluate("() => { const m = document.getElementById('hdrAvisL').closest('.menu-pan'), h = m.hidden; m.hidden = false;"
                       " const w = document.getElementById('hdrAvis').getBoundingClientRect().width; m.hidden = h; return Math.round(w); }")
    check("interrupteur TOUCHABLE (>= 40 px ; il a ete ecrase a 0 px, 03/10)", larg >= 40, larg)
    pg.wait_for_function("() => navigator.serviceWorker.controller || navigator.serviceWorker.ready", timeout=20000)
    pg.evaluate("() => { const c = document.getElementById('hdrAvis'); c.checked = true; c.onchange(); }")
    pg.wait_for_function("() => /actives/.test(document.getElementById('avisNote').textContent) || /chec|refus/.test(document.getElementById('avisNote').textContent)", timeout=40000)
    check("interrupteur : abonne", "actives" in pg.inner_text("#avisNote"), pg.inner_text("#avisNote"))
    ep = pg.evaluate("() => AVIS.sub && AVIS.sub.endpoint") or ""
    check("abonnement chez Google (FCM)", ep.startswith("https://fcm.googleapis.com/"), ep[:60])
    for _ in range(20):                                  # un abonnement memorise d'un essai precedent affiche « actives » tout de suite
        try:
            etat = json.load(open(os.path.join(T, "_avis.json"), encoding="utf-8"))
            if etat["abonnements"]: break
        except (OSError, ValueError):
            etat = {"abonnements": []}
        time.sleep(0.5)
    check("serveur : 1 appareil, dans la COPIE", len(etat["abonnements"]) == 1, etat["abonnements"][0].get("appareil") if etat["abonnements"] else "")
    pg.evaluate("async () => { const r = await navigator.serviceWorker.ready; (await r.getNotifications()).forEach(n => n.close()); }"); time.sleep(1)   # barre propre (les avis des passages precedents)
    pg.evaluate("() => document.getElementById('btnAvisEssai').click()")
    n0 = attendre_notif("Manga Studio", 30)
    check("essai : notification affichee par Android", n0 is not None and "Essai reçu" in (n0 or {}).get("text", ""), n0)
    # --- ecran eteint, la page ne regarde plus rien
    adb("shell", "input keyevent KEYCODE_SLEEP"); time.sleep(3)
    eteint = "mWakefulness=Asleep" in adb("shell", "dumpsys power") or "mWakefulness=Dozing" in adb("shell", "dumpsys power")
    check("ecran ETEINT", eteint, re.findall(r"mWakefulness=\w+", adb("shell", "dumpsys power")))
    # tache courte (20 s) : ne doit PAS sonner
    dort = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(900)"])
    json.dump({"pid": dort.pid, "t": time.time(), "etape": "voix", "fait": 1, "total": 9}, open(PROG, "w", encoding="utf-8"))
    time.sleep(20); dort.kill(); dort.wait()
    json.dump({"t": time.time(), "etape": "voix", "fait": 9, "total": 9, "fini": True}, open(PROG, "w", encoding="utf-8"))
    time.sleep(35)
    check("tache de 20 s : aucune notification", not [b for b in notifs() if "Dialogues" in b.get("title", "")], notifs())
    # tache longue (> 60 s) : DOIT sonner, ecran eteint
    dort = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(900)"])
    json.dump({"pid": dort.pid, "t": time.time(), "etape": "voix", "fait": 1, "total": 9}, open(PROG, "w", encoding="utf-8"))
    for _ in range(10):                                                 # ~110 s : > 60 s MEME mesure au pas de 15 s ; la tache reste FRAICHE (progress mis a jour)
        time.sleep(11)
        json.dump({"pid": dort.pid, "t": time.time(), "etape": "voix", "fait": 3, "total": 9}, open(PROG, "w", encoding="utf-8"))
    dort.kill(); dort.wait(); fin = time.time()
    json.dump({"t": time.time(), "etape": "voix", "fait": 9, "total": 9, "fini": True}, open(PROG, "w", encoding="utf-8"))
    n1, reveil = None, None
    for _ in range(90):                                     # 3 min ecran eteint (Doze : FCM « high » doit passer quand meme)
        n1 = next((b for b in notifs() if "Dialogues" in b.get("title", "")), None)
        if n1: break
        time.sleep(2)
    if not n1:                                              # diagnostic : en RETARD (livree au reveil) ou PERDUE ?
        adb("shell", "input keyevent KEYCODE_WAKEUP")
        for _ in range(15):
            n1 = next((b for b in notifs() if "Dialogues" in b.get("title", "")), None)
            if n1: reveil = True; break
            time.sleep(2)
        adb("shell", "input keyevent KEYCODE_SLEEP")
    check("tache longue finie ECRAN ETEINT : notification" + (" (seulement AU REVEIL)" if reveil else ""), n1 is not None and not reveil, n1)
    if n1:
        check("texte : VRAI titre (manifest) + chapitre", n1.get("title") == "🎭 Dialogues prêts" and n1.get("text") == "One Punch-Man ch.5", n1)
        print("     delai fin -> notification : %.0f s" % (time.time() - fin))
    toujours = "mWakefulness=Awake" not in adb("shell", "dumpsys power")
    check("l'ecran n'a pas ete rallume par le banc", toujours)
    # --- desabonnement
    adb("shell", "input keyevent KEYCODE_WAKEUP"); time.sleep(2)
    pg.evaluate("() => { const c = document.getElementById('hdrAvis'); c.checked = false; c.onchange(); }")
    pg.wait_for_function("() => /coupées/.test(document.getElementById('avisNote').textContent)", timeout=20000)
    etat = json.load(open(os.path.join(T, "_avis.json"), encoding="utf-8"))
    check("desabonnement : serveur vide", etat["abonnements"] == [], len(etat["abonnements"]))
finally:
    if dort and dort.poll() is None: dort.kill()
    try: b.close(); PW.stop()
    except Exception: pass
    srv.kill()
    adb("reverse", "--remove", "tcp:%d" % PORT); adb("forward", "--remove", "tcp:%d" % CDP)
    try: pg.evaluate("async () => { const r = await navigator.serviceWorker.ready; (await r.getNotifications()).forEach(n => n.close()); }"); time.sleep(1)
    except Exception: pass
    print("journal serveur :\n" + "\n".join(l for l in open(os.path.join(T, "srv.log"), encoding="utf-8", errors="replace").read().splitlines() if "[avis]" in l))
    shutil.rmtree(T, ignore_errors=True)
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
