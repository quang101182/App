"""Moderation : reconnaitre un REFUS, continuer, et le garder en ALERTE jusqu'a ce que Quang le traite
(feuille de route 4-decies, specification de Quang du 24/09/2026).

Avant : un refus de Gemini (reponse vide) etait lu comme « JSON illisible » -> 3 essais PAYES -> chapitre abandonne.
Ici : detection -> exception Refus (jamais de nouvel essai payant) ; l'appelant met la page de cote et continue ;
ajouter_alerte() l'inscrit dans sources/_alertes.json (persistant, lu par l'app et par la fabrication des videos).
"""
import json, os, re, time, uuid

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
ALERTES = os.environ.get("MANGA_ALERTES") or os.path.join(SRC, "_alertes.json")   # bancs : fichier jetable

_GEMINI_BLOC = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY", "IMAGE_PROHIBITED_CONTENT",
                "RECITATION", "OTHER_SAFETY"}
_MARQUEURS_HTTP = re.compile(r"content[_ ]?filter|high risk|content exists risk|inappropriate|safety|prohibited|"
                             r"blocked|sensitive|moderation|policy", re.I)
_REFUS_TEXTE = re.compile(r"^\W*(i'?m sorry|i am sorry|sorry,? (but )?i (can|cannot|can't)|i (cannot|can't|won't) "
                          r"(help|assist|provide|describe|comply)|je (suis desole|suis désolé|ne peux pas)|"
                          r"désolé,? (mais )?je ne peux)", re.I)


class Refus(Exception):
    """Contenu refuse par la moderation d'un fournisseur. `motif` = explication lisible par Quang."""
    def __init__(self, moteur, motif):
        super().__init__("%s : %s" % (moteur, motif))
        self.moteur, self.motif = moteur, motif


def refus_http(code, brut):
    """Erreur HTTP d'un fournisseur -> motif lisible si c'est un refus de moderation, sinon None."""
    if code in (400, 403, 422, 451) and _MARQUEURS_HTTP.search(brut or ""):
        return "requete refusee (HTTP %d) : %s" % (code, (brut or "")[:140])
    return None


def refus_gemini(r):
    """Reponse NATIVE de Gemini -> motif si bloquee, sinon None."""
    pf = (r or {}).get("promptFeedback") or {}
    if pf.get("blockReason"):
        return "Gemini a bloque la demande (%s)" % pf["blockReason"]
    cands = (r or {}).get("candidates")
    if cands == []:
        return "Gemini n'a rendu aucune reponse (contenu bloque)"
    fr = ((cands or [{}])[0] or {}).get("finishReason") or ""
    if fr in _GEMINI_BLOC:
        return "Gemini a arrete sa reponse pour %s" % {"RECITATION": "droits d'auteur (RECITATION)"}.get(fr, "securite (%s)" % fr)
    return None


def refus_openai(r):
    """Reponse au format OpenAI (Kimi, DeepSeek, Mistral) -> motif si filtree, sinon None."""
    ch = ((r or {}).get("choices") or [{}])[0] or {}
    if ch.get("finish_reason") == "content_filter":
        return "reponse filtree par la moderation (content_filter)"
    return None


def refus_texte(texte):
    """Le modele a repondu, mais par un REFUS en toutes lettres (pas de JSON)."""
    t = (texte or "").strip()
    if t and "{" not in t[:200] and _REFUS_TEXTE.search(t[:200]):
        return "refus en toutes lettres : « %s »" % t[:120]
    return None


# ------------------------------------------------------------------ registre des alertes (persistant)
def _lire():
    try:
        with open(ALERTES, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "alertes": []}


def _ecrire(doc):
    tmp = ALERTES + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    for _ in range(20):                      # un autre programme ecrit peut-etre au meme instant (Windows)
        try:
            os.replace(tmp, ALERTES)
            return
        except PermissionError:
            time.sleep(0.1)
    os.replace(tmp, ALERTES)


def ajouter_alerte(d, etape, pages, moteur, motif, detail=""):
    """Une alerte OUVERTE par (chapitre, etape) : les pages s'y ajoutent. -> id de l'alerte."""
    doc = _lire()
    for a in doc["alertes"]:
        if a["d"] == d and a["etape"] == etape and a["etat"] == "ouverte":
            a["pages"] = sorted(set(a["pages"]) | set(pages))
            a["motifs"] = list(dict.fromkeys(a.get("motifs", []) + [motif]))[-5:]
            a["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _ecrire(doc)
            return a["id"]
    a = {"id": uuid.uuid4().hex[:10], "d": d, "serie": d.split("/")[0], "etape": etape, "pages": sorted(set(pages)),
         "moteur": moteur, "motifs": [motif], "detail": detail, "etat": "ouverte",
         "cree": time.strftime("%Y-%m-%dT%H:%M:%S"), "maj": time.strftime("%Y-%m-%dT%H:%M:%S")}
    doc["alertes"].append(a)
    _ecrire(doc)
    return a["id"]


def alertes(etat=None):
    return [a for a in _lire()["alertes"] if etat is None or a["etat"] == etat]


def ouvertes_pour(d):
    """Alertes OUVERTES d'un chapitre (la video attend qu'elles soient traitees ou ignorees)."""
    return [a for a in alertes("ouverte") if a["d"] == d]


def changer_etat(ids, etat, note=""):
    doc = _lire()
    n = 0
    for a in doc["alertes"]:
        if a["id"] in ids:
            a["etat"], a["maj"] = etat, time.strftime("%Y-%m-%dT%H:%M:%S")
            if note:
                a["note"] = note
            n += 1
    _ecrire(doc)
    return n
