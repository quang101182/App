# -*- coding: utf-8 -*-
"""Karaoke : temps de CHAQUE MOT d'une narration (Manga Studio v1.86.0, 22/09/2026, etape 2-bis de l'ordre Quang).

Pour chaque page avec voix : Whisper (Groq whisper-large-v3-turbo, via le gateway, timestamp_granularities=word
-- meme appel que promoclip-local whisperTimestamps(), commit 401b3f7^) sur le MP3, puis RECALAGE sur le texte
exact de la narration (le texte affiche est celui qui a ete lu, pas ce que Whisper a entendu) : les mots
reconnus servent d'ancres (difflib), les autres sont interpoles au prorata de leur longueur.
Ecrit pages[].mots = [[debut, fin], ...] (un couple par mot de narration.split()) dans narration.json.

Usage : python karaoke_mots.py <serie/ch_N> <tag> [--force]
"""
import difflib, json, os, re, sys, time, unicodedata, urllib.error, urllib.request, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narrate_chapter as nc          # GATEWAY, secret, frein 18/min

VERSION = "1.89.0"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
MODELE = "whisper-large-v3-turbo"
MAX_CPS = 25                          # debit maximal plausible d'une voix (caracteres/s, espaces compris)
PRIX_HEURE = 0.04                     # $ / heure d'audio (Groq), 10 s factures au minimum par appel


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", w)


def whisper(mp3, prompt, langue="fr"):
    """POST multipart -> {words:[{word,start,end}], duration}. Reessaie les 429 / 52x comme nc.post."""
    bnd = "----manga" + uuid.uuid4().hex
    champs = [("model", MODELE), ("response_format", "verbose_json"), ("language", langue),
              ("timestamp_granularities[]", "word"), ("prompt", prompt[:800])]
    corps = b"".join(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (bnd, k, v)).encode()
                     for k, v in champs)
    corps += ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"page.mp3\"\r\n"
              "Content-Type: audio/mpeg\r\n\r\n" % bnd).encode() + open(mp3, "rb").read() + ("\r\n--%s--\r\n" % bnd).encode()
    req = urllib.request.Request(nc.GATEWAY + "/api/groq", data=corps, headers={
        "Content-Type": "multipart/form-data; boundary=" + bnd, "Authorization": "Bearer " + nc.SECRET,
        "X-Api-Path": "/openai/v1/audio/transcriptions", "User-Agent": "manga-studio/" + VERSION})
    last = None
    for essai in range(5):
        nc._frein()
        attente = 4 * (essai + 1)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            brut = e.read()[:300].decode("utf-8", "replace")
            last = "HTTP %d %s" % (e.code, brut[:200])
            if e.code not in (429, 500, 502, 503, 504, 520, 521, 522, 523, 524):
                break
            if e.code == 429:
                try:
                    attente = float(json.loads(brut).get("retry_after") or 60) + 1
                except Exception:
                    attente = 61
        except Exception as e:
            last = str(e)
        time.sleep(attente)
    raise RuntimeError("whisper : " + str(last))


