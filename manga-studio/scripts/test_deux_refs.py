# -*- coding: utf-8 -*-
"""DEUX personnages, DEUX references : est-ce que chacun garde son visage ?

C'est le chantier laisse ouvert le 27/07 au soir. Aujourd'hui l'app n'applique
qu'UNE reference (le premier personnage du casting qui en a une) -- limite ecrite
noir sur blanc dans `manga_studio.html` et dans REVALIDATION.md §3. Concretement :
quand Jo et Kimiko sont dans la meme case, Jo n'a aucun verrou d'identite.

Le commentaire du code disait « IPAdapter melangerait les identites si on en
empilait deux, et on ne sait pas encore ce que ca vaut ». Ce banc mesure ce que
ca vaut, au lieu de continuer a le supposer.

QUATRE BRAS, meme seed, meme prompt a deux personnages
------------------------------------------------------
  rien    : prompt seul (temoin -- c'est deja ce que Jo obtient aujourd'hui)
  ref1    : UNE seule reference, celle de A  = l'etat livre en v1.51.0
  chaine  : DEUX IPAdapterAdvanced en serie, sans masque
  masque  : DEUX IPAdapterAdvanced en serie, chacun borne a une MOITIE de l'image
            par `attn_mask` (A a gauche, B a droite)

Le bras `masque` est le seul qui puisse repondre « chacun garde SON visage » : sans
masque, les deux conditionnements s'appliquent a toute l'image, et rien ne dit au
modele lequel va sur qui. C'est la difference entre melanger deux identites et en
placer deux.

L'INSTRUMENT est celui du 27/07, repris tel quel (`test_ipadapter.Visages`) :
YOLO face detecte, CLIP-ViT-H embedde le visage recadre. Il a ete mesure capable
de separer deux designs ELOIGNES (0,908 contre 0,650) et INCAPABLE de separer un
changement d'yeux (0,868, en plein dans le nuage). Ici on lui demande exactement
ce qu'il sait faire -- distinguer une brune a frange d'une blonde en blouse -- et
rien d'autre. La calibration est rejouee : si les nuages se chevauchent, le banc
REFUSE de conclure.

DEUX QUESTIONS, mesurees separement, parce qu'elles n'ont pas la meme reponse
-----------------------------------------------------------------------------
  Q1 « deux identites DISTINCTES sont-elles presentes ? »  -> le meilleur des deux
      appariements possibles. Vrai des que chaque visage est plus proche d'une
      reference differente.
  Q2 « chacune est-elle a SA place ? »                     -> l'appariement impose
      gauche=A / droite=B. Ne peut etre garanti que par le masque ; sans masque,
      le tirer au sort une fois sur deux ne serait pas un resultat.

Usage:
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_deux_refs.py
    ... --seeds 3            (nombre de seeds par bras, defaut 3)
    ... --bras masque        (n'en jouer qu'un)
"""
import argparse
import os
import sys
import time

# ⚠ Pas de `sys.stdout = TextIOWrapper(...)` ici : `test_ipadapter` en pose un a
# l'import, ce qui FERME celui qu'on aurait cree avant -- et le banc mourait sur
# le premier print avec « I/O operation on closed file ». Le sien suffit.

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_ipadapter import (  # noqa: E402  (l'instrument vit la-bas, on ne le duplique pas)
    CKPT, NEG, QUAL, BW, SEED, DATASET, Visages, fetch, get, noirceur, post,
    saturation, upload,
)

import json          # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402
import uuid          # noqa: E402

COMFY = "http://127.0.0.1:8188"
OUT = os.path.join(HERE, "duo_refs_out")
W, H = 1024, 1024          # carre : deux personnages cote a cote tiennent mieux
IPA = {"preset": "PLUS (high strength)", "poids": 0.4, "endAt": 0.5}

