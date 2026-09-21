@echo off
chcp 65001 >nul
title Capture de chapitre - manga-fetch v0.1.0
setlocal

set "PY=%LOCALAPPDATA%\manga-fetch\venv\Scripts\python.exe"
set "MOD=D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga-fetch\manga_fetch.py"
set "SRC=D:\Download\02-Apps-Web\Repo-github\App\manga-studio\sources"

echo ==========================================================
echo   CAPTURE DE CHAPITRE   (manga-fetch v0.1.0)
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
echo.
echo   ETAPES :
echo   1. Dans la fenetre Edge DEDIEE ^(celle que l'outil vient
echo      d'ouvrir ou deja ouverte^), ouvre le chapitre que tu veux
echo      capturer - n'importe quel site de lecture marche.
echo   2. Attends que la PREMIERE PAGE du chapitre s'affiche.
echo   3. Reviens ici et appuie sur une touche.
echo.
pause

set "SITE=mangadex"
set /p "REP=Morceau de l'adresse du site (Entree = mangadex) : "
if not "%REP%"=="" set "SITE=%REP%"
set /p "TITRE=Titre du manga (ex: Dragon Ball Super) : "
set /p "CHAP=Numero du chapitre (ex: 104) : "
echo.
echo Capture en cours : l'outil va faire DEFILER le chapitre
echo tout seul dans la fenetre Edge et enregistrer chaque page.
echo   --^> Ne touche a rien pendant 2 a 4 minutes. --
echo.
"%PY%" "%MOD%" capture --tab "%SITE%" --title "%TITRE%" --chapter "%CHAP%"
set "CODE=%errorlevel%"

echo.
if "%CODE%"=="0" goto ok
if "%CODE%"=="3" goto oknotes
echo ==========================================================
echo   ECHEC - lis le message ci-dessus pour la cause
echo ==========================================================
goto fin
:oknotes
echo ==========================================================
echo   CAPTURE TERMINEE ^(avec des notes - voir ci-dessus^)
echo ==========================================================
goto suite
:ok
echo ==========================================================
echo   CAPTURE TERMINEE
echo ==========================================================
:suite
echo   Les pages sont dans :
echo   %SRC%
echo ==========================================================
explorer "%SRC%"
:fin
pause