def recaler(texte, mots, dur):
    """Un couple [debut, fin] par mot de texte.split(). Ancres = mots Whisper retrouves dans le texte."""
    toks = texte.split()
    if not toks:
        return []
    # Whisper derive parfois d'environ 3 % : son dernier mot finit APRES la fin reelle du MP3 (mesure 22/09 :
    # 11,20 s pour 10,85 s). On ramene alors toute son echelle de temps a la duree vraie.
    fin_w = max([float(m["end"]) for m in mots] or [0])
    if dur and fin_w > dur:
        mots = [dict(m, start=float(m["start"]) * dur / fin_w, end=float(m["end"]) * dur / fin_w) for m in mots]
    a, b = [norm(t) for t in toks], [norm(m.get("word", "")) for m in mots]
    deb, fin = [None] * len(toks), [None] * len(toks)
    for bl in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(bl.size):
            if a[bl.a + k]:
                deb[bl.a + k], fin[bl.a + k] = float(mots[bl.b + k]["start"]), float(mots[bl.b + k]["end"])
    # Whisper SAUTE parfois un passage et etire le mot suivant pour boucher le trou (mesure 22/09, Claymore p.2 :
    # 15 mots absents, « ombre » dure 2,7 s). Les ancres qui bordent un trou impossible a dire (> MAX_CPS
    # caracteres/s) sont donc fausses : on les retire, le trou s'elargit, jusqu'a un debit plausible.
    while True:
        retire, i = False, 0
        while i < len(toks):
            if deb[i] is not None:
                i += 1
                continue
            j = i
            while j < len(toks) and deb[j] is None:
                j += 1
            t0 = fin[i - 1] if i > 0 else 0.0
            t1 = deb[j] if j < len(toks) else max(dur, t0)
            if sum(len(t) + 1 for t in toks[i:j]) > MAX_CPS * max(t1 - t0, 0.01):
                for k in (i - 1, j):
                    if 0 <= k < len(toks) and deb[k] is not None:
                        deb[k] = fin[k] = None
                        retire = True
                if retire:
                    break                   # les bornes ont bouge : on repart du debut
            i = j
        if not retire:
            break
    # trous : repartis entre l'ancre d'avant et celle d'apres, au prorata de la longueur des mots
    i = 0
    while i < len(toks):
        if deb[i] is not None:
            i += 1
            continue
        j = i
        while j < len(toks) and deb[j] is None:
            j += 1
        t0 = fin[i - 1] if i > 0 else 0.0
        t1 = deb[j] if j < len(toks) else max(dur, t0)
        poids = [len(t) + 1 for t in toks[i:j]]
        tot, t = float(sum(poids)), t0
        for k, pz in zip(range(i, j), poids):
            d = (t1 - t0) * pz / tot
            deb[k], fin[k], t = t, t + d, t + d
        i = j
    for k in range(1, len(toks)):                  # jamais de recul (Whisper chevauche parfois deux mots)
        deb[k] = max(deb[k], deb[k - 1])
        fin[k] = max(fin[k], deb[k])
    return [[round(x, 2), round(y, 2)] for x, y in zip(deb, fin)]


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    force = "--force" in sys.argv
    if len(args) != 2:
        raise SystemExit(__doc__)
    chap, tag = args[0].strip("/"), args[1]
    nd = os.path.join(SRC, chap, "narration", tag)
    fj = os.path.join(nd, "narration.json")
    n = json.load(open(fj, encoding="utf-8"))
    nc.SECRET = nc._secret()
    t0, secs, faits, ancres, total = time.time(), 0.0, 0, 0, 0
    a_faire = [p for p in n["pages"] if p.get("audio") and (p.get("narration") or "").strip() and (force or not p.get("mots"))]
    fp = os.path.join(nd, "karaoke_progress.json")

    def progres(fini=False):                     # v1.88.0 : lu par le proxy (cellule d'activite, survit a un redemarrage)
        json.dump({"fait": faits, "total": len(a_faire), "t": time.time(), "fini": fini, "pid": os.getpid()}, open(fp, "w", encoding="utf-8"))

    progres()
    for p in a_faire:
        r = whisper(os.path.join(nd, p["audio"]), p["narration"], n.get("langue") or "fr")   # v1.89.0 : narration en anglais
        mots = r.get("words") or []
        dur = float(p.get("dur") or r.get("duration") or 0)
        p["mots"] = recaler(p["narration"], mots, dur)
        secs += max(10.0, dur)
        faits += 1
        a = [norm(t) for t in p["narration"].split()]
        m = difflib.SequenceMatcher(None, a, [norm(x.get("word", "")) for x in mots], autojunk=False)
        ancres += sum(bl.size for bl in m.get_matching_blocks())
        total += len(a)
        print("  page %s : %d mots, %d reconnus par Whisper" % (p["page"], len(a), sum(bl.size for bl in m.get_matching_blocks())), flush=True)
        progres()
    st = n.setdefault("stats", {})
    k = st.get("karaoke") or {}
    k.update(modele=MODELE, pages=faits + (k.get("pages", 0) if not force else 0),
             cout=round((k.get("cout", 0) if not force else 0) + secs / 3600 * PRIX_HEURE, 5),
             ancres=round(ancres / total, 3) if total else None, s=round(time.time() - t0, 1), version=VERSION,
             quand=time.strftime("%Y-%m-%dT%H:%M:%S"))                  # v1.91.0 : date de la depense (pastille des couts)
    st["karaoke"] = k
    tmp = fj + ".tmp"
    json.dump(n, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, fj)
    progres(fini=True)
    nc.dep.noter("karaoke", chap, tag, "whisper", secs / 3600 * PRIX_HEURE)     # v1.90.0 : registre des depenses
    print("OK : %d page(s) calee(s), %.0f %% des mots reconnus, %.4f $, %.0f s"
          % (faits, 100.0 * ancres / total if total else 0, secs / 3600 * PRIX_HEURE, time.time() - t0))


if __name__ == "__main__":
    main()
