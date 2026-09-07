# -*- coding: utf-8 -*-
"""Rejoue EXACTEMENT le chemin cloud de SubWhisper (transcribeCloud, index.html:2372)
pour un moteur STT donne : presign -> PUT R2 -> POST /process -> poll /job-status.

Le secret ne transite jamais par la sortie.
"""
import os, sys, time, json, requests
from secret import worker_secret

BASE = "https://subwhisper-worker.quang101182.workers.dev"
GATEWAY = "https://api-gateway.quang101182.workers.dev"
FICHIER = os.environ.get("SUBWHISPER_TEST_FILE", "").strip() or sys.exit(
    "Definis SUBWHISPER_TEST_FILE = le fichier audio/video a tester "
    "(non-WAV et > 24 Mo pour emprunter le chemin cloud).")

def run(moteur):
    secret = worker_secret()
    taille = os.path.getsize(FICHIER)
    t0 = time.time()
    print(f"\n===== moteur = {moteur} · {taille/1048576:.1f} Mo =====", flush=True)

    r = requests.post(BASE + "/upload-presign", json={
        "filename": FICHIER, "filesize": taille,
        "mimeType": "video/mp4", "multipart": False}, timeout=60)
    r.raise_for_status()
    p = r.json()
    jobId = p["jobId"]
    print(f"[{time.time()-t0:6.1f}s] presign OK  jobId={jobId}", flush=True)

    with open(FICHIER, "rb") as f:
        up = requests.put(p["presignedUrl"], data=f,
                          headers={"Content-Type": "video/mp4"}, timeout=900)
    print(f"[{time.time()-t0:6.1f}s] upload R2 -> {up.status_code}", flush=True)
    up.raise_for_status()

    r = requests.post(BASE + "/process", json={
        "jobId": jobId, "sttEngine": moteur, "r2Key": p["r2Key"],
        "srcLang": "", "groqKey": None,
        "gatewayKey": secret, "gatewayUrl": GATEWAY}, timeout=120)
    print(f"[{time.time()-t0:6.1f}s] /process -> {r.status_code} {r.text[:200]}", flush=True)

    vus = set()
    dernier = None
    for i in range(900):          # 900 x 3s = 45 min
        time.sleep(3)
        s = requests.get(f"{BASE}/job-status/{jobId}", timeout=60)
        if s.status_code == 404:
            print(f"[{time.time()-t0:6.1f}s] JOB DISPARU (404)", flush=True)
            return {"moteur": moteur, "etat": "404"}
        d = s.json()
        dernier = d
        for l in (d.get("logs") or []):
            txt = l if isinstance(l, str) else json.dumps(l, ensure_ascii=False)
            if txt not in vus:
                vus.add(txt)
                print(f"[{time.time()-t0:6.1f}s]   {txt}", flush=True)
        lg = d.get("log")
        if lg and lg not in vus:
            vus.add(lg)
            print(f"[{time.time()-t0:6.1f}s]   {d.get('progress')}% {lg}", flush=True)
        if d.get("status") in ("done", "completed", "error", "failed"):
            break
    srt = (dernier or {}).get("srt") or ""
    print(f"[{time.time()-t0:6.1f}s] etat final = {(dernier or {}).get('status')} · SRT {len(srt)} car", flush=True)
    if srt:
        print("--- 8 premieres lignes du SRT ---")
        print("\n".join(srt.splitlines()[:8]))
    return {"moteur": moteur, "etat": (dernier or {}).get("status"),
            "srt_len": len(srt), "duree_s": round(time.time()-t0, 1),
            "srt": srt}

if __name__ == "__main__":
    res = run(sys.argv[1] if len(sys.argv) > 1 else "groq")
    json.dump({k: v for k, v in res.items() if k != "srt"},
              open(f"resultat_{res['moteur']}.json", "w"), indent=2)
    if res.get("srt"):
        open(f"sortie_{res['moteur']}.srt", "w", encoding="utf-8").write(res["srt"])
