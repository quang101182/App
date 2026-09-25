# -*- coding: utf-8 -*-
"""Banc v2.50.0 : BILAN PERSISTANT d'une capture (proxy, _mf_bilan_ecrire). HORS LIGNE : journaux FICTIFS dans un dossier
temporaire, aucun navigateur, aucune ecriture dans les vraies donnees.
Origine : le 25/09 a 02h57, une serie de 40 chapitres s'est arretee au 22e (verification Cloudflare au ch.23) sans aucun
signal -- le bilan ne vivait qu'en memoire du serveur. Cas : serie tenue (« : fait », « depasse la borne »), arret au
milieu, 1er chapitre en echec, plus de lien suivant, capture seule OK / en echec ; reprise TOUJOURS au debut du chapitre
en echec, nombre restant juste, adresse SANS jeton Cloudflare.
Usage : python test_capture_bilan.py
"""
import importlib.util, json, os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
COMFY = os.path.expanduser(r"~\Documents\ComfyUI")
sys.path.insert(0, COMFY)
spec = importlib.util.spec_from_file_location("proxy_banc_bilan", os.path.join(COMFY, "_studio_llm_proxy.py"))
px = importlib.util.module_from_spec(spec); spec.loader.exec_module(px)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


D = tempfile.mkdtemp(prefix="banc_bilan_")
px.MANGA_SOURCES = D
px.MF_RUNLOG, px.MF_EVENTS = os.path.join(D, "run.log"), os.path.join(D, "events.log")


class Fini:
    def __init__(self, code): self.code = code
    def wait(self): return self.code


def cas(code, serie, evts="", suite=0, jusqua="", chapitre="1", tab="https://site.test/serie/chapter-1/"):
    open(px.MF_RUNLOG, "w", encoding="utf-8").write("=== debut ===\n" + (serie + "\n" if serie else ""))
    open(px.MF_EVENTS, "w", encoding="utf-8").write(evts)
    px._mf_bilan_ecrire(Fini(code), {"offset": 0, "debut": 1.0, "titre": "Serie Banc", "chapitre": chapitre, "suite": suite,
                                     "jusqua": jusqua, "tab": tab, "page1": False, "entiers": True})
    return px.manga_capture_derniere()


EV = ("2026-09-25 02:55:33 [série] chapitre suivant 23 onglet=https://site.test/serie/chapter-23/?__cf_chl_rt_tk=ABC.def\n"
      "2026-09-25 02:57:48 [échec] ÉCHEC : capture tronquée\n")
print("=== 1. arrêt au MILIEU d'une série « 39 suivants » (le cas du 25/09)")
j = cas(2, "SÉRIE : 22 chapitre(s) : " + ", ".join(str(i) for i in range(1, 23)) + " — arrêt : le chapitre 23 a échoué (code 2)", EV, suite=39)
check("but NON atteint (tenu = faux)", j.get("tenu") is False, j.get("tenu"))
check("22 chapitres faits, arrêt lu", len(j["faits"]) == 22 and "23 a échoué" in j["arret"], (len(j["faits"]), j["arret"]))
r = j.get("reprise") or {}
check("reprise au DÉBUT du ch. 23", r.get("chapitre") == "23", r)
check("reste 17 suivants (23 → 40 = 18 chapitres)", r.get("suite") == 17 and "jusqua" not in r, r)
check("adresse de reprise SANS jeton Cloudflare", r.get("url") == "https://site.test/serie/chapter-23/", r.get("url"))
check("options gardées (sans intermédiaires)", r.get("entiers") is True and r.get("page1") is False)
print("=== 2. même arrêt, série « jusqu'au 40 »")
r = cas(2, "SÉRIE : 22 chapitre(s) : 1, 2 — arrêt : le chapitre 23 a échoué (code 2)", EV, jusqua="40").get("reprise") or {}
check("reprise ch. 23 jusqu'au 40", r.get("chapitre") == "23" and r.get("jusqua") == "40" and "suite" not in r, r)
print("=== 3. séries TENUES")
j = cas(0, "SÉRIE : 5 chapitre(s) : 1, 2, 3, 4, 5 — arrêt : 4 chapitre(s) suivant(s) demandé(s) : fait", suite=4)
check("« : fait » → tenu, rien à reprendre", j["tenu"] is True and j["reprise"] is None, (j["tenu"], j["reprise"]))
j = cas(0, "SÉRIE : 3 chapitre(s) : 1, 2, 3 — arrêt : le chapitre suivant (4) dépasse la borne demandée (3)", jusqua="3")
check("« dépasse la borne » (jusqu'au) → tenu", j["tenu"] is True and j["reprise"] is None)
print("=== 4. séries NON tenues sans chapitre en échec")
j = cas(0, "SÉRIE : 3 chapitre(s) : 1, 2, 3 — arrêt : aucun lien vers le chapitre suivant", suite=9)
check("plus de lien suivant → NON tenu (alerte), pas de reprise possible", j["tenu"] is False and j["reprise"] is None, j)
j = cas(2, "SÉRIE : arrêt — le premier chapitre a échoué.", suite=9, chapitre="7", tab="https://site.test/serie/chapter-7/?__cf_chl_tk=Z")
r = j.get("reprise") or {}
check("1er chapitre en échec → NON tenu, reprise au ch. 7 (même onglet, sans jeton)", j["tenu"] is False and r.get("chapitre") == "7"
      and r.get("url") == "https://site.test/serie/chapter-7/" and r.get("suite") == 9, r)
print("=== 5. capture d'UN chapitre")
j = cas(0, "", chapitre="12")
check("réussie → tenu", j["tenu"] is True and j["reprise"] is None)
j = cas(3, "", chapitre="12")
check("réussie avec avertissements (code 3) → tenu", j["tenu"] is True)
j = cas(2, "", chapitre="12", tab="https://site.test/serie/chapter-12/")
check("en échec → NON tenu, reprise ce chapitre, cet onglet", j["tenu"] is False and (j["reprise"] or {}).get("chapitre") == "12"
      and j["reprise"]["url"] == "https://site.test/serie/chapter-12/", j["reprise"])
print("=== 6. robustesse")
check("fichier atomique (pas de .tmp laissé)", not os.path.exists(os.path.join(D, "_capture_derniere.json.tmp")))
os.remove(os.path.join(D, "_capture_derniere.json"))
check("aucun bilan → {}", px.manga_capture_derniere() == {})
print("=== 7. avancement dans l'activité (v2.53.0 : plus de « calcul du temps restant… » sans fin)")
f = px._capture_avancement
b0 = {"titre": "T", "chapitre": "31", "chapitre_depart": "23", "pages": 2, "duree_s": 1600.0}
x = f(dict(b0, jusqua="40", suite=0, dossiers=["d"] * 8))
check("série jusqu'au 40 depuis 23 : 8/18 chapitres, étape « ch. 31 »", (x["fait"], x["total"], x.get("etape")) == (8, 18, "ch. 31"), x)
check("temps restant = 1600 s / 8 × 10 = 2000 s", x.get("reste_s") == 2000, x.get("reste_s"))
x = f(dict(b0, jusqua="", suite=17, dossiers=[]))
check("série « 17 suivants », rien de fini : 0/18, pas de temps inventé", (x["fait"], x["total"]) == (0, 18) and "reste_s" not in x, x)
x = f(dict(b0, jusqua="", suite=0, dossiers=[]))
check("un seul chapitre : compte de pages, total inconnu", x["fait"] == 2 and x["total"] is None, x)
x = f(dict(b0, jusqua="abc", suite=0, dossiers=[]))
check("valeur illisible : pas de plantage", x["type"] == "capture")
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
