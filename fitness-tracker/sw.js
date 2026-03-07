var CACHE = 'fitness-tracker-v1.1';
var FILES = ['./', './index.html'];

self.addEventListener('install', function(e) {
  e.waitUntil(caches.open(CACHE).then(function(c) { return c.addAll(FILES); }));
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      var old = keys.filter(function(k) { return k !== CACHE; });
      return Promise.all(old.map(function(k) { return caches.delete(k); })).then(function() {
        if (old.length > 0) {
          self.clients.matchAll().then(function(clients) {
            clients.forEach(function(c) { c.postMessage({ type: 'SW_UPDATED', version: CACHE }); });
          });
        }
      });
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  var url = e.request.url;

  // Navigation → network-first
  if (e.request.mode === 'navigate' || url.endsWith('index.html')) {
    e.respondWith(
      fetch(e.request).then(function(r) {
        var clone = r.clone();
        caches.open(CACHE).then(function(c) { c.put(e.request, clone); });
        return r;
      }).catch(function() {
        return caches.match(e.request);
      })
    );
    return;
  }

  // CDN resources (Tailwind, Chart.js, Font Awesome, Google Fonts) → cache-first
  if (url.indexOf('cdn.tailwindcss.com') !== -1 ||
      url.indexOf('cdn.jsdelivr.net') !== -1 ||
      url.indexOf('cdnjs.cloudflare.com') !== -1 ||
      url.indexOf('fonts.googleapis.com') !== -1 ||
      url.indexOf('fonts.gstatic.com') !== -1) {
    e.respondWith(
      caches.match(e.request).then(function(cached) {
        if (cached) return cached;
        return fetch(e.request).then(function(r) {
          var clone = r.clone();
          caches.open(CACHE).then(function(c) { c.put(e.request, clone); });
          return r;
        });
      })
    );
    return;
  }

  // APIs (MCP Drive, etc.) → network only
  e.respondWith(fetch(e.request));
});
