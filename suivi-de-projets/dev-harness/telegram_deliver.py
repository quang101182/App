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

CAPTION = """📦 <b>Suivi de Projets — Livraison 4 sprints</b>

Renommages UI + statut/phase tech + PJ (10, multi, drag&drop) + polish a11y.

Détail dans le message suivant. GitHub : <code>quang101182/App</code> main."""


def main():
    print("[telegram] envoi du document...")
    res_doc = send_document(HTML_PATH, CAPTION)
    print(json.dumps(res_doc, indent=2, ensure_ascii=False)[:500])
    if not res_doc.get("ok"):
        print("[telegram] echec doc")
        sys.exit(1)

    note = (
        "📝 <b>Détail des 4 sprints</b>\n\n"
        "<b>S1 — Renommages</b>\n"
        "• Configuration → Domaine\n"
        "• Profil → Projet\n"
        "• Onglet Projets → Thématiques\n"
        "• Onglet Configuration → Réglages\n"
        "• Champ libre Thématique → Tags\n"
        "• Aide HTML synchronisée + bandeau info temporaire\n\n"
        "<b>S2 — Statut/Phase tech</b>\n"
        "• Restent séparés (option A) — visuels distincts\n"
        "• Constante STATUS centrale + helper isActionLate factorisé\n"
        "• Correction bug : KPI dashboard ignorait les actions « Bloqué » en retard\n"
        "• Doublon de fonction supprimé\n\n"
        "<b>S3 — Pièces jointes</b>\n"
        "• Limite 5 → 10\n"
        "• Sélection multiple + glisser-déposer\n"
        "• Auto-add (plus de bouton « Ajouter PJ »)\n"
        "• Compteur visuel (X/10) + zone saturée\n\n"
        "<b>S4 — Polish</b>\n"
        "• prefers-reduced-motion respecté\n"
        "• Badges compteurs sur les onglets Thématiques + Actions\n"
        "• Escape + clic backdrop unifiés sur 6 modales\n"
        "• Audit trail amélioré sur corruption localStorage\n\n"
        "<b>Effets de bord vérifiés</b>\n"
        "• Format JSON sauvegardes inchangé\n"
        "• Noms fichiers disque inchangés\n"
        "• Anciens préfixes PRJ-001 valides\n"
        "• Anciennes sauvegardes se rechargent 100%\n\n"
        "<b>Tests live</b> : Playwright Edge headless, captures resize ≤1800px, zero page_error.\n\n"
        "🧪 <b>À tester en vrai</b>\n"
        "1. Ouvrir index.html dans Edge\n"
        "2. Autoriser dossiers → choisir Backup + PJ\n"
        "3. Créer thématique + action + glisser-déposer 2-3 PJ\n"
        "4. Changer statut via badge inline → KPIs OK ?\n"
        "5. Escape sur modales\n\n"
        "Tout retour bienvenu — on ajuste."
    )
    print("[telegram] envoi note...")
    res_msg = send_message(note)
    print(json.dumps(res_msg, indent=2, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
