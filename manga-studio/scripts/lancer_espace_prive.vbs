' Manga Studio - lance lancer_espace_prive.ps1 sans aucune fenetre (tache planifiee MangaStudioInstance2).
Dim sh, fso
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & fso.GetParentFolderName(WScript.ScriptFullName) & "\lancer_espace_prive.ps1""", 0, False
