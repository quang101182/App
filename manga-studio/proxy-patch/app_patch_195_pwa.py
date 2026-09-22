# -*- coding: utf-8 -*-
"""App v1.94.0 -> v1.95.0 : installable depuis Chrome (etape 14, demande Quang 22/09 08h36).
<link rel=manifest> + theme-color + icone + enregistrement de pwa/sw.js (portee /manga/). Plein ecran
(display fullscreen : ni barre d'adresse ni bandeau de notifications). Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.94.0</title>", "<title>Manga Studio v1.95.0</title>"),
             ('id="verBadge">v1.94.0<', 'id="verBadge">v1.95.0<'),
             ('const VERSION = "1.94.0";', 'const VERSION = "1.95.0";')):
    rep(a, b)
rep('''<title>Manga Studio v1.95.0</title>''',
    '''<title>Manga Studio v1.95.0</title>
<!-- v1.95.0 : app INSTALLABLE (manifeste + icones + service worker servis PUBLICS par le proxy, sans secret) -->
<link rel="manifest" href="/manga/manifest.webmanifest">
<meta name="theme-color" content="#0d0f13">
<link rel="icon" type="image/png" sizes="192x192" href="/manga/icon-192.png">
<link rel="apple-touch-icon" href="/manga/icon-192.png">''')
rep('''// Meme convention que Generate Studio : #k=<secret> depose la cle puis disparait de l'URL.''',
    '''// v1.95.0 : service worker = condition d'installation. Il ne met RIEN en cache (cf pwa/sw.js).
if ("serviceWorker" in navigator && location.protocol.startsWith("http"))
  navigator.serviceWorker.register("/manga/sw.js", { scope: "/manga/" }).catch(e => console.warn("sw : " + e.message));
// Meme convention que Generate Studio : #k=<secret> depose la cle puis disparait de l'URL.''')
shutil.copy(p, p + ".bak-20260922-v195")
open(p, "w", encoding="utf-8").write(s)
print("app v1.95.0 OK")