# Personnage A = celui du dataset (Kimiko), le seul dont on ait 24 vraies images.
IDENT_A = ("18 years old, short messy black hair, blunt bangs, sharp amber eyes, "
           "black sailor uniform with red scarf, slender build")
# Personnage B = volontairement TRES different de A. Ce n'est pas de la facilite :
# l'instrument n'a ete valide QUE sur cet ecart-la (cf. l'epreuve difficile
# echouee le 27/07). Prendre deux personnages proches donnerait des chiffres que
# l'instrument n'a pas le droit d'interpreter.
IDENT_B = ("30 years old, very long wavy light hair, round soft face, "
           "white lab coat, tall")
SCENE = ("2girls, standing side by side, facing viewer, upper body, "
         "indoor classroom background, %s on the left, %s on the right")
# La MEME scene, sans dire qui est de quel cote. Question qui decide du code de
# l'app : le masque suffit-il a placer chacun, ou faut-il que le prompt l'annonce ?
# Si le masque suffit, l'app n'a rien a ajouter au texte de Quang -- sinon elle
# doit y injecter une mention de placement, ce qui se voit et doit etre dit.
SCENE_MUETTE = ("2girls, standing side by side, facing viewer, upper body, "
                "indoor classroom background, %s, and %s")
MUET = [False]


def wf(seed, refs, masques, poids=None):
    """Un squelette unique ; SEULES les ancres d'identite changent d'un bras a l'autre.

    `refs`    : 0, 1 ou 2 noms de fichiers deja deposes dans ComfyUI/input.
    `masques` : True -> chaque IPAdapter est borne a une moitie par `attn_mask`.

    Les masques sont fabriques DANS le graphe (SolidMask + MaskComposite) plutot
    qu'uploades : un masque est une donnee geometrique exacte, le faire calculer
    par ComfyUI evite un fichier de plus a garder d'accord avec le format.
    """
    pos = QUAL + BW + ((SCENE_MUETTE if MUET[0] else SCENE) % (IDENT_A, IDENT_B))
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": W, "height": H, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": "manga/_duorefs/duo"}},
    }
    if not refs:
        return g
    g["21"] = {"class_type": "IPAdapterUnifiedLoader",
               "inputs": {"model": ["1", 0], "preset": IPA["preset"]}}
    if masques:
        # Fond noir plein cadre, puis une moitie blanche posee dedans. `multiply`
        # n'aurait rien donne sur un fond a 0 : on ECRIT la moitie (« add » sur du
        # noir = la moitie elle-meme), c'est le seul operateur qui compose ici.
        g["30"] = {"class_type": "SolidMask",
                   "inputs": {"value": 0.0, "width": W, "height": H}}
        g["31"] = {"class_type": "SolidMask",
                   "inputs": {"value": 1.0, "width": W // 2, "height": H}}
        g["32"] = {"class_type": "MaskComposite", "inputs": {
            "destination": ["30", 0], "source": ["31", 0], "x": 0, "y": 0,
            "operation": "add"}}
        g["33"] = {"class_type": "MaskComposite", "inputs": {
            "destination": ["30", 0], "source": ["31", 0], "x": W // 2, "y": 0,
            "operation": "add"}}
    modele = ["21", 0]
    for i, nom in enumerate(refs):
        ld, ip = str(40 + i * 2), str(41 + i * 2)
        g[ld] = {"class_type": "LoadImage", "inputs": {"image": nom}}
        g[ip] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": modele, "ipadapter": ["21", 1], "image": [ld, 0],
            "weight": IPA["poids"] if poids is None else poids,
            "weight_type": "linear",
            "combine_embeds": "concat", "start_at": 0.0, "end_at": IPA["endAt"],
            "embeds_scaling": "V only"}}
        if masques:
            g[ip]["inputs"]["attn_mask"] = [["32", 0], ["33", 0]][i]
        modele = [ip, 0]
    g["5"]["inputs"]["model"] = modele
    return g


