/**
 * SubWhisper Benchmark — Heuristiques de scoring
 * Compare un SRT "AI" vs le BRUT de référence
 */

function parseSRT(content) {
  return content.trim().split(/\r?\n\r?\n/).map(function(b) {
    var lines = b.trim().split(/\r?\n/);
    if (lines.length < 3) return null;
    return { id: lines[0].trim(), ts: lines[1].trim(), text: lines.slice(2).join('\n').trim() };
  }).filter(Boolean);
}

function score(brutPath, aiContent, srcLang) {
  var fs = require('fs');
  var brut = parseSRT(fs.readFileSync(brutPath, 'utf8'));
  var ai   = parseSRT(aiContent);

  var issues = [];
  var penalties = 0;
  var bonuses = 0;

  // ── 1. Block count ────────────────────────────────────────
  var blockDiff = Math.abs(brut.length - ai.length);
  if (blockDiff > 0) {
    issues.push({ type: 'BLOCK_COUNT', sev: 'HIGH',
      msg: 'Block count: BRUT=' + brut.length + ' AI=' + ai.length + ' (diff=' + blockDiff + ')' });
    penalties += blockDiff * 5;
  }

  var max = Math.min(brut.length, ai.length);
  var ellipsisAdded = 0, timestampInText = 0, ellipsisRemoved = 0;
  var properNounChanged = 0, exclamationRemoved = 0, typoRegressed = 0;

  for (var i = 0; i < max; i++) {
    var b = brut[i].text, a = ai[i].text;
    if (b === a) continue;

    // ── 2. Timestamp dans texte ───────────────────────────
    if (/\d{2}:\d{2}:\d{2}[,.]/.test(a) && !/\d{2}:\d{2}:\d{2}[,.]/.test(b)) {
      issues.push({ type: 'TIMESTAMP_IN_TEXT', sev: 'CRITICAL', id: brut[i].id,
        msg: '#' + brut[i].id + ' Timestamp injecté dans texte: ' + a.substring(0,80) });
      penalties += 20;
      timestampInText++;
    }

    // ── 3. [...] introduit sur contenu valide ─────────────
    var brutHasEllipsis = (b.match(/\[\.\.\.\]/g) || []).length;
    var aiHasEllipsis   = (a.match(/\[\.\.\.\]/g) || []).length;
    if (aiHasEllipsis > brutHasEllipsis) {
      // Vérifier si c'était du vrai contenu (plus de 3 chars hors [...])
      var cleanB = b.replace(/\[\.\.\.\]/g,'').trim();
      if (cleanB.length > 3) {
        issues.push({ type: 'INVALID_ELLIPSIS', sev: 'HIGH', id: brut[i].id,
          msg: '#' + brut[i].id + ' [...] sur contenu valide\n    BRUT: ' + b + '\n    AI  : ' + a });
        penalties += 8;
        ellipsisAdded++;
      }
    }

    // ── 4. Phrase complétée (mots ajoutés) ────────────────
    // Ligne BRUT sans ponctuation finale → AI a ajouté des mots
    if (!/[.!?…]$/.test(b) && a.length > b.length + 5 && a.startsWith(b.substring(0, Math.floor(b.length * 0.8)))) {
      issues.push({ type: 'SENTENCE_COMPLETED', sev: 'HIGH', id: brut[i].id,
        msg: '#' + brut[i].id + ' Phrase tronquée complétée\n    BRUT: ' + b + '\n    AI  : ' + a });
      penalties += 10;
    }

    // ── 5. Nom propre modifié ─────────────────────────────
    var brutWords = b.split(/\s+/);
    var aiWords   = a.split(/\s+/);
    brutWords.forEach(function(w, wi) {
      if (!aiWords[wi]) return;
      // Mot avec majuscule pas en début de phrase
      if (/^[A-ZÀÂÉÈÊ][a-zàâéèêôû]{2,}$/.test(w) && aiWords[wi] !== w && wi > 0) {
        issues.push({ type: 'PROPER_NOUN_CHANGED', sev: 'MEDIUM', id: brut[i].id,
          msg: '#' + brut[i].id + ' Nom propre modifié: "' + w + '" → "' + aiWords[wi] + '"' });
        penalties += 6;
        properNounChanged++;
      }
    });

    // ── 6. Typo française régression (espace avant ? ! retiré) ──
    if (/ [?!]/.test(b) && !/ [?!]/.test(a) && a.replace(/ /g,'') === b.replace(/ /g,'')) {
      issues.push({ type: 'TYPO_REGRESSION', sev: 'MEDIUM', id: brut[i].id,
        msg: '#' + brut[i].id + ' Espace avant ? ! supprimé\n    BRUT: ' + b + '\n    AI  : ' + a });
      penalties += 4;
      typoRegressed++;
    }

    // ── 7. Interjection courte supprimée ─────────────────
    if (/^\[?\.\.\.\]?$/.test(a.replace(/[^a-zA-Z.[\]]/g,'')) &&
        /^[A-ZÀÂÉÈÊa-zàâéèêôû]{1,6}[!?]?$/.test(b.trim())) {
      issues.push({ type: 'EXCLAMATION_REMOVED', sev: 'MEDIUM', id: brut[i].id,
        msg: '#' + brut[i].id + ' Interjection remplacée: "' + b + '" → "' + a + '"' });
      penalties += 5;
      exclamationRemoved++;
    }

    // ── 8. Bonus : faute réelle corrigée ─────────────────
    if (/\bsi il\b/i.test(b) && /\bs'il\b/i.test(a)) bonuses += 3;
    if (/\bca \b/.test(b) && /\bça \b/.test(a)) bonuses += 2;
  }

  var rawScore = Math.max(0, 100 - penalties + bonuses);

  return {
    file: brutPath.split(/[/\\]/).pop(),
    srcLang: srcLang,
    brutBlocks: brut.length,
    aiBlocks: ai.length,
    score: rawScore,
    penalties: penalties,
    bonuses: bonuses,
    issues: issues,
    stats: { timestampInText, ellipsisAdded, properNounChanged, exclamationRemoved, typoRegressed }
  };
}

module.exports = { score, parseSRT };
