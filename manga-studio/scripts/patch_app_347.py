"""app 3.4.6 -> 3.4.7 : verification des bulles -- glisser une pastille marche dans les DEUX sens (elle prend la PLACE de la
cible : 1 sur 2 = 2 1 ; avant, vers l'avant elle se posait juste AVANT la cible = rien ne bougeait) ; la cible est cherchee
la ou les pastilles sont VRAIMENT dessinees (depuis v3.4.5 a cote du texte) OU dans la zone de texte d'une bulle ; le message
dit le resultat (« 1 → n° 2 »). Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_347.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.4.7"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n"

def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)

rep("<title>Manga Studio v3.4.6</title>", "<title>Manga Studio v3.4.7</title>")
rep('id="verBadge">v3.4.6</span>', 'id="verBadge">v3.4.7</span>')
rep('const VERSION = "3.4.6";', 'const VERSION = "3.4.7";   // v3.4.7 : verification des bulles -- glisser une pastille marche dans les deux sens (elle prend la place de la cible) ')

# une SEULE regle de placement des pastilles, partagee par le dessin et par le glisser
rep('''function dlvDessiner(extra){''', '''function dlvPastille(box, W, H, R){             // v3.4.7 : centre (px image) de la pastille d'une bulle -- dessin ET glisser
  const bx = box.x * W, by = box.y * H, bw = box.w * W;
  let cx = bx + bw + R * 0.85; if (cx > W - R) cx = bx - R * 0.85; if (cx < R) cx = Math.min(W - R, bx + bw + R * 0.85);
  return { cx, cy: Math.max(R, Math.min(H - R, by - R * 0.15)) };
}
function dlvDessiner(extra){''')
rep('''    let cx = bx + bw + R * 0.85; if (cx > W - R) cx = bx - R * 0.85; if (cx < R) cx = Math.min(W - R, bx + bw + R * 0.85);
    const cy = Math.max(R, Math.min(H - R, by - R * 0.15));''',
'''    const { cx, cy } = dlvPastille(x.box, W, H, R);''')

rep('''      const img = $("dlvImg"), R = (+$("dlvSvg").dataset.r || 20) / (img.naturalWidth || 1000);
      let cible = -1, dm = Infinity;
      p.items.forEach((it, k) => { if (k === x.k) return; const cx = it.box.x + it.box.w - R * 0.4, cy = (it.box.y * (img.naturalHeight || 1400) / (img.naturalWidth || 1000)) + R * 0.4;
        const d = Math.hypot(cx - f.x, cy - f.y * (img.naturalHeight || 1400) / (img.naturalWidth || 1000)); if (d < dm){ dm = d; cible = k; } });
      if (cible < 0 || dm > R * 3){ dlvDessiner(); return; }
      dlvSnap(); const [it] = p.items.splice(x.k, 1); const c2 = cible > x.k ? cible - 1 : cible; p.items.splice(c2, 0, it); p.modif++;
      dlvDessiner(); dlvBas(); return dlvToast("↕ ordre changé");''',
'''      // v3.4.7 : cible = la pastille la plus proche du doigt (la ou elle est DESSINEE), sinon la bulle dont la zone de texte
      // contient le doigt ; la pastille glissee PREND LA PLACE de la cible, dans les deux sens (1 sur 2 -> 2 1 ; 3 sur 1 -> 3 1 2)
      const img = $("dlvImg"), W = img.naturalWidth || 1000, H = img.naturalHeight || 1400, R = +$("dlvSvg").dataset.r || 20;
      const fx = f.x * W, fy = f.y * H, num = it => it.exclu ? "✕" : String(p.items.filter(y => !y.exclu).indexOf(it) + 1);
      let cible = -1, dm = Infinity;
      p.items.forEach((it, k) => { if (k === x.k) return; const c = dlvPastille(it.box, W, H, R), d = Math.hypot(c.cx - fx, c.cy - fy); if (d < dm){ dm = d; cible = k; } });
      if (dm > R * 2.2){ cible = -1;
        p.items.forEach((it, k) => { if (k !== x.k && cible < 0 && fx >= it.box.x * W - R * 0.5 && fx <= (it.box.x + it.box.w) * W + R * 0.5
                                         && fy >= it.box.y * H - R * 0.5 && fy <= (it.box.y + it.box.h) * H + R * 0.5) cible = k; }); }
      if (cible < 0){ dlvDessiner(); return dlvToast("lâche la pastille sur un autre numéro"); }
      const avant = num(p.items[x.k]);
      dlvSnap(); const [it] = p.items.splice(x.k, 1); p.items.splice(cible, 0, it); p.modif++;
      dlvDessiner(); dlvBas(); return dlvToast("↕ " + avant + " → n° " + num(it));''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
shutil.copy2(F, F + ".bak-v3460")
shutil.copy2(TMP, F)
print("ok v3.4.7")
