// Manga Studio — service worker minimal (v1.95.0) : il rend l'app INSTALLABLE, rien de plus.
// Aucun cache : tout vient du PC en direct (la lecture sans PC = etape 10, pas ici). Le gestionnaire
// fetch ne repond a RIEN (pas de respondWith) : le navigateur traite chaque requete comme sans lui,
// Range des MP3 / videos compris.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
