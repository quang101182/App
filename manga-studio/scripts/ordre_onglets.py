# -*- coding: utf-8 -*-
"""ordre_onglets.py v1.0.0 (27/09/2026, Quang : « j'ai l'habitude de voir les onglets dans un certain ordre sur mon PC ») :
l'ORDRE REEL des onglets de la fenetre de capture, tel qu'affiche dans sa barre d'onglets -- LECTURE SEULE par l'accessibilite
de Windows (UI Automation), rien n'est clique ni deplace. CDP ne donne PAS cet ordre (/json/list = du plus recemment actif au
plus ancien). Fenetre trouvee par son port de pilotage (--remote-debugging-port=<port>, processus principal d'Edge).
Sortie : une ligne JSON {"ok": true, "titres": [...]} ou {"ok": false, "raison": "..."}.
Usage : python ordre_onglets.py <port CDP>"""
import json, subprocess, sys


def pid_navigateur(port):
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine -match "
                        "'--remote-debugging-port=%d(\\s|$)' -and $_.CommandLine -notmatch '--type=' } | ForEach-Object { $_.ProcessId }" % port],
                       capture_output=True, text=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    p = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return p[0] if p else None


def titres(pid):
    import comtypes.client
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation, TreeScope_Children, TreeScope_Descendants
    ua = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
    UIA_ProcessIdPropertyId, UIA_ControlTypePropertyId, UIA_TabItemControlTypeId = 30002, 30003, 50019
    racine = ua.GetRootElement()
    fen = racine.FindAll(TreeScope_Children, ua.CreatePropertyCondition(UIA_ProcessIdPropertyId, pid))
    out = []
    for i in range(fen.Length):
        f = fen.GetElement(i)
        items = f.FindAll(TreeScope_Descendants, ua.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_TabItemControlTypeId))
        for j in range(items.Length):
            n = items.GetElement(j).CurrentName or ""
            if n:
                out.append(n)
    return out


def main():
    port = int(sys.argv[1])
    pid = pid_navigateur(port)
    if not pid:
        print(json.dumps({"ok": False, "raison": "fenetre introuvable (port %d)" % port})); return 1
    try:
        t = titres(pid)
    except Exception as e:
        print(json.dumps({"ok": False, "raison": "accessibilite : %s" % str(e)[:160]})); return 1
    print(json.dumps({"ok": bool(t), "titres": t, **({} if t else {"raison": "aucun onglet lu"})}))   # ASCII pur : pas de souci d encodage entre processus
    return 0


if __name__ == "__main__":
    sys.exit(main())
