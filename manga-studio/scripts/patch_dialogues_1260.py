"""dialogues.py 1.25.0 -> 1.26.0 : une bulle ENTOUREE qui recouvre une bulle deja connue = la MEME bulle (plus de doublon).
Rejouable : ne fait rien si deja applique."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/dialogues.py"
s = open(F, encoding="utf-8", newline="").read()
if "def couvre(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-1250")

def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)

rep('VERSION = "1.25.0"  # 1.25.0 (27/09)',
    'VERSION = "1.26.0"  # 1.26.0 (27/09) : bulle ENTOUREE qui recouvre une bulle connue = la MEME (plus de replique en double) ;  # 1.25.0 (27/09)')

rep('''def apparier(ref, bulles):''', '''def couvre(grande, petite):
    """1.26.0 : part de la PETITE zone contenue dans la GRANDE (1.0 = entierement dedans). Une bulle entouree au doigt est
    souvent bien plus large que la zone de lettres detectee : l'IoU est alors faible alors que c'est la meme bulle."""
    x1, y1 = max(grande["x"], petite["x"]), max(grande["y"], petite["y"])
    x2, y2 = min(grande["x"] + grande["w"], petite["x"] + petite["w"]), min(grande["y"] + grande["h"], petite["y"] + petite["h"])
    a = petite["w"] * petite["h"]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1) / a if a > 0 else 0.0


def meme_zone(ajout, b):
    """1.26.0 : l'ajout (zone) designe-t-il la bulle de zone b ? meme zone, ou b contenue dans le trace."""
    return iou(ajout, b) >= 0.5 or couvre(ajout, b) >= 0.8


def apparier(ref, bulles):''')

# apparier : repli sur « contenue dans le trace »
rep('''    same = [b for b in bulles if b["id"] == ref.get("id")]
    return same[0] if same and iou(ref["box"], same[0]["box"]) >= 0.2 else None''',
'''    same = [b for b in bulles if b["id"] == ref.get("id")]
    if same and iou(ref["box"], same[0]["box"]) >= 0.2:
        return same[0]
    dedans = sorted(((couvre(ref["box"], b["box"]), b) for b in bulles if not b.get("ajout")), key=lambda t: -t[0])
    return dedans[0][1] if dedans and dedans[0][0] >= 0.8 else None      # 1.26.0 : bulle connue DANS le trace''')

# appliquer_verif : un ajout deja pose en double dans la traduction (<= 1.25.0) disparait ; un ajout qui recouvre une bulle connue n'est pas ajoute
rep('''    ex = [apparier(r, bulles) for r in v.get("exclues") or []]''',
'''    bulles = [b for b in bulles if not (b.get("ajout") and any(couvre(b["box"], c["box"]) >= 0.8 for c in bulles if not c.get("ajout")))]   # 1.26.0
    ex = [apparier(r, bulles) for r in v.get("exclues") or []]''')
rep('''        if not any(iou(z["box"], b["box"]) >= 0.5 for b in reste):''',
    '''        if not any(meme_zone(z["box"], b["box"]) for b in reste):             # 1.26.0 : recouvrement compris''')

# traduire_ajouts : idem, on ne retraduit pas (et on ne reecrit pas sur l'image) une bulle deja traduite
rep('''        nouveaux = [z for z in v.get("ajouts") or [] if not any(iou(z["box"], b["box"]) >= 0.5 for b in p["bulles"] if b.get("box"))]''',
    '''        nouveaux = [z for z in v.get("ajouts") or [] if not any(meme_zone(z["box"], b["box"]) for b in p["bulles"] if b.get("box") and not b.get("ajout"))
                    and not any(iou(z["box"], b["box"]) >= 0.5 for b in p["bulles"] if b.get("box"))]''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok")
