"""app 3.5.2 -> 3.5.3 (Quang 21h10, capture : « tu arrives a les placer sur une seule ligne, les trois, meme sur smartphone ») :
options du bloc Dialogues -- « Tons », « Encarts », « Musique » sur UNE ligne (3 colonnes), libelles courts avec icone, le detail
passe dans l'info-bulle (title). « Enchainer les voix » garde sa ligne entiere. Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_353.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.3"' in s:
    print("deja applique"); sys.exit(0)


def rep(a, b):
    global s
    for nl in ("\r\n", "\n", "\r\r\n"):
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        if s.count(a2) == 1:
            s = s.replace(a2, b2); return
    raise SystemExit("ancre introuvable : " + a[:80])


rep("<title>Manga Studio v3.5.2</title>", "<title>Manga Studio v3.5.3</title>")
rep('id="verBadge">v3.5.2</span>', 'id="verBadge">v3.5.3</span>')
rep('const VERSION = "3.5.2";', 'const VERSION = "3.5.3";   // v3.5.3 : options des Dialogues (tons, encarts, musique) sur une seule ligne ')

rep('''#dlgBox.cl-ouv .dlg-opts{display:grid;grid-template-columns:1fr 1fr;gap:0 14px;margin:2px 0 4px;border-top:1px solid var(--line)}   /* v3.1.1 : ouvert seulement ; 2 par ligne */''',
    '''#dlgBox.cl-ouv .dlg-opts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 10px;margin:2px 0 4px;border-top:1px solid var(--line)}   /* v3.5.3 : 3 sur UNE ligne (Quang) */
#dlgBox .dlg-opts label>span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media (max-width:440px){ #dlgBox.cl-ouv .dlg-opts label:not(#dlgEnchL){flex-direction:column;gap:5px;justify-content:center;text-align:center;padding:6px 0}
  #dlgBox.cl-ouv .dlg-opts label:not(#dlgEnchL)>span{flex:none;max-width:100%} }   /* etroit : libelle AU-DESSUS de l'interrupteur, toujours 1 ligne */''')

rep('''  $("dlgNarr").closest("label").querySelector("span").innerHTML = 'Lire les encarts <small class="muted" style="display:block;font-size:11.5px">voix du narrateur</small>';''',
    '''  $("dlgNarr").closest("label").querySelector("span").innerHTML = "📜 Encarts";                              // v3.5.3 : court, detail en info-bulle
  $("dlgNarr").closest("label").title = "lire les encarts de récit (voix du narrateur)";
  $("dlgTons").closest("label").querySelector("span").innerHTML = "🎭 Tons";
  $("dlgTons").closest("label").title = "un ton d'acteur par réplique (colère, murmure…)";
  dlgMusBloc();''')

rep('''  if (sp) sp.innerHTML = 'Musique de fond <small class="muted" style="display:block;font-size:11.5px">' + (ok ? "celle de la série, sous les voix" : "aucun morceau pour cette série") + "</small>";''',
    '''  if (sp) sp.innerHTML = "🎵 Musique";                                          // v3.5.3 : court, detail en info-bulle
  i.closest("label").title = ok ? "musique de fond de la série, baissée sous les voix (lecteur et vidéo des Dialogues)" : "aucun morceau pour cette série";''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3520")
shutil.copy2(TMP, F)
print("ok v3.5.3")
