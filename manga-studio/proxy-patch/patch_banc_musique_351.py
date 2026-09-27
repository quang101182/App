"""Banc test_musique_dialogues_ui.py -> v3.5.1 : musique des Dialogues = reglage PROPRE (plus celui de la narration) + interrupteur
« Musique de fond » du bloc (visible, coupe la musique de la video demandee, la remet). Rejouable."""
F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/test_musique_dialogues_ui.py"
s = open(F, encoding="utf-8", newline="").read()
if "dlgMus" in s:
    print("deja applique"); raise SystemExit
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep("""localStorage.setItem('manga_mus_on','1'); localStorage.setItem('manga_mus_vol','60');""",
    """localStorage.setItem('manga_mus_on','1'); localStorage.setItem('manga_dlg_mus_on','1'); localStorage.setItem('manga_mus_vol','60');""")
rep('''    check("interrupteur coupe : la musique s'eteint", pg.evaluate("() => MP.g < 0.01 && !MUS_ON"), pg.evaluate("() => MP.g"))
    check("meme reglage que la narration (lecMusOn suit)", pg.evaluate("() => $('lecMusOn').checked === MUS_ON"))''',
    '''    check("interrupteur coupe : la musique s'eteint", pg.evaluate("() => MP.g < 0.01 && !DLG_MUS_ON"), pg.evaluate("() => MP.g"))
    check("v3.5.1 : reglage PROPRE aux Dialogues -- la narration garde le sien, le bloc suit", pg.evaluate("() => MUS_ON === true && $('lecMusOn').checked && !$('dlgMus').checked"),
          pg.evaluate("() => ({ MUS_ON, DLG_MUS_ON, lec: $('lecMusOn').checked, bloc: $('dlgMus').checked })"))''')
rep('''    posts.clear()
    pg.evaluate("() => { $('dlgVid').dataset.dpl = ''; DLG.plan = Object.assign({}, DLG.plan, { repliques: {} }); $('dlgVid').disabled = false; $('dlgVid').click(); }"); pg.wait_for_timeout(1500)''',
    '''    b_ = pg.evaluate("() => { const i = $('dlgMus'); return { vis: !!(i && i.closest('label').offsetParent), on: i && i.checked, dis: i && i.disabled, t: i && i.closest('label').textContent }; }")
    check("v3.5.1 : bloc Dialogues -- interrupteur « Musique de fond » visible et actif", b_["vis"] and b_["on"] and not b_["dis"] and "Musique" in (b_["t"] or ""), b_)
    pg.evaluate("() => $('dlgMus').click()"); pg.wait_for_timeout(400)
    posts.clear()
    pg.evaluate("() => { $('dlgVid').dataset.dpl = ''; DLG.plan = Object.assign({}, DLG.plan, { repliques: {} }); $('dlgVid').disabled = false; $('dlgVid').click(); }"); pg.wait_for_timeout(1500)
    env0 = [json.loads(x[1]) for x in posts if x[0] == "dialogues_lancer"]
    check("v3.5.1 : bloc coupe -> la video est demandee SANS musique", bool(env0) and not env0[-1].get("musique"), env0[-1:])
    check("v3.5.1 : bloc coupe -> reglages du lecteur suivent, narration intacte", pg.evaluate("() => !DLG_MUS_ON && !$('dllMus').checked && MUS_ON"))
    pg.evaluate("() => $('dlgMus').click()"); pg.wait_for_timeout(400)
    posts.clear()
    pg.evaluate("() => { $('dlgVid').dataset.dpl = ''; DLG.plan = Object.assign({}, DLG.plan, { repliques: {} }); $('dlgVid').disabled = false; $('dlgVid').click(); }"); pg.wait_for_timeout(1500)''')
open(F, "w", encoding="utf-8", newline="").write(s)
print("ok")
