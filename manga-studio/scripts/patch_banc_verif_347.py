"""Banc test_verif_bulles_ui.py : ajoute le glisser dans les DEUX sens (v3.4.7). Rejouable."""
F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/test_verif_bulles_ui.py"
s = open(F, encoding="utf-8", newline="").read()
if "def glisser(" in s:
    print("deja applique"); raise SystemExit
NL = "\r\n" if "\r\n" in s else "\n"
a = '''            check("glisser la derniere pastille sur la 1re = elle passe en tete", ids1[0] == ids0[-1] and len(ids1) == len(ids0), (ids0, ids1))
'''
b = a + '''            def glisser(i, j, sur_texte=False):                                     # v3.4.7 : pastille i lachee sur la pastille j (ou sur son texte)
                P = pts(); a2 = P[i]
                b2 = pg.evaluate("(j) => { const it = dlvPage().items[j], r = $('dlvCadre').getBoundingClientRect(); return { x: r.left + (it.box.x + it.box.w / 2) * r.width, y: r.top + (it.box.y + it.box.h / 2) * r.height }; }", j) if sur_texte else P[j]
                pg.mouse.move(a2["x"], a2["y"]); pg.mouse.down()
                for k in range(1, 11): pg.mouse.move(a2["x"] + (b2["x"] - a2["x"]) * k / 10, a2["y"] + (b2["y"] - a2["y"]) * k / 10); pg.wait_for_timeout(15)
                pg.mouse.up(); pg.wait_for_timeout(300)
                return pg.evaluate("() => dlvPage().items.map(x => x.id)")
            if len(P0) >= 3:
                ids2 = glisser(0, 1)
                check("glisser VERS L'AVANT : 1 sur 2 = ils echangent", ids2[:2] == [ids1[1], ids1[0]] and ids2[2:] == ids1[2:], (ids1, ids2))
                ids3 = glisser(1, 0)
                check("glisser VERS L'ARRIERE : 2 sur 1 = ils echangent a nouveau", ids3 == ids1, (ids2, ids3))
                ids4 = glisser(0, 2)
                check("glisser 1 sur 3 = il prend la place n° 3", ids4 == [ids1[1], ids1[2], ids1[0]] + ids1[3:], (ids1, ids4))
                check("message = resultat (« 1 → n° 3 »)", "1 → n° 3" in pg.evaluate("() => $('dlvToast').textContent"), pg.evaluate("() => $('dlvToast').textContent"))
                ids5 = glisser(2, 0, sur_texte=True)
                check("lacher SUR LE TEXTE d'une bulle marche aussi (3 sur le texte de 1)", ids5 == ids1, (ids4, ids5))
                for _ in range(4): pg.evaluate("() => $('dlvAnnuler').click()"); pg.wait_for_timeout(120)
                check("↶ x4 = ordre d'avant les 4 glissers", pg.evaluate("() => dlvPage().items.map(x => x.id)") == ids1)
'''
a, b = a.replace("\n", NL), b.replace("\n", NL)
assert s.count(a) == 1
open(F, "w", encoding="utf-8", newline="").write(s.replace(a, b))
print("ok")
