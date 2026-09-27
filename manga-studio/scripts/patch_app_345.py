"""app 3.4.4 -> 3.4.5 : (1) « Preparer » ne reste plus rouge a tort : la bulle entouree est reconnue comme dialogues.py 1.26.0
la reconnait (meme zone OU bulle connue dans le trace) ; (2) les numeros de la verification des bulles sont poses A COTE
du texte (coin haut-droit, hors des lettres), plus dessus. Ecrit sur une COPIE, puis node --check, puis remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_345.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.4.5"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n"

def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)

# version aux 3 endroits
rep("<title>Manga Studio v3.4.4</title>", "<title>Manga Studio v3.4.5</title>")
rep('id="verBadge">v3.4.4</span>', 'id="verBadge">v3.4.5</span>')
rep('const VERSION = "3.4.4";', 'const VERSION = "3.4.5";   // v3.4.5 : « Preparer » ne reste plus rouge a tort (bulle entouree reconnue) ; numeros des bulles poses a cote du texte ')

# (1) dplDepasse : meme appariement que dialogues.py 1.26.0 (appliquer_verif / apparier / meme_zone)
rep('''  Object.keys(vf).map(Number).filter(n => n >= a && n <= b).forEach(n => {
    const v = vf[n] || {}, reps = (doc.repliques || []).filter(x => x.page === n).sort((x, y) => (x.ordre ?? x.id) - (y.ordre ?? y.id));
    const ids = reps.map(x => x.id), dans = new Set(ids), ov = (v.ordre || []).map(r => r.id), ovs = new Set(ov);
    const sv = ov.filter(i => dans.has(i)), sd = ids.filter(i => ovs.has(i));
    if (sv.join() !== sd.join() || (v.exclues || []).some(r => dans.has(r.id)) || (v.ajouts || []).some(r => !dans.has(r.id))) out.push(n);
  });''',
'''  // v3.4.5 : MEME appariement que dialogues.py (>= 1.26.0) -- une bulle entouree qui recouvre une bulle deja lue EST cette bulle.
  // Avant : comparaison des seuls n° -> la bulle entouree (n° 900) « manquait » toujours et « Preparer » restait rouge a vie.
  const couvre = (g, p) => { const x1 = Math.max(g.x, p.x), y1 = Math.max(g.y, p.y), x2 = Math.min(g.x + g.w, p.x + p.w), y2 = Math.min(g.y + g.h, p.y + p.h), s = p.w * p.h;
    return s > 0 ? Math.max(0, x2 - x1) * Math.max(0, y2 - y1) / s : 0; };
  const meme = (z, r) => r.box && z.box && (dlvIou(z.box, r.box) >= 0.5 || couvre(z.box, r.box) >= 0.8);
  const trouve = (r, reps) => { let best = null, bi = 0; reps.forEach(x => { const q = x.box && r.box ? dlvIou(r.box, x.box) : 0; if (q > bi){ bi = q; best = x; } });
    if (bi >= 0.5) return best;
    const same = reps.find(x => x.id === r.id); if (same && same.box && r.box && dlvIou(r.box, same.box) >= 0.2) return same;
    const d = reps.filter(x => x.box && r.box).map(x => [couvre(r.box, x.box), x]).sort((u, w) => w[0] - u[0]);
    return d.length && d[0][0] >= 0.8 ? d[0][1] : null; };
  Object.keys(vf).map(Number).filter(n => n >= a && n <= b).forEach(n => {
    const v = vf[n] || {}, reps = (doc.repliques || []).filter(x => x.page === n).sort((x, y) => (x.ordre ?? x.id) - (y.ordre ?? y.id));
    const vus = [];
    (v.ordre || []).forEach(r => { const x = reps.find(y => y.id === r.id && meme(r, y)) || trouve(r, reps); if (x && !vus.includes(x)) vus.push(x); });
    const sd = reps.filter(x => vus.includes(x));
    if (vus.map(x => x.cle).join() !== sd.map(x => x.cle).join() || (v.exclues || []).some(r => { const x = trouve(r, reps); return x && !vus.includes(x); })
        || (v.ajouts || []).some(z => !reps.some(x => x.id === z.id || meme(z, x)))) out.push(n);
  });''')

# (2) pastille : a cote du texte (coin haut-droit, a l'exterieur), ramenee dans l'image si elle deborde
rep('''    const cx = (x.box.x + x.box.w) * W - R * 0.4, cy = x.box.y * H + R * 0.4, num = x.exclu ? "✕" : String(++n);''',
'''    // v3.4.5 : pastille A COTE du texte (coin haut-droit, dehors), plus sur les lettres ; a gauche si le bord droit manque
    const bx = x.box.x * W, by = x.box.y * H, bw = x.box.w * W, bh = x.box.h * H, num = x.exclu ? "✕" : String(++n);
    let cx = bx + bw + R * 0.85; if (cx > W - R) cx = bx - R * 0.85; if (cx < R) cx = Math.min(W - R, bx + bw + R * 0.85);
    const cy = Math.max(R, Math.min(H - R, by - R * 0.15));
    if (!x.ajout) h += '<rect x="' + bx + '" y="' + by + '" width="' + bw + '" height="' + bh + '" rx="' + R * 0.2 + '" fill="none" stroke="' + (x.exclu ? "#5a6070" : "#3fc7a8") + '" stroke-width="' + R * 0.1 + '" opacity=".85" pointer-events="none"/>';''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
shutil.copy2(F, F + ".bak-v3440")
shutil.copy2(TMP, F)
print("ok v3.4.5")
