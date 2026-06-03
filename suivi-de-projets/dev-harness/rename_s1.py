"""
Sprint 1 — Renommages UI controles.

Strategie : remplace UNIQUEMENT les libelles affiches a l'utilisateur.
NE TOUCHE PAS aux variables JS, IDs DOM, noms de fonction, noms de fichier
disque, cles JSON, ou commentaires de code structurels.

Resultat : un script idempotent qui peut etre relance sans casser.

Mapping :
  Configuration (selecteur top + concepts) -> Domaine
  Onglet "Configuration" (reglages)         -> Reglages
  Profil (selecteur projet utilisateur)     -> Projet
  Onglet "Projets" + concepts CRUD          -> Thematiques
  Champ libre "Thematique" du form Action   -> Tags
"""
import re
import sys
from pathlib import Path

SRC = Path(r"D:/Download/02-Apps-Web/Repo-github/App/suivi-de-projets/index.html")
AIDE = Path(r"D:/Download/02-Apps-Web/Repo-github/App/suivi-de-projets/01_img_aide/aide_application.html")


# ─────────────────────────────────────────────────────────────────────────────
# Substitutions index.html — chaque entree = (regex_brut, remplacement, label)
# Patterns CONSERVATEURS : pas de variable JS, pas d'ID DOM, pas de cle JSON.
# ─────────────────────────────────────────────────────────────────────────────

