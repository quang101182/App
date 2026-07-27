# -*- coding: utf-8 -*-
"""La question de securite avant de couper le moteur local.

Quang, 27/07 : « il manque la pop-up de securite quand je veux arreter le moteur,
comme sur Generate Studio ». Generate Studio la pose avec un `confirm()` natif ;
ici c'est proscrit -- une boite native peut etre refusee par le navigateur et
renvoyer « non » sans rien afficher, ce qui a deja coute deux versions sur la
sequence (v1.20.1, v1.27.0). La question est donc posee A L'ECRAN.

Ce que le banc verifie, EN CONDITIONS REELLES (le moteur est vraiment coupe puis
rallume, rien n'est simule) :

  - cliquer « Local » moteur allume ne coupe RIEN tout de suite : ca demande ;
  - repondre « Laisser tourner » laisse le moteur EN VIE (le point vert reste,
    et surtout : le proxy n'a jamais recu l'ordre) ;
  - Echap et le clic hors de la boite valent « non » -- le defaut d'une question
    de securite doit etre « on ne fait rien » ;
  - repondre « Couper » coupe pour de vrai ;
  - DEMARRER ne pose aucune question : allumer ne detruit rien, et une question
    sans enjeu apprend a repondre oui sans lire.

Le moteur est rendu dans l'etat ou le banc l'a trouve.

Usage:
    python test_arret_moteur.py [--headed]
    python test_arret_moteur.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    # flush : ce banc coupe un moteur, il dure des minutes et peut mourir en
    # route. Une sortie tamponnee disparait avec le processus -- on perd alors
    # justement les lignes qui disent OU ca s'est arrete.
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


def etat(pg):
    """■ = moteur allume, ▶ = eteint (ce que l'utilisateur VOIT)."""
    return pg.eval_on_selector("#engPw", "el => el.textContent")


def question_ouverte(pg):
    return pg.eval_on_selector("#ask", "el => !el.hidden")


def repond(pg, bouton):
    """Clique « oui »/« non » SI la question est la.

    Sans ce garde-fou, un banc mute (ou une regression) meurt sur un timeout
    Playwright de 30 s au lieu d'annoncer « la question ne s'affiche pas » -- et
    il meurt APRES avoir coupe le moteur, qu'il laisse alors eteint derriere lui.
    Un banc qui touche a une ressource reelle doit savoir echouer proprement.
    """
    if not question_ouverte(pg):
        return False
    pg.click(bouton)
    pg.wait_for_timeout(400)
    return True


def attendre(pg, cible, tours=30):
    for _ in range(tours):
        pg.wait_for_timeout(3000)
        if etat(pg) == cible:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="l'arret ne demande plus rien : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, ordres = [], []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 700},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        # On ESPIONNE les ordres d'arret sans les bloquer : la seule preuve
        # qu'« annuler » annule vraiment, c'est que le proxy n'a rien recu.
        def voir(route):
            ordres.append(route.request.post_data or "{}")
            route.continue_()
        pg.route("**/shutdown", voir)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)

        depart = etat(pg)
        if depart != "■":
            print("   moteur eteint au depart : on l'allume pour pouvoir tester l'arret", flush=True)
            pg.click("#engComfy")
            # 4 min d'attente, pas 90 s : ComfyUI ne repond a /system_stats
            # qu'une fois SES MODELES charges. Un banc trop presse conclut
            # « il n'a pas demarre » sur un moteur qui demarrait tres bien.
            attendre(pg, "■", tours=80)
        if not verifie("moteur allume, pret pour le test", etat(pg) == "■",
                       "etat %s" % etat(pg)):
            print("   -> on s'arrete la : sans moteur allume, tester l'ARRET n'a pas de sens",
                  flush=True)
            br.close()
            return 1

        if args.muter:
            # MUTATION : on court-circuite la question -- elle repond « oui »
            # toute seule. L'arret marche toujours, il n'est juste plus protege.
            pg.evaluate("window.demander = async () => true;")

        # ---------- 1. cliquer ne coupe pas : ca demande ----------
        avant = len(ordres)
        pg.click("#engComfy")
        pg.wait_for_timeout(700)
        visible = question_ouverte(pg)
        verifie("cliquer « Local » pose une question au lieu de couper", visible is True)
        verifie("aucun ordre d'arret n'est encore parti", len(ordres) == avant,
                "%d ordre(s)" % (len(ordres) - avant))
        if visible:
            txt = pg.eval_on_selector("#ask", "el => el.textContent")
            verifie("elle dit ce qu'on perd (la carte, le temps de relance)",
                    "carte" in txt and ("30" in txt or "60" in txt), txt[:80])

        # ---------- 2. « Laisser tourner » ne coupe rien ----------
        repond(pg, "#askNo")
        pg.wait_for_timeout(1100)
        verifie("« Laisser tourner » : aucun ordre envoye au proxy",
                len(ordres) == avant, "%d ordre(s)" % (len(ordres) - avant))
        verifie("le moteur tourne toujours", etat(pg) == "■")

        # ---------- 3. Echap et clic dehors valent NON ----------
        pg.click("#engComfy"); pg.wait_for_timeout(600)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        verifie("Echap ferme la question sans rien couper",
                pg.eval_on_selector("#ask", "el => el.hidden") is True
                and len(ordres) == avant)
        pg.click("#engComfy"); pg.wait_for_timeout(600)
        pg.mouse.click(5, 5)            # hors de la boite
        pg.wait_for_timeout(500)
        verifie("cliquer hors de la boite vaut « non »",
                pg.eval_on_selector("#ask", "el => el.hidden") is True
                and len(ordres) == avant)

        # ---------- 4. « Couper » coupe pour de vrai ----------
        pg.click("#engComfy"); pg.wait_for_timeout(600)
        repond(pg, "#askYes")
        pg.wait_for_timeout(1200)
        verifie("« Couper » envoie bien l'ordre", len(ordres) > avant,
                "%d ordre(s)" % (len(ordres) - avant))
        verifie("le moteur s'eteint pour de vrai", attendre(pg, "▶"),
                "etat final %s" % etat(pg))

        # ---------- 5. demarrer ne demande RIEN ----------
        pg.click("#engComfy")
        pg.wait_for_timeout(800)
        verifie("demarrer ne pose aucune question (rien ne se perd)",
                pg.eval_on_selector("#ask", "el => el.hidden") is True)
        rallume = attendre(pg, "■")
        verifie("le moteur redemarre", rallume, "etat %s" % etat(pg))

        # --- on rend le moteur dans l'etat trouve ---
        if depart == "▶" and etat(pg) == "■":
            pg.click("#engComfy"); pg.wait_for_timeout(600)
            repond(pg, "#askYes")
            attendre(pg, "▶")
        verifie("le moteur est rendu dans l'etat trouve", etat(pg) == depart,
                "depart %s, fin %s" % (depart, etat(pg)))

        if depart == "■" and etat(pg) != "■":
            print("   le banc a laisse le moteur eteint : on le rallume", flush=True)
            pg.click("#engComfy")
            attendre(pg, "■", tours=80)
        verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
        br.close()

    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
