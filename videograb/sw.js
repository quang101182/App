// VideoGrab Service Worker v4.9 — with ad domain blocking
var CACHE = 'videograb-v5.1';
var FILES = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png'];

// ── Ad domain blocklist (network-level, blocks before request leaves browser) ──
var AD_DOMAINS = [
  'doubleclick.net','googlesyndication.com','googleadservices.com','adnxs.com','pubmatic.com',
  'openx.net','criteo.com','rubiconproject.com','casalemedia.com','sizmek.com','adform.net',
  'sovrn.com','bidswitch.net','bidvertiser.com','exoclick.com','exosrv.com',
  'propellerads.com','popads.net','popcash.net','popunder.net',
  'juicyads.com','trafficjunky.net','trafficjunky.com','trafficfactory.biz',
  'adsterra.com','hilltopads.com','clickadu.com','clickaine.com',
  'pushame.com','ad-maven.com','plugrush.com','trafficstars.com','crakrevenue.com',
  'tsyndicate.com','realsrv.com','onclkds.com','onclickds.com','onclickmax.com',
  'magsrv.com','ero-advertising.com','monetag.com','a-ads.com','coinzilla.com',
  'adcash.com','richpush.net','evadav.com','notifadz.com','mondiad.com','galaksion.com',
  'clictune.com','linkvertise.com','amazon-adsystem.com','moatads.com',
  'histats.com','statcounter.com','hotjar.com','googletagmanager.com',
  'google-analytics.com','taboola.com','outbrain.com','mgid.com','revcontent.com',
  'liveadsexchange.com','betteradsexchange.com','spotx.tv',
];

function isAdUrl(url) {
  try {
    var h = new URL(url).hostname.toLowerCase();
    for (var i = 0; i < AD_DOMAINS.length; i++) {
      if (h === AD_DOMAINS[i] || h.endsWith('.' + AD_DOMAINS[i])) return true;
    }
  } catch(e) {}
  return false;
}

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
  // ── Ad blocking: return empty 204 for ad domains ──
  if (isAdUrl(e.request.url)) {
    e.respondWith(new Response('', { status: 204 }));
    return;
  }

  // Cache navigation + index.html
  if (e.request.mode === 'navigate' || e.request.url.endsWith('index.html')) {
    e.respondWith(
      fetch(e.request).then(function(r) {
        var clone = r.clone();
        caches.open(CACHE).then(function(c) { c.put(e.request, clone); });
        return r;
      }).catch(function() { return caches.match(e.request); })
    );
    return;
  }
  // Cache CDN libs
  if (e.request.url.indexOf('cdn.jsdelivr.net') !== -1 ||
      e.request.url.indexOf('cdnjs.cloudflare.com') !== -1) {
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
  // Everything else: network only
  e.respondWith(fetch(e.request));
});