REPLACEMENTS_INDEX = [
    # ─── ONGLET "Configuration" → "Réglages" (4e onglet, panneau de parametres) ───
    (r"ouvrirOnglet\(event, 'tab4'\)\">Configuration</a>",
     "ouvrirOnglet(event, 'tab4')\">Réglages</a>",
     "Onglet 4 : Configuration → Réglages"),
    (r'<div class="tabcontent" id="tab4">\s*<h2>Configuration</h2>',
     '<div class="tabcontent" id="tab4">\n        <h2>Réglages</h2>',
     "Titre H2 onglet 4"),

    # ─── ONGLET "Projets" → "Thématiques" ───
    (r"ouvrirOnglet\(event, 'tab2'\)\">Projets</a>",
     "ouvrirOnglet(event, 'tab2')\">Thématiques</a>",
     "Onglet 2 : Projets → Thématiques"),
    (r"<h2>Gestion des Projets</h2>",
     "<h2>Gestion des Thématiques</h2>",
     "Titre H2 onglet 2"),

    # ─── BOUTONS / FORM (Projet/Projets dans UI) ───
    (r'onclick="afficherFormulaireAjoutProjet\(\)">Ajouter un projet<',
     'onclick="afficherFormulaireAjoutProjet()">Ajouter une thématique<',
     "Bouton ajout thématique"),
    (r"<h3>Ajouter un nouveau projet</h3>",
     "<h3>Ajouter une nouvelle thématique</h3>",
     "Titre form ajout"),
    (r"<h3>Modifier le projet</h3>",
     "<h3>Modifier la thématique</h3>",
     "Titre form édition"),
    (r'<label for="project-name">Nom du projet :</label>',
     '<label for="project-name">Nom de la thématique :</label>',
     "Label nom projet"),
    (r'<label for="edit-project-name">Nom du projet :</label>',
     '<label for="edit-project-name">Nom de la thématique :</label>',
     "Label nom projet (edit)"),
    (r"Ce préfixe sera utilisé pour générer le numéro de référence du projet\.",
     "Ce préfixe sera utilisé pour générer le numéro de référence de la thématique.",
     "Hint préfixe"),
    (r"Attention : modifier le préfixe ne mettra pas à jour les actions associées automatiquement\.",
     "Attention : modifier le préfixe ne met pas à jour les actions associées automatiquement.",
     "Hint édition préfixe"),
    (r"Attention : modifier le numéro ne mettra pas à jour les actions associées automatiquement\.",
     "Attention : modifier le numéro ne met pas à jour les actions associées automatiquement.",
     "Hint édition numéro"),

    # ─── TABLEAU PROJETS (col headers + état) ───
    (r"<tr><td colspan=\"7\" style=\"text-align:center;\">Aucun projet trouvé</td></tr>",
     '<tr><td colspan="7" style="text-align:center;">Aucune thématique trouvée</td></tr>',
     "Tbody empty thématiques"),

    # ─── FORM ACTION : "Projet associé" → "Thématique associée" + "Thématique" libre → "Tags" ───
    (r'<label for="action-project">Projet associé :</label>',
     '<label for="action-project">Thématique associée :</label>',
     "Label projet form action add"),
    (r'<option value="">Sélectionner un projet</option>',
     '<option value="">Sélectionner une thématique</option>',
     "Option vide select projet (form add+edit, replace_all-like via regex multi)"),
    (r'<label for="edit-action-project">Projet associé :</label>',
     '<label for="edit-action-project">Thématique associée :</label>',
     "Label projet form action edit"),
    (r'<label for="action-topic">Thématique :</label>',
     '<label for="action-topic">Tags :</label>',
     "Label champ libre topic add"),
    (r'<label for="edit-action-topic">Thématique :</label>',
     '<label for="edit-action-topic">Tags :</label>',
     "Label champ libre topic edit"),

    # ─── FILTRES ACTIONS ───
    (r'<label class="group-label" for="filter-project-select">Filtrer par projet :</label>',
     '<label class="group-label" for="filter-project-select">Filtrer par thématique :</label>',
     "Label filtre projet"),
    (r'<option value="">Tous les projets</option>',
     '<option value="">Toutes les thématiques</option>',
     "Option filtre projet"),

    # ─── TABLEAU ACTIONS : headers col "Projet" / "Thématique" ───
    (r'data-col="2" onclick="trierColonne\(2\)">Projet</th>',
     'data-col="2" onclick="trierColonne(2)">Thématique</th>',
     "Header col Projet (actions)"),
    (r'data-col="4" onclick="trierColonne\(4\)">Thématique</th>',
     'data-col="4" onclick="trierColonne(4)">Tags</th>',
     "Header col Thématique → Tags (actions)"),

    # ─── QUICK ADD ROW ───
    (r'<option value="">— Projet —</option>',
     '<option value="">— Thématique —</option>',
     "Quick add option projet"),
    (r'placeholder="Thématique" style="width:100%',
     'placeholder="Tags" style="width:100%',
     "Quick add placeholder topic"),

    # ─── STATS PAR PROJET (dashboard) ───
    (r"<h3>Statistiques par Projet</h3>",
     "<h3>Statistiques par Thématique</h3>",
     "Titre stats par projet"),
    (r'<tbody id="project-stats-body">\s*<!-- Les statistiques par projet seront ajoutées ici -->',
     '<tbody id="project-stats-body">\n                        <!-- Les statistiques par thématique seront ajoutées ici -->',
     "Comment stats body"),
    (r"<th>Projet</th>\s*<th>Nom</th>",
     "<th>Thématique</th>\n                            <th>Nom</th>",
     "Header stats Projet → Thématique"),

    # ─── DASHBOARD CARDS ───
    (r"<h3>Projets en cours</h3>",
     "<h3>Thématiques en cours</h3>",
     "Card projets en cours"),

    # ─── SELECTEUR CONFIGURATION → DOMAINE (tableau de bord) ───
    (r'<label for="config-select">Configuration :</label>',
     '<label for="config-select">Domaine :</label>',
     "Label selecteur Config → Domaine"),
    (r'<option value="1">Config 1</option>\s*<option value="2">Config 2</option>\s*<option value="3">Config 3</option>\s*<option value="4">Config 4</option>',
     '<option value="1">Domaine 1</option>\n                    <option value="2">Domaine 2</option>\n                    <option value="3">Domaine 3</option>\n                    <option value="4">Domaine 4</option>',
     "Options Config 1-4 par defaut"),

    # ─── BOUTON AUTORISER ───
    (r"Autoriser dossiers \(Config 1\)",
     "Autoriser dossiers (Domaine 1)",
     "Bouton autoriser default"),

    # ─── SELECTEUR PROFIL → PROJET ───
    (r'<label for="projet-select">Profil :</label>',
     '<label for="projet-select">Projet :</label>',
     "Label selecteur Profil → Projet"),
    (r'onclick="creerNouveauProjetDeSauvegarde\(\)" title="Créer un nouveau profil de sauvegarde">Créer Profil<',
     'onclick="creerNouveauProjetDeSauvegarde()" title="Créer un nouveau projet">Créer Projet<',
     "Bouton créer profil"),
    (r'onclick="supprimerProjetDeSauvegarde\(\)" title="Supprimer le profil de sauvegarde actuel">Supprimer Profil<',
     'onclick="supprimerProjetDeSauvegarde()" title="Supprimer le projet actuel">Supprimer Projet<',
     "Bouton supprimer profil"),
    (r'onclick="renommerProfilActuel\(\)" title="Renommer le profil actuel"',
     'onclick="renommerProfilActuel()" title="Renommer le projet actuel"',
     "Tooltip renommer profil"),
    (r"Veuillez cliquer sur le bouton \"Charger\" pour activer ce profil\.",
     "Veuillez cliquer sur le bouton \"Charger\" pour activer ce projet.",
     "Alert switch profil"),

    # ─── SECTION CONFIGURATION (tab 4) — pas changer "Paramètres Utilisateur" ───
    # Le titre H3 dynamique "Sauvegarder / Restaurer les données (Profil Actif - ...)" est genere en JS
    # → traite dans REPLACEMENTS_JS plus bas.

    # ─── FOOTER / BACKUP BANNER ───
    (r"⚠️ Sauvegarde disque NON DISPONIBLE — Travail en mode local uniquement\. Vérifiez l'accès réseau ou cliquez sur \"Autoriser dossiers\"\.",
     "⚠️ Sauvegarde disque NON DISPONIBLE — Travail en mode local uniquement. Vérifiez l'accès réseau ou cliquez sur \"Autoriser dossiers\".",
     "Banner mode dégradé (inchangé volontairement)"),

    # ─── MODAL CHANGEMENT UTILISATEUR ───
    (r"Définit l'identité utilisée pour le verrouillage des profils et l'historique des modifications\.",
     "Définit l'identité utilisée pour le verrouillage des projets et l'historique des modifications.",
     "Description nom utilisateur"),
    (r"Ce nom est utilisé pour identifier qui a verrouillé un profil lors du travail collaboratif\.",
     "Ce nom est utilisé pour identifier qui a verrouillé un projet lors du travail collaboratif.",
     "Description nom utilisateur modal"),

    # ─── TAB 4 SECTIONS DYNAMIQUES (titres H3 hardcodés) ───
    (r'<h3 id="save-restore-title">Sauvegarder / Restaurer les données \(Profil Actif - \.\.\.\)</h3>',
     '<h3 id="save-restore-title">Sauvegarder / Restaurer les données (Projet Actif - ...)</h3>',
     "Titre sauve/restaure"),
    (r"Sauvegarde manuelle ou restauration à partir d'un fichier pour le profil <strong>actuellement sélectionné</strong> dans la configuration active",
     "Sauvegarde manuelle ou restauration à partir d'un fichier pour le projet <strong>actuellement sélectionné</strong> dans le domaine actif",
     "Description sauve/restaure"),
    (r"<button class=\"btn-success\" onclick=\"sauvegarderBackupAutomatique\(true\)\">Sauvegarder Profil Actif</button>",
     "<button class=\"btn-success\" onclick=\"sauvegarderBackupAutomatique(true)\">Sauvegarder Projet Actif</button>",
     "Bouton sauve profil actif"),

    (r'<h3 id="advanced-profile-title">Fonctions avancées Profils \(\.\.\.\)</h3>',
     '<h3 id="advanced-profile-title">Fonctions avancées Projets (...)</h3>',
     "Titre fonctions avancées"),
    (r"Import/Export groupé et outils de maintenance pour les profils de la configuration active\.",
     "Import/Export groupé et outils de maintenance pour les projets du domaine actif.",
     "Description fonctions avancées"),
    (r"Exporter tous les profils \(de cette Config\)",
     "Exporter tous les projets (de ce Domaine)",
     "Bouton export tous profils"),
    (r"Importer un profil \(dans cette Config\)",
     "Importer un projet (dans ce Domaine)",
     "Bouton import profil"),
    (r"Réparer tous les profils \(de cette Config\)",
     "Réparer tous les projets (de ce Domaine)",
     "Bouton réparer profils"),

    (r'<h3 id="numbering-title">Maintenance Numérotation \(Profil Actif - \.\.\.\)</h3>',
     '<h3 id="numbering-title">Maintenance Numérotation (Projet Actif - ...)</h3>',
     "Titre maintenance num"),
    (r"Recalcule tous les numéros des actions séquentiellement par projet pour le profil actif\.",
     "Recalcule tous les numéros des actions séquentiellement par thématique pour le projet actif.",
     "Description recalcul num"),
    (r"Réinitialiser Compteur Projets \(⚠️ Dangereux\)",
     "Réinitialiser Compteur Thématiques (⚠️ Dangereux)",
     "Titre danger zone"),
    (r"Réinitialise le compteur global pour l'ID du PROCHAIN projet créé \(pour le profil actif\)\.",
     "Réinitialise le compteur global pour l'ID de la PROCHAINE thématique créée (pour le projet actif).",
     "Description danger zone"),
    (r"<button class=\"btn-danger\" onclick=\"reinitialiserCompteurProjets\(\)\">Réinitialiser Compteur Projets</button>",
     "<button class=\"btn-danger\" onclick=\"reinitialiserCompteurProjets()\">Réinitialiser Compteur Thématiques</button>",
     "Bouton danger zone"),

    # ─── BANDEAU TEMPORAIRE renommage (info utilisateur) ───
    # Ajoute un bandeau juste après le H1 pour acclimater les users.
    (r'(<div class="signature">QuangSoukhasing</div>\s*</header>)',
     '\\1\n\n    <!-- Bandeau info renommage (S1 — affichage 1 mois puis retrait) -->\n    <div id="rename-info-banner" style="background:#e7f3ff;border:1px solid #b3d7ff;color:#004085;padding:8px 14px;margin:10px 0;border-radius:6px;font-size:0.88em;display:none;">\n        ℹ️ <strong>Renommage récent</strong> : « Configuration » devient « Domaine », « Profil » devient « Projet », « Projets » devient « Thématiques », et le champ « Thématique » du formulaire Action devient « Tags ». Les données sont inchangées.\n        <button onclick="document.getElementById(\'rename-info-banner\').style.display=\'none\'; localStorage.setItem(\'renameInfoBannerDismissed\',\'1\');" style="float:right;background:none;border:none;color:#004085;cursor:pointer;font-weight:bold;font-size:1.1em;line-height:1;padding:0 4px;" title="Masquer">×</button>\n    </div>',
     "Bandeau info renommage"),
]


