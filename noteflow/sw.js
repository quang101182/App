// NoteFlow Service Worker v1.2.2
const CACHE = 'noteflow-v1.2.2';
const ASSETS = ['./', 'index.html', 'manifest.json', 'icon.svg', 'prompts.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
      if (resp.ok && e.request.url.startsWith(self.location.origin)) {
        const cl = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, cl));
      }
      return resp;
    }).catch(() => caches.match('./index.html')))
  );
});
