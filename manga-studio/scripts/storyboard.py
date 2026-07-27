# -*- coding: utf-8 -*-
"""Texte -> DECOUPAGE en cases, avec dialogues. Le coeur de la creation.

Demande de Quang (27/07) : « ce qui sera important, ce sera surtout la creation
[...] la definition des images, la coherence des actions, les textes de dialogue
generes automatiquement, meme si je pourrai les corriger ».

Ce module fait la partie qui ne depend PAS du sujet : transformer une intention
narrative en une suite de cases. Du texte vers du texte -- donc peu risque, et
valable pour une romance comme pour un duel de mechas.

Trois choses le distinguent d'un simple « demande a un LLM » :

 1. **Il produit des PROMPTS, pas des descriptions.** Une case n'est utile que si
    elle peut etre generee telle quelle : tags courts et concrets, pas de prose.
 2. **Il impose la regle des deux types de case** (mesuree en phase 2) : une case
    d'ambiance porte le decor, une case de dialogue porte le visage. Melanger les
    deux dans une meme case ne marche pas, c'est mesure.
 3. **Il separe ce qui est CONSTANT de ce qui VARIE.** Le decor et les personnages
    sont decrits UNE fois en tete ; chaque case ne dit que son action. C'est ce qui
    donne la coherence -- et c'est la meme discipline que les captions de LoRA.

Usage:
    python storyboard.py "deux lyceennes se disputent sur un toit, puis se reconcilient"
    python storyboard.py --fichier scenario.txt --cases 6 --lang fr
"""
import argparse
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GATEWAY = "https://api-gateway.quang101182.workers.dev"
# ⚠ Le secret du gateway NE VIT PLUS DANS LE CODE (28/07). Ce depot est PUBLIC,
# et le secret y a ete versionne en clair du 26 au 28/07 : l'historique git en garde
# la trace, donc il doit etre CHANGE cote gateway, pas seulement retire d'ici.
def _secret():
    s = os.environ.get('WORKER_SECRET', '').strip()
    if s:
        return s
    base = os.path.join(os.path.expanduser('~'), 'Documents', 'ComfyUI')
    for nom in ('.worker_secret', '.studio_secret'):
        p = os.path.join(base, nom)
        if os.path.isfile(p):
            v = open(p, encoding='utf-8').read().strip()
            if v:
                return v
    raise SystemExit('ARRET : secret du gateway introuvable. Definir WORKER_SECRET '
                     'dans l environnement, ou le poser dans ComfyUI/.worker_secret.')


SECRET = _secret()
HERE = os.path.dirname(os.path.abspath(__file__))

SYS = """You are a manga storyboard artist. You turn a premise into a page breakdown.

CRITICAL RULES, learned from measurement on this project — follow them exactly:

1. Each panel gets a "kind": either "ambiance" or "dialogue".
   - "ambiance" = wide/establishing shot. The SETTING carries the information.
     The character is small; their face will NOT be readable. Never put a close
     emotional beat here.
   - "dialogue" = tight shot (bust or close-up). The FACE carries the information.
     The background is out of frame or blurred; never rely on scenery here.
   A panel cannot do both. This is measured, not stylistic.

2. "prompt" must be a GENERATION PROMPT, not prose. Short comma-separated visual
   tags, in ENGLISH, describing ONLY what varies in this panel: framing, pose,
   action, expression, camera angle. 6 to 14 tags.
   Never repeat the character's constant traits (hair, outfit) or the setting —
   those are declared once in "cast" and "setting" and injected automatically.

3. "dialogue" is the spoken line, in the requested language, or "" if the panel is
   silent. Silent panels are good: a manga page that is all talk is a bad page.
   Keep lines SHORT — they must fit in a speech bubble.

4. The page must READ. Vary the framing (do not make 6 close-ups). Respect the
   requested panel count exactly.

Return STRICT JSON only, no commentary:
{
 "title": "short page title",
 "setting": "the location, described ONCE, as english visual tags",
 "cast": [{"id":"a","name":"...","look":"english visual tags, constant traits only"}],
 "panels": [
   {"idx":1, "kind":"ambiance|dialogue", "who":"a|b|null",
    "prompt":"english visual tags for THIS panel only",
    "dialogue":"the spoken line, or empty",
    "note":"one short note in FRENCH on the intent of this panel"}
 ]
}"""


def ask(sys_prompt, user, max_tokens=2600, model="pixtral-12b-latest"):
    body = {"model": model, "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user}],
        "max_tokens": max_tokens, "temperature": 0.7}
    req = urllib.request.Request(GATEWAY + "/api/mistral", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + SECRET,
                                          "User-Agent": "manga-studio/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = json.load(r)["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw[:4].lower() == "json":
            raw = raw[4:]
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("pas de JSON dans la reponse : " + raw[:200])
    return json.loads(raw[a:b + 1])


def storyboard(premisse, n=6, lang="francais", style="", model="pixtral-12b-latest"):
    u = ("Premise: %s\n\nPanels: exactly %d.\nDialogue language: %s.\n%s"
         % (premisse, n, lang,
            ("Visual style constraint: %s\n" % style) if style else ""))
    d = ask(SYS, u, model=model)
    # Garde-fous : on ne fait pas confiance au modele sur la forme.
    d.setdefault("panels", [])
    d["panels"] = d["panels"][:n]
    for i, p in enumerate(d["panels"], 1):
        p["idx"] = i
        if p.get("kind") not in ("ambiance", "dialogue"):
            p["kind"] = "dialogue"
        p["prompt"] = (p.get("prompt") or "").strip()
        p["dialogue"] = (p.get("dialogue") or "").strip()
    return d


def rendu(d):
    out = []
    out.append("TITRE   : %s" % d.get("title", "?"))
    out.append("DECOR   : %s" % d.get("setting", "?"))
    for c in d.get("cast", []):
        out.append("PERSO %-2s: %s — %s" % (c.get("id", "?"), c.get("name", "?"), c.get("look", "")))
    out.append("")
    amb = sum(1 for p in d["panels"] if p["kind"] == "ambiance")
    muet = sum(1 for p in d["panels"] if not p["dialogue"])
    out.append("%d cases · %d ambiance / %d dialogue · %d muette(s)"
               % (len(d["panels"]), amb, len(d["panels"]) - amb, muet))
    out.append("")
    for p in d["panels"]:
        out.append("  [%d] %-9s %s" % (p["idx"], p["kind"], p["prompt"][:78]))
        if p["dialogue"]:
            out.append("      « %s »" % p["dialogue"])
        if p.get("note"):
            out.append("      (%s)" % p["note"][:76])
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("premisse", nargs="*")
    ap.add_argument("--fichier", default="")
    ap.add_argument("--cases", type=int, default=6)
    ap.add_argument("--lang", default="francais")
    ap.add_argument("--style", default="")
    ap.add_argument("--json", default="", help="ecrire le resultat dans ce fichier")
    a = ap.parse_args()

    prem = " ".join(a.premisse).strip()
    if a.fichier:
        prem = open(a.fichier, encoding="utf-8").read().strip()
    if not prem:
        print("Donne une premisse. Exemple :")
        print('  python storyboard.py "un duel de mechas sur une station orbitale"')
        return 2

    d = storyboard(prem, a.cases, a.lang, a.style)
    print(rendu(d))
    if a.json:
        json.dump(d, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n-> %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