def run(label, seed, refs, masques, poids=None):
    t0 = time.time()
    try:
        pid = post("/prompt", {"prompt": wf(seed, refs, masques, poids),
                               "client_id": str(uuid.uuid4())})["prompt_id"]
    except urllib.error.HTTPError as e:
        print("  [%s] REFUS ComfyUI : %s" % (label, e.read().decode()[:600]), flush=True)
        return None
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("  [%s] TIMEOUT" % label, flush=True)
            return None
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("  [%s] ERREUR %s" % (label, json.dumps(st)[:600]), flush=True)
        return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("  [%s] AUCUNE IMAGE" % label, flush=True)
        return None
    dest = os.path.join(OUT, label + ".png")
    fetch(imgs[0], dest)
    print("  [%s] %.0fs" % (label, time.time() - t0), flush=True)
    return dest


def visages_tries(vis, path, n=2):
    """Les `n` plus grands visages, rendus DE GAUCHE A DROITE avec leur embedding.

    Deux tris, dans cet ordre, et l'ordre compte : on choisit les visages par leur
    TAILLE (un figurant du fond n'est pas un des deux personnages) puis on les
    remet dans l'ordre de LECTURE (c'est la position qui porte la question Q2).
    """
    import cv2
    im = cv2.imread(path)
    if im is None:
        return []
    Hh, Ww = im.shape[:2]
    r = vis.yolo.predict(path, conf=0.35, verbose=False)[0]
    boites = []
    for b in r.boxes:
        x1, y1, x2, y2 = [float(t) for t in b.xyxy[0]]
        boites.append(((x2 - x1) * (y2 - y1), x1, y1, x2, y2))
    boites.sort(reverse=True)
    gardes = sorted(boites[:n], key=lambda t: t[1])
    out = []
    for _, x1, y1, x2, y2 in gardes:
        mx, my = (x2 - x1) * 0.35, (y2 - y1) * 0.35
        crop = im[max(0, int(y1 - my)):min(Hh, int(y2 + my)),
                  max(0, int(x1 - mx)):min(Ww, int(x2 + mx))]
        if not crop.size:
            continue
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        px = vis.proc(images=crop, return_tensors="pt")["pixel_values"]
        px = px.to(vis.dev, dtype=vis.clip.dtype)
        with vis.torch.no_grad():
            e = vis.clip(px).image_embeds[0].float().cpu().numpy()
        out.append({"x": (x1 + x2) / 2 / Ww,
                    "e": e / (vis.np.linalg.norm(e) + 1e-8)})
    return out


def moy_sim(vis, e, refs_emb):
    return float(sum(vis.np.dot(e, r) for r in refs_emb) / len(refs_emb))


