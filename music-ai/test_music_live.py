#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness de test LIVE music·ai (pattern permanent — mandat Quang 12/06/2026).

Lance l'app dans un VRAI navigateur (Edge headless via CDP), comme l'utilisateur,
injecte le secret gateway + un profil complet, déclenche N recommandations en
boucle (avec pauses), et pour CHAQUE reco compare :
   reco IA (titre/artiste)  ↔  videoId résolu  ↔  vrai titre YouTube (oEmbed)
Sort un VERDICT CHIFFRÉ du taux de "mauvais audio" (titre joué ≠ reco affichée).

Dépendances: stdlib + websocket-client. Usage:
  WORKER_SECRET=xxx python test_music_live.py [N]
"""
import json, subprocess, time, tempfile, os, sys, re, urllib.request
import websocket
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PORT = 9333; HTTP_PORT = 9334
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8

def get_secret():
    s = os.environ.get("WORKER_SECRET")
    if s: return s
    try:
        for line in open(os.path.join(HERE, "..", "api-gateway", ".secrets.local"), encoding="utf-8"):
            m = re.match(r"\s*WORKER_SECRET\s*=\s*(\S+)", line)
            if m: return m.group(1).strip().strip('"')
    except Exception: pass
    return ""

SECRET = get_secret()
if not SECRET:
    print("[FATAL] WORKER_SECRET introuvable"); sys.exit(1)

def http_json(url):
    return json.load(urllib.request.urlopen(url, timeout=10))

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, max_size=30*1024*1024, suppress_origin=True)
        self._id = 0
    def cmd(self, method, params=None, timeout=60):
        self._id += 1; mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        self.ws.settimeout(timeout)
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg: raise Exception(f"{method}: {msg['error']}")
                return msg.get("result", {})
    def ev(self, expr, await_promise=True, timeout=60):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": await_promise,
                                          "returnByValue": True}, timeout=timeout)
        if r.get("exceptionDetails"):
            return {"__exc__": json.dumps(r["exceptionDetails"])[:400]}
        return r.get("result", {}).get("value")

def oembed(vid):
    try:
        d = http_json(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json")
        return d.get("title", ""), d.get("author_name", "")
    except Exception:
        return None, None

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
def title_tokens(s): return [w for w in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split() if len(w) > 2]
def title_match_ratio(ai_title, yt_title):
    toks = title_tokens(ai_title)
    if not toks: return 1.0
    ytn = norm(yt_title)
    return sum(1 for t in toks if t in ytn) / len(toks)

def main():
    tmp = tempfile.mkdtemp(prefix="musicai_cdp_")
    print(f"[harness] N={N}")
    httpd = subprocess.Popen([sys.executable, "-m", "http.server", str(HTTP_PORT), "--directory", HERE],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={tmp}", "--no-first-run", "--no-default-browser-check",
                             "--disable-gpu", "--remote-allow-origins=*",
                             "--autoplay-policy=no-user-gesture-required", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        ver = None
        for _ in range(40):
            try: ver = http_json(f"http://127.0.0.1:{PORT}/json/version"); break
            except Exception: time.sleep(0.25)
        if not ver: raise Exception("CDP indisponible")
        tgt = None
        for _ in range(20):
            tabs = [t for t in http_json(f"http://127.0.0.1:{PORT}/json") if t.get("type") == "page"]
            if tabs: tgt = tabs[0]; break
            time.sleep(0.25)
        cdp = CDP(tgt["webSocketDebuggerUrl"])
        cdp.cmd("Page.enable"); cdp.cmd("Runtime.enable")
        cdp.cmd("Page.navigate", {"url": f"http://127.0.0.1:{HTTP_PORT}/index.html"})
        time.sleep(2.5)
        profile = {"completedOnboarding": True, "genres": ["pop","rock","electro","indie"],
                   "artists": ["Daft Punk","Tame Impala","The Weeknd"], "eras": [], "contexts": ["detente"],
                   "adventurousness": 0.5}
        cfg = {"provider":"claude","model":"claude-opus-4-8","keys":{"claude":"","gemini":"","openai":""}}
        cdp.ev(f"localStorage.setItem('music_ai_gw_secret',{json.dumps(SECRET)});"
               f"localStorage.setItem('music_ai_config',{json.dumps(json.dumps(cfg))});"
               f"localStorage.setItem('music_ai_profile',{json.dumps(json.dumps(profile))});'ok'", await_promise=False)
        cdp.cmd("Page.reload"); time.sleep(4)
        for _ in range(20):
            if cdp.ev("typeof ST!=='undefined' && typeof getRecommendation==='function'", await_promise=False) is True:
                break
            time.sleep(0.5)
        # PREFLIGHT: secret injecté + IA répond ?
        sec_ok = cdp.ev("getGwSecret().length>0", await_promise=False)
        print(f"[preflight] gateway secret injecté: {sec_ok}")
        ai = cdp.ev("(async()=>{try{const r=await callAI(buildSystemPrompt('onetap'),"
                    "'Recommande-moi une chanson.',0.8);return 'OK:'+r.slice(0,80);}"
                    "catch(e){return 'ERR:'+e.message;}})()", await_promise=True, timeout=40)
        print(f"[preflight] callAI → {ai}\n")
        for i in range(N):
            cdp.ev("if(typeof ST!=='undefined')ST.currentTrack=null; 'r'", await_promise=False)
            cdp.ev(("getRecommendation('onetap')" if i == 0 else "ytNext()") + "; 'go'", await_promise=False)
            rec = None
            for _ in range(70):
                v = cdp.ev("(typeof ST!=='undefined'&&ST.currentTrack&&ST.currentTrack.videoId)?JSON.stringify({"
                           "t:ST.currentTrack.title,a:ST.currentTrack.artist,"
                           "it:ST.currentTrack._iaTitle||null,ia:ST.currentTrack._iaArtist||null,"
                           "vid:ST.currentTrack.videoId}):null", await_promise=False)
                if v: rec = json.loads(v); break
                time.sleep(0.5)
            if not rec:
                err = cdp.ev("(function(){var e=document.getElementById('result-onetap');"
                             "return JSON.stringify({card:(e?e.innerText:'').slice(0,60),"
                             "loading:typeof ST!=='undefined'?ST.isLoading:null,cont:typeof ST!=='undefined'?ST.continuousMode:null,"
                             "ready:typeof ST!=='undefined'?ST.ytPlayerReady:null,"
                             "ct:typeof ST!=='undefined'&&ST.currentTrack?(ST.currentTrack.title+'|vid='+ST.currentTrack.videoId):null});})()", await_promise=False)
                print(f"  #{i+1}: [PAS DE VIDEO] diag={err}")
                if i == 0:
                    probe = cdp.ev("(async()=>{try{const v=await ytSearch('Daft Punk Get Lucky official audio');return 'ytSearch='+v;}catch(e){return 'ytSearch ERR:'+e.message;}})()", await_promise=True, timeout=30)
                    print(f"       probe {probe}")
                results.append({"i": i+1, "status": "no_video", "diag": err}); time.sleep(3); continue
            ai_title = rec.get("it") or rec.get("t"); ai_artist = rec.get("ia") or rec.get("a"); vid = rec.get("vid")
            yt_title, yt_author = oembed(vid)
            ratio = title_match_ratio(ai_title, yt_title) if yt_title else None
            mismatch = (ratio is not None and ratio < 0.5)
            corrected = bool(rec.get("it"))
            tag = "[MAUVAIS TITRE]" if mismatch else ("[corrige]" if corrected else "[ok]")
            print(f"  #{i+1}: IA='{ai_title}' - {ai_artist}")
            print(f"       YT={vid} '{yt_title}' [{yt_author}] match={ratio} {tag}")
            results.append({"i": i+1, "ai": ai_title, "ai_artist": ai_artist, "vid": vid,
                            "yt": yt_title, "author": yt_author, "ratio": ratio,
                            "mismatch": mismatch, "corrected": corrected})
            # écriture incrémentale (survit à un timeout)
            json.dump({"results": results}, open(os.path.join(HERE, "test_music_live_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            time.sleep(2)
    finally:
        for p in (edge, httpd):
            try: p.terminate()
            except Exception: pass
    played = [r for r in results if r.get("vid")]
    bad = [r for r in played if r.get("mismatch")]
    print("\n" + "="*60)
    print(f"VERDICT — {len(played)}/{N} recos jouees | mauvais titre (audio != reco): {len(bad)}/{len(played)}")
    for r in bad:
        print(f"   [BAD] '{r['ai']}' - {r['ai_artist']}  ->  joue '{r['yt']}' [{r['author']}]")
    print("="*60)
    json.dump({"n": N, "played": len(played), "bad": len(bad), "results": results},
              open(os.path.join(HERE, "test_music_live_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
