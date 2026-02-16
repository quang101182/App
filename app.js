// ============================================================
// Bloc-Notes Express - Application principale
// ============================================================

(function () {
    'use strict';

    // --- DOM Elements ---
    const textInput = document.getElementById('text-input');
    const fileContent = document.getElementById('file-content');
    const fileEmptyState = document.getElementById('file-empty-state');
    const fileName = document.getElementById('file-name');
    const lineBreaks = document.getElementById('line-breaks');
    const toast = document.getElementById('toast');

    // Buttons
    const btnCut = document.getElementById('btn-cut');
    const btnCopy = document.getElementById('btn-copy');
    const btnPaste = document.getElementById('btn-paste');
    const btnClear = document.getElementById('btn-clear');
    const btnValidate = document.getElementById('btn-validate');
    const btnDownload = document.getElementById('btn-download');
    const btnClearFile = document.getElementById('btn-clear-file');
    const btnRename = document.getElementById('btn-rename');
    const btnLbMinus = document.getElementById('btn-lb-minus');
    const btnLbPlus = document.getElementById('btn-lb-plus');

    // Settings
    const btnSettings = document.getElementById('btn-settings');
    const settingsModal = document.getElementById('settings-modal');
    const btnCloseSettings = document.getElementById('btn-close-settings');
    const btnSaveSettings = document.getElementById('btn-save-settings');
    const inputClientId = document.getElementById('input-client-id');
    const inputApiKey = document.getElementById('input-api-key');
    const inputFolderId = document.getElementById('input-folder-id');

    // Drive
    const btnDriveConnect = document.getElementById('btn-drive-connect');
    const btnDriveOpen = document.getElementById('btn-drive-open');
    const btnDriveSave = document.getElementById('btn-drive-save');
    const btnDriveSync = document.getElementById('btn-drive-sync');
    const driveStatus = document.getElementById('drive-status');

    // --- State ---
    let fileText = '';
    let driveConnected = false;
    let driveFileId = null;
    let tokenClient = null;
    let accessToken = null;
    let autoSyncEnabled = false;

    const DISCOVERY_DOC = 'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest';
    const SCOPES = 'https://www.googleapis.com/auth/drive.file';

    // --- Init ---
    init();

    function init() {
        loadSettings();
        loadLocalState();
        bindEvents();
        updateFileDisplay();
    }

    // --- Local Storage ---
    function loadLocalState() {
        const saved = localStorage.getItem('blocnotes_state');
        if (saved) {
            try {
                const state = JSON.parse(saved);
                fileText = state.fileText || '';
                fileName.value = state.fileName || 'fichier.txt';
                lineBreaks.value = state.lineBreaks ?? 2;
                driveFileId = state.driveFileId || null;
            } catch (e) {
                // ignore
            }
        }
    }

    function saveLocalState() {
        const state = {
            fileText,
            fileName: fileName.value,
            lineBreaks: parseInt(lineBreaks.value, 10),
            driveFileId
        };
        localStorage.setItem('blocnotes_state', JSON.stringify(state));
    }

    function loadSettings() {
        const saved = localStorage.getItem('blocnotes_settings');
        if (saved) {
            try {
                const settings = JSON.parse(saved);
                inputClientId.value = settings.clientId || '';
                inputApiKey.value = settings.apiKey || '';
                inputFolderId.value = settings.folderId || '';
            } catch (e) {
                // ignore
            }
        }
    }

    function saveSettings() {
        const settings = {
            clientId: inputClientId.value.trim(),
            apiKey: inputApiKey.value.trim(),
            folderId: inputFolderId.value.trim()
        };
        localStorage.setItem('blocnotes_settings', JSON.stringify(settings));
    }

    function getSettings() {
        const saved = localStorage.getItem('blocnotes_settings');
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) {
                return {};
            }
        }
        return {};
    }

    // --- Events ---
    function bindEvents() {
        // Quick actions
        btnCut.addEventListener('click', doCut);
        btnCopy.addEventListener('click', doCopy);
        btnPaste.addEventListener('click', doPaste);
        btnClear.addEventListener('click', doClearInput);

        // Validate
        btnValidate.addEventListener('click', doValidate);

        // File actions
        btnDownload.addEventListener('click', doDownload);
        btnClearFile.addEventListener('click', doClearFile);
        btnRename.addEventListener('click', () => {
            fileName.focus();
            fileName.select();
        });

        // Line breaks controls
        btnLbMinus.addEventListener('click', () => {
            const val = parseInt(lineBreaks.value, 10);
            if (val > 0) lineBreaks.value = val - 1;
            saveLocalState();
        });
        btnLbPlus.addEventListener('click', () => {
            const val = parseInt(lineBreaks.value, 10);
            if (val < 20) lineBreaks.value = val + 1;
            saveLocalState();
        });
        lineBreaks.addEventListener('change', () => {
            let val = parseInt(lineBreaks.value, 10);
            if (isNaN(val) || val < 0) val = 0;
            if (val > 20) val = 20;
            lineBreaks.value = val;
            saveLocalState();
        });

        // File name change
        fileName.addEventListener('change', saveLocalState);

        // File content editable
        fileContent.addEventListener('input', () => {
            fileText = fileContent.textContent;
            saveLocalState();
            updateEmptyState();
        });

        // Settings
        btnSettings.addEventListener('click', () => settingsModal.classList.remove('hidden'));
        btnCloseSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) settingsModal.classList.add('hidden');
        });
        btnSaveSettings.addEventListener('click', () => {
            saveSettings();
            settingsModal.classList.add('hidden');
            showToast('Paramètres sauvegardés', 'success');
        });

        // Google Drive
        btnDriveConnect.addEventListener('click', connectDrive);
        btnDriveOpen.addEventListener('click', openFromDrive);
        btnDriveSave.addEventListener('click', saveToDrive);
        btnDriveSync.addEventListener('click', syncWithDrive);

        // Keyboard shortcuts
        textInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                doValidate();
            }
        });
    }

    // --- Quick Actions ---
    function doCut() {
        const ta = textInput;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        if (start === end) {
            // Select all and cut
            ta.select();
        }
        const selected = ta.value.substring(ta.selectionStart, ta.selectionEnd);
        if (selected) {
            navigator.clipboard.writeText(selected).then(() => {
                const s = ta.selectionStart;
                const e = ta.selectionEnd;
                ta.value = ta.value.substring(0, s) + ta.value.substring(e);
                ta.selectionStart = ta.selectionEnd = s;
                ta.focus();
                showToast('Texte coupé', 'success');
            }).catch(() => {
                document.execCommand('cut');
                showToast('Texte coupé', 'success');
            });
        }
    }

    function doCopy() {
        const ta = textInput;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        let textToCopy;
        if (start === end) {
            textToCopy = ta.value;
        } else {
            textToCopy = ta.value.substring(start, end);
        }
        if (textToCopy) {
            navigator.clipboard.writeText(textToCopy).then(() => {
                showToast('Texte copié', 'success');
            }).catch(() => {
                ta.select();
                document.execCommand('copy');
                showToast('Texte copié', 'success');
            });
        }
    }

    function doPaste() {
        navigator.clipboard.readText().then((text) => {
            const ta = textInput;
            const start = ta.selectionStart;
            const end = ta.selectionEnd;
            ta.value = ta.value.substring(0, start) + text + ta.value.substring(end);
            ta.selectionStart = ta.selectionEnd = start + text.length;
            ta.focus();
            showToast('Texte collé', 'success');
        }).catch(() => {
            textInput.focus();
            document.execCommand('paste');
        });
    }

    function doClearInput() {
        if (textInput.value.length === 0) return;
        textInput.value = '';
        textInput.focus();
        showToast('Zone de saisie effacée', 'success');
    }

    // --- Validate: Insert text at top ---
    function doValidate() {
        const newText = textInput.value.trim();
        if (!newText) {
            showToast('Rien à insérer — la zone de saisie est vide', 'error');
            textInput.focus();
            return;
        }

        const nbLineBreaks = parseInt(lineBreaks.value, 10) || 0;
        const separator = '\n'.repeat(nbLineBreaks);

        if (fileText.trim().length > 0) {
            fileText = newText + separator + fileText;
        } else {
            fileText = newText;
        }

        textInput.value = '';
        saveLocalState();
        updateFileDisplay();
        showToast('Texte inséré en haut du fichier', 'success');

        // Auto-sync if connected
        if (driveConnected && autoSyncEnabled && driveFileId) {
            syncWithDrive();
        }
    }

    // --- File Display ---
    function updateFileDisplay() {
        fileContent.textContent = fileText;
        updateEmptyState();
    }

    function updateEmptyState() {
        if (fileText.trim().length === 0) {
            fileEmptyState.classList.remove('hidden');
        } else {
            fileEmptyState.classList.add('hidden');
        }
    }

    // --- File Actions ---
    function doDownload() {
        if (!fileText.trim()) {
            showToast('Le fichier est vide', 'error');
            return;
        }
        const blob = new Blob([fileText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName.value || 'fichier.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Fichier téléchargé', 'success');
    }

    function doClearFile() {
        if (!fileText.trim()) return;
        if (confirm('Voulez-vous vraiment vider le fichier ?')) {
            fileText = '';
            saveLocalState();
            updateFileDisplay();
            showToast('Fichier vidé', 'success');
        }
    }

    // --- Toast ---
    function showToast(message, type) {
        toast.textContent = message;
        toast.className = 'toast ' + (type || '');
        // Force reflow
        toast.offsetHeight;
        toast.classList.add('show');
        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 2500);
    }

    // ============================================================
    // Google Drive Integration
    // ============================================================

    function connectDrive() {
        const settings = getSettings();
        if (!settings.clientId || !settings.apiKey) {
            showToast('Configurez d\'abord le Client ID et la clé API dans les paramètres', 'error');
            settingsModal.classList.remove('hidden');
            return;
        }

        setDriveStatus('Connexion...', 'syncing');

        // Load the Google API client
        gapi.load('client', () => {
            gapi.client.init({
                apiKey: settings.apiKey,
                discoveryDocs: [DISCOVERY_DOC],
            }).then(() => {
                // Initialize the token client
                tokenClient = google.accounts.oauth2.initTokenClient({
                    client_id: settings.clientId,
                    scope: SCOPES,
                    callback: (response) => {
                        if (response.error) {
                            setDriveStatus('Erreur de connexion', 'error');
                            showToast('Erreur de connexion Google Drive', 'error');
                            return;
                        }
                        accessToken = response.access_token;
                        driveConnected = true;
                        onDriveConnected();
                    },
                });
                tokenClient.requestAccessToken({ prompt: 'consent' });
            }).catch((err) => {
                console.error('Erreur init Google API:', err);
                setDriveStatus('Erreur', 'error');
                showToast('Erreur d\'initialisation de l\'API Google', 'error');
            });
        });
    }

    function onDriveConnected() {
        setDriveStatus('Connecté', 'connected');
        showToast('Google Drive connecté', 'success');

        btnDriveConnect.classList.add('hidden');
        btnDriveOpen.classList.remove('hidden');
        btnDriveSave.classList.remove('hidden');
        btnDriveSync.classList.remove('hidden');
    }

    function setDriveStatus(text, className) {
        driveStatus.textContent = text;
        driveStatus.className = 'drive-status ' + className;
        driveStatus.classList.remove('hidden');
    }

    // --- Open file from Drive ---
    async function openFromDrive() {
        if (!driveConnected) return;

        setDriveStatus('Chargement...', 'syncing');

        try {
            // Search for files with the current name
            const currentName = fileName.value || 'fichier.txt';
            const response = await gapi.client.drive.files.list({
                q: `name='${currentName}' and mimeType='text/plain' and trashed=false`,
                fields: 'files(id, name, modifiedTime)',
                spaces: 'drive',
                orderBy: 'modifiedTime desc',
                pageSize: 10,
            });

            const files = response.result.files;
            if (!files || files.length === 0) {
                showToast('Aucun fichier trouvé avec ce nom sur Drive', 'error');
                setDriveStatus('Connecté', 'connected');
                return;
            }

            // Use the most recent one
            const file = files[0];
            driveFileId = file.id;

            // Download content
            const contentResponse = await gapi.client.drive.files.get({
                fileId: driveFileId,
                alt: 'media',
            });

            fileText = contentResponse.body;
            saveLocalState();
            updateFileDisplay();
            setDriveStatus('Connecté', 'connected');
            showToast(`Fichier "${file.name}" chargé depuis Drive`, 'success');
        } catch (err) {
            console.error('Erreur ouverture Drive:', err);
            setDriveStatus('Erreur', 'error');
            showToast('Erreur lors de l\'ouverture du fichier', 'error');
        }
    }

    // --- Save to Drive ---
    async function saveToDrive() {
        if (!driveConnected) return;

        setDriveStatus('Sauvegarde...', 'syncing');

        try {
            const currentName = fileName.value || 'fichier.txt';
            const settings = getSettings();
            const fileBlob = new Blob([fileText], { type: 'text/plain' });

            if (driveFileId) {
                // Update existing file
                await updateDriveFile(driveFileId, fileBlob, currentName);
                showToast('Fichier mis à jour sur Drive', 'success');
            } else {
                // Create new file
                const metadata = {
                    name: currentName,
                    mimeType: 'text/plain',
                };
                if (settings.folderId) {
                    metadata.parents = [settings.folderId];
                }
                const newFileId = await createDriveFile(metadata, fileBlob);
                driveFileId = newFileId;
                saveLocalState();
                showToast('Fichier créé sur Drive', 'success');
            }
            setDriveStatus('Connecté', 'connected');
        } catch (err) {
            console.error('Erreur sauvegarde Drive:', err);
            setDriveStatus('Erreur', 'error');
            showToast('Erreur lors de la sauvegarde sur Drive', 'error');
        }
    }

    async function createDriveFile(metadata, blob) {
        const form = new FormData();
        form.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }));
        form.append('file', blob);

        const response = await fetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + accessToken },
            body: form,
        });

        const data = await response.json();
        return data.id;
    }

    async function updateDriveFile(fileId, blob, name) {
        // Update metadata
        await gapi.client.drive.files.update({
            fileId: fileId,
            resource: { name: name },
        });

        // Update content
        await fetch(`https://www.googleapis.com/upload/drive/v3/files/${fileId}?uploadType=media`, {
            method: 'PATCH',
            headers: {
                'Authorization': 'Bearer ' + accessToken,
                'Content-Type': 'text/plain',
            },
            body: blob,
        });
    }

    // --- Sync (pull latest then push) ---
    async function syncWithDrive() {
        if (!driveConnected) return;

        setDriveStatus('Synchronisation...', 'syncing');

        try {
            if (driveFileId) {
                // Pull latest from Drive
                const contentResponse = await gapi.client.drive.files.get({
                    fileId: driveFileId,
                    alt: 'media',
                });

                const remoteText = contentResponse.body;

                // If remote is different and local has changed, local wins (prepend mode)
                // If they're the same, no action needed
                if (remoteText !== fileText) {
                    // Push local version to Drive
                    const blob = new Blob([fileText], { type: 'text/plain' });
                    await updateDriveFile(driveFileId, blob, fileName.value);
                    showToast('Synchronisation terminée', 'success');
                } else {
                    showToast('Déjà synchronisé', 'success');
                }
            } else {
                // No file on Drive yet, save it
                await saveToDrive();
                return;
            }
            setDriveStatus('Connecté', 'connected');
        } catch (err) {
            console.error('Erreur sync Drive:', err);
            setDriveStatus('Erreur', 'error');
            showToast('Erreur de synchronisation', 'error');
        }
    }

})();
