"""Sonde LECTURE SEULE sur l'app reelle 8190 : pour chaque chapitre prepare en Dialogues, part des repliques zoomees par la camera."""
import os, sys
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
CHAPS = sys.argv[1:]
JS = """async () => { const out = [];
  for (let i = 0; i < DLL.liste.length; i++){ const x = DLL.liste[i]; if (x.vide){ out.push({vide:1}); continue; }
    DLL.i = i; dllMontrer(); try { DLL.audio.pause(); } catch(e){} await new Promise(r => setTimeout(r, 900));
    const r = dllCaseDe(x); const mm = ($('dllZoom').style.transform.match(/scale\(([\d.]+)\)/) || [0, 1])[1]; let k = +mm;
    out.push({k, r: !!r, page: x.page}); }
  return { cases: !!(DLL.cases && DLL.cases.pages), npages: DLL.cases && DLL.cases.pages ? Object.keys(DLL.cases.pages).length : 0,
           cam: DLL_CAM, liste: out, err: DLL.cases && DLL.cases.error }; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    bloques = []
    def filtre(rt):
        if rt.request.method != "GET" and "/manga/cases" not in rt.request.url:
            bloques.append(rt.request.url.split("/manga/")[-1][:40]); return rt.fulfill(status=200, body="{}", content_type="application/json")
        return rt.continue_()
    pg.route("**/*", filtre)
    pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(4000)
    for c in CHAPS:
        serie = c.split("/")[0]
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", serie)
        pg.reload(); pg.wait_for_timeout(4000)
        i = pg.evaluate("d => CHAPS.findIndex(c => c.dir === d)", c)
        if i < 0: print(c, "introuvable"); continue
        pg.evaluate("i => openChap(i)", i); pg.wait_for_timeout(3500)
        pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(5000)
        pg.evaluate("() => { try { DLL.audio.pause(); } catch(e){} }")
        r = pg.evaluate(JS)
        L = [x for x in r["liste"] if not x.get("vide")]
        z = [x for x in L if x["k"] > 1.05]
        fmt = pg.evaluate("i => (CHAPS[i] && (CHAPS[i].format || CHAPS[i].type)) || ''", i)
        print(f"{c} fmt={fmt!r} cam={r['cam']} cases_chargees={r['cases']} ({r['npages']} p.) repliques={len(L)} "
              f"zoomees={len(z)} sans_case={sum(1 for x in L if not x['r'])} k_moy={sum(x['k'] for x in L)/max(1,len(L)):.2f} err={r['err']}")
    print("ecritures bloquees:", sorted(set(bloques)))
    b.close()
