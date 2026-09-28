"""Banc test_nav_flot_ui.py -> v3.5.6 : en SERIE, ‹ › = series voisines (actifs s'il y en a une), glisser a gauche = serie
PRECEDENTE (avant : retour a toutes les series, qui reste sur « ← Séries »). Rejouable. Accepte aussi --page f.html."""
F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/test_nav_flot_ui.py"
s = open(F, encoding="utf-8", newline="").read()
if "nfSerieVoisine" in s:
    print("deja applique"); raise SystemExit
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep('''PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"''',
    '''_a = sys.argv[1:]; PAGE = None
if "--page" in _a:                                # v3.5.6 : tester une version avant de la servir
    _i = _a.index("--page"); PAGE = open(_a[_i + 1], encoding="utf-8").read(); del _a[_i:_i + 2]
PORT = _a[0] if _a else "8190"''')
rep('''            rt.continue_()
        pg.route("**/*", route)''', '''            if PAGE and r.method == "GET" and r.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
            rt.continue_()
        pg.route("**/*", route)''')
VOIS = '''pg.evaluate("() => ['nfPrev:' + (nfSerieVoisine(-1) ? 'actif' : 'grise'), 'nfSuiv:' + (nfSerieVoisine(1) ? 'actif' : 'grise')]")'''
rep('''        check("série, en haut : 5 boutons, ‹ › et ↑ GRISÉS (jamais masqués)", etat == ["nfRet:actif", "nfPrev:grise", "nfRefr:actif", "nfSuiv:grise", "nfHaut:grise"], etat)''',
    '''        vs = ''' + VOIS + '''                  # v3.5.6 : ‹ › = series voisines
        check("série, en haut : 5 boutons, ‹ › = séries voisines, ↑ GRISÉ (jamais masqués)", etat == ["nfRet:actif", vs[0], "nfRefr:actif", vs[1], "nfHaut:grise"], (etat, vs))''')
rep('''        check("série, descendu : ← ↻ ↑ actifs, ‹ › grisés", etat == ["nfRet:actif", "nfPrev:grise", "nfRefr:actif", "nfSuiv:grise", "nfHaut:actif"], etat)''',
    '''        check("série, descendu : ← ↻ ↑ actifs, ‹ › = séries voisines", etat == ["nfRet:actif", vs[0], "nfRefr:actif", vs[1], "nfHaut:actif"], (etat, vs))''')
rep('''            pg.evaluate(GLISSE, [-140]); pg.wait_for_timeout(1500)
            check("glissement à GAUCHE en série : retour à toutes les séries (le sens de « ← Séries »)", pg.evaluate("() => !LIB_SERIE"))''',
    '''            prec = pg.evaluate("() => (nfSerieVoisine(-1) || {}).slug || null")
            pg.evaluate(GLISSE, [-140]); pg.wait_for_timeout(1500)
            check("glissement à GAUCHE en série : série PRÉCÉDENTE (v3.5.6 ; « ← Séries » garde le retour)",
                  pg.evaluate("() => LIB_SERIE") == (prec or "one-punch-man"), (prec, pg.evaluate("() => LIB_SERIE")))''')
open(F, "w", encoding="utf-8", newline="").write(s)
print("ok")