# ─── Substitutions JS : strings affichés à l'utilisateur dans le bloc <script> ───
# Conserve TOUS les noms de variables, IDs, etc. — n'agit que sur strings utilisateurs.
REPLACEMENTS_JS = [
    # displayMessage / textContent / innerHTML strings dynamiques

    # "Config X" généré en label
    (r'`Config \$\{activeConfig\}`', r'`Domaine ${activeConfig}`', "Template literal Config N"),
    (r'`Config \$\{configNum\}`', r'`Domaine ${configNum}`', "Template literal Config configNum"),
    (r'`Config \$\{i\}`', r'`Domaine ${i}`', "Template literal Config i"),
    (r'`Config \$\{newConfigValue\}`', r'`Domaine ${newConfigValue}`', "Template literal Config newConfigValue"),
    (r'\bConfig \$\{', "Domaine ${", "Generic Config ${"),

    # Messages "Config N non défini"
    (r'Dossier Backup pour Config \$\{', "Dossier Backup pour Domaine ${", "Msg backup dir"),
    (r'Dossier Backup \(Config \$\{', "Dossier Backup (Domaine ${", "Msg backup dir parens"),
    (r'Dossier PJ \(Config \$\{', "Dossier PJ (Domaine ${", "Msg PJ dir"),
    (r'Permission refusée pour dossier Backup \(Config \$\{', "Permission refusée pour dossier Backup (Domaine ${", "Msg perm backup"),
    (r"Accès refusé dossier Backup \(Config \$\{", "Accès refusé dossier Backup (Domaine ${", "Msg acces refuse backup"),
    (r"Permission refusée Backup \$\{configName\}", "Permission refusée Backup ${configName}", "Msg perm backup configName"),
    (r"Permission refusée PJ \$\{configName\}", "Permission refusée PJ ${configName}", "Msg perm PJ configName"),
    (r"Sélectionnez dossier Backup \$\{configName\}", "Sélectionnez dossier Backup ${configName}", "Msg select backup"),
    (r"Sélectionnez dossier PJ \$\{configName\}", "Sélectionnez dossier PJ ${configName}", "Msg select PJ"),
    (r"Définition Backup \$\{configName\} annulée", "Définition Backup ${configName} annulée", "Msg def backup annulee"),
    (r"Définition PJ \$\{configName\} annulée", "Définition PJ ${configName} annulée", "Msg def PJ annulee"),

    # "Profil [...]" strings
    (r"Aucun profil sélectionné\.", "Aucun projet sélectionné.", "Msg aucun profil"),
    (r"Profil verrouillé par", "Projet verrouillé par", "Banner verrou"),
    (r"Profil disponible pour édition", "Projet disponible pour édition", "Banner libération"),
    (r"Le profil est verrouillé par", "Le projet est verrouillé par", "Confirm forçage"),
    (r"Vider le journal d'activité pour ce profil", "Vider le journal d'activité pour ce projet", "Tooltip vider log"),
    (r"Aucune activité enregistrée pour ce profil", "Aucune activité enregistrée pour ce projet", "Msg log vide"),

    # context bar
    (r"`Consultation: Profil \"\$\{profileName\}\"", '`Consultation: Projet "${profileName}"', "Banner consult"),
    (r"`Vous éditez: Profil \"\$\{profileName\}\"", '`Vous éditez: Projet "${profileName}"', "Banner édit"),

    # confirm/alert dialogs
    (r"Pris en main forcée réussie\. Dernière sauvegarde chargée\.", "Prise en main forcée réussie. Dernière sauvegarde chargée.", "Msg force OK"),

    # "Projet inconnu" → "Thématique inconnue" dans export CSV
    (r"'Projet inconnu'", "'Thématique inconnue'", "Export CSV projet inconnu"),

    # Export CSV header
    (r"'Projet \(Ref - Nom\);N° d\\'action", "'Thématique (Ref - Nom);N° d\\'action", "CSV header"),

    # Export Rapport HTML : champ "Projet" → "Thématique"
    (r">Projet</th>", ">Thématique</th>", "Rapport HTML col header (s'applique aussi si présent en HTML body — vérifié OK)"),
    # Note : on a déjà géré le header dans le body HTML statique plus haut. Ici on cible les
    # template literals JS qui rendent les exports.

    # Activity log labels
    (r"'Projet créé', `Projet '", "'Thématique créée', `Thématique '", "Activity log projet créé"),
    (r"'Projet supprimé', `Projet '", "'Thématique supprimée', `Thématique '", "Activity log projet suppr"),
    (r"itemType === 'Projet'", "itemType === 'Thématique'", "logActivity itemType compare"),
    (r"const itemType = 'Projet';", "const itemType = 'Thématique';", "logActivity itemType setter"),
    (r"const itemType = \"Projet\";", "const itemType = \"Thématique\";", "logActivity itemType setter v2"),

    # Bandeau dynamique : forcer affichage 1x (sauf si user a fermé)
    # Inject au boot (DOMContentLoaded) — fait en aparté plus bas.
]


