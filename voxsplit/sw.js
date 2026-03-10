var CACHE = 'voxsplit-v3.6.2';
var FILES = ['./', './index.html', './icon.svg', './manifest.json'];

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
          setTimeout(function() {
            self.clients.matchAll().then(function(clients) {
              clients.forEach(function(c) { c.postMessage({ type: 'SW_UPDATED', version: CACHE }); });
            });
          }, 1000);
        }
      });
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  if (e.request.mode === 'navigate' || e.request.url.endsWith('index.html')) {
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
  if (e.request.url.indexOf('cdn.tailwindcss.com') !== -1 ||
      e.request.url.indexOf('cdn.jsdelivr.net') !== -1 ||
      e.request.url.indexOf('cdnjs.cloudflare.com') !== -1 ||
      e.request.url.indexOf('fonts.googleapis.com') !== -1 ||
      e.request.url.indexOf('fonts.gstatic.com') !== -1) {
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
  e.respondWith(fetch(e.request));
});
