@echo off
chcp 65001 >nul
title Capture de chapitres - manga-fetch v0.1.1
setlocal

set "PY=%LOCALAPPDATA%\manga-fetch\venv\Scripts\python.exe"
set "MOD=D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga-fetch\manga_fetch.py"
set "SRC=D:\Download\02-Apps-Web\Repo-github\App\manga-studio\sources"

echo ==========================================================
echo   CAPTURE DE CHAPITRES   (manga-fetch v0.1.1)
echo ==========================================================
echo.

rem --- la fenetre Edge dediee est-elle ouverte ? sinon on la lance
curl -s -o nul -m 3 http://localhost:9223/json/version
if errorlevel 1 (
    echo La fenetre Edge dediee n'est pas ouverte : je la lance...
    "%PY%" "%MOD%" launch-edge
    timeout /t 6 /nobreak >nul
) else (
    echo Fenetre Edge dediee : OUVERTE.
)

:capture
echo ----------------------------------------------------------
echo   Ouvre le chapitre a capturer dans la fenetre Edge dediee
echo   ^(n'importe quel site de lecture^). Attends que la PREMIERE
echo   PAGE s'affiche. L'onglet du chapitre doit rester l'onglet
echo   ACTIF ^(affiche a l'ecran^) : c'est LUI que l'outil capture.
echo   Puis reviens ici et appuie sur une touche.
echo ----------------------------------------------------------
pause

set "TITRE="
set "CHAP="
set /p "TITRE=Titre du manga (ex: Dragon Ball Super) : "
set /p "CHAP=Numero du chapitre (ex: 104) : "
echo.
echo Capture en cours : la fenetre Edge va DEFILER le chapitre
echo toute seule et enregistrer chaque page.
echo   --^> Ne touche a rien pendant 2 a 4 minutes. --
echo   (ne MINIMISE pas la fenetre Edge pendant la capture ; elle peut
echo    rester derriere d'autres fenetres, mais pas reduite dans la barre)
echo.
"%PY%" "%MOD%" capture --title "%TITRE%" --chapter "%CHAP%"
set "CODE=%errorlevel%"
echo.
if "%CODE%"=="0" goto ok
if "%CODE%"=="3" goto oknotes
echo ==========================================================
echo   ECHEC - lis le message ci-dessus pour la cause
echo ==========================================================
goto encore
:oknotes
echo ==========================================================
echo   CAPTURE TERMINEE ^(avec des notes - voir ci-dessus^)
echo ==========================================================
goto encore
:ok
echo ==========================================================
echo   CAPTURE TERMINEE
echo ==========================================================

:encore
echo.
set "ENCORE="
set /p "ENCORE=Autre chapitre a capturer ? (O/N) : "
if /i "%ENCORE%"=="O" goto capture
echo.
echo Fermeture. Toutes les pages capturees sont dans :
echo   %SRC%
explorer "%SRC%"
pause
