"""Livraison Telegram du HTML final + note de release.
Pattern Python urllib UTF-8 (curl casse les accents).

SECURITE — le token ne doit JAMAIS etre ecrit ici : ce fichier vit dans un depot
PUBLIC. Un token en clair y a ete expose du 03/06 au 01/08/2026, ramasse par un
robot, et le bot a ete detourne. Il se lit desormais depuis l'environnement, ou
a defaut depuis jarvis/.env (hors depot). Voir security-incident-2026-08-01/.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


def _load_bot_token() -> str:
    """1) variable d'environnement, 2) jarvis/.env (hors depot). Jamais en dur."""
    tok = os.environ.get("JARVIS_TELEGRAM_BOT_TOKEN")
    if tok:
        return tok.strip()
    env = Path(r"D:/Download/02-Apps-Web/Repo-github/jarvis/.env")
    if env.exists():
        m = re.search(r"^JARVIS_TELEGRAM_BOT_TOKEN\s*=\s*(\S+)", env.read_text(encoding="utf-8", errors="ignore"), re.M)
        if m:
            return m.group(1).strip("\"'")
    sys.exit(
        "[telegram] token introuvable.\n"
        "  -> definir JARVIS_TELEGRAM_BOT_TOKEN, ou renseigner jarvis/.env.\n"
        "  -> ne JAMAIS ecrire le token dans ce fichier (depot public)."
    )


BOT_TOKEN = _load_bot_token()
CHAT_ID = os.environ.get("JARVIS_TELEGRAM_CHAT_ID", "5867229613")
HTML_PATH = Path(r"D:/Download/02-Apps-Web/Repo-github/App/suivi-de-projets/index.html")


def send_document(file_path: Path, caption: str):
    """Multipart upload — RFC 7578 simple, sans dépendance."""
    boundary = "----TelegramDelivery1234567890"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"

    body = []
    # chat_id
    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body.append(f"{CHAT_ID}\r\n".encode())
    # caption
    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="caption"\r\n')
    body.append(b'Content-Type: text/plain; charset=utf-8\r\n\r\n')
    body.append(caption.encode("utf-8"))
    body.append(b"\r\n")
    # parse_mode
    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\n')
    body.append(b"HTML\r\n")
    # file
    body.append(f"--{boundary}\r\n".encode())
    body.append(
        f'Content-Disposition: form-data; name="document"; filename="{file_path.name}"\r\n'.encode()
    )
    body.append(b"Content-Type: text/html\r\n\r\n")
    body.append(file_path.read_bytes())
    body.append(b"\r\n")
    body.append(f"--{boundary}--\r\n".encode())

    payload = b"".join(body)
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


import urllib.parse  # noqa: E402

CAPTION = """🛠 <b>Suivi de Projets — Correction des bugs de création / changement de projet</b>

⚠️ <b>À faire AVANT de t'en servir : copie ton dossier Backup réseau.</b>

6 correctifs + les 3 boutons « Fonctions avancées » enfin implémentés.
Détail dans le message suivant. GitHub : <code>quang101182/App</code> main (commits 48bf185 + a78c583)."""


def main():
    print("[telegram] envoi du document...")
    res_doc = send_document(HTML_PATH, CAPTION)
    print(json.dumps(res_doc, indent=2, ensure_ascii=False)[:500])
    if not res_doc.get("ok"):
        print("[telegram] echec doc")
        sys.exit(1)

    note = (
        "📝 <b>Détail — ce qui était cassé et ce qui est corrigé</b>\n\n"
        "<b>1. « Le fichier disparaît, ça passe en lecture seule »</b>\n"
        "• Cause : à la création d'un projet, son fichier verrou n'était jamais créé. "
        "L'app se croyait en édition, puis sa surveillance (60 s) ne trouvait pas le verrou "
        "et concluait qu'un collègue avait pris la main.\n"
        "• Le message « (fichier disparu) » venait de l'app : rien n'avait disparu.\n"
        "• Corrigé : le verrou est pris à la création. Vérifié : plus aucune bascule après 65 s.\n\n"
        "<b>2. Les thématiques d'un autre projet qui s'affichent</b>\n"
        "• Cause : la sauvegarde automatique lisait le nom du fichier et les données à deux "
        "instants différents, séparés par des accès disque. En changeant de projet pendant "
        "ce laps de temps, les données d'un projet partaient dans le fichier d'un autre.\n"
        "• ⚠️ Et le projet d'origine se retrouvait avec une sauvegarde VIDE : il y avait "
        "perte de données, pas seulement un affichage trompeur.\n"
        "• Corrigé : sauvegarde atomique, abandonnée si le projet change en cours de route.\n\n"
        "<b>3. Danger caché : la suppression d'un projet</b>\n"
        "• Le dossier PJ est partagé et la suppression se fait par nom de fichier. "
        "Supprimer un projet « contaminé » effaçait les pièces jointes d'un AUTRE projet, "
        "définitivement. Ton intuition de ne pas y toucher était la bonne.\n"
        "• Corrigé : tout fichier encore utilisé par un autre projet est conservé.\n\n"
        "<b>4-6.</b> Sauvegarde locale de l'ancien projet qui était annulée · identité du "
        "projet inscrite dans chaque sauvegarde (une sauvegarde étrangère est refusée au lieu "
        "d'être affichée en silence) · indicateur de chargement dès le début du changement de projet.\n\n"
        "<b>⚙️ Fonctions avancées (Réglages)</b> — elles n'avaient jamais été écrites :\n"
        "• <b>Exporter</b> : archive JSON de tous les projets du domaine\n"
        "• <b>Importer</b> : recrée des projets, sans jamais écraser un existant\n"
        "• <b>Réparer</b> : analyse de cohérence + rapport détaillé\n"
        "Audit complet : 82 boutons vérifiés, ces 3 étaient les seuls morts.\n\n"
        "<b>🚨 Important — le correctif ne répare PAS l'existant</b>\n"
        "Il empêche que ça se reproduise. Tes 2 projets neufs restent contaminés.\n"
        "1) Copie ton dossier Backup réseau (la rotation à 10 sauvegardes peut purger les bonnes versions)\n"
        "2) Récupère une sauvegarde antérieure saine via le sélecteur « Sauvegarde »\n"
        "3) Tu peux ensuite supprimer les projets neufs sans risque pour tes PJ\n\n"
        "<b>Tests</b> : chaque bug reproduit en live AVANT correction, revérifié APRÈS. "
        "Le test de suppression échoue sur l'ancienne version et passe sur la nouvelle.\n"
        "Format des sauvegardes, noms de fichiers et verrous : inchangés.\n\n"
        "Non testé : vrai partage réseau et deux postes simultanés. Dis-moi ce que ça donne."
    )
    print("[telegram] envoi note...")
    res_msg = send_message(note)
    print(json.dumps(res_msg, indent=2, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
