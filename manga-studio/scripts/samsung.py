"""Harness Samsung réel — CDP pour MESURER, adb pour TOUCHER.

La règle du projet : le SM-A326B est le device de test dédié. Un Edge émulé mesure
un DOM, il ne mesure pas un doigt. Ici on lit l'écran par CDP (positions réelles,
en pixels CSS) et on tape par `adb input tap` (vrai tactile, vrai clavier virtuel).

Usage comme bibliothèque :
    from samsung import Phone
    p = Phone()
    p.tap_text("Démarrer une planche")
    p.type_text("le maître entre dans la salle")
    print(p.js("document.title"))
"""
import json
import subprocess
import time
import os

ADB = r"C:/Users/quang/AppData/Local/Android/Sdk/platform-tools/adb.exe"
CDP_PORT = 9333  # jamais 9222 (règle projet)
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
APP_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "manga_studio.html")


def version_source():
    """La version écrite dans le fichier servi. Sert de juge : un onglet ouvert
    depuis longtemps peut afficher une version PÉRIMÉE sans que rien ne le dise
    (payé le 27/07 : un vieil onglet en v1.2.0 a répondu à la place de la v1.22.0)."""
    import re
    with open(APP_HTML, encoding="utf-8") as f:
        head = f.read(4000)
    m = re.search(r"<title>[^<]*?v(\d+\.\d+\.\d+)", head)
    return m.group(1) if m else None


def secret():
    with open(SECRET_FILE) as f:
        return f.read().strip()


def adb(*args, timeout=30):
    return subprocess.run([ADB, *args], capture_output=True, text=True,
                          timeout=timeout, encoding="utf-8", errors="replace")