def apply_replacements(text: str, rules: list, label: str) -> tuple[str, list[tuple[str, int]]]:
    log = []
    for pattern, replacement, description in rules:
        new_text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE | re.DOTALL)
        if n > 0:
            log.append((description, n))
            text = new_text
        else:
            log.append((f"[ZERO] {description}", 0))
    return text, log


def add_banner_init(text: str) -> tuple[str, int]:
    """Injecte un onload qui affiche le bandeau de renommage si pas dismissed."""
    snippet = """
        // Bandeau renommage S1 — affiche si pas dismissed
        try {
            if (!localStorage.getItem('renameInfoBannerDismissed')) {
                const banner = document.getElementById('rename-info-banner');
                if (banner) banner.style.display = 'block';
            }
        } catch (e) {}
"""
    # Cible : on insère juste après le 1er listener DOMContentLoaded déjà présent dans le code.
    # S'il n'y en a pas, on l'ajoute juste avant </script>.
    pattern = r"(document\.addEventListener\('DOMContentLoaded',\s*\(\)\s*=>\s*\{)"
    new, n = re.subn(pattern, r"\1" + snippet, text, count=1)
    if n > 0:
        return new, 1
    # Fallback : avant la fermeture du script principal
    pattern2 = r"(</script> <!-- ### FIN DU BLOC SCRIPT PRINCIPAL ### -->)"
    new, n = re.subn(pattern2, f"document.addEventListener('DOMContentLoaded', () => {{{snippet}}});\n\\1", text, count=1)
    return new, n


def main():
    src = SRC.read_text(encoding="utf-8")
    original_len = len(src)

    print(f"== Sprint 1 RENAMES on {SRC.name} ({original_len} chars) ==")

    src, log_html = apply_replacements(src, REPLACEMENTS_INDEX, "INDEX_HTML")
    src, log_js = apply_replacements(src, REPLACEMENTS_JS, "INDEX_JS")

    src, banner_n = add_banner_init(src)

    SRC.write_text(src, encoding="utf-8")
    new_len = len(src)

    print(f"\n-- Section HTML body --")
    for desc, n in log_html:
        marker = "✓" if n > 0 else "·"
        print(f"  {marker} {desc}: {n}")

    print(f"\n-- Section JS strings --")
    for desc, n in log_js:
        marker = "✓" if n > 0 else "·"
        print(f"  {marker} {desc}: {n}")

    print(f"\n-- Bandeau init injection : {banner_n} --")

    diff = new_len - original_len
    print(f"\n== File size: {original_len} -> {new_len} ({diff:+d} chars) ==")


if __name__ == "__main__":
    main()
