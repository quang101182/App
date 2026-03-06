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

  // Skip per-block analysis if block count differs by > 10%: comparisons are unreliable
  var blockDiffPct = brut.length > 0 ? blockDiff / brut.length : 0;
  if (blockDiffPct > 0.10) {
    issues.push({ type: 'BLOCK_ANALYSIS_SKIPPED', sev: 'INFO',
      msg: 'Analyse détaillée ignorée (blockDiff=' + blockDiff + ' soit ' + Math.round(blockDiffPct*100) + '% — correspondances non fiables)' });
    var rawScore = Math.max(0, 100 - penalties + bonuses);
    return { file: brutPath.split(/[/\\]/).pop(), srcLang, brutBlocks: brut.length, aiBlocks: ai.length,
      score: rawScore, penalties, bonuses, issues,
      stats: { timestampInText, ellipsisAdded, properNounChanged, exclamationRemoved, typoRegressed } };
  }

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
    // Ne check que les mots capitalisés hors début de ligne, absents PARTOUT dans le texte AI
    // (évite les faux positifs quand l'IA corrige des contractions FR et décale les positions)
    var COMMON_FR = /^(Non|Sur|Mais|Alors|Ainsi|Donc|Car|Ni|Ou|Et|La|Le|Les|Un|Une|Des|Du|Au|Aux|Ce|Se|Si|Il|Elle|Ils|Elles|Je|Tu|Nous|Vous|On|Que|Qui|Dont|Pour|Par|Dans|Avec|Sous|Sans|En|À|De)$/i;
    var brutWords = b.split(/\s+/);
    brutWords.forEach(function(w, wi) {
      if (wi === 0) return; // premier mot = début de phrase, pas un NP
      // Mot capitalisé (3+ chars), non commun, absent partout dans le texte AI
      if (/^[A-ZÀÂÉÈÊ][a-zàâéèêôû]{2,}$/.test(w) && !COMMON_FR.test(w) && !a.includes(w)) {
        issues.push({ type: 'PROPER_NOUN_CHANGED', sev: 'MEDIUM', id: brut[i].id,
          msg: '#' + brut[i].id + ' Nom propre modifié: "' + w + '" absent du texte AI' });
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

// ── BRUT QUALITY SCORE ───────────────────────────────────
// Évalue la qualité du pipeline de transcription lui-même
function scoreBrut(filePath, srcLang) {
  var fs = require('fs');
  var blocks = parseSRT(fs.readFileSync(filePath, 'utf8'));
  if (!blocks.length) return { score: 0, issues: [{ type: 'EMPTY', sev: 'CRITICAL', msg: 'Fichier vide ou invalide' }] };

  var issues = [];
  var penalties = 0;

  // ── 1. Micro-blocs consécutifs < 500ms ────────────────
  var microCount = 0, microRun = 0;
  for (var i = 0; i < blocks.length; i++) {
    var pts = blocks[i].ts.split(' --> ');
    var dur = tsToMs(pts[1]) - tsToMs(pts[0]);
    if (dur < 500 && dur > 0) { microRun++; } else { if (microRun >= 3) microCount += microRun; microRun = 0; }
  }
  if (microRun >= 3) microCount += microRun;
  if (microCount > 5) {
    issues.push({ type: 'MICRO_BLOCKS', sev: 'HIGH', msg: microCount + ' micro-blocs <500ms consécutifs → over-segmentation Groq' });
    penalties += Math.min(30, microCount);
  }

  // ── 2. Hallucination phonétique répétée ──────────────
  var repeatMap = {};
  blocks.forEach(function(b) {
    var t = b.text.trim().toLowerCase();
    if (/^(ah|oh|euh|hm|mm|ugh|ouh|eï)[!?.]?$/.test(t)) repeatMap[t] = (repeatMap[t]||0) + 1;
  });
  var totalRepeat = Object.values(repeatMap).reduce(function(a,b){return a+b;},0);
  if (totalRepeat > 10) {
    issues.push({ type: 'PHONETIC_HALLUCINATION', sev: 'MEDIUM', msg: totalRepeat + ' blocs phonétiques répétés (Ah/Oh/Euh...) — possible hallucination silence' });
    penalties += Math.min(20, Math.floor(totalRepeat / 2));
  }

  // ── 3. Langue étrangère dans SRT censé être FR ───────
  var foreignWords = 0;
  var foreignSamples = [];
  blocks.forEach(function(b) {
    var t = b.text;
    // Mots cyrilliques, CJK, arabes dans un texte majoritairement latin
    var foreignChars = (t.match(/[\u0400-\u04ff\u4e00-\u9fff\u0600-\u06ff]/g) || []).length;
    var latinChars   = (t.match(/[a-zA-ZÀ-ÿ]/g) || []).length;
    if (foreignChars > 2 && foreignChars > latinChars * 0.3) {
      foreignWords++;
      if (foreignSamples.length < 3) foreignSamples.push('#' + b.id + ': ' + t.substring(0,50));
    }
  });
  if (foreignWords > 0) {
    issues.push({ type: 'FOREIGN_LANG_IN_FR', sev: 'HIGH', msg: foreignWords + ' blocs avec caractères non-latins dans SRT français\n    Ex: ' + foreignSamples.join(' | ') });
    penalties += foreignWords * 4;
  }

  // ── 4. Gaps > 30s entre blocs ────────────────────────
  var bigGaps = 0;
  for (var i = 1; i < blocks.length; i++) {
    var prevEnd   = tsToMs(blocks[i-1].ts.split(' --> ')[1]);
    var curStart  = tsToMs(blocks[i].ts.split(' --> ')[0]);
    if (curStart - prevEnd > 30000) bigGaps++;
  }
  if (bigGaps > 3) {
    issues.push({ type: 'BIG_GAPS', sev: 'MEDIUM', msg: bigGaps + ' gaps > 30s — possibles boundaries de chunks problématiques' });
    penalties += bigGaps * 2;
  }

  // ── 5. Chevauchements timestamps ─────────────────────
  var overlaps = 0;
  for (var i = 1; i < blocks.length; i++) {
    var prevEnd  = tsToMs(blocks[i-1].ts.split(' --> ')[1]);
    var curStart = tsToMs(blocks[i].ts.split(' --> ')[0]);
    if (curStart < prevEnd - 50) overlaps++;
  }
  if (overlaps > 0) {
    issues.push({ type: 'OVERLAPS', sev: 'HIGH', msg: overlaps + ' chevauchements de timestamps' });
    penalties += overlaps * 3;
  }

  // ── 6. Blocs > 20s (under-segmentation) ──────────────
  var longBlocks = 0;
  blocks.forEach(function(b) {
    var pts = b.ts.split(' --> ');
    if (tsToMs(pts[1]) - tsToMs(pts[0]) > 20000) longBlocks++;
  });
  if (longBlocks > 2) {
    issues.push({ type: 'LONG_BLOCKS', sev: 'LOW', msg: longBlocks + ' blocs > 20s → under-segmentation' });
    penalties += longBlocks;
  }

  // ── 7. Recommandation pipeline ────────────────────────
  var recommendations = [];
  if (foreignWords > 0 && srcLang !== 'fr') recommendations.push('Relancer avec SOURCE=' + srcLang.toUpperCase() + ' forcé (auto-detect cause hallucinations de langue)');
  if (microCount > 10) recommendations.push('Réduire la sensibilité de segmentation Groq ou activer repairSRTTimestamps');
  if (bigGaps > 3) recommendations.push('Vérifier la taille des chunks — boundaries à ' + bigGaps + ' endroits');

  var brutScore = Math.max(0, 100 - penalties);
  return {
    file: filePath.split(/[/\\]/).pop(),
    srcLang: srcLang,
    blocks: blocks.length,
    score: brutScore,
    penalties: penalties,
    issues: issues,
    recommendations: recommendations,
    stats: { microCount, totalRepeat, foreignWords, bigGaps, overlaps, longBlocks }
  };
}

function tsToMs(ts) {
  var m = ts.match(/(\d+):(\d+):(\d+)[,.](\d+)/);
  if (!m) return 0;
  return +m[1]*3600000 + +m[2]*60000 + +m[3]*1000 + +m[4];
}

// ── TRANSLATION QUALITY SCORE ────────────────────────────
// Évalue la qualité d'une traduction SRT (sans référence ground truth)
function scoreTranslation(inputSRT, outputSRT, srcLang, tgtLang) {
  var input  = parseSRT(inputSRT);
  var output = parseSRT(outputSRT);
  var issues = [];
  var penalties = 0;

  // ── 1. Block count ────────────────────────────────────
  var blockDiff = Math.abs(input.length - output.length);
  if (blockDiff > 0) {
    issues.push({ type: 'BLOCK_COUNT', sev: 'HIGH',
      msg: 'Block count: INPUT=' + input.length + ' OUTPUT=' + output.length + ' (diff=' + blockDiff + ')' });
    penalties += blockDiff * 5;
  }

  // ── 2. Timestamps préservés ───────────────────────────
  var tsMismatch = 0;
  var max = Math.min(input.length, output.length);
  for (var i = 0; i < max; i++) {
    if (input[i].ts !== output[i].ts) tsMismatch++;
  }
  if (tsMismatch > 0) {
    issues.push({ type: 'TIMESTAMP_CHANGED', sev: 'HIGH',
      msg: tsMismatch + ' timestamps modifiés (doivent être identiques à l\'input)' });
    penalties += tsMismatch * 3;
  }

  // ── 3. Timestamp injecté dans texte ──────────────────
  var tsInText = 0;
  output.forEach(function(b) {
    if (/\d{2}:\d{2}:\d{2}[,.]/.test(b.text)) {
      issues.push({ type: 'TIMESTAMP_IN_TEXT', sev: 'CRITICAL', id: b.id,
        msg: '#' + b.id + ' Timestamp injecté dans texte: ' + b.text.substring(0,80) });
      penalties += 20; tsInText++;
    }
  });

  // ── 4. [...] interdit en traduction ──────────────────
  var invalidEllipsis = 0;
  output.forEach(function(b) {
    if (/\[\.\.\.\]/.test(b.text)) {
      issues.push({ type: 'INVALID_ELLIPSIS_TRAD', sev: 'HIGH', id: b.id,
        msg: '#' + b.id + ' [...] interdit en traduction: ' + b.text.substring(0,80) });
      penalties += 8; invalidEllipsis++;
    }
  });

  // ── 5. Langue source encore présente (CJK → latin) ──
  var isCJKSrc = /^(zh|ja|ko)$/.test(srcLang);
  var srcRemaining = 0;
  if (isCJKSrc) {
    output.forEach(function(b) {
      var cjk = (b.text.match(/[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]/g) || []).length;
      var latin = (b.text.match(/[a-zA-ZÀ-ÿ]/g) || []).length;
      if (cjk > 2 && cjk > latin) {
        issues.push({ type: 'SRC_LANG_REMAINING', sev: 'HIGH', id: b.id,
          msg: '#' + b.id + ' Texte source non traduit: ' + b.text.substring(0,80) });
        penalties += 10; srcRemaining++;
      }
    });
  }

  // ── 6. Blocs vides ────────────────────────────────────
  var emptyBlocks = 0;
  output.forEach(function(b) {
    if (!b.text.trim()) {
      issues.push({ type: 'EMPTY_BLOCK', sev: 'MEDIUM', id: b.id,
        msg: '#' + b.id + ' Bloc vide après traduction' });
      penalties += 5; emptyBlocks++;
    }
  });

  // ── 7. Typo FR (espace avant ? ! manquant) ───────────
  var typoFR = 0;
  if (tgtLang === 'fr') {
    output.forEach(function(b) {
      if (/[a-zàâéèêôûùî][?!:;]/.test(b.text)) {
        issues.push({ type: 'TYPO_FR', sev: 'LOW', id: b.id,
          msg: '#' + b.id + ' Espace manquant avant ? ! : ; : ' + b.text.substring(0,60) });
        penalties += 2; typoFR++;
      }
    });
  }

  var rawScore = Math.max(0, 100 - penalties);
  return {
    inputBlocks: input.length,
    outputBlocks: output.length,
    score: rawScore,
    penalties,
    issues,
    stats: { blockDiff, tsMismatch, tsInText, invalidEllipsis, srcRemaining, emptyBlocks, typoFR }
  };
}

module.exports = { score, scoreBrut, scoreTranslation, parseSRT };
