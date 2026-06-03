"""Sprint 1b — Finir les renommages residuels user-facing."""
import re
from pathlib import Path

SRC = Path(r"D:/Download/02-Apps-Web/Repo-github/App/suivi-de-projets/index.html")

# (pattern, replacement, label) — strings user-facing dans JS uniquement
RULES = [
    # Confirms / prompts / alerts
    (r"Êtes-vous sûr de vouloir vider TOUT le journal d'activité pour ce profil \?",
     "Êtes-vous sûr de vouloir vider TOUT le journal d'activité pour ce projet ?",
     "Confirm vider log"),
    (r"a pris le contrôle de ce profil !",
     "a pris le contrôle de ce projet !",
     "Alert takeover"),
    # Banner takeover topBanner
    (r"\) - Profil \"\$\{profileName\}\" \(\$\{currentConfigName\}\)",
     ') - Projet "${profileName}" (${currentConfigName})',
     "TopBanner takeover"),
    # Tab 4 titres dynamiques
    (r"Sauvegarder / Restaurer les données \(Profil Actif - \$\{activeName\}\)",
     "Sauvegarder / Restaurer les données (Projet Actif - ${activeName})",
     "Save/restore dynamic title"),
    (r"Fonctions avancées Profils \(\$\{activeName\}\)",
     "Fonctions avancées Projets (${activeName})",
     "Advanced title"),
    (r"Maintenance Numérotation \(Profil Actif - \$\{activeName\}\)",
     "Maintenance Numérotation (Projet Actif - ${activeName})",
     "Numbering title"),
    # Profils data / handles
    (r"Erreur lecture fichier profils \(\$\{profilesFilename\}\)\.",
     "Erreur lecture fichier projets (${profilesFilename}).",
     "Read profiles file error"),
    (r"Liste profils non sauvée\.",
     "Liste projets non sauvée.",
     "List profiles save warn"),
    (r"Erreur écriture fichier profils \(\$\{profilesFilename\}\)\.",
     "Erreur écriture fichier projets (${profilesFilename}).",
     "Write profiles file error"),
    # User actions
    (r"Veuillez d\\'abord cliquer sur \"Charger\" avant de changer de profil\.",
     "Veuillez d\\'abord cliquer sur \"Charger\" avant de changer de projet.",
     "Charge before switch"),
    (r"Chargement du profil\.\.\.",
     "Chargement du projet...",
     "Loading profile"),
    (r"showToast\('Profil chargé',",
     "showToast('Projet chargé',",
     "Toast profile loaded"),
    (r"Erreur chargement profil\. Cliquez sur Charger manuellement\.",
     "Erreur chargement projet. Cliquez sur Charger manuellement.",
     "Error load profile"),
    (r"Profil \"\$\{getProjectSaveName\(selectedProjectSaveId\)\}\" sélectionné\. Cliquez sur \"Charger\" pour l\\'activer\.",
     'Projet "${getProjectSaveName(selectedProjectSaveId)}" sélectionné. Cliquez sur "Charger" pour l\\\'activer.',
     "Profile selected"),
    (r"Un profil avec ce nom existe déjà\.",
     "Un projet avec ce nom existe déjà.",
     "Profile exists"),
    (r"Profil '\$\{profileName\.trim\(\)\}' créé\.",
     "Projet '${profileName.trim()}' créé.",
     "Log profile created"),
    (r"Profil introuvable\.",
     "Projet introuvable.",
     "Profile not found"),
    (r"Entrez le nouveau nom pour ce profil:",
     "Entrez le nouveau nom pour ce projet:",
     "Prompt rename"),
    (r"Un autre profil utilise déjà ce nom\.",
     "Un autre projet utilise déjà ce nom.",
     "Other profile uses name"),
    (r"Profil renommé: '\$\{ancienNom\}' → '\$\{nouveauNom\.trim\(\)\}'\.",
     "Projet renommé: '${ancienNom}' → '${nouveauNom.trim()}'.",
     "Log profile renamed"),
    (r"Profil renommé en \"\$\{nouveauNom\}\"\.",
     'Projet renommé en "${nouveauNom}".',
     "Profile renamed msg"),
    (r"if \(currentText\.includes\(\"Profil\"\)\) \{ topBanner\.textContent = currentText\.replace\(/Profil \".\*\?\"/, `Profil \"\$\{profil\.name\}\"`\); \}",
     'if (currentText.includes("Projet")) { topBanner.textContent = currentText.replace(/Projet ".*?"/, `Projet "${profil.name}"`); }',
     "TopBanner rename refresh"),
    (r"Impossible de supprimer le dernier profil\.",
     "Impossible de supprimer le dernier projet.",
     "Cannot delete last"),
    (r"Supprimer le profil \"\$\{profileNameToDelete\}\" \?",
     'Supprimer le projet "${profileNameToDelete}" ?',
     "Confirm delete"),
    (r"Suppression du profil \"\$\{profileNameToDelete\}\"\.\.\.",
     'Suppression du projet "${profileNameToDelete}"...',
     "Deleting"),
    (r"Profil \"\$\{profileNameToDelete\}\" supprimé\.",
     'Projet "${profileNameToDelete}" supprimé.',
     "Deleted msg"),
    (r"Erreur lors de la suppression du profil : \$\{e\.message\}",
     "Erreur lors de la suppression du projet : ${e.message}",
     "Delete error"),
    (r"Recalculer tous les numéros d\\'actions pour ce profil \?",
     "Recalculer tous les numéros d\\'actions pour ce projet ?",
     "Confirm recalc"),
    (r"Aucune action trouvée pour ce profil",
     "Aucune action trouvée pour ce projet",
     "No action found"),
    # Comments user-facing dans contextBar / data stores (ne pas refactor, juste cosmétique)
    # Comments internal restent en français = OK.
]


def main():
    s = SRC.read_text(encoding="utf-8")
    orig_len = len(s)
    print(f"== Sprint 1b RESIDUS on {SRC.name} ({orig_len} chars) ==\n")
    total_replacements = 0
    for pattern, repl, label in RULES:
        new, n = re.subn(pattern, repl, s, flags=re.MULTILINE | re.DOTALL)
        marker = "OK" if n > 0 else "--"
        print(f"  [{marker}] {label}: {n}")
        if n > 0:
            s = new
            total_replacements += n
    SRC.write_text(s, encoding="utf-8")
    print(f"\n== {total_replacements} remplacements, taille: {orig_len} -> {len(s)} ==")


if __name__ == "__main__":
    main()
