# -*- coding: utf-8 -*-
"""
gateway_logs.py — lire le journal des appels de l'api-gateway.

Ecrit le 29/08/2026 (P4.1 de ROADMAP-securite-cles-api.md), au lendemain du vol de
la cle Anthropic : 1200 requetes en 17 minutes, et ce worker n'en gardait aucune
trace. Il a fallu une heure et les analytics Cloudflare pour seulement l'ecarter.

Le worker ecrit dans le dataset Analytics Engine 'gateway_calls' (binding
GATEWAY_LOG). Ce script le relit en SQL.

  python scripts/gateway_logs.py              # resume des 24 dernieres heures
  python scripts/gateway_logs.py --hours 2    # fenetre plus courte
  python scripts/gateway_logs.py --minutes    # courbe par minute : voir une RAFALE
  python scripts/gateway_logs.py --refus      # uniquement les 401/403
  python scripts/gateway_logs.py --sql "..."  # requete libre

⚠ Analytics Engine met ~1 minute avant qu'un point ecrit soit interrogeable.
   Un resultat vide juste apres un appel n'est PAS une panne : re-essayer.
⚠ Le dataset ne contient AUCUN secret : ni cle, ni token, ni corps de requete.
   L'IP est tronquee en /24 (ou /48 en IPv6) — assez pour voir qu'une rafale vient
   d'un meme reseau, pas assez pour etre une donnee de trafic.
"""
import argparse, io, json, os, re, sys, urllib.request, urllib.error

ACCOUNT = "9252be67c92c344899dfc0647bcdb1a0"
ENVFILE = r"D:\Download\02-Apps-Web\Repo-github\llm-cli\.env"

def token():
    t = os.environ.get("CF_API_TOKEN")
    if t: return t
    for line in io.open(ENVFILE, encoding="utf-8", errors="ignore"):
        m = re.match(r"\s*CF_API_TOKEN\s*=\s*(\S+)", line)
        if m: return m.group(1).strip("\"'")
    sys.exit("CF_API_TOKEN introuvable")

def sql(q):
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/analytics_engine/sql",
        data=q.encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + token()})
    try:
        return json.loads(urllib.request.urlopen(req).read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        if e.code == 403:
            sys.exit("HTTP 403 — le token n'a pas la permission « Account Analytics : Read ».")
        sys.exit(f"HTTP {e.code} : {body}")

def table(rows, cols):
    if not rows:
        print("  (aucune donnee — Analytics Engine a ~1 min de latence, re-essayer)")
        return
    w = [max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols]
    print("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    print("  " + "  ".join("-" * w[i] for i in range(len(cols))))
    for r in rows:
        print("  " + "  ".join(str(r.get(c, "")).ljust(w[i]) for i, c in enumerate(cols)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--minutes", action="store_true", help="courbe par minute (detecter une rafale)")
    ap.add_argument("--refus", action="store_true", help="uniquement les 401/403")
    ap.add_argument("--sql", help="requete SQL libre sur gateway_calls")
    a = ap.parse_args()
    W = f"timestamp > NOW() - INTERVAL '{a.hours}' HOUR"

    if a.sql:
        print(json.dumps(sql(a.sql), indent=1, ensure_ascii=False)); return

    if a.minutes:
        # Une rafale se voit ICI et nulle part ailleurs : le 28/08, le pic etait a
        # 1044 requetes EN UNE MINUTE. Un total journalier ne l'aurait jamais montre.
        print(f"\n== Appels par minute ({a.hours} h) — les 30 minutes les plus chargees ==")
        r = sql(f"""SELECT toStartOfMinute(timestamp) AS minute, blob1 AS route,
                    SUM(_sample_interval) AS appels
                    FROM gateway_calls WHERE {W}
                    GROUP BY minute, route ORDER BY appels DESC LIMIT 30 FORMAT JSON""")
        table(r.get("data", []), ["minute", "route", "appels"]); return

    if a.refus:
        print(f"\n== Refus d'authentification 401/403 ({a.hours} h) ==")
        print("   Un refus repete = une cle perimee qui traine quelque part, ou quelqu'un qui essaie.")
        r = sql(f"""SELECT blob1 AS route, blob4 AS origine, blob5 AS pays, blob6 AS reseau,
                    SUM(_sample_interval) AS refus
                    FROM gateway_calls WHERE {W} AND double3 > 0
                    GROUP BY route, origine, pays, reseau ORDER BY refus DESC LIMIT 25 FORMAT JSON""")
        table(r.get("data", []), ["route", "origine", "pays", "reseau", "refus"]); return

    print(f"\n== Par route ({a.hours} h) ==")
    r = sql(f"""SELECT blob1 AS route, SUM(_sample_interval) AS appels,
                SUM(double2 * _sample_interval) AS erreurs,
                ROUND(AVG(double1)) AS ms_moyen
                FROM gateway_calls WHERE {W}
                GROUP BY route ORDER BY appels DESC LIMIT 25 FORMAT JSON""")
    table(r.get("data", []), ["route", "appels", "erreurs", "ms_moyen"])

    print(f"\n== Qui appelle ({a.hours} h) ==")
    r = sql(f"""SELECT blob4 AS origine, blob5 AS pays, SUM(_sample_interval) AS appels
                FROM gateway_calls WHERE {W}
                GROUP BY origine, pays ORDER BY appels DESC LIMIT 25 FORMAT JSON""")
    table(r.get("data", []), ["origine", "pays", "appels"])

    print(f"\n== Refus d'authentification ({a.hours} h) ==")
    r = sql(f"""SELECT SUM(double3 * _sample_interval) AS refus FROM gateway_calls
                WHERE {W} FORMAT JSON""")
    n = (r.get("data") or [{}])[0].get("refus", 0)
    print(f"  {n}" + ("   <-- a regarder : python scripts/gateway_logs.py --refus" if n and float(n) > 0 else ""))
    print()

if __name__ == "__main__":
    main()
