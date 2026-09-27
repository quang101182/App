# -*- coding: utf-8 -*-
"""v2.82.2 (27/09, D12 -- Quang 02h26 « un meme homme nomme 4 fois » ; 02h28 « que la solution devienne de plus en plus fiable
dans la globalite ») : les DOUBLONS PROBABLES de personnages (dialogues.py >= 1.11.0 les detecte, jamais ne les fusionne) sont
montres en tete de l'ecran ✏ : « ⚠ Doublon probable : B, C = A ? (raison) » + [Fusionner dans « A »] (confirmation : les
repliques de tous les chapitres suivent, leurs voix sont a refaire) + [Ce ne sont pas les mêmes] (plus jamais propose). La ligne
🎭 et le panneau de la serie le signalent. Serveur : patch_dialogues_8. Suppose app_patch_2821. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.82.2" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.82.1" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2821_video_portee.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
BS = "\\"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep(""".dlg-vids[hidden]{display:none}""", """.dlg-vids[hidden]{display:none}
.dlgp-dbl{border:1px solid #8a6a2e;background:#2a2112;color:#f0c46b;border-radius:10px;padding:10px 12px;margin:0 0 12px;font-size:14px}
.dlgp-dbl b{color:#ffd98a}.dlgp-dbl .muted{font-size:12px}.dlgp-dbl .row{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}""")
rep("""  let h = '<h3>Distribution du manga <span class="muted">— vaut pour <b>tous les chapitres</b> de la série · ' + (persos.length - 1) + ' personnage(s) · '""",
    """  let h = dlgDoublonsHtml()                                                  // v2.82.2 (D12) : doublons probables d'abord
    + '<h3>Distribution du manga <span class="muted">— vaut pour <b>tous les chapitres</b> de la série · ' + (persos.length - 1) + ' personnage(s) · '""")
rep("""function dlgPrepRendre(){""", """function dlgDoublons(){ return (((DLG.e || {}).distribution || {}).doublons || []).filter(g => g && g.garder && (g.avec || []).length); }
function dlgDoublonsHtml(){
  return dlgDoublons().map((g, i) => '<div class="dlgp-dbl">⚠ <b>Doublon probable</b> : ' + g.avec.map(n => "« " + esc(n) + " »").join(", ")
    + " = « " + esc(g.garder) + " » ?" + (g.raison ? '<br><span class="muted">' + esc(g.raison) + "</span>" : "")
    + '<div class="row"><button class="btn sm pri" data-dbl="fusion" data-i="' + i + '">Fusionner dans « ' + esc(g.garder) + ' »</button>'
    + '<button class="btn sm" data-dbl="non" data-i="' + i + '">Ce ne sont pas les mêmes</button></div></div>').join("");
}
document.addEventListener("click", async ev => {  // v2.82.2 : la decision est TOUJOURS celle de Quang
  const t = ev.target.closest("#dlgPrep [data-dbl]"); if (!t) return;
  const g = dlgDoublons()[+t.dataset.i]; if (!g) return;
  if (t.dataset.dbl === "fusion"){
    if (!confirm("Fusionner " + g.avec.map(n => "« " + n + " »").join(", ") + " dans « " + g.garder + " » ?""" + BS + "n" + BS + """n"
        + "Leurs répliques, dans TOUS les chapitres de la série, passent à « " + g.garder + " » (les anciens noms restent reconnus). "
        + "Celles qui avaient déjà une voix seront à refaire avec la voix de « " + g.garder + " ».")) return;
    await dlgRegler({ fusionner: { garder: g.garder, avec: g.avec } });
    toast("fusionné dans « " + g.garder + " »");
  } else {
    await dlgRegler({ pas_doublon: [g.garder].concat(g.avec) });
    toast("noté : ce ne sont pas les mêmes (ne sera plus proposé)");
  }
});
function dlgPrepRendre(){""")
rep("""  if (trait) etat += " · ⚠ " + trait + " à traiter";""", """  if (trait) etat += " · ⚠ " + trait + " à traiter";
  if (dlgDoublons().length) etat += " · ⚠ " + dlgDoublons().length + " doublon" + (dlgDoublons().length > 1 ? "s" : "") + " probable" + (dlgDoublons().length > 1 ? "s" : "") + " (✏)";   // v2.82.2""")
rep("""    : "Aucun personnage pour l'instant : prépare un chapitre (ligne 🎭 du chapitre, ou « plusieurs chapitres » plus bas).";""",
    """    : "Aucun personnage pour l'instant : prépare un chapitre (ligne 🎭 du chapitre, ou « plusieurs chapitres » plus bas).";
  const dbl = (((e0 || {}).distribution || {}).doublons || []).length;                      // v2.82.2 (D12)
  if (dbl && avec.length) $("dlgsDist").innerHTML += ' <span class="dlg-pill ko">⚠ ' + dbl + " doublon" + (dbl > 1 ? "s" : "") + " probable" + (dbl > 1 ? "s" : "") + " — ✏ pour décider</span>";""")
s = s.replace("<title>Manga Studio v2.82.1</title>", "<title>Manga Studio v2.82.2</title>", 1)
s = s.replace('id="verBadge">v2.82.1<', 'id="verBadge">v2.82.2<', 1)
s = s.replace('const VERSION = "2.82.1";', 'const VERSION = "2.82.2";   // v2.82.2 : doublons probables de personnages, fusion sur decision (D12)', 1)
assert s.count("2.82.2") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
