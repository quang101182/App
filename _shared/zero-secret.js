/**
 * zero-secret — retire la saisie de secret des applications PERSO de Quang.
 *
 * Écrit le 29/08/2026, en application de .claude/rules/apps-perso-zero-secret.md :
 * « une application perso ne demande JAMAIS de secret à Quang ».
 * Chaque app est désormais servie par le worker se7enai-apps sur son propre
 * sous-domaine, derrière Cloudflare Access, et le secret y est injecté côté serveur.
 *
 * ⚠ SOURCE DE VÉRITÉ : ce fichier. Il est INLINÉ dans chaque index.html (les apps
 * sont mono-fichier). Corriger ICI, puis re-inliner — ne jamais laisser diverger.
 *
 * Usage (à la fin du <body>) :
 *   ZeroSecret.init({
 *     home: 'music.se7enai.com',        // l'adresse qui sert cette app
 *     name: 'music·ai',
 *     fields: ['cfg-gw-secret'],        // les id des champs de saisie à masquer
 *     hasSecret: function(){ return !!localStorage.getItem('music_ai_gw_secret'); }
 *   });
 *
 * Trois cas, et un seul laisse un champ visible :
 *   1. secret présent            -> on masque le champ : il n'a plus de raison d'être.
 *   2. secret absent, hors home  -> écran de renvoi vers la bonne adresse.
 *   3. secret absent, SUR home   -> on laisse le champ ET on explique : c'est le cas
 *      de panne (worker ou Access), et priver Quang de tout recours serait pire que
 *      le problème qu'on corrige.
 */
window.ZeroSecret = (function () {
  function hide(ids) {
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      // On masque le CONTENEUR visuel, pas l'input : le code de l'app lit encore
      // sa .value, et supprimer l'élément casserait tout ce qui le référence.
      var box = el.closest('.setting-group, .settings-row, .field-row, label, div') || el;
      box.style.display = 'none';
      el.setAttribute('data-zero-secret', 'hidden');
    });
  }

  function screen(name, home) {
    var d = document.createElement('div');
    d.setAttribute('style',
      'position:fixed;inset:0;z-index:2147483647;background:#0e0e11;color:#eee;' +
      'display:flex;align-items:center;justify-content:center;padding:1.5rem;' +
      'font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif');
    d.innerHTML =
      '<div style="max-width:30rem">' +
      '<h1 style="font-size:1.35rem;margin:0 0 .8rem">' + name + ' a déménagé</h1>' +
      '<p style="margin:0 0 1rem;color:#bbb">Cette adresse ne sert plus l\'application : ' +
      'elle demandait une clé à saisir à la main. La nouvelle te reconnaît toute seule, ' +
      'et tu n\'as plus rien à coller nulle part.</p>' +
      '<p style="margin:0 0 1.5rem"><a href="https://' + home + '/" ' +
      'style="color:#7cc4ff;font-size:1.1rem;font-weight:600">' + home + '</a></p>' +
      '<p style="margin:0;color:#777;font-size:.85rem">Pense à remplacer ton favori.</p>' +
      '</div>';
    document.body.appendChild(d);
  }

  function notice(home) {
    var d = document.createElement('div');
    d.setAttribute('style',
      'position:fixed;left:0;right:0;top:0;z-index:2147483646;background:#7a2020;color:#fff;' +
      'padding:.6rem 1rem;font:14px/1.5 system-ui,sans-serif;text-align:center');
    d.textContent = 'La clé n\'a pas été injectée par ' + home +
      ' — saisis-la dans les réglages en attendant, et signale-le.';
    document.body.appendChild(d);
  }

  return {
    init: function (cfg) {
      try {
        var ok = false;
        try { ok = !!cfg.hasSecret(); } catch (e) { ok = false; }
        if (ok) { hide(cfg.fields); return; }
        if (location.hostname !== cfg.home) { screen(cfg.name, cfg.home); return; }
        notice(cfg.home);            // sur le bon domaine mais sans secret = panne
      } catch (e) { /* ne JAMAIS casser l'app pour ça */ }
    }
  };
})();
