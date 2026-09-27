"""dialogues.py 1.26.0 -> 1.27.0 (S4, maquette_qui_parle_v1 validee par Quang le 27/09 20h38) : « qui parle » choisi par Quang
PENDANT la verification des bulles (champ « qui » d'une entree de bulles_verifiees.json) -> transmis a l'IA comme FAIT impose
(elle s'en sert aussi d'indice pour les bulles voisines) et FORCE dans la replique. Les bulles laissees libres : l'IA decide,
comme avant. Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/dialogues.py"
s = open(F, encoding="utf-8", newline="").read()
if "qui_impose" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-1260")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "1.26.0"  # 1.26.0 (27/09)',
    'VERSION = "1.27.0"  # 1.27.0 (27/09, S4) : « qui parle » choisi par Quang a la verification des bulles = impose a l\'IA et a la replique ;  # 1.26.0 (27/09)')

rep('''4. Pour chaque NOUVEAU personnage : genre (homme|femme|?), age apparent, une phrase sur sa facon de parler, et la voix la plus
   juste dans le CATALOGUE ci-dessous (id exact), differente de celles deja prises si possible.''',
    '''4. Pour chaque NOUVEAU personnage : genre (homme|femme|?), age apparent, une phrase sur sa facon de parler, et la voix la plus
   juste dans le CATALOGUE ci-dessous (id exact), differente de celles deja prises si possible.
5. Une bulle qui arrive AVEC un champ "qui" a ete attribuee par l'UTILISATEUR, qui a regarde la page : rends EXACTEMENT ce nom
   dans "qui" (ne le discute pas). Sers-toi de ces attributions comme de FAITS pour les autres bulles (qui repond a qui, qui
   est dans quelle case, alternance d'une conversation).''')

# la verification porte « qui » -> la bulle le porte
rep('''        if b is not None and id(b) not in rang:
            rang[id(b)] = i''',
    '''        if b is not None and id(b) not in rang:
            rang[id(b)] = i
            if str(r.get("qui") or "").strip():                             # 1.27.0 (S4) : choisi par Quang
                b["qui_impose"] = str(r["qui"]).strip()[:40]''')

# l'IA le recoit
rep('''json.dumps([{"id": b["id"], "type": b["type"], "texte": b["trad"],
                                                                "pos": [round(b["box"][k], 3) for k in ("x", "y", "w", "h")]}
                                                               for b in p["_bulles"]], ensure_ascii=False))})''',
    '''json.dumps([dict({"id": b["id"], "type": b["type"], "texte": b["trad"],
                                                                     "pos": [round(b["box"][k], 3) for k in ("x", "y", "w", "h")]},
                                                                    **({"qui": b["qui_impose"]} if b.get("qui_impose") else {}))   # 1.27.0 (S4)
                                                               for b in p["_bulles"]], ensure_ascii=False))})''')

# la replique le garde, quoi que l'IA ait repondu
rep('''                    "qui": nom_connu(distrib, x.get("qui")) if x else "inconnu",''',
    '''                    "qui": (nom_connu(distrib, b["qui_impose"]) if b.get("qui_impose")                 # 1.27.0 (S4) : Quang d'abord
                            else nom_connu(distrib, x.get("qui")) if x else "inconnu"),''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 1.27.0")
