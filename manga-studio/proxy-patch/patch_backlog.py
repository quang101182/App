# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : file d'attente des connexions 5 -> 128 (Manga Studio v2.5.3, 23/09/2026).

Mesure (Quang 10h27, vignettes vides sur Noritaka ch.1) : a l'ouverture d'un chapitre, le navigateur demande ~70 images
d'un coup via le tunnel Cloudflare. ThreadingHTTPServer n'accepte par defaut que 5 connexions en attente
(request_queue_size) : au-dela, Windows refuse ou coupe -> cloudflared renvoie 502 (454 coupures dans _agent_cf.err.log,
en plus des 10 486 refus dus a « localhost » resolu en ::1, corriges dans config-generate-agent.yml).
Rejouable : python patch_backlog.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "request_queue_size = 128" in s:
    print("deja patche"); sys.exit(0)
a = "    ThreadingHTTPServer((host, port), H).serve_forever()"
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, "    ThreadingHTTPServer.request_queue_size = 128          # 23/09 : 5 par defaut -> 502 du tunnel sur ~70 images d'un coup\n" + a)
open(p, "w", encoding="utf-8").write(s)
print("patche")
