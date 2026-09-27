"""Banc test_dialogues_preparer.py : section H (S4, dialogues.py 1.27.0) -- « qui » choisi a la verification = impose. Rejouable."""
F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/test_dialogues_preparer.py"
s = open(F, encoding="utf-8", newline="").read()
if "def scenario_qui(" in s:
    print("deja applique"); raise SystemExit
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep('''        ETAT["appels"].append((moteur, pages))''', '''        ETAT["appels"].append((moteur, pages))
        ETAT.setdefault("textes", []).extend(textes)                     # H (1.27.0) : ce que l'IA a RECU''')

rep('''print("=== E. mutations (doivent rendre le banc ROUGE)")''', '''def scenario_qui(m, verbeux=True):
    """H (S4, 1.27.0) : une bulle attribuee par Quang a la verification -> la replique est a lui, l'IA l'a recu, les autres : l'IA."""
    k0 = len(KO)
    ch = copie()
    ETAT.update(qui5="Fille-Moustique", refuse=set(), appels=[], textes=[])
    tr = json.load(open(os.path.join(ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    p5 = [b for b in next(p for p in tr["pages"] if p["page"] == 5)["bulles"] if b["type"] == "dialogue" and (b.get("trad") or "").strip()]
    b0 = sorted(p5, key=lambda b: b["id"])[0]
    os.makedirs(os.path.join(ch, "dialogues"), exist_ok=True)
    json.dump({"pages": {"5": {"ordre": [{"id": b0["id"], "box": b0["box"], "qui": "Genos"}], "exclues": [], "ajouts": []}}},
              open(os.path.join(ch, "dialogues", "bulles_verifiees.json"), "w", encoding="utf-8"), ensure_ascii=False)
    lancer(m)
    d = doc(ch)
    x = next(y for y in d["repliques"] if y["cle"] == "5-%d" % b0["id"])
    autres = [y["qui"] for y in d["repliques"] if y["page"] == 5 and y["cle"] != x["cle"] and y["type"] == "dialogue"]
    check("H. la bulle attribuee par Quang est a lui (l'IA disait Fille-Moustique)", x["qui"] == "Genos", x["qui"])
    check("H. les bulles laissees libres : l'IA decide", autres and all(q == "Fille-Moustique" for q in autres), autres)
    check("H. l'IA a RECU le choix (champ « qui » de la bulle envoyee)", any('"qui": "Genos"' in t for t in ETAT["textes"]), "")
    check("H. consigne : regle 5 (attribution de l'utilisateur)", "attribuee par l'UTILISATEUR" in m.SYS)
    return len(KO) == k0


print("=== H. (S4, 1.27.0) qui parle choisi a la verification des bulles")
scenario_qui(charger())

print("=== E. mutations (doivent rendre le banc ROUGE)")''')

rep('''                       ("corrections ecrasees", [('neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})',
                                                  'pass')], scenario)):''',
    '''                       ("corrections ecrasees", [('neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})',
                                                  'pass')], scenario),
                       ("qui de Quang ignore (avant 1.27.0)", [('"qui": (nom_connu(distrib, b["qui_impose"]) if b.get("qui_impose")',
                                                                '"qui": (nom_connu(distrib, b["qui_impose"]) if False')], scenario_qui)):''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok")
