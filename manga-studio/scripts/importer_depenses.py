"""Reconstitue le registre des depenses (sources/_depenses.jsonl) a partir de l'HISTORIQUE, une seule fois (24/09/2026).

Deux sources :
  1. les fichiers ENCORE presents (narration.json, traduction.json, karaoke, precedemment) -> montant exact + detail ;
  2. le journal %LOCALAPPDATA%/manga-studio/narration.log -> les passages PAYES dont le fichier a ete ecrase ou supprime
     (traductions refaites, chapitres supprimes, corbeille videe). Une narration disparue qui reutilisait une analyse
     n'a paye que recit + voix : estime par le ratio mesure sur les narrations « reutilisation » encore presentes
     (ligne marquee estime=true).
Refuse de tourner si le registre existe deja (--force pour le refaire). Usage : python importer_depenses.py [--force]
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import depenses as dep

SRC = dep.SRC
LOG = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-studio", "narration.log")
ETAPES = ("cout_noms", "cout_vision", "cout_verif", "cout_recit", "cout_tts")


def fichiers():
    """(type, chapitre, tag) -> ligne exacte, pour tout ce qui est encore sur le disque."""
    out = {}
    for slug in os.listdir(SRC):
        sd = os.path.join(SRC, slug)
        if slug.startswith(("_", ".")) or not os.path.isdir(sd):
            continue
        for ch in os.listdir(sd):
            d = slug + "/" + ch
            nd = os.path.join(sd, ch, "narration")
            for tag in (os.listdir(nd) if ch.startswith("ch_") and os.path.isdir(nd) else []):
                f = os.path.join(nd, tag, "narration.json")
                try:
                    n = json.load(open(f, encoding="utf-8"))
                except Exception:
                    continue
                st = n.get("stats") or {}
                reuse = n.get("reuse_vision")
                detail = {k: round(float(st.get(k) or 0), 5) for k in ETAPES if st.get(k)}
                if reuse:
                    detail.pop("cout_vision", None)
                t = (n.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(f))))[:19]
                out[("narration", d, tag)] = dict(t=t, type="narration", d=d, tag=tag, moteur=n.get("engine") or "?",
                                                   paye=round(sum(detail.values()), 5), detail=detail, reuse=reuse,
                                                   source="fichier", brut=float(st.get("cout_total") or 0))
                ka = st.get("karaoke") or {}
                if ka.get("cout"):
                    out[("karaoke", d, tag)] = dict(t=(ka.get("quand") or t)[:19], type="karaoke", d=d, tag=tag,
                                                     moteur="whisper", paye=round(ka["cout"], 5), source="fichier")
            for tag in (os.listdir(nd) if ch.startswith("ch_") and os.path.isdir(nd) else []):   # narrations ECHOUEES, payees
                pj = os.path.join(nd, tag, "progress.json")
                if os.path.isfile(pj) and not os.path.isfile(os.path.join(nd, tag, "narration.json")):
                    try:
                        pr = json.load(open(pj, encoding="utf-8"))
                    except Exception:
                        continue
                    c = sum(float(v or 0) for v in (pr.get("couts") or {}).values())
                    if c:
                        out[("narration", d, tag)] = dict(t=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(pr.get("t") or os.path.getmtime(pj))),
                                                          type="narration", d=d, tag=tag, moteur="?", paye=round(c, 5),
                                                          detail=pr.get("couts"), source="fichier", note="narration echouee")
            trd = os.path.join(sd, ch, "traduction")
            for lg in (os.listdir(trd) if ch.startswith("ch_") and os.path.isdir(trd) else []):
                try:
                    tj = json.load(open(os.path.join(trd, lg, "traduction.json"), encoding="utf-8"))
                except Exception:
                    continue
                c = (tj.get("stats") or {}).get("cout", 0)
                out[("traduction", d, "traduction " + lg)] = dict(t=(tj.get("created_at") or "")[:19], type="traduction", d=d,
                                                                 tag="traduction " + lg, moteur=tj.get("engine") or "?",
                                                                 paye=round(c, 5), source="fichier")
            for mode in ("ouverture", "rattrapage"):
                pj = os.path.join(sd, ch, "precedemment", mode + ".json")
                if os.path.isfile(pj):
                    try:
                        pq = json.load(open(pj, encoding="utf-8"))
                        out[("precedemment", d, mode)] = dict(t=(pq.get("created_at") or "")[:19], type="precedemment", d=d,
                                                              tag=mode, moteur="deepseek",
                                                              paye=round((pq.get("stats") or {}).get("cout_total", 0), 5),
                                                              source="fichier")
                    except Exception:
                        pass
    return out


def journal(ratio_reuse):
    """Passages payes d'apres le journal : [(type, chapitre, tag, t, montant, reutilisation?)] dans l'ordre."""
    evs = []
    for l in open(LOG, encoding="utf-8", errors="replace"):
        try:
            evs.append(json.loads(l))
        except ValueError:
            pass
    out, ouverts = [], {}
    for e in evs:
        ev = e.get("ev")
        if ev == "start":
            ouverts[e.get("tag")] = {"d": e.get("chapitre"), "vision": 0}
        elif ev in ("vision_lot_v2", "vision_lot") and ouverts:
            ouverts[list(ouverts)[-1]]["vision"] += 1
        elif ev == "done" and e.get("tag") in ouverts:
            o = ouverts.pop(e["tag"])
            out.append(("narration", (o["d"] or "").replace("\\", "/"), e["tag"], e["t"], float(e.get("cout") or 0), not o["vision"]))
        elif ev == "traduction_done":
            out.append(("traduction", (e.get("chapitre") or "").replace("\\", "/"), "traduction " + (e.get("langue") or "?"),
                        e["t"], float(e.get("cout") or 0), False))
    return out


def main():
    if os.path.exists(dep.REGISTRE) and "--force" not in sys.argv:
        raise SystemExit("le registre existe deja : %s (--force pour le refaire)" % dep.REGISTRE)
    fic = fichiers()
    reuses = [v for v in fic.values() if v["type"] == "narration" and v.get("reuse") and v.get("brut")]
    ratio = (sum(v["paye"] for v in reuses) / sum(v["brut"] for v in reuses)) if reuses else 0.55
    print("ratio mesure « narration qui reutilise une analyse » : %.2f (sur %d narrations presentes)" % (ratio, len(reuses)))
    jr = journal(ratio)
    # le DERNIER passage du journal pour (type, chapitre, tag) est celui du fichier present ; les autres ont disparu
    derniers = {}
    for i, (ty, d, tag, t, c, reu) in enumerate(jr):
        derniers[(ty, d, tag)] = i
    lignes = [v for v in fic.values() if v["paye"]]
    perdus = 0.0
    for i, (ty, d, tag, t, c, reu) in enumerate(jr):
        if (ty, d, tag) in fic and derniers[(ty, d, tag)] == i:
            continue                                                  # c'est celui du fichier : deja compte, exact
        paye = c * ratio if (ty == "narration" and reu) else c
        if paye <= 0:
            continue
        perdus += paye
        lignes.append(dict(t=t[:19], type=ty, d=d, tag=tag, moteur="?", paye=round(paye, 5), source="journal",
                           estime=bool(ty == "narration" and reu), note="fichier ecrase ou supprime"))
    # incident du 23/09 21h12-21h17 (journal _incidents) : 6 narrations OPM ch.5-10 plantaient APRES avoir tout paye (print
    # cp1252), puis etaient relancees -> la voix payee deux fois, ~0,8 $ ; aucun fichier ne le garde
    if any(e[3].startswith("2026-09-23T21:1") for e in jr) and "2026-09" == time.strftime("%Y-%m"):
        lignes.append(dict(t="2026-09-23T21:17:00", type="narration", d="one-punch-man/ch_5-10", tag="voix payee 2x (incident)",
                           moteur="gcptts", paye=0.8, source="incident", estime=True, note="_incidents.md 23/09"))
    lignes.sort(key=lambda x: x["t"])
    tmp = dep.REGISTRE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for l in lignes:
            l.pop("brut", None)
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    os.replace(tmp, dep.REGISTRE)
    mois = time.strftime("%Y-%m")
    tot = sum(l["paye"] for l in lignes); tm = sum(l["paye"] for l in lignes if l["t"].startswith(mois))
    print("%d lignes ecrites | total %.2f $ | ce mois %.2f $ | dont retrouves dans le journal %.2f $ (estimes : %.2f $)"
          % (len(lignes), tot, tm, perdus, sum(l["paye"] for l in lignes if l.get("estime"))))


if __name__ == "__main__":
    main()
