# -*- coding: utf-8 -*-
"""v2.85.0 (27/09, R10 + R10-bis -- Quang 11h41 : preparation lancee sur le telephone, « Dialogue fini » en haut du telephone,
« Rien en cours » sur le PC) : le « ✓ fini » est COMMUN a tous les appareils. L'app fusionne le journal des fins tenu par le
serveur (patch_activite_finis.py : /manga/activite -> « finis ») avec ce qu'elle a vu elle-meme (dedoublonne : meme tache, a
moins de 5 min). Pastille « ✓ … » 10 min sur tous les appareils ; liste « Terminé récemment » (24 h cote serveur).
Arret = « ⏹ … arrêtée », quota / erreur = « ⚠ … ». R10-bis : la fin des Dialogues dit l'etape (« 🔊 Voix des dialogues
finies », « 🎭 Préparation des dialogues finie », « 🎬 Vidéo des dialogues finie », « 🌐 Traduction des pages finie »).
Serveur d'avant (sans « finis ») : rien ne change. Suppose v2.84.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.85.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.84.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2840_dlgs_compact.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.84.0</title>", "<title>Manga Studio v2.85.0</title>")
rep('<span class="ver" id="verBadge">v2.84.0</span>', '<span class="ver" id="verBadge">v2.85.0</span>')
rep('const VERSION = "2.84.0";', 'const VERSION = "2.85.0";   // v2.85.0 : « ✓ fini » commun a tous les appareils (journal serveur), fin des Dialogues par etape (R10)')
# --- le libelle d'une fin (R10-bis)
rep("""const actFini = it => it.type === "karaoke" ? " fini" : " finie";""",
    """const actFini = it => it.type === "karaoke" ? " fini" : " finie";
// v2.85.0 (R10-bis) : le libelle d'une FIN -- l'etape pour les Dialogues, l'issue (fini / arrete / quota / erreur) pour tous
const ACT_DLG_FIN = { voix: ["🔊 Voix des dialogues", "es"], video: ["🎬 Vidéo des dialogues", "e"], traduction: ["🌐 Traduction des pages", "e"] };
function actFinTxt(x){
  const [lbl, acc] = x.type === "dialogues" ? (ACT_DLG_FIN[x.etape] || ["🎭 Préparation des dialogues", "e"])
    : [ACT_LBL[x.type] || x.type, actFini(x) === " fini" ? "" : "e"];
  if (x.issue === "arrete") return "⏹ " + lbl + " arrêté" + acc;
  if (x.issue === "quota") return "⚠ " + lbl + " : quota ElevenLabs épuisé";
  if (x.issue === "erreur") return "⚠ " + lbl + " en erreur";
  return "✓ " + lbl + " fini" + acc;
}""")
rep("""    : b.classList.contains("fini") ? "✓ " + ACT_LBL[ACT.finis[0].type] + actFini(ACT.finis[0]) : "Rien en cours";""",
    """    : b.classList.contains("fini") ? actFinTxt(ACT.finis[0]) : "Rien en cours";   // v2.85.0 : commun a tous les appareils""")
rep("""  $("actFinis").innerHTML = ACT.finis.length ? '<div class="act-finis-t">Terminé pendant cette session</div>'""",
    """  $("actFinis").innerHTML = ACT.finis.length ? '<div class="act-finis-t">Terminé récemment</div>'""")
rep("""      if (!ACT.restaure) toast("✅ " + (ACT_LBL[x.type] || x.type) + actFini(x) + " : " + actNom(x));""",
    """      if (!ACT.restaure) toast(actFinTxt(x).replace(/^✓ /, "✅ ") + " : " + actNom(x));""")
# --- fusion du journal du serveur, APRES la detection locale (dedoublonnage : meme tache a moins de 5 min)
rep("""    // v2.0.1 : la pastille des couts suit TOUT ce qui travaille""",
    """    (j.finis || []).forEach(f => {                    // v2.85.0 (R10) : les fins vues par le SERVEUR, donc par tout appareil
      const t = (f.t || 0) * 1000, k = actCle(f), id = k + "@" + f.t;
      if (ACT.finis.some(x => x.srvId === id)) return;                   // deja fusionnee
      // la MEME fin vue ici (detectee apres la derniere fois ou le serveur l'a vue tourner) : une seule entree, l'issue du serveur
      const loc = ACT.finis.find(x => !x.srvId && actCle(x) === k && x.t >= t - 1000 && x.t - t < 2 * 60 * 1000);
      if (loc){ loc.srvId = id; if (f.issue) loc.issue = f.issue; if (f.etape) loc.etape = f.etape; return; }
      ACT.finis.push(Object.assign({}, f, { t, srvId: id }));
    });
    ACT.finis.sort((a, b) => b.t - a.t); ACT.finis.length = Math.min(ACT.finis.length, 50);
    // v2.0.1 : la pastille des couts suit TOUT ce qui travaille""")
# la liste : l'icone et l'etape de la fin
rep("""    + ACT.finis.slice(0, 8).map((x, i) => '<button class="act-it" data-fini="' + i + '">✅ ' + esc(ACT_LBL[x.type] || x.type) + " — \"""",
    """    + ACT.finis.slice(0, 8).map((x, i) => '<button class="act-it" data-fini="' + i + '">' + esc(actFinTxt(x)) + " — \"""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
