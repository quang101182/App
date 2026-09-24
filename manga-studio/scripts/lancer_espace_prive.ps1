# Manga Studio - garde en vie la 2e instance du serveur (S1, 24/09/2026) : si le port 8192 ne repond pas, la lance
# (espace_prive.py, meme interpreteur que le proxy 8190), cachee. Appele par lancer_espace_prive.vbs (tache planifiee
# MangaStudioInstance2, ouverture de session + toutes les 10 min). Ne tue jamais rien.
$ErrorActionPreference = "Continue"
$port = 8192
try { (New-Object Net.Sockets.TcpClient).Connect("127.0.0.1", $port); exit 0 } catch {}
$py  = "$env:USERPROFILE\Documents\ComfyUI\.venv\Scripts\python.exe"
$log = "$env:LOCALAPPDATA\manga-studio\espace_prive.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
Add-Content -Path "$log.vie" -Value ("{0} lancement (port {1} muet)" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $port) -Encoding UTF8
Start-Process -FilePath $py -ArgumentList "`"$PSScriptRoot\espace_prive.py`"" -WorkingDirectory "$env:USERPROFILE\Documents\ComfyUI" `
    -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError "$log.err"
