// Manga Studio — service worker v2.7.0
// v2.7.0 : le chemin direct Wi-Fi (manga-wifi.crushrank.xyz:8723) CONTOURNE le worker par une regle de routage
// posee a l'installation : sinon Chrome n'affiche pas l'invite « reseau local » et la requete echoue en silence
// (recette Telegramme Video, 13/09/2026). Service worker v2.4.6 (etape 10 : ecouter PC eteint, decision Quang 22/09 : DANS le telephone).
// v2.4.6 : les pages et MP3 du lecteur sont REVALIDES a chaque fois (cache: no-cache -> ETag -> 304). Un chapitre
// supprime puis recapture reprend les MEMES noms de pages : le cache HTTP ressortait les anciennes (Claymore, 22/09).
// Regle : le RESEAU d'abord, toujours (l'app reste a jour). Le stockage ne sert QUE si le PC ne repond pas
// (erreur reseau, ou 5xx du tunnel quand le PC est eteint). N'intercepte que la page de l'app et ce que le LECTEUR
// lit : /manga/narration, /manga/precedemment, /manga/source_file (images, MP3). Tout le reste (videos, zip,
// telechargements, actions) va au PC sans passer par ici.
// Les chapitres « gardes hors-ligne » sont ranges par l'app dans le cache HL, cle = l'URL SANS le jeton (_k).
const SHELL = "manga-shell-v1", HL = "manga-horsligne-v1";
const LECTEUR = /^\/manga\/(narration|precedemment|source_file)$/;
const COQUILLE = /^\/manga\/(manifest\.webmanifest|icon-[a-z0-9-]+\.png)$/;

// la coquille est gardee DES l'installation : sinon elle ne l'etait qu'a la 2e ouverture de l'app
self.addEventListener("install", e => { self.skipWaiting(); e.waitUntil(caches.open(SHELL).then(c => c.addAll(
  ["/manga/", "/manga/manifest.webmanifest", "/manga/icon-192.png", "/manga/icon-512.png", "/manga/icon-maskable-512.png"])).catch(() => {})); });
self.addEventListener("install", e => {
  if (e.addRoutes) e.waitUntil(e.addRoutes([{ condition: { urlPattern: { hostname: "manga-wifi.crushrank.xyz" } }, source: "network" }])
                                .catch(() => {}));
});
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

const cle = u => { const x = new URL(u); x.searchParams.delete("_k"); return x.toString(); };
const panne = r => !r || r.status >= 500;          // tunnel sans PC : 502 / 530 de Cloudflare

async function depuisHL(req){
  const c = await caches.open(HL), m = await c.match(cle(req.url));
  if (!m) return null;
  const rg = req.headers.get("range");
  if (!rg) return m;
  // l'audio demande des morceaux (Range) : on les decoupe dans la reponse entiere gardee
  const b = await m.arrayBuffer(), x = /bytes=(\d*)-(\d*)/.exec(rg) || [];
  let debut = x[1] ? +x[1] : Math.max(0, b.byteLength - +(x[2] || 0)), fin = x[1] && x[2] ? Math.min(+x[2], b.byteLength - 1) : b.byteLength - 1;
  if (debut > fin) debut = 0;
  return new Response(b.slice(debut, fin + 1), { status: 206, headers: {
    "Content-Type": m.headers.get("Content-Type") || "application/octet-stream", "Accept-Ranges": "bytes",
    "Content-Range": "bytes " + debut + "-" + fin + "/" + b.byteLength, "Content-Length": String(fin - debut + 1) } });
}

async function page(req){
  try {
    const r = await fetch(req);
    if (!panne(r)){
      if (r.ok && (r.headers.get("Content-Type") || "").includes("text/html"))
        (await caches.open(SHELL)).put("/manga/", r.clone());
      return r;
    }
  } catch (e) {}
  return (await caches.match("/manga/", { cacheName: SHELL })) || new Response("Manga Studio : PC injoignable et app pas encore gardée.", { status: 503 });
}

async function reseauSinonHL(req, garderCoquille){
  let r = null;
  try { r = await fetch(garderCoquille ? req : new Request(req, { cache: "no-cache" })); } catch (e) {}
  if (!panne(r)){
    if (garderCoquille && r.ok) (await caches.open(SHELL)).put(cle(req.url), r.clone());
    return r;
  }
  const c = garderCoquille ? await caches.match(cle(req.url), { cacheName: SHELL }) : await depuisHL(req);
  return c || r || new Response('{"error":"hors-ligne : pas garde sur ce telephone"}', { status: 503, headers: { "Content-Type": "application/json" } });
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin) return;
  if (req.mode === "navigate" && (u.pathname === "/manga/" || u.pathname === "/manga")) return e.respondWith(page(req));
  if (COQUILLE.test(u.pathname)) return e.respondWith(reseauSinonHL(req, true));
  if (LECTEUR.test(u.pathname)) return e.respondWith(reseauSinonHL(req, false));
});
