' Lance Caddy (chemin direct HTTPS) SANS aucune fenetre.
' Utilise par la tache planifiee "MangaStudioDirect" (demarrage a l'ouverture de session).
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
racine = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & racine & "\lancer-direct.ps1""", 0, False
