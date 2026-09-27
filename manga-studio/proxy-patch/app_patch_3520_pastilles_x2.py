"""app 3.5.1 -> 3.5.2 (Quang 21h03 : « sur smartphone […] doubler la taille des bulles, ca fait un peu petit ») : verification des
bulles -- pastilles (numeros + personnages) DOUBLEES sur un ecran de moins de 800 px (telephone, Fold ferme ET ouvert). Tout
suit le meme rayon (dessin, glisser, cible, toucher). Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_352.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.2"' in s:
    print("deja applique"); sys.exit(0)


def rep(a, b):
    global s
    for nl in ("\r\n", "\n", "\r\r\n"):
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        if s.count(a2) == 1:
            s = s.replace(a2, b2); return
    raise SystemExit("ancre introuvable : " + a[:80])


rep("<title>Manga Studio v3.5.1</title>", "<title>Manga Studio v3.5.2</title>")
rep('id="verBadge">v3.5.1</span>', 'id="verBadge">v3.5.2</span>')
rep('const VERSION = "3.5.1";', 'const VERSION = "3.5.2";   // v3.5.2 : verification des bulles -- pastilles doublees sur telephone (< 800 px) ')
rep('''  const img = $("dlvImg"), W = img.naturalWidth || 1000, H = img.naturalHeight || 1400, R = Math.max(W, H) * 0.021, svg = $("dlvSvg");''',
    '''  const img = $("dlvImg"), W = img.naturalWidth || 1000, H = img.naturalHeight || 1400, svg = $("dlvSvg");
  const R = Math.max(W, H) * 0.021 * (window.innerWidth < 800 ? 2 : 1);      // v3.5.2 : x2 sur telephone (Quang : « un peu petit »)''')

# numero un peu plus ecarte du texte (le bord du cercle ne mord plus la zone)
rep('''  let cx = bx + bw + R * 0.85; if (cx > W - R) cx = bx - R * 0.85; if (cx < R) cx = Math.min(W - R, bx + bw + R * 0.85);''',
    '''  let cx = bx + bw + R * 1.05; if (cx > W - R) cx = bx - R * 1.05; if (cx < R) cx = Math.min(W - R, bx + bw + R * 1.05);   // v3.5.2 : hors du texte''')
# pastille-personnage du cote OPPOSE a la bulle (jamais sur son texte) ; pas de place -> au-dessus, sinon en dessous
rep('''    if (qn){ const moi = !!x.qui, col = dlgCouleur(qn); let qx = cx - R * 2.05; if (qx < R) qx = cx + R * 2.05;''',
    '''    if (qn){ const moi = !!x.qui, col = dlgCouleur(qn), cote = cx >= bx + bw / 2 ? 1 : -1;               // v3.5.2 : cote oppose a la bulle
      let qx = cx + cote * R * 2.05, qy = cy;
      if (qx < R || qx > W - R){ qx = cx; qy = cy - R * 2.05 >= R ? cy - R * 2.05 : cy + R * 2.05; }''')
rep('''+ '" y="' + (cy + R * 0.34) + '" text-anchor="middle" font-size="' + R * 0.95 + '" font-weight="800" font-family="system-ui,sans-serif" fill="#111">' + esc(dlvInit(qn))''',
    '''+ '" y="' + (qy + R * 0.34) + '" text-anchor="middle" font-size="' + R * 0.95 + '" font-weight="800" font-family="system-ui,sans-serif" fill="#111">' + esc(dlvInit(qn))''')
rep('''<g opacity="' + (moi ? 1 : 0.62) + '" pointer-events="none"><circle cx="' + qx + '" cy="' + cy + '" r="' + R * 0.92''',
    '''<g opacity="' + (moi ? 1 : 0.62) + '" pointer-events="none"><circle cx="' + qx + '" cy="' + qy + '" r="' + R * 0.92''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3510")
shutil.copy2(TMP, F)
print("ok v3.5.2")
