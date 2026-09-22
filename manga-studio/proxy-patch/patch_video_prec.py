# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : la video peut commencer par le « Precedemment... » (Manga Studio v1.95.1, 22/09/2026).
Decision Quang (09h00) : oui, si la case 📜 du lecteur est cochee. Le reglage passe la liste blanche de
manga_video_ajoute ; l'empreinte (video_chapitre.py) le suit -> « le Precedemment... a ete refait ».
Rejouable : python patch_video_prec.py <chemin du proxy>. Suppose patch_video.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
PARTIE1 = '"precedemment": bool(reg.get("precedemment"))' not in s
if not PARTIE1 and "def _video_nom(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


if PARTIE1:
  rep('''              "pages": reg.get("pages") if re.match(r"^[a-z]{2}$", reg.get("pages") or "") else ""}''',
    '''              "pages": reg.get("pages") if re.match(r"^[a-z]{2}$", reg.get("pages") or "") else "",
              "precedemment": bool(reg.get("precedemment"))}                         # v1.95.1''')
  rep('''              "traduction": "la traduction a été refaite", "musique": "un morceau de musique a changé"}''',
    '''              "traduction": "la traduction a été refaite", "musique": "un morceau de musique a changé",
              "precedemment": "le « Précédemment… » a été refait"}                     # v1.95.1''')
# v1.95.1 : NOM DU FICHIER TELECHARGE (Quang 09h10 : « que les tags soient corrects, pour que je puisse me reperer via le
# nom des videos ») -- serie, chapitre (3 chiffres : tri), voix, pages, sous-titres, musique, precedemment, vitesse, date.
rep('''                parts = rel.replace("\\\\", "/").strip("/").split("/")
                nom = re.sub(r"[^A-Za-z0-9._-]+", "-", "%s-%s-%s" % (parts[0], parts[1] if len(parts) > 1 else "", parts[-1]))
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % nom)''',
    '''                nom = _video_nom(rel, full)
                ascii_ = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode() or "video.mp4"
                self.send_header("Content-Disposition", "attachment; filename=\\"%s\\"; filename*=UTF-8''%s"
                                 % (ascii_.replace('"', ""), quote(nom, safe="")))''')
rep('''def manga_videos(serie):''',
    '''def _video_nom(rel, full):
    """v1.95.1 : « Claymore - ch001 - Charon - FR - karaoke - musique 25 % - precedemment - 1,15x - 2026-09-22 09h12.mp4 »."""
    parts = rel.replace("\\\\", "/").strip("/").split("/")
    serie, ch, tag = parts[0], (parts[1] if len(parts) > 1 else "")[3:], os.path.splitext(parts[-1])[0]
    info, man, voix = {}, {}, ""
    try:
        with open(full[:-4] + ".json", encoding="utf-8") as f: info = json.load(f)
    except Exception:
        pass
    try:
        with open(os.path.join(MANGA_SOURCES, parts[0], parts[1], "manifest.json"), encoding="utf-8") as f: man = json.load(f)
    except Exception:
        pass
    try:
        with open(os.path.join(MANGA_SOURCES, parts[0], parts[1], "narration", tag, "narration.json"), encoding="utf-8") as f:
            voix = json.load(f).get("voice") or ""
    except Exception:
        pass
    r = info.get("reglages") or {}
    num = str(man.get("chapter") or ch)
    num = num.zfill(3) if num.isdigit() else num
    morceaux = [man.get("title") or serie, "ch" + num, voix or tag, (r.get("pages") or "VO").upper()]
    morceaux.append(("karaoké" if r.get("karaoke") else "sous-titres") if r.get("sous") else "sans sous-titres")
    morceaux.append("musique %d %%" % int(r.get("volume") or 0) if r.get("musique") else "sans musique")
    if r.get("precedemment"):
        morceaux.append("précédemment")
    if r.get("vitesse"):
        morceaux.append(("%g" % float(r["vitesse"])).replace(".", ",") + "x")
    quand = (info.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(full))))
    morceaux.append(quand[:10] + " " + quand[11:13] + "h" + quand[14:16])
    nom = " - ".join(str(x) for x in morceaux if x)
    return re.sub(r'[\\\\/:*?"<>|\\x00-\\x1f]+', " ", nom).strip()[:180] + ".mp4"


def manga_videos(serie):''')
open(p, "w", encoding="utf-8").write(s)
print("patch video precedemment + nom OK")
