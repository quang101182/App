# -*- coding: utf-8 -*-
"""Rejoue la voie MULTIPART du chemin cloud : fichiers > 100 Mo.

⚠️ POURQUOI CE BANC EXISTE. Le 07/09/2026, `test_cloud.py` passait au vert sur les
3 moteurs pendant que la voie multipart etait CASSEE — parce que tous mes fichiers
de test faisaient moins de 100 Mo et empruntaient donc l'autre branche
(`index.html` : `isMultipart = filesize > 100 * 1024 * 1024`).

Le defaut : `dispatchToFly` avait gagne un parametre, et cet appelant-la ne
l'avait pas suivi. Arguments positionnels => tout decale d'un cran => Fly appelait
Groq en presentant une URL comme cle d'API (HTTP 401) et renvoyait ses mises a
jour a une adresse invalide, si bien que le navigateur restait fige a 35 %.

⇒ **Une branche non testee n'est pas une branche qui marche.** Ce banc couvre
celle que le poids du fichier reserve aux vraies grosses videos.

Usage :
    export SUBWHISPER_TEST_FILE=/chemin/vers/video_de_plus_de_100Mo.mp4
    python test_multipart.py croise
"""
import os
import sys
import time
import json
import requests
from secret import worker_secret

BASE    = "https://subwhisper-worker.quang101182.workers.dev"
GATEWAY = "https://api-gateway.quang101182.workers.dev"
SEUIL   = 100 * 1024 * 1024
MORCEAU = 100 * 1024 * 1024          # meme decoupe que le client

FICHIER = os.environ.get("SUBWHISPER_TEST_FILE", "").strip() or sys.exit(
    "Definis SUBWHISPER_TEST_FILE = un fichier de PLUS de 100 Mo "
    "(en dessous, c'est l'autre voie qui est testee — voir test_cloud.py).")


def run(moteur):
    taille = os.path.getsize(FICHIER)
    if taille <= SEUIL:
        sys.exit(f"Ce fichier fait {taille/1048576:.0f} Mo : sous les 100 Mo, il "
                 f"n'empruntera PAS la voie multipart. Ce banc ne prouverait rien.")
    secret = worker_secret()
    t0 = time.time()
    print(f"\n===== multipart · {moteur} · {taille/1048576:.0f} Mo =====", flush=True)

    p = requests.post(BASE + "/upload-presign", json={
        "filename": os.path.basename(FICHIER), "filesize": taille,
        "mimeType": "video/mp4", "multipart": True}, timeout=120).json()
    job = p["jobId"]
    urls = p["chunkPresignedUrls"]
    print(f"[{time.time()-t0:6.1f}s] presign multipart OK · {len(urls)} parties · job {job}", flush=True)

    parts = []
    with open(FICHIER, "rb") as f:
        for i, u in enumerate(urls):
            f.seek(i * MORCEAU)
            data = f.read(MORCEAU)
            r = requests.put(u["url"], data=data,
                             headers={"Content-Type": "video/mp4"}, timeout=1800)
            r.raise_for_status()
            etag = (r.headers.get("ETag") or "").replace('"', "")
            parts.append({"ETag": etag, "PartNumber": i + 1})
            print(f"[{time.time()-t0:6.1f}s] partie {i+1}/{len(urls)} envoyee", flush=True)

    r = requests.post(BASE + "/upload-complete", json={
        "uploadId": p["uploadId"], "r2Key": p["r2Key"], "jobId": job,
        "parts": parts, "sttEngine": moteur, "groqKey": None,
        "gatewayKey": secret, "gatewayUrl": GATEWAY}, timeout=300)
    print(f"[{time.time()-t0:6.1f}s] /upload-complete -> {r.status_code} {r.text[:160]}", flush=True)

    prec, d = None, {}
    for _ in range(2400):
        d = requests.get(f"{BASE}/job-status/{job}", timeout=60).json()
        cur = (d.get("status"), d.get("progress"), d.get("log"))
        if cur != prec:
            prec = cur
            print(f"[{time.time()-t0:6.1f}s] {cur[0]} · {cur[1]}% · {cur[2]}", flush=True)
        if d.get("status") in ("done", "error", "failed"):
            break
        time.sleep(2)

    srt = d.get("srt") or ""
    res = {"moteur": moteur, "voie": "multipart", "etat": d.get("status"),
           "erreur": d.get("error"), "srt_car": len(srt),
           "blocs": srt.count(" --> "), "duree_s": round(time.time()-t0, 1)}
    print(json.dumps(res, ensure_ascii=False), flush=True)
    if srt:
        open(f"multipart_{moteur}.srt", "w", encoding="utf-8").write(srt)
    return res


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "croise")
