"""manga-fetch 0.8.4 -> 0.8.5 (Quang 27/09 21h35 : « a chaque fois que je clique pour ouvrir une fenetre Edge, ca ouvre un nouvel
onglet MangaDex, ce que je ne veux pas ; je veux la fenetre exactement comme je l'avais laissee au niveau des onglets ») :
launch_edge() ne passe PLUS d'adresse (avant : https://mangadex.org/ a chaque ouverture) et le profil est regle pour
RESTAURER la derniere session (session.restore_on_startup = 1) ; la fermeture precedente est marquee propre (exit_type Normal)
pour que Edge restaure d'office au lieu de proposer « Restaurer les pages ? » apres une fermeture forcee. Vaut pour les deux
applications (meme fonction, profil / port par variables d'environnement). Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga-fetch/manga_fetch.py"
s = open(F, encoding="utf-8", newline="").read()
if "def profil_restaurer_session(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-084")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "0.8.4"', 'VERSION = "0.8.5"  # 0.8.5 (27/09) : la fenetre de capture rouvre SES onglets, plus d\'onglet MangaDex d\'office')

rep('''def launch_edge() -> int:''', '''def profil_restaurer_session(profil):
    """0.8.5 : Edge rouvre les onglets laisses la derniere fois (reglage « Continuer la ou vous en etiez »), et la fermeture
    precedente est marquee PROPRE -- sinon, apres une fermeture forcee (taskkill), Edge n'ouvre qu'un onglet vide et propose
    « Restaurer les pages ? ». A appeler navigateur FERME (Edge reecrit Preferences en quittant)."""
    f = os.path.join(profil, "Default", "Preferences")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    try:
        p = json.load(open(f, encoding="utf-8"))
    except Exception:
        p = {}
    # (session.restore_on_startup n'est PAS ecrit : Edge le protege et le remet -- mesure 27/09 ; c'est --restore-last-session
    # qui rouvre les onglets. Ici seulement la fermeture marquee propre.)
    p.setdefault("profile", {}).update(exit_type="Normal", exited_cleanly=True)
    json.dump(p, open(f, "w", encoding="utf-8"))
    # SAUVEGARDE des onglets avant tout lancement (Quang 21h38 : « il ne faut surtout pas me perdre les onglets ») :
    # Default/Sessions -> Default/_sessions_sauvegarde/<date> (les 5 dernieres gardees)
    import shutil as _sh, time as _t
    src = os.path.join(profil, "Default", "Sessions")
    if os.path.isdir(src) and os.listdir(src):
        dst_r = os.path.join(profil, "Default", "_sessions_sauvegarde")
        os.makedirs(dst_r, exist_ok=True)
        _sh.copytree(src, os.path.join(dst_r, _t.strftime("%Y%m%d-%H%M%S")), dirs_exist_ok=True)
        for vieux in sorted(os.listdir(dst_r))[:-5]:
            _sh.rmtree(os.path.join(dst_r, vieux), ignore_errors=True)


def edge_ouvert(port) -> bool:
    """0.8.5 : la fenetre de capture tourne-t-elle deja (CDP repond) ? Alors on ne touche ni au profil ni a ses onglets."""
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1.5).read()
        return True
    except Exception:
        return False


def launch_edge() -> int:''')

rep('''    os.makedirs(EDGE_PROFILE, exist_ok=True)''', '''    os.makedirs(EDGE_PROFILE, exist_ok=True)
    deja = edge_ouvert(EDGE_PORT)                        # 0.8.5 : deja ouverte -> Preferences intact (Edge le reecrit)
    if deja:                                             # 0.8.5 : deja ouverte -> la ramener devant, rien d'autre (ni fenetre, ni onglet)
        try:
            import urllib.request
            pages = [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % EDGE_PORT, timeout=3)) if t.get("type") == "page"]
            if pages:
                urllib.request.urlopen("http://127.0.0.1:%d/json/activate/%s" % (EDGE_PORT, pages[0]["id"]), timeout=3).read()
        except Exception:
            pass
        print("Fenêtre dédiée déjà ouverte : ramenée devant (CDP port %d), onglets inchangés." % EDGE_PORT)
        return 0''')
rep('''    if sans_synchro:
        profil_sans_synchro(EDGE_PROFILE)''', '''    if sans_synchro and not deja:
        profil_sans_synchro(EDGE_PROFILE)
    if not deja:
        profil_restaurer_session(EDGE_PROFILE)''')
rep('''                      "--window-position=%d,%d" % (place["left"], place["top"]),
                      "https://mangadex.org/"])''', '''                      "--window-position=%d,%d" % (place["left"], place["top"]),
                      "--restore-last-session"])   # 0.8.5 : AUCUNE adresse + reprise de la session -> SES onglets
                      # (le reglage « session.restore_on_startup » ecrit dans Preferences est PROTEGE par Edge et remis : mesure)''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 0.8.5")
