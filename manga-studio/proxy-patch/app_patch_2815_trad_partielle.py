# -*- coding: utf-8 -*-
"""v2.81.5 (27/09, Quang 01:53 « traduire seulement les pages lues » ; 01:55 « une tracabilite pour que le mode normal ne
confonde pas ») -- avec patch_dialogues_5 (serveur), dialogues.py 1.8.0, traduire_chapitre.py 2.1.0 :
- ligne 🎭 : pages choisies pas encore en francais -> « 🌐 Traduire puis préparer », cout de traduction (tarif MESURE :
  etalonnage, 0,009 $/page) + preparation, confirmation explicite (c'est paye) ; jamais de traduction sans ce geste ;
- ligne 🌐 : une traduction PARTIELLE le dit (« français : 25 / 846 pages · dont 25 via 🎭 Dialogues · le reste en VO ») ;
- bibliotheque : « 🌐 FR » = chapitre traduit EN ENTIER ; partiel = « 🌐 FR partiel ». Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.81.5" in s[:400]:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a)); s = s.replace(a, b)

# --- ligne 🎭 : pages a traduire d'abord
rep("""function dlgNbPages(){""", """function dlgPlagesTxt(ns){                 // v2.81.5 : [2,3,5,7,8] -> « 2-3, 5, 7-8 »
  const out = []; ns.forEach(n => { const l = out[out.length - 1]; if (l && n === l[1] + 1) l[1] = n; else out.push([n, n]); });
  return out.map(([a, b]) => a === b ? String(a) : a + "-" + b).join(", ");
}
function dlgManquantes(){                   // v2.81.5 : pages DEMANDEES qui ne sont pas encore en francais
  const e = DLG.e || {}; if (e.vf || DLG.portee !== "pages" || !Array.isArray(e.trad_pages)) return [];   // serveur d'avant v2.81.5 : ne rien supposer
  const tot = CHAP_PAGES || 1, de = Math.max(1, parseInt($("dlgDe").value) || 1), a = Math.min(tot, parseInt($("dlgA").value) || de);
  const fr = new Set(e.trad_pages || []), out = [];
  for (let n = de; n <= a; n++) if (!fr.has(n)) out.push(n);
  return out;
}
const dlgTarifTrad = () => (ETAL && ETAL.traduction && ETAL.traduction.usd) || 0.009;   // mesure (etalonnage), pas devine
function dlgNbPages(){""")
rep("""  if (e.en_cours) return { etat: (pr.etape === "voix" ? "voix en cours" : pr.etape === "video" ? "vidéo en cours" : "préparation en cours")""",
    """  if (e.en_cours) return { etat: (pr.etape === "voix" ? "voix en cours" : pr.etape === "video" ? "vidéo en cours" : pr.etape === "traduction" ? "traduction des pages en cours" : "préparation en cours")""")
rep("""  if (!e.traduit) return { etat: "traduis d'abord ce chapitre en français", est: "", act: "" };""",
    """  const manq = dlgManquantes();
  if (manq.length) return { etat: manq.length + " page" + (manq.length > 1 ? "s" : "") + " à traduire d'abord (p. " + dlgPlagesTxt(manq) + ")",
                            est: pastille("≈ " + fmtUsd(dlgTarifTrad() * manq.length) + " traduction + " + fmtUsd(0.004 * dlgNbPages()) + " préparation"),
                            act: '<button class="btn sm pri" data-dlg="preparer">🌐 Traduire puis préparer</button>' };
  if (!e.traduit) return { etat: "traduis d'abord ce chapitre — ou choisis « des pages » : elles seront traduites seules", est: "", act: "" };""")
rep("""  if (!e.doc) return { etat: "pas encore préparé", est: prep,""",
    """  const partiel = !e.trad_complete && !e.vf && (e.trad_pages || []).length ? " · traduit en partie (" + e.trad_pages.length + " / " + (CHAP_PAGES || "?") + " p.)" : "";
  if (!e.doc) return { etat: "pas encore préparé" + partiel, est: prep,""")
rep("""  $("dlgPreparer").disabled = occupe || !e.traduit && DLG.portee !== "lot";""",
    """  $("dlgPreparer").disabled = occupe || (!e.traduit && DLG.portee === "chap");
  $("dlgPreparer").textContent = DLG.portee !== "lot" && dlgManquantes().length ? "🌐 Traduire puis préparer" : "🎭 Préparer";   // v2.81.5""")
rep("""      const pages = DLG.portee === "pages" ? (($("dlgDe").value || "1") + "-" + ($("dlgA").value || $("dlgDe").value || "1")) : "";""",
    """      const pages = DLG.portee === "pages" ? (($("dlgDe").value || "1") + "-" + ($("dlgA").value || $("dlgDe").value || "1")) : "";
      const manq = action === "preparer" ? dlgManquantes() : [];                 // v2.81.5 : traduire d'abord, sur accord
      if (manq.length && !confirm("Traduire " + manq.length + " page" + (manq.length > 1 ? "s" : "") + " (p. " + dlgPlagesTxt(manq) + ", ≈ "
          + fmtUsd(dlgTarifTrad() * manq.length) + ") puis préparer les dialogues ?\\n\\nElles s'ajoutent à la traduction du chapitre, marquées « via 🎭 Dialogues ». "
          + "Le reste du chapitre reste en version originale.")) return;""")
rep("""      const r = await api("/manga/dialogues_lancer", { d: CHAP_OPEN, action, pages });""",
    """      const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action, pages }, manq.length ? { traduire: true } : {}));""")

# --- ligne 🌐 : la traduction partielle se dit
rep("""      : f && f.stats ? "✅ " + esc(LANGUE_LBL[f.langue] || f.langue) + " : " + f.stats.traduites + " bulle(s) traduite(s), \"""",
    """      : f && f.complete === false ? "🟠 " + esc(LANGUE_LBL[f.langue] || f.langue) + " : " + f.n + " / " + (f.total || "?") + " pages traduites"
        + ((f.via_dialogues || []).length ? " (dont " + f.via_dialogues.length + " via 🎭 Dialogues)" : "") + " — le reste est en version originale"
      : f && f.stats ? "✅ " + esc(LANGUE_LBL[f.langue] || f.langue) + " : " + f.stats.traduites + " bulle(s) traduite(s), \"""")
rep("""      + (/en cours|\d+\s*\/\s*\d+/i.test($("tradEtat").textContent || "") ? " · " + $("tradEtat").textContent.trim() : "");   // seulement un avancement""",
    """      + (/en cours|\d+\s*\/\s*\d+/i.test($("tradEtat").textContent || "") ? " · " + $("tradEtat").textContent.trim().replace(/ — le reste.*$/, "") : "");   // avancement, ou « n / N pages » (v2.81.5)""")

# --- bibliotheque : complet et partiel distincts
rep("""  if (r.trad.length) m.push("🌐 " + r.trad.map(x => x.toUpperCase()).join(" "));""",
    """  if (r.trad.length) m.push("🌐 " + r.trad.map(x => x.toUpperCase()).join(" "));
  if ((r.trad_partiel || []).length) m.push("🌐 " + r.trad_partiel.map(x => x.toUpperCase()).join(" ") + " partiel");   // v2.81.5""")

s = s.replace("<title>Manga Studio v2.81.4</title>", "<title>Manga Studio v2.81.5</title>", 1)
s = s.replace('id="verBadge">v2.81.4<', 'id="verBadge">v2.81.5<', 1)
s = s.replace('const VERSION = "2.81.4";', 'const VERSION = "2.81.5";   // v2.81.5 : traduire seulement les pages des Dialogues (tracees)', 1)
assert s.count("2.81.5") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
