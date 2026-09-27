"""app 3.4.5 -> 3.4.6 : verification des bulles -- une bulle ENTOUREE deja traduite (dialogues.py >= 1.22.0 l'ecrit dans
traduction.json) n'apparait plus DEUX fois (pastille 2 cachee sous une pastille 13 au meme endroit). Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_346.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.4.6"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n"

def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)

rep("<title>Manga Studio v3.4.5</title>", "<title>Manga Studio v3.4.6</title>")
rep('id="verBadge">v3.4.5</span>', 'id="verBadge">v3.4.6</span>')
rep('const VERSION = "3.4.5";', 'const VERSION = "3.4.6";   // v3.4.6 : verification des bulles -- une bulle entouree deja traduite n apparait plus en double ')

rep('''  const pris = new Set(), trouve = r => { let best = null, bi = 0; bl.forEach(b => { if (pris.has(b)) return; const x = dlvIou(r.box, b.box); if (x > bi){ bi = x; best = b; } }); return bi >= 0.5 ? best : null; };
  const out = [];
  (v.ordre || []).forEach(r => { const aj = (v.ajouts || []).find(z => z.id === r.id && dlvIou(z.box, r.box) >= 0.5);
    if (aj) out.push({ id: aj.id, box: aj.box, ajout: true }); else { const b = trouve(r); if (b){ pris.add(b); out.push(b); } } });''',
'''  const pris = new Set(), trouve = r => { let best = null, bi = 0; bl.forEach(b => { if (pris.has(b)) return; const x = dlvIou(r.box, b.box); if (x > bi){ bi = x; best = b; } }); return bi >= 0.5 ? best : null; };
  // v3.4.6 : une bulle entouree, une fois traduite, figure AUSSI dans la traduction (meme n°, meme zone) -> c'est la meme : on ne
  // la montre qu'une fois (avant : pastille 2 de l'ajout cachee sous une pastille 13 au meme endroit, Noritaka p. 6)
  const absorber = z => bl.forEach(b => { if (!pris.has(b) && (b.id === z.id || dlvIou(b.box, z.box) >= 0.5)) pris.add(b); });
  const out = [];
  (v.ordre || []).forEach(r => { const aj = (v.ajouts || []).find(z => z.id === r.id && dlvIou(z.box, r.box) >= 0.5);
    if (aj){ absorber(aj); out.push({ id: aj.id, box: aj.box, ajout: true }); } else { const b = trouve(r); if (b){ pris.add(b); out.push(b); } } });
  (v.ajouts || []).forEach(absorber);''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
shutil.copy2(F, F + ".bak-v3450")
shutil.copy2(TMP, F)
print("ok v3.4.6")
