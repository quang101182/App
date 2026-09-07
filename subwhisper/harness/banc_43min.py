# -*- coding: utf-8 -*-
"""Banc : le meme audio de 43 min (CJK reel) passe dans les 3 moteurs, par le
chemin cloud complet. Mesure la QUALITE (segments, mots) et la CADENCE des
mises a jour de progression reellement recues par le client.
"""
import sys, time, os, json, requests
from secret import worker_secret

BASE = "https://subwhisper-worker.quang101182.workers.dev"
GW   = "https://api-gateway.quang101182.workers.dev"
F    = os.environ.get("SUBWHISPER_TEST_FILE", "").strip() or sys.exit(
    "Definis SUBWHISPER_TEST_FILE = le fichier audio/video a tester "
    "(non-WAV et > 24 Mo pour emprunter le chemin cloud).")

def run(moteur):
    p = requests.post(BASE + "/upload-presign", json={
        "filename": F, "filesize": os.path.getsize(F),
        "mimeType": "audio/mp4", "multipart": False}, timeout=60).json()
    requests.put(p["presignedUrl"], data=open(F, "rb"),
                 headers={"Content-Type": "audio/mp4"}, timeout=1800)
    t0 = time.time()
    requests.post(BASE + "/process", json={
        "jobId": p["jobId"], "sttEngine": moteur, "r2Key": p["r2Key"],
        "srcLang": "", "groqKey": None,
        "gatewayKey": worker_secret(), "gatewayUrl": GW}, timeout=120)
    print(f"\n===== {moteur} · job {p['jobId']} =====", flush=True)

    prec, majs, d = None, [], {}
    for _ in range(1800):
        d = requests.get(f"{BASE}/job-status/{p['jobId']}", timeout=30).json()
        cur = (d.get("status"), d.get("progress"), d.get("log"))
        if cur != prec:
            dt = time.time() - t0
            majs.append(dt)
            prec = cur
            print(f"[{dt:6.1f}s] {cur[1]}% | {cur[2]}", flush=True)
        if d.get("status") in ("done", "error", "failed"):
            break
        time.sleep(1)

    srt = d.get("srt") or ""
    open(f"srt43_{moteur}.srt", "w", encoding="utf-8").write(srt)
    blocs = srt.count(" --> ")
    texte = "\n".join(l for l in srt.splitlines()
                      if l.strip() and "-->" not in l and not l.strip().isdigit())
    ecarts = [round(majs[i+1]-majs[i], 1) for i in range(len(majs)-1)]
    res = {"moteur": moteur, "duree_s": round(time.time()-t0, 1),
           "blocs": blocs, "caracteres": len(texte),
           "maj_recues": len(majs), "ecarts_entre_maj_s": ecarts}
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res

if __name__ == "__main__":
    out = []
    for m in sys.argv[1:] or ["groq", "gemini", "croise"]:
        out.append(run(m))
        time.sleep(5)
    json.dump(out, open("banc43_resultats.json", "w"), indent=2, ensure_ascii=False)
    print("\n===== SYNTHESE =====")
    for r in out:
        print(f"{r['moteur']:7s} {r['blocs']:4d} blocs · {r['caracteres']:6d} car · "
              f"{r['duree_s']:6.1f}s · {r['maj_recues']} maj recues · ecarts {r['ecarts_entre_maj_s']}")
