"""Livraison Telegram du HTML final + note de release.
Bot principal Quang (token 8716414004, chat 5867229613).
Pattern Python urllib UTF-8 (curl casse les accents).
"""
import json
import sys
import urllib.request
from pathlib import Path

BOT_TOKEN = "8716414004:AAFVSPchPl236LCgA2H9UPp0xx8EQcM7h_E"
CHAT_ID = "5867229613"
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

CAPTION = """📎 <b>Suivi de Projets — Refonte visionneuse Pièces Jointes</b>

Homonymes acceptés + anti-latence VPN (cache) + navigation Préc/Suiv + lecture vidéo/audio + bouton Retour galerie.

Détail dans le message suivant. GitHub : <code>quang101182/App</code> main (commit d9d581a)."""


def main():
    print("[telegram] envoi du document...")
    res_doc = send_document(HTML_PATH, CAPTION)
    print(json.dumps(res_doc, indent=2, ensure_ascii=False)[:500])
    if not res_doc.get("ok"):
        print("[telegram] echec doc")
        sys.exit(1)

    note = (
        "📝 <b>Détail — Refonte Pièces Jointes</b>\n\n"
        "<b>A — Doublons de nom</b>\n"
        "• Un fichier de même nom est désormais ACCEPTÉ et renommé auto (photo.png → photo_1.png)\n"
        "• Le dossier PJ étant partagé, l'unicité reste garantie au moment de l'enregistrement\n"
        "• Seul un vrai re-clic du MÊME fichier (nom+taille+date) est ignoré\n\n"
        "<b>B — Latence réseau / VPN</b>\n"
        "• Cache : chaque PJ n'est lue qu'une seule fois depuis le réseau\n"
        "• Galerie qui s'ouvre instantanément (vignettes chargées en parallèle)\n"
        "• Préchargement des PJ voisines pour une navigation fluide\n"
        "• Fuite mémoire d'origine corrigée\n\n"
        "<b>C — Navigation</b>\n"
        "• Boutons Précédent / Suivant + flèches clavier ← →\n"
        "• Compteur « 2 / 5 — nom-du-fichier », bouclage aux extrémités\n\n"
        "<b>D — Vidéo / audio</b>\n"
        "• Lecture directe dans l'app (lecteur intégré) pour mp4, webm, audio…\n"
        "• MOV iPhone : lu si H.264 ; si codec non supporté (HEVC) → bouton « Télécharger pour lire »\n\n"
        "<b>+ Bouton « Retour galerie »</b>\n"
        "• Permanent en aperçu : marche pour vidéo / PDF / audio (plus seulement l'image)\n\n"
        "<b>Tests live</b> : Playwright Edge headless, vraies vidéos (MP4 & MOV) lues in-app, 0 erreur.\n"
        "Sauvegardes et noms de fichiers/verrous : format inchangé.\n\n"
        "Tout retour bienvenu — on ajuste."
    )
    print("[telegram] envoi note...")
    res_msg = send_message(note)
    print(json.dumps(res_msg, indent=2, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
