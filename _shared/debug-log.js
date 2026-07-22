/* ============================================================================
 * DebugLog — journal PERSISTANT pour les apps web / PWA / Capacitor (brique commune)
 *
 * POURQUOI (mandat Quang, 22/07/2026)
 * -----------------------------------
 * « Tout nouveau projet doit avoir un système de logs bien détaillé et fiable. »
 * Sur ces apps, TOUT passait par console.log : invisible dès que la page est fermée,
 * et invisible tout court sur téléphone. Un bug chez un utilisateur ne laissait donc
 * AUCUNE trace — et surtout, AUCUNE erreur JS non capturée n'était enregistrée.
 *
 * ÉQUIVALENT JS de dictokey/app/src/main/java/com/dictokey/app/util/DebugLog.kt.
 * Ces apps (music-ai, videograb, promoclip) sont des wrappers Capacitor : leur code
 * réel est en JavaScript, un logger Kotlin n'y journaliserait que la coquille native.
 *
 * SANS AUCUNE DÉPENDANCE — volontaire : @capacitor/filesystem n'est pas installé et
 * l'ajouter changerait la chaîne de build de chaque app. On se contente de
 * localStorage, disponible partout (navigateur, PWA installée, WebView Capacitor).
 *
 * ⛔ SECRETS — ces apps portent des clés d'API côté client. Un message d'erreur peut
 * en contenir une. Tout ce qui ressemble à une clé est MASQUÉ à l'écriture : rendre
 * un log persistant sans filtrer, ce serait fabriquer un fichier de clés en clair.
 *
 * USAGE  : à coller le PLUS TÔT possible dans <head>, avant tout autre script.
 * LECTURE: DebugLog.dump()      -> texte des N dernières entrées (console ou CDP)
 *          DebugLog.export()    -> télécharge un .txt (ce que l'utilisateur envoie)
 *          DebugLog.clear()     -> vider avant de reproduire un bug
 * ==========================================================================*/
(function () {
  'use strict';
  var KEY = 'debuglog.v1';
  var MAX = 400;          // entrées conservées (buffer circulaire)
  var FLUSH_MS = 1500;    // écriture différée : ne pas marteler localStorage
  var buf = [];
  var dirty = false;

  try { buf = JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { buf = []; }
  if (!Array.isArray(buf)) buf = [];

  // Masque ce qui ressemble à une clé/token. Large volontairement : mieux vaut
  // masquer un identifiant anodin que laisser fuiter une clé.
  function redact(s) {
    return String(s)
      .replace(/sk-[A-Za-z0-9_\-]{8,}/g, 'sk-***')
      .replace(/\b[A-Za-z0-9_\-]{32,}\b/g, function (m) { return m.slice(0, 4) + '***' + m.slice(-2); })
      .replace(/("?(?:api[_-]?key|token|authorization|password|secret)"?\s*[:=]\s*)("?)[^",}\s]+/gi, '$1$2***');
  }

  function stamp() {
    var d = new Date(), p = function (n, l) { return String(n).padStart(l || 2, '0'); };
    return p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' +
           p(d.getMinutes()) + ':' + p(d.getSeconds()) + '.' + p(d.getMilliseconds(), 3);
  }

  function push(level, args) {
    try {
      var msg = Array.prototype.map.call(args, function (a) {
        if (a instanceof Error) return a.name + ': ' + a.message;
        if (typeof a === 'object') { try { return JSON.stringify(a).slice(0, 400); } catch (e) { return '[object]'; } }
        return String(a);
      }).join(' ');
      buf.push(stamp() + ' ' + level + ' ' + redact(msg).slice(0, 600));
      if (buf.length > MAX) buf.splice(0, buf.length - MAX);
      dirty = true;
    } catch (e) { /* le journal ne doit JAMAIS casser l'app */ }
  }

  setInterval(function () {
    if (!dirty) return;
    dirty = false;
    try { localStorage.setItem(KEY, JSON.stringify(buf)); }
    catch (e) {
      // Quota dépassé : on sacrifie la moitié la plus ancienne plutôt que de
      // perdre l'écriture (et donc tout le journal) à chaque tour.
      try { buf.splice(0, Math.floor(buf.length / 2)); localStorage.setItem(KEY, JSON.stringify(buf)); } catch (e2) {}
    }
  }, FLUSH_MS);

  // --- Capture AUTOMATIQUE : c'est ici que se trouve le vrai gain -------------
  // Aucune de ces erreurs n'était enregistrée nulle part auparavant.
  window.addEventListener('error', function (ev) {
    push('E', [(ev.message || 'error'), '@', (ev.filename || '?') + ':' + (ev.lineno || 0)]);
  });
  window.addEventListener('unhandledrejection', function (ev) {
    var r = ev.reason;
    push('E', ['unhandled promise:', (r && (r.message || r)) || '?']);
  });

  // On enveloppe console.error/warn pour capter l'existant SANS toucher aux
  // centaines d'appels déjà en place. console.log n'est PAS enveloppé : trop
  // volumineux, et il noierait les entrées utiles.
  ['error', 'warn'].forEach(function (lvl) {
    var orig = console[lvl] ? console[lvl].bind(console) : function () {};
    console[lvl] = function () { push(lvl === 'error' ? 'E' : 'W', arguments); orig.apply(null, arguments); };
  });

  window.DebugLog = {
    log:  function () { push('I', arguments); },
    warn: function () { push('W', arguments); },
    err:  function () { push('E', arguments); },
    /** Les n dernières entrées, en texte. */
    dump: function (n) { return buf.slice(-(n || 200)).join('\n'); },
    /** Télécharge le journal — ce que l'utilisateur peut envoyer en pièce jointe. */
    export: function () {
      try {
        var blob = new Blob([buf.join('\n')], { type: 'text/plain' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'debug-' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.txt';
        document.body.appendChild(a); a.click(); a.remove();
      } catch (e) { console.warn('export failed', e); }
    },
    clear: function () { buf = []; dirty = true; try { localStorage.removeItem(KEY); } catch (e) {} },
    size:  function () { return buf.length; }
  };

  push('I', ['=== session start ===', navigator.userAgent.slice(0, 120)]);
})();
