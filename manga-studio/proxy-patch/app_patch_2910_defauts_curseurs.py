# -*- coding: utf-8 -*-
"""v2.91.0 (27/09, R18 phase 2 -- Quang 13h13 : « quand je bouge les curseurs, peu importe ou, j'aimerais un bouton pour
indiquer que c'est la valeur par defaut que je souhaite desormais sur toute l'application […] tu separes ces valeurs entre la
principale et la secondaire ») : un « ☆ » a cote des reglages de lecture :
  vitesse des narrations (☁ en ligne / 🖥 PC : bloc Narration + lecteur), volume general (lecteur + Dialogues), musique,
  vitesse du lecteur des Dialogues, vitesse des videos (menu ⋯ du lecteur video).
☆ -> la valeur devient le DEFAUT de CETTE application (reglages.py 1.5.0, _reglages.json de l'instance). Chaque appareil
l'adopte au tour de suivi suivant (4-15 s) ou a son prochain chargement ; il peut la changer ensuite pour lui seul ; un
nouveau ☆ la reimpose partout. ★ = la valeur affichee EST le defaut. Au passage : vitesses du lecteur des Dialogues et des
videos MEMORISEES (avant : remises a 1 a chaque ouverture). Suppose v2.90.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.91.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.90.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2900_bascule_replace.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.90.0</title>", "<title>Manga Studio v2.91.0</title>")
rep('<span class="ver" id="verBadge">v2.90.0</span>', '<span class="ver" id="verBadge">v2.91.0</span>')
rep('const VERSION = "2.90.0";', 'const VERSION = "2.91.0";   // v2.91.0 : ☆ valeurs par defaut des curseurs de lecture, par application (R18 phase 2)')
rep(""".dlgp-def{flex:none;""", """.def-star{background:none;border:0;color:var(--dim);font-size:15px;line-height:1;padding:2px 4px;cursor:pointer;flex:none}
.def-star.on{color:#ffd24a}   /* v2.91.0 (R18 phase 2) */
.dlgp-def{flex:none;""")
# le suivi des reglages (deja appele a chaque tour d'activite) propage les defauts
rep("""        if (r && typeof r.flou_discretion === "boolean" && r.flou_discretion !== FLOU_ON) flouMaj(r.flou_discretion); }   // v2.51.0""",
    """        if (r && typeof r.flou_discretion === "boolean" && r.flou_discretion !== FLOU_ON) flouMaj(r.flou_discretion);   // v2.51.0
        if (r && r.defauts && typeof defautsSuivre === "function") defautsSuivre(r.defauts); }                           // v2.91.0""")
rep("""$("dllVit").onchange = () => { const x = DLL.liste && DLL.liste[DLL.i]; DLL.audio.playbackRate = +$("dllVit").value * (x ? dlgEcoute(x.qui) : 1); };""",
    """$("dllVit").onchange = () => { const x = DLL.liste && DLL.liste[DLL.i]; DLL.audio.playbackRate = +$("dllVit").value * (x ? dlgEcoute(x.qui) : 1); };
/* ---- v2.91.0 (R18 phase 2) : ☆ = valeur PAR DEFAUT de cette application (principale / secondaire), propagee a tous les appareils ---- */
const lsLire = (k, d) => { try { const v = localStorage.getItem(k); return v === null || isNaN(+v) ? d : +v; } catch (e) { return d; } };
const lsEcrire = (k, v) => { try { localStorage.setItem(k, String(v)); } catch (e) {} };
function selMettre(el, v){ const o = [...el.options].find(x => Math.abs(+x.value - v) < 0.001); if (o){ el.value = o.value; return true; } return false; }
const DEF_CURSEURS = {
  vit_cloud: { lib: "vitesse des voix en ligne", lire: () => lsLire("manga_vit_cloud", 1.15),
               mettre: v => { lsEcrire("manga_vit_cloud", v); narrVitMaj(); if (!$("lecteur").hidden && vitSorte() === "cloud") vitAppliquer(); } },
  vit_local: { lib: "vitesse des voix du PC", lire: () => lsLire("manga_vit_local", 1),
               mettre: v => { lsEcrire("manga_vit_local", v); narrVitMaj(); if (!$("lecteur").hidden && vitSorte() === "local") vitAppliquer(); } },
  vol_g:     { lib: "volume général", lire: () => VOL_G,
               mettre: v => { $("lecVolG").value = v; $("lecVolG").dispatchEvent(new Event("input")); if ($("dllVol")) $("dllVol").value = v; if (DLL.audio) DLL.audio.volume = v / 100; } },
  mus_vol:   { lib: "volume de la musique", lire: () => MUS_VOL,
               mettre: v => { $("lecMusVol").value = v; $("lecMusVol").dispatchEvent(new Event("input")); } },
  dll_vit:   { lib: "vitesse du lecteur des Dialogues", lire: () => +$("dllVit").value,
               mettre: v => { lsEcrire("manga_dll_vit", v); if (selMettre($("dllVit"), v)) $("dllVit").dispatchEvent(new Event("change")); } },
  vid_vit:   { lib: "vitesse des vidéos", lire: () => VID.vit,
               mettre: v => { lsEcrire("manga_vid_vit", v); VID.vit = v; if (vEl()) vEl().playbackRate = v;
                              document.querySelectorAll("#vidMenu [data-vit]").forEach(x => x.classList.toggle("on", Math.abs(+x.dataset.vit - v) < 0.001)); } },
};
let DEF_SRV = {};
const defCle = k => k === "vit_auto" ? "vit_" + vitSorte() : k;
function defEtoiles(){
  document.querySelectorAll("[data-def]").forEach(b => { const k = defCle(b.dataset.def), c = DEF_CURSEURS[k]; if (!c) return;
    const on = DEF_SRV[k] != null && Math.abs(DEF_SRV[k] - c.lire()) < 0.001;
    b.classList.toggle("on", on); b.textContent = (on ? "★" : "☆") + (b.dataset.txt || "");
    b.title = (on ? "c'est la valeur par défaut" : "en faire la valeur par défaut") + " (" + c.lib + ") de l'application " + (ESPACE.nom === "prive" ? "secondaire" : "principale")
      + (DEF_SRV[k] != null && !on ? " — aujourd'hui " + String(DEF_SRV[k]).replace(".", ",") : ""); });
}
function defautsSuivre(defs){                        // appele par modeSuivre (chaque tour) : un defaut NOUVEAU s'impose une fois
  DEF_SRV = defs || {};
  Object.entries(DEF_SRV).forEach(([k, v]) => { const c = DEF_CURSEURS[k]; if (!c) return;
    let vu = null; try { vu = localStorage.getItem("manga_def_vu:" + k); } catch (e) {}
    if (vu !== String(v)){ try { c.mettre(v); } catch (e) {} lsEcrire("manga_def_vu:" + k, v); } });
  defEtoiles();
}
[["narrVitCloud", "vit_cloud"], ["narrVitLocal", "vit_local"], ["lecVit", "vit_auto"], ["lecVolG", "vol_g"], ["lecMusVol", "mus_vol"],
 ["dllVit", "dll_vit"], ["dllVol", "vol_g"]].forEach(([id, k]) => { const el = $(id); if (el) el.insertAdjacentHTML("afterend", '<button type="button" class="def-star" data-def="' + k + '">☆</button>'); });
(function(){ const m = document.querySelector("#vidMenu .menu-pan"); if (m) m.insertAdjacentHTML("beforeend", '<button role="menuitem" class="def-star" data-def="vid_vit" data-txt=" vitesse actuelle par défaut">☆ vitesse actuelle par défaut</button>'); })();
(function(){ const v = lsLire("manga_dll_vit", null); if (v != null) selMettre($("dllVit"), v);          // memorisees desormais
  const w = lsLire("manga_vid_vit", null); if (w != null) DEF_CURSEURS.vid_vit.mettre(w); })();
$("dllVit").addEventListener("change", () => lsEcrire("manga_dll_vit", +$("dllVit").value));
document.querySelectorAll("#vidMenu [data-vit]").forEach(b => b.addEventListener("click", () => lsEcrire("manga_vid_vit", +b.dataset.vit)));
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-def]"); if (!b) return;
  e.preventDefault(); e.stopPropagation();
  const k = defCle(b.dataset.def), c = DEF_CURSEURS[k]; if (!c) return;
  const v = c.lire(), app = ESPACE.nom === "prive" ? "secondaire" : "principale";
  try { const r = await api("/manga/reglages", { defauts: { [k]: v } }); if (r.error) throw new Error(r.error);
        if (!r.defauts) throw new Error("serveur à relancer (réglage inconnu)");
        lsEcrire("manga_def_vu:" + k, r.defauts[k]); DEF_SRV = r.defauts; defEtoiles();
        toast("★ " + c.lib + " " + String(v).replace(".", ",") + " : par défaut pour l'application " + app + " (tous les appareils)"); }
  catch (err) { toast("par défaut non enregistré : " + err.message); }
}, true);
["input", "change"].forEach(ev => document.addEventListener(ev, () => { if (typeof defEtoiles === "function") setTimeout(defEtoiles, 0); }));""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
