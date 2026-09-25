# -*- coding: utf-8 -*-
"""Patch du proxy : deux routes qui ne dependent PAS du moteur local (Manga Studio v2.46.0, 25/09/2026).

Constat (mesure 25/09, moteur eteint, un chapitre ouvert 60 s) : 10 reponses 502 -- sondes /comfy/system_stats (6),
listes LoRA / checkpoints (2) et SURTOUT 2 images /comfy/view : les references des personnages sont des FICHIERS du
disque (ComfyUI/input), mais l'app les demandait au moteur -> moteur eteint = references invisibles.
Meme defaut que Generate Studio v5.69 (/output_file), meme remede :
  GET /manga/comfy_file?filename=&type=input|output|temp&subfolder=   lecture DIRECTE sur le disque, confinee
  GET /manga/comfy_up                                                  {"up": bool, "stats": {...}} -- toujours 200
Rejouable : python patch_comfy_hors_moteur.py <chemin du proxy>. Ancre verifiee ; fins de ligne du fichier conservees.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in s else "\n"
MARQUE = "/manga/comfy_file"
if MARQUE in s:
    print("deja patche"); sys.exit(0)

# 1. la methode qui sert un fichier de ComfyUI depuis le disque (inseree avant serve_output_file)
A1 = "    def serve_output_file(self, rel):" + NL
M = [
    "    def serve_comfy_file(self, q):",
    '        """Manga Studio v2.46.0 : un fichier de ComfyUI (input / output / temp) lu SUR LE DISQUE, moteur allume ou non.',
    "        Confinement : la cible normalisee doit retomber SOUS le dossier du type (couvre les .. et les chemins absolus).\"\"\"",
    '        typ = (q.get("type") or ["output"])[0]',
    '        racines = {"input": COMFY_INPUT_DIR, "output": OUT_ROOT, "temp": os.path.join(os.path.dirname(OUT_ROOT), "temp")}',
    "        if typ not in racines:",
    '            self._json(400, {"error": "type inconnu"}); return',
    "        root = os.path.normpath(racines[typ])",
    '        nom = (q.get("filename") or [""])[0].replace("\\\\", "/")',
    '        sous = (q.get("subfolder") or [""])[0].replace("\\\\", "/").strip("/")',
    '        if not nom or "/" in nom:',
    '            self._json(400, {"error": "nom invalide"}); return',
    "        target = os.path.normpath(os.path.join(root, sous, nom))",
    "        if not target.startswith(root + os.sep):",
    '            self._json(403, {"error": "chemin hors du dossier"}); return',
    "        if not os.path.isfile(target):",
    '            self._json(404, {"error": "not found"}); return',
    '        ctype = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",',
    '                 ".gif": "image/gif"}.get(os.path.splitext(target)[1].lower())',
    "        if not ctype:",
    '            self._json(415, {"error": "type de fichier non servi"}); return',
    '        with open(target, "rb") as f:',
    "            data = f.read()",
    "        self.send_response(200); self._cors()",
    '        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))',
    '        self.send_header("Cache-Control", "no-cache"); self.end_headers()',
    "        self.wfile.write(data)",
]
B1 = NL.join(M) + NL + A1

# 2. les deux routes GET, a cote de /manga/gpu
A2 = '        elif self.path.split("?", 1)[0] == "/manga/gpu":                   # Manga Studio v2.10.0' + NL
R = [
    '        elif self.path.split("?", 1)[0] == "/manga/comfy_file":            # Manga Studio v2.46.0 : disque, sans moteur',
    "            self.serve_comfy_file(parse_qs(urlparse(self.path).query))",
    '        elif self.path.split("?", 1)[0] == "/manga/comfy_up":              # Manga Studio v2.46.0 : sonde sans 502',
    "            try:",
    '                self._json(200, {"up": True, "stats": _get_json(COMFY + "/system_stats", timeout=3)})',
    "            except Exception:",
    '                self._json(200, {"up": False})',
]
B2 = NL.join(R) + NL + A2

for a in (A1, A2):
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:60]))
s = s.replace(A1, B1, 1).replace(A2, B2, 1)
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