def juge(vis, path, embA, embB):
    """Q1 (deux identites distinctes) et Q2 (chacune a sa place), separement."""
    vs = visages_tries(vis, path)
    if len(vs) < 2:
        return {"n": len(vs), "q1": False, "q2": False}
    g, d = vs[0], vs[1]
    gA, gB = moy_sim(vis, g["e"], embA), moy_sim(vis, g["e"], embB)
    dA, dB = moy_sim(vis, d["e"], embA), moy_sim(vis, d["e"], embB)
    # Q1 : il EXISTE un appariement ou les deux visages vont a des refs differentes.
    direct = (gA > gB) and (dB > dA)
    croise = (gB > gA) and (dA > dB)
    return {"n": len(vs), "q1": direct or croise, "q2": direct,
            "gA": gA, "gB": gB, "dA": dA, "dB": dB,
            "sat": saturation(path), "noir": noirceur(path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--bras", nargs="*",
                    default=["rien", "ref1", "chaine", "masque"])
    ap.add_argument("--poids-masque", nargs="*", type=float, default=[],
                    dest="poids_masque",
                    help="poids supplementaires a essayer sur le bras masque "
                         "(cree les bras masque06, masque08, ...)")
    ap.add_argument("--muet", action="store_true",
                    help="le prompt NE DIT PAS qui est a gauche : le masque"
                         " place-t-il seul les deux personnages ?")
    args = ap.parse_args()
    MUET[0] = args.muet
    os.makedirs(OUT, exist_ok=True)
    if args.muet:
        print("*** prompt MUET sur le placement (le masque est seul a decider) ***")

    refsA = [os.path.join(DATASET, f) for f in sorted(os.listdir(DATASET))
             if f.endswith(".png")][:8]
    if len(refsA) < 4:
        print("ARRET : dataset du personnage A introuvable (%s)" % DATASET)
        return 2
    vis = Visages()

    # --- Le personnage B n'existe pas encore : on le FABRIQUE, meme checkpoint,
    #     meme rendu. Le comparer a des images d'ailleurs aurait mesure un ecart
    #     de style au lieu d'un ecart d'identite.
    print("=== references du personnage B (fabriquees ici, seul et de face) ===")
    refsB = []
    for i in range(3):
        p = os.path.join(OUT, "refB_%d.png" % i)
        if not os.path.isfile(p):
            g = wf(SEED + 3000 + i, [], False)
            g["2"]["inputs"]["text"] = (QUAL + BW + "1girl, solo, " + IDENT_B
                                        + ", close-up portrait, looking at viewer, "
                                          "plain background")
            g["7"]["inputs"]["filename_prefix"] = "manga/_duorefs/refB"
            try:
                pid = post("/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})["prompt_id"]
            except urllib.error.HTTPError as e:
                print("  REFUS ComfyUI : %s" % e.read().decode()[:400])
                return 2
            while pid not in get("/history/" + pid):
                time.sleep(2)
            h = get("/history/" + pid)
            imgs = [x for n in h[pid]["outputs"].values() for x in n.get("images", [])]
            if not imgs:
                continue
            fetch(imgs[0], p)
        refsB.append(p)
        print("  %s" % os.path.basename(p))

    embA = [vis.emb(r) for r in refsA]
    embA = [e for e in embA if e is not None]
    embB = [vis.emb(r) for r in refsB]
    embB = [e for e in embB if e is not None]
    if len(embA) < 3 or len(embB) < 2:
        print("ARRET : trop peu de visages detectes sur les references (A %d, B %d)"
              % (len(embA), len(embB)))
        return 2

    # --- CALIBRATION : l'instrument separe-t-il A de B ? Sans ca, tous les
    #     chiffres qui suivent sont des nombres sans echelle.
    print("\n=== CALIBRATION (A contre B) ===")
    intraA = [float(vis.np.dot(embA[i], embA[j]))
              for i in range(len(embA)) for j in range(i + 1, len(embA))]
    intraB = [float(vis.np.dot(embB[i], embB[j]))
              for i in range(len(embB)) for j in range(i + 1, len(embB))]
    inter = [float(vis.np.dot(a, b)) for a in embA for b in embB]
    for nom, v in (("A vs A", intraA), ("B vs B", intraB), ("A vs B", inter)):
        print("  %-7s (n=%2d) : min %.3f  moy %.3f  max %.3f"
              % (nom, len(v), min(v), sum(v) / len(v), max(v)))
    marge = min(intraA + intraB) - max(inter)
    if marge <= 0:
        print("VERDICT : l'instrument NE SEPARE PAS A de B (marge %.3f)." % marge)
        print("  => aucun bras ne peut etre juge. Le banc s'arrete plutot que de")
        print("     produire des chiffres qu'il n'a pas le droit de lire.")
        return 1
    print("  marge %.3f > 0 -> l'instrument distingue A de B, il peut juger." % marge)

    # --- Les references donnees a IPAdapter : la plus « lisible » de chaque
    #     personnage (visage le plus grand), converties en N&B a l'upload.
    tA = sorted([(vis.taille_visage(r), r) for r in refsA], reverse=True)
    tB = sorted([(vis.taille_visage(r), r) for r in refsB], reverse=True)
    nomA = upload(tA[0][1], en_nb=True)
    nomB = upload(tB[0][1], en_nb=True)
    print("\nreference A -> %s (visage %.1f %%)" % (nomA, 100 * tA[0][0]))
    print("reference B -> %s (visage %.1f %%)" % (nomB, 100 * tB[0][0]))
    # Le defaut qui a fausse le premier run : les deux references arrivaient sous
    # le meme nom dans ComfyUI/input, donc le graphe chargeait deux fois la meme
    # image -- et le tableau final avait l'air rempli. On refuse desormais de
    # jouer un banc dont les deux entrees sont, en fait, une seule.
    if nomA == nomB:
        print("ARRET : les deux references portent le MEME nom cote ComfyUI (%s)."
              " Le banc ne mesurerait qu'une seule identite." % nomA)
        return 2

    # Le poids du masque se BALAIE : chaque adapter n'agissant plus que sur une
    # moitie, rien ne dit que 0,4 -- mesure plein cadre le 27/07 -- reste le bon
    # reglage quand l'influence est bornee a une region.
    BRAS = {"rien": ([], False, None), "ref1": ([nomA], False, None),
            "chaine": ([nomA, nomB], False, None),
            "masque": ([nomA, nomB], True, None)}
    for p in args.poids_masque:
        BRAS["masque%02d" % round(p * 10)] = ([nomA, nomB], True, p)
    res = {}
    for nom in args.bras:
        refs, masq, pds = BRAS[nom]
        print("\n-- bras %s" % nom)
        res[nom] = []
        for k in range(args.seeds):
            p = run("%s_s%d%s" % (nom, k, "_muet" if MUET[0] else ""),
                    SEED + k, refs, masq, pds)
            res[nom].append(juge(vis, p, embA, embB) if p else None)

    print("\n================ DEUX IDENTITES DANS UNE CASE ================")
    print("Q1 = deux identites distinctes presentes (appariement libre)")
    print("Q2 = chacune a SA place (gauche = A, droite = B)")
    print("%-9s | %-9s | %-6s | %-6s | %-6s | %-6s"
          % ("bras", "2 visages", "Q1", "Q2", "sat", "noir"))
    print("-" * 60)
    for nom in args.bras:
        v = [x for x in res[nom] if x]
        if not v:
            print("%-9s | (aucune image)" % nom)
            continue
        deux = sum(1 for x in v if x["n"] >= 2)
        q1 = sum(1 for x in v if x["q1"])
        q2 = sum(1 for x in v if x["q2"])
        sat = [x.get("sat") for x in v if x.get("sat") is not None]
        noi = [x.get("noir") for x in v if x.get("noir") is not None]
        print("%-9s | %d/%-7d | %d/%-4d | %d/%-4d | %-6s | %-6s"
              % (nom, deux, len(v), q1, len(v), q2, len(v),
                 "%.3f" % (sum(sat) / len(sat)) if sat else "-",
                 "%.3f" % (sum(noi) / len(noi)) if noi else "-"))
    print("-" * 60)
    print("(sat : un vrai N&B tend vers 0 -- un bras qui tient l'identite en")
    print(" injectant de la couleur n'est pas utilisable dans cette app)")
    print("\ndetail par image :")
    for nom in args.bras:
        for k, x in enumerate(res[nom]):
            if not x:
                print("  %-9s s%d : (echec)" % (nom, k))
            elif x["n"] < 2:
                print("  %-9s s%d : %d visage(s) detecte(s)" % (nom, k, x["n"]))
            else:
                print("  %-9s s%d : gauche A%.3f/B%.3f  droite A%.3f/B%.3f  %s %s"
                      % (nom, k, x["gA"], x["gB"], x["dA"], x["dB"],
                         "Q1v" if x["q1"] else "Q1x", "Q2v" if x["q2"] else "Q2x"))
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
