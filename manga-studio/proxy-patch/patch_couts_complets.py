# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : la pastille des couts compte TOUT (Manga Studio v1.91.0, 22/09/2026).

Quang (05h45) : « tu as lance une narration, mais je n'ai pas l'impression que le cout ait ete calcule et affiche. »
Mesure : /manga/costs ne lisait QUE les narration.json (ecrits a la FIN d'un run) -> une narration en cours
etait invisible, et les TRADUCTIONS (0,54 $ la nuit du 22/09) et le KARAOKE n'etaient jamais comptes.
Maintenant : + narration en cours (progress.json « couts », narrate_chapter v1.91) ; + traductions finies et en
cours (traduction.json / progress.json « cout ») ; + karaoke (stats.karaoke de la narration).
Rejouable : python patch_couts_complets.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "cout_traduction" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''                nd = os.path.join(sd, ch, "narration")
                if not ch.startswith("ch_") or not os.path.isdir(nd):
                    continue
                for tag in os.listdir(nd):
                    td = os.path.join(nd, tag)
                    np_ = os.path.join(td, "narration.json")
                    if os.path.isfile(np_):''',
    '''                nd = os.path.join(sd, ch, "narration")
                # v1.91.0 : les TRADUCTIONS sont des depenses aussi (finies ET en cours)
                trd = os.path.join(sd, ch, "traduction")
                for lg in (os.listdir(trd) if ch.startswith("ch_") and os.path.isdir(trd) else []):
                    tj, tp = os.path.join(trd, lg, "traduction.json"), os.path.join(trd, lg, "progress.json")
                    try:
                        if os.path.isfile(tj):
                            with open(tj, encoding="utf-8") as f: t = json.load(f)
                            runs.append({"chap": slug + "/" + ch, "tag": "traduction " + lg, "engine": t.get("engine") or "?",
                                         "date": (t.get("created_at") or "")[:19], "prompt": "traduction", "reuse": None,
                                         "st": {"cout_traduction": (t.get("stats") or {}).get("cout", 0)}})
                        if os.path.isfile(tp):
                            with open(tp, encoding="utf-8") as f: pr = json.load(f)
                            if not pr.get("fini") and pr.get("cout"):
                                runs.append({"chap": slug + "/" + ch, "tag": "traduction " + lg + " (en cours)", "engine": "gemini",
                                             "date": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(float(pr.get("t") or 0))),
                                             "prompt": "traduction", "reuse": None, "st": {"cout_traduction": pr["cout"]}})
                    except Exception:
                        pass
                if not ch.startswith("ch_") or not os.path.isdir(nd):
                    continue
                for tag in os.listdir(nd):
                    td = os.path.join(nd, tag)
                    np_ = os.path.join(td, "narration.json")
                    pp_ = os.path.join(td, "progress.json")
                    if not os.path.isfile(np_) and os.path.isfile(pp_):     # v1.91.0 : narration EN COURS
                        try:
                            with open(pp_, encoding="utf-8") as f: pr = json.load(f)
                            if pr.get("etape") != "fini" and pr.get("couts"):
                                runs.append({"chap": slug + "/" + ch, "tag": tag + " (en cours)", "engine": tag.split("-")[0],
                                             "date": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(float(pr.get("t") or 0))),
                                             "prompt": None, "reuse": None, "st": dict(pr["couts"])})
                        except Exception:
                            pass
                    if os.path.isfile(np_):''')

rep('''                        runs.append({"chap": slug + "/" + ch, "tag": tag, "engine": n.get("engine") or "?",
                                     "date": (n.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S",
                                     time.localtime(os.path.getmtime(np_))))[:19], "prompt": n.get("prompt"),
                                     "reuse": n.get("reuse_vision"), "st": st})''',
    '''                        runs.append({"chap": slug + "/" + ch, "tag": tag, "engine": n.get("engine") or "?",
                                     "date": (n.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S",
                                     time.localtime(os.path.getmtime(np_))))[:19], "prompt": n.get("prompt"),
                                     "reuse": n.get("reuse_vision"), "st": st})
                        ka = st.get("karaoke") or {}                          # v1.91.0 : le karaoke, a sa date
                        if ka.get("cout"):
                            runs.append({"chap": slug + "/" + ch, "tag": tag + " (karaoke)", "engine": "whisper",
                                         "date": (ka.get("quand") or time.strftime("%Y-%m-%dT%H:%M:%S",
                                                  time.localtime(os.path.getmtime(np_))))[:19],
                                         "prompt": "karaoke", "reuse": None, "st": {"cout_karaoke": ka["cout"]}})''')

rep('''              "voix": "cout_tts", "fusion": "cout_fusion", "juge": "cout_juge"}''',
    '''              "voix": "cout_tts", "fusion": "cout_fusion", "juge": "cout_juge",
              "traduction": "cout_traduction", "karaoke": "cout_karaoke"}                  # v1.91.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch couts complets OK")
