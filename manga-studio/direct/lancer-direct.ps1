# Manga Studio — lance Caddy (chemin direct Wi-Fi HTTPS, v2.7.0, 23/09/2026).
# Repris de telegram-video/direct/lancer-direct.ps1 (v0.96.1), avec ses deux leçons :
#  1. ATTENDRE l'adresse du `bind` avant de lancer (14/09 : Caddy lancé avant le réseau s'arrête EN ENTIER) ;
#  2. PowerShell 5.1 : rediriger la sortie d'erreur d'un exécutable tue le script avec 'Stop' -> Start-Process.
# Le jeton Cloudflare (DNS-01) est LU dans llm-cli/.env et passé en variable d'environnement : écrit nulle part ailleurs.
# Un seul Caddy à la fois : si le port 8723 écoute déjà, on ne relance pas. La tâche planifiée « MangaStudioDirect »
# relance ce script toutes les 10 min : un Caddy tombé revient seul.
param(
    [int]$AttenteMax = 600,
    [switch]$Essai                # banc : attend, dit ce qu'il a vu, ne lance rien
)
$ErrorActionPreference = 'Stop'
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8723

$bind = Get-Content (Join-Path $ici 'Caddyfile') | Where-Object { $_ -match '^\s*bind\s' } | Select-Object -First 1
$Adresses = @(($bind -replace '^\s*bind\s+', '').Trim() -split '\s+' | Where-Object { $_ })
function AdressesManquantes {
    $presentes = @(Get-NetIPAddress -ErrorAction SilentlyContinue | ForEach-Object { $_.IPAddress })
    @($Adresses | Where-Object { $presentes -notcontains $_ })
}
$debut = Get-Date
$manquantes = AdressesManquantes
while ($manquantes.Count -and ((Get-Date) - $debut).TotalSeconds -lt $AttenteMax) {
    Start-Sleep -Seconds 5
    $manquantes = AdressesManquantes
}
if ($Essai) {
    "adresses=$($Adresses -join ',') manquantes=$($manquantes -join ',') attendu_s=$([int]((Get-Date) - $debut).TotalSeconds)"
    exit 0
}
if ($manquantes.Count) { exit 1 }         # pas de Wi-Fi : la prochaine passe de la tâche réessaiera

$env = Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ici))) 'llm-cli\.env'
$ligne = Get-Content $env | Where-Object { $_ -match '^\s*CF_API_TOKEN\s*=' } | Select-Object -First 1
if (-not $ligne) { throw "CF_API_TOKEN absent de $env" }
$Env:CF_API_TOKEN = ($ligne -replace '^\s*CF_API_TOKEN\s*=\s*', '').Trim().Trim('"').Trim("'")
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { exit 0 }
Set-Location $ici
New-Item -ItemType Directory -Force (Join-Path $ici 'logs') | Out-Null
Start-Process -FilePath (Join-Path $ici 'caddy.exe') -ArgumentList @('run', '--config', (Join-Path $ici 'Caddyfile')) `
    -WorkingDirectory $ici -WindowStyle Hidden -Wait `
    -RedirectStandardOutput (Join-Path $ici 'logs\direct.stdout') -RedirectStandardError (Join-Path $ici 'logs\direct.out')
