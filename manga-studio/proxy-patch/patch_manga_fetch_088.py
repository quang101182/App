"""manga-fetch 0.8.7 -> 0.8.8 (28/09) : un site qui ENCHAINE les chapitres a la verticale charge l'image d'ouverture du
chapitre SUIVANT avant que l'adresse ne change -> elle etait capturee en DERNIERE page du chapitre en cours (constate :
ch. 9 = 33 pages pour 32 annoncees, sa derniere = la 1re du 10 ; idem 10 / 11, octets identiques). Correction :
- retirer_debut_suivant(prec, suiv) : si la derniere page du precedent a les MEMES OCTETS que la 1re du suivant, elle sort du
  precedent (deplacee dans <prec>/_retirees/, jamais effacee ; manifest mis a jour) ;
- appelee dans la boucle de serie apres chaque chapitre capture ;
- commande « dedoublonner <dossier de serie> » : la meme regle sur les chapitres deja la (reparation par le CODE).
Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga-fetch/manga_fetch.py"
s = open(F, encoding="utf-8", newline="").read()
if "def retirer_debut_suivant(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-087")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "0.8.7"  # 0.8.7 (28/09)', 'VERSION = "0.8.8"  # 0.8.8 (28/09) : 1re page du chapitre suivant retiree de la fin du precedent ; 0.8.7 (28/09)')

rep('''def _mettre_de_cote(dossier: str, pourquoi: str):''', '''def retirer_debut_suivant(prec: str, suiv: str) -> str:
    """0.8.8 : la DERNIERE page du chapitre precedent a-t-elle les memes octets que la 1re du suivant ? (site qui enchaine les
    chapitres a la verticale : l'image d'ouverture du suivant est chargee avant que l'adresse change.) Alors elle sort du
    precedent -- deplacee dans <prec>/_retirees/, jamais effacee -- et le manifeste du precedent est mis a jour.
    Rend le nom du fichier retire, ou ""."""
    import hashlib
    try:
        mp = json.load(open(os.path.join(prec, "manifest.json"), encoding="utf-8"))
        ms = json.load(open(os.path.join(suiv, "manifest.json"), encoding="utf-8"))
        der, pre = (mp.get("pages") or [])[-1]["file"], (ms.get("pages") or [])[0]["file"]
    except Exception:
        return ""
    h = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    fp, fs = os.path.join(prec, der), os.path.join(suiv, pre)
    if len(mp["pages"]) < 2 or not (os.path.isfile(fp) and os.path.isfile(fs)) or os.path.getsize(fp) != os.path.getsize(fs) or h(fp) != h(fs):
        return ""
    os.makedirs(os.path.join(prec, "_retirees"), exist_ok=True)
    os.replace(fp, os.path.join(prec, "_retirees", der))
    mp["pages"] = mp["pages"][:-1]
    mp.setdefault("notes", []).append("dernière page retirée (%s) : c'était la 1re du chapitre suivant (%s)" % (der, os.path.basename(suiv)))
    json.dump(mp, open(os.path.join(prec, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log_evt("série", "1re page du chapitre suivant retirée de la fin du précédent", precedent=os.path.basename(prec),
            suivant=os.path.basename(suiv), fichier=der)
    return der


def dedoublonner_serie(serie_dir: str) -> int:
    """0.8.8 : retirer_debut_suivant() sur chaque paire de chapitres CONSECUTIFS deja presents d'une serie."""
    chs = []
    for d in os.listdir(serie_dir):
        m = re.fullmatch(r"ch_(\\d+(?:[.-]\\d+)?)", d)
        if m and os.path.isfile(os.path.join(serie_dir, d, "manifest.json")):
            chs.append((float(m.group(1).replace("-", ".")), d))
    chs.sort()
    n = 0
    for (a, da), (b, db) in zip(chs, chs[1:]):
        r = retirer_debut_suivant(os.path.join(serie_dir, da), os.path.join(serie_dir, db))
        if r:
            print(f"{da} : {r} retirée (= 1re page de {db})")
            n += 1
    print(f"{n} page(s) retirée(s)")
    return 0


def _mettre_de_cote(dossier: str, pourquoi: str):''')

rep('''            faits.append(num)
            chap = num
            if c2 == 3:''', '''            if not DERNIER.get("deja_la"):                    # 0.8.8 : image d'ouverture du suivant restee en fin du precedent
                retirer_debut_suivant(chap_dir(args.out, args.title, chap), chap_dir(args.out, args.title, num))
            faits.append(num)
            chap = num
            if c2 == 3:''')

rep('''    s = sub.add_parser("verify", help="contrôler manifeste <-> fichiers")
    s.add_argument("dossier")''', '''    s = sub.add_parser("verify", help="contrôler manifeste <-> fichiers")
    s.add_argument("dossier")

    s = sub.add_parser("dedoublonner", help="0.8.8 : retirer d'un chapitre sa derniere page si c'est la 1re du suivant")
    s.add_argument("serie_dir")''')

rep('''    if args.cmd == "verify":
        return verify(args.dossier)''', '''    if args.cmd == "verify":
        return verify(args.dossier)
    if args.cmd == "dedoublonner":
        return dedoublonner_serie(args.serie_dir)''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 0.8.8")
