# -*- coding: utf-8 -*-
"""Ferme, a l'ouverture de session, les fenetres Edge de Manga Studio que WINDOWS a rouvertes toutes seules (27/09/2026).

Pourquoi (Quang 27/09 : « les fenetres Edge devraient etre fermees au demarrage du PC par defaut ») : Windows rouvre a la
connexion les applications laissees ouvertes a l'arret (reglage « Redemarrer mes applications », RestartApps=1). Mesure
du 27/09 : demarrage 09:54:21, fenetre de capture de la secondaire rouverte 09:54:30 avec `--restore-last-session
--restart` ajoutes a sa ligne de commande. Ce `--restart` est la SIGNATURE d'une relance par Windows : une fenetre
ouverte par l'app (manga_fetch launch-edge, fenetre_espace.py ouvrir) ne l'a jamais.

Ce script ne ferme QUE : un processus Edge principal (pas un sous-processus --type=) portant `--restart` ET l'un des
3 profils de Manga Studio. Rien d'autre (ni le Edge de Quang, ni Friday, ni le Terminal Mobile). Fermeture propre par
CDP (Browser.close) sur le port de pilotage de la fenetre ; a defaut, taskkill /T du SEUL PID concerne.
Ne change pas la reglage Windows (il vaut pour toutes les applications de Quang).

Tache planifiee MangaStudioFermerFenetres (ouverture de session) -> surveille 4 min (Windows rouvre en quelques
secondes, mais apres une mise a jour cela peut tarder). Journal : %LOCALAPPDATA%\\manga-studio\\fermeture_demarrage.log

Usage : fermer_fenetres_demarrage.py [--duree S] [--essai]      (--essai : liste sans fermer)
"""
import json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cdp_mini as c

VERSION = "1.0.0"
LA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
PROFILS = [os.path.normcase(os.path.join(LA, p)) for p in ("manga-fetch-edge", "manga-fetch-edge-2",
                                                          os.path.join("EdgeApps", "MangaStudio-2"))]
JOURNAL = os.path.join(LA, "manga-studio", "fermeture_demarrage.log")
SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def noter(msg):
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))


def processus_edge():
    """[(pid, ligne de commande)] des processus Edge PRINCIPAUX (sans --type=)."""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | ? { $_.CommandLine -and $_.CommandLine "
          "-notmatch '--type=' } | % { [pscustomobject]@{p=$_.ProcessId; c=$_.CommandLine} } | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", creationflags=SANS_FENETRE).stdout.strip()
    if not out:
        return []
    d = json.loads(out)
    return [(x["p"], x["c"]) for x in (d if isinstance(d, list) else [d])]


def profil_de(ligne):
    m = re.search(r'--user-data-dir="?([^"]+?)"?(?:\s+--|\s*$)', ligne)
    return os.path.normcase(os.path.normpath(m.group(1))) if m else None


def a_fermer(ligne):
    return bool(re.search(r"(^|\s)--restart(\s|$)", ligne)) and profil_de(ligne) in PROFILS


def fermer(pid, ligne):
    m = re.search(r"--remote-debugging-port=(\d+)", ligne)
    if m:
        try:
            v = json.load(urllib.request.urlopen("http://127.0.0.1:%s/json/version" % m.group(1), timeout=3))
            with c.Onglet(v["webSocketDebuggerUrl"]) as n:
                n.cmd("Browser.close")
            return "CDP %s" % m.group(1)
        except Exception as e:
            noter("  CDP impossible (%s) -> taskkill" % str(e)[:80])
    subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, creationflags=SANS_FENETRE)
    return "taskkill"


def main():
    duree = int(sys.argv[sys.argv.index("--duree") + 1]) if "--duree" in sys.argv else 240
    essai = "--essai" in sys.argv
    noter("v%s debut (surveillance %d s%s)" % (VERSION, duree, ", ESSAI" if essai else ""))
    vus, fin = set(), time.time() + duree
    while True:
        for pid, ligne in processus_edge():
            if pid in vus or not a_fermer(ligne):
                continue
            vus.add(pid)
            profil = os.path.basename(profil_de(ligne))
            if essai:
                noter("  [essai] a fermer : PID %s, profil %s" % (pid, profil)); continue
            noter("  fermee : PID %s, profil %s (%s)" % (pid, profil, fermer(pid, ligne)))
        if time.time() >= fin:
            break
        time.sleep(5)
    noter("fin (%d fenetre(s))" % len(vus))
    print(json.dumps({"ok": True, "fenetres": len(vus)}))


if __name__ == "__main__":
    main()