class Phone:
    def __init__(self, url_contains="/manga", title_contains="Manga Studio", open_if_missing=True):
        import websocket
        self._ws_mod = websocket
        adb("reverse", "tcp:8190", "tcp:8190")
        adb("forward", f"tcp:{CDP_PORT}", "localabstract:chrome_devtools_remote")
        self.wake()
        target = self._find_target(url_contains, title_contains)
        if target is None and open_if_missing:
            self.open_app()
            time.sleep(6)
            target = self._find_target(url_contains, title_contains)
        if target is None:
            raise RuntimeError("aucun onglet Manga Studio trouvé sur le téléphone")
        # suppress_origin : Chrome 111+ refuse (403) un handshake portant un Origin
        # qu'il n'a pas autorisé par --remote-allow-origins. Pas d'Origin = accepté.
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=60,
                                              suppress_origin=True)
        self._id = 0
        # taille écran physique (pour convertir CSS -> pixels device)
        out = adb("shell", "wm", "size").stdout
        self.dev_w, self.dev_h = (int(x) for x in out.split(":")[-1].strip().split("x"))
        self.css_w = self.js("window.innerWidth")
        self.dpr = self.dev_w / self.css_w
        self.errors = []
        self._check_version()
        self._arm_error_capture()
        self._arm_touch_capture()
        # Décalage vertical entre le haut de l'écran physique et le haut de la page :
        # la barre d'URL de Chrome. Il VARIE (elle se rétracte au scroll) → mesuré, jamais deviné.
        self.y_off = self.dev_h - self.js("innerHeight") * self.dpr - 26
        self.focus_app()   # calibrer une page qui n'est pas au premier plan ne veut rien dire
        self.calibrate()

    # --- socle ---------------------------------------------------------
    def _find_target(self, url_contains, title_contains):
        import urllib.request
        raw = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=10).read()
        pages = [p for p in json.loads(raw) if p.get("type") == "page"]
        cand = [p for p in pages
                if url_contains in p.get("url", "") and title_contains in p.get("title", "")]
        if not cand:
            return None
        # le plus récent en tête de liste chez Chrome ; on préfère la version la plus haute
        def ver(p):
            import re
            m = re.search(r"v(\d+)\.(\d+)\.(\d+)", p.get("title", ""))
            return tuple(int(g) for g in m.groups()) if m else (0, 0, 0)
        cand.sort(key=ver, reverse=True)
        return cand[0]

    def send(self, method, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise, userGesture=True)
        res = r.get("result", {})
        if r.get("exceptionDetails"):
            raise RuntimeError(f"JS: {r['exceptionDetails'].get('text')} / {res.get('description')}")
        return res.get("value")

    def _check_version(self, retried=False):
        want = version_source()
        seen = self.js("document.title")
        if want and want in str(seen):
            self.version = want
            return want
        if retried:
            raise RuntimeError(f"le téléphone affiche {seen!r}, la source dit v{want} — "
                               "onglet périmé, rechargement sans effet")
        # onglet périmé (veille, cache, onglet fermé par mégarde) : on en ouvre un neuf
        self.focus_app()
        self.open_app()
        time.sleep(7)
        self.ws.close()
        target = self._find_target("/manga", "Manga Studio")
        self.ws = self._ws_mod.create_connection(target["webSocketDebuggerUrl"],
                                                 timeout=60, suppress_origin=True)
        self._id = 0
        return self._check_version(retried=True)

    def _arm_error_capture(self):
        """Un piège à erreurs JS posé dans la page, relu par `js_errors()`."""
        self.js("""
        (() => {
          if (window.__msErr) return 'deja';
          window.__msErr = [];
          window.addEventListener('error', e =>
            window.__msErr.push({t: Date.now(), m: String(e.message), s: String(e.filename||'')+':'+e.lineno}));
          window.addEventListener('unhandledrejection', e =>
            window.__msErr.push({t: Date.now(), m: 'promise: ' + String(e.reason)}));
          const ce = console.error;
          console.error = function(...a){ window.__msErr.push({t: Date.now(), m: a.map(String).join(' ')}); return ce.apply(this, a); };
          return 'arme';
        })()""")

    def js_errors(self):
        return self.js("window.__msErr || []")

    def _arm_touch_capture(self):
        """Enregistre le DERNIER point réellement touché dans la page.

        C'est le seul moyen de savoir où le doigt a atterri : un tap qui tombe sur la
        barre d'URL de Chrome n'atteint jamais la page et passerait inaperçu.
        """
        self.js("""
        (() => {
          if (window.__msTapArmed) return 'deja';
          window.__msTapArmed = true;
          window.__msTap = null;
          document.addEventListener('pointerdown', e => {
            const el = e.target;
            window.__msTap = {x: e.clientX, y: e.clientY, tag: el.tagName,
                              id: el.id || '', cls: el.className ? String(el.className).slice(0,60) : '',
                              txt: (el.textContent||'').trim().slice(0,40), t: Date.now()};
          }, true);
          return 'arme';
        })()""")

    def calibrate(self, tries=5):
        """Trouve `y_off` en tapant un point connu et en lisant où la page l'a reçu.

        Le tap se fait sur un voile posé par-dessus l'app : on mesure sans rien déclencher.
        """
        self.js("""
        (() => { let v = document.getElementById('__msVeil');
          if (!v) { v = document.createElement('div'); v.id = '__msVeil';
            v.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:transparent';
            document.body.appendChild(v); }
          v.style.display = 'block'; return 1; })()""")
        try:
            ih = self.js("innerHeight")
            x_dev = int(self.css_w / 2 * self.dpr)
            # on vise haut d'abord : le bas de la page peut être masqué par le clavier virtuel
            for frac in (0.20, 0.35, 0.55):
                target_css_y = ih * frac
                for _ in range(tries):
                    self.js("window.__msTap = null")
                    y_dev = int(self.y_off + target_css_y * self.dpr)
                    adb("shell", "input", "tap", str(x_dev), str(y_dev))
                    time.sleep(0.4)
                    tap = self.js("window.__msTap")
                    if tap is None:
                        self.y_off += 40   # le doigt n'a pas touché la page : on descend
                        continue
                    err = tap["y"] - target_css_y
                    self.y_off -= err * self.dpr
                    if abs(err) < 3:
                        self.y_off_error = err
                        return self.y_off
                self.y_off = self.dev_h - ih * self.dpr - 26   # on repart de l'estimation
            raise RuntimeError(f"calibration impossible (y_off={self.y_off})")
        finally:
            self.js("(document.getElementById('__msVeil')||{style:{}}).style.display='none'")

    # --- device --------------------------------------------------------
    def wake(self):
        adb("shell", "settings", "put", "global", "stay_on_while_plugged_in", "7")
        st = adb("shell", "dumpsys", "power").stdout
        if "mWakefulness=Awake" not in st:
            adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
            time.sleep(1)

    def open_app(self):
        adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", f"{APP_URL}#k={secret()}")

    def reload(self, wait=5):
        self.js("location.reload()")
        time.sleep(wait)
        self.ws.close()
        self.__init__()

    def screenshot(self, name, max_side=1200):
        from PIL import Image
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsung_out")
        os.makedirs(out, exist_ok=True)
        path = os.path.join(out, f"{name}.png")
        png = subprocess.run([ADB, "exec-out", "screencap", "-p"], capture_output=True).stdout
        with open(path, "wb") as f:
            f.write(png)
        im = Image.open(path)
        w, h = im.size
        if max(w, h) > max_side:
            r = max_side / max(w, h)
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
            im.save(path)
        return path, im.size

    # --- gestes RÉELS (adb, pas dispatchEvent) --------------------------
    def _rect(self, selector_js):
        """selector_js renvoie un élément ; on retourne son rect CSS + visibilité."""
        return self.js(f"""
        (() => {{
          const el = {selector_js};
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {{x: r.x, y: r.y, w: r.width, h: r.height,
                   inview: r.top >= 0 && r.bottom <= innerHeight && r.width > 0 && r.height > 0,
                   top: r.top, bottom: r.bottom, ih: innerHeight}};
        }})()""")

    def find_text(self, text, tag="button, a, label, .tab, [role=tab], div, span"):
        """Le premier élément cliquable dont le texte contient `text`."""
        t = json.dumps(text)
        return f"""[...document.querySelectorAll({json.dumps(tag)})]
            .filter(e => (e.textContent||'').trim().includes({t}) && e.offsetParent !== null)
            .sort((a,b) => (a.textContent.length - b.textContent.length))[0]"""

    def scroll_into_view(self, selector_js, settle=0.6):
        ok = self.js(f"""
        (() => {{ const el = {selector_js}; if (!el) return false;
           el.scrollIntoView({{block:'center', behavior:'instant'}}); return true; }})()""")
        time.sleep(settle)
        return ok

    def tap_el(self, selector_js, settle=0.8, verify=True, retry=True):
        """Tape au DOIGT au centre de l'élément (après l'avoir amené à l'écran).

        `verify` relit où la page a reçu le pointerdown : un doigt qui rate sa cible
        (barre d'URL, élément recouvert, offset périmé) doit être une ERREUR bruyante,
        pas un vert silencieux.
        """
        if not self.scroll_into_view(selector_js):
            raise RuntimeError(f"élément introuvable: {selector_js[:80]}")
        r = self._rect(selector_js)
        if r is None:
            raise RuntimeError("élément disparu après scroll")
        self.js("window.__msTap = null")
        cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
        adb("shell", "input", "tap", str(int(cx * self.dpr)), str(int(self.y_off + cy * self.dpr)))
        time.sleep(settle)
        if not verify:
            return r
        tap = self.js("window.__msTap")
        if tap is None or abs(tap["x"] - cx) > r["w"] / 2 + 4 or abs(tap["y"] - cy) > r["h"] / 2 + 4:
            if retry:
                self.calibrate()
                return self.tap_el(selector_js, settle=settle, verify=verify, retry=False)
            raise RuntimeError(f"le doigt a raté la cible : visé ({cx:.0f},{cy:.0f}), reçu {tap}")
        r["tap"] = tap
        return r

    def tap_text(self, text, tag="button, a, label, .tab, [role=tab]", settle=0.8):
        return self.tap_el(self.find_text(text, tag), settle=settle)

    def tap_xy_css(self, x, y, settle=0.5):
        adb("shell", "input", "tap", str(int(x * self.dpr)), str(int(self.y_off + y * self.dpr)))
        time.sleep(settle)

    def swipe_css(self, x1, y1, x2, y2, ms=300, settle=0.5):
        adb("shell", "input", "swipe",
            str(int(x1 * self.dpr)), str(int(self.y_off + y1 * self.dpr)),
            str(int(x2 * self.dpr)), str(int(self.y_off + y2 * self.dpr)), str(ms))
        time.sleep(settle)

    def type_text(self, text, settle=0.6):
        """Vrai clavier virtuel. `input text` n'accepte pas les espaces bruts."""
        adb("shell", "input", "text", text.replace(" ", "%s"))
        time.sleep(settle)

    # --- boîtes natives du navigateur (prompt/confirm) -------------------
    def ui_dump(self):
        """L'arbre des vues Android. Seul moyen de VOIR une boîte native :
        pendant un prompt(), l'exécution JS de la page est gelée, donc CDP est muet."""
        return subprocess.run([ADB, "exec-out", "uiautomator", "dump", "/dev/tty"],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace").stdout

    def ui_nodes(self, xml=None):
        import re
        xml = xml if xml is not None else self.ui_dump()
        out = []
        for m in re.finditer(r'text="([^"]*)"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
            t = m.group(1)
            if t.strip():
                x1, y1, x2, y2 = (int(g) for g in m.group(2, 3, 4, 5))
                out.append({"text": t, "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2,
                            "bounds": (x1, y1, x2, y2)})
        return out

    def ui_tap(self, text, exact=False, settle=1.0):
        for n in self.ui_nodes():
            if (n["text"] == text) if exact else (text in n["text"]):
                adb("shell", "input", "tap", str(n["cx"]), str(n["cy"]))
                time.sleep(settle)
                return n
        raise RuntimeError(f"vue Android introuvable : {text!r}")

    def dialog_answer(self, value=None, button="OK"):
        """Répond à un prompt() natif au doigt : champ, effacement, saisie, bouton."""
        if value is not None:
            nodes = self.ui_nodes()
            # le champ de saisie est la vue éditable au-dessus des boutons
            btn_y = min((n["cy"] for n in nodes if n["text"] in ("OK", "Annuler")), default=10**9)
            champs = [n for n in nodes if n["cy"] < btn_y and n["bounds"][3] - n["bounds"][1] > 60]
            if not champs:
                raise RuntimeError("champ du prompt introuvable")
            f = max(champs, key=lambda n: n["cy"])
            adb("shell", "input", "tap", str(f["cx"]), str(f["cy"]))
            time.sleep(0.5)
            adb("shell", "input", "keyevent", "KEYCODE_MOVE_END")
            for _ in range(12):
                adb("shell", "input", "keyevent", "KEYCODE_DEL")
            adb("shell", "input", "text", str(value).replace(" ", "%s"))
            time.sleep(0.4)
        return self.ui_tap(button, exact=True)

    def keyboard_open(self):
        out = adb("shell", "dumpsys", "input_method").stdout
        return "mInputShown=true" in out

    def close_keyboard(self, settle=0.8):
        """⚠ JAMAIS `KEYCODE_BACK` : quand le clavier est déjà fermé, BACK quitte Chrome
        et bascule sur l'app précédente (payé le 27/07 — on s'est retrouvé dans Macro Deck)."""
        self.js("document.activeElement && document.activeElement.blur()")
        time.sleep(settle)
        return not self.keyboard_open()

    def focus_app(self, settle=2.0):
        """Ramène Chrome au premier plan sans recharger la page."""
        adb("shell", "am", "start", "-n",
            "com.android.chrome/com.google.android.apps.chrome.Main")
        time.sleep(settle)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    p = Phone()
    print("titre     :", p.js("document.title"))
    print("écran CSS :", p.css_w, "x", p.js("innerHeight"), f"(dpr {p.dpr:.2f}, device {p.dev_w}x{p.dev_h})")
    print("version   :", p.js("(document.querySelector('#version, .version, [class*=version]')||{}).textContent"))
    print("erreurs JS:", p.js_errors())
