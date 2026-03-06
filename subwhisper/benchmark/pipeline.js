/**
 * SubWhisper Pipeline — Benchmark Autonome
 * v1.0 — 2026-03-06
 *
 * Pipeline complet : RAW_GROQ → BRUT → IA → TRAD
 * Moteurs : Gemini ET/OU DeepSeek
 *
 * Usage :
 *   node pipeline.js --src zh --tgt fr \
 *                    --gem-key GEM_KEY --dsk-key DSK_KEY \
 *                    --input /path/ZH_FR_RAW_GROQ.srt [--outdir /path/]
 *
 * Fichiers générés dans --outdir (défaut : même dossier que --input) :
 *   {SRC}_{TGT}_GEM_BRUT.srt
 *   {SRC}_{TGT}_GEM_IA.srt
 *   {SRC}_{TGT}_GEM_TRAD.srt
 *   {SRC}_{TGT}_DSK_BRUT.srt
 *   {SRC}_{TGT}_DSK_IA.srt
 *   {SRC}_{TGT}_DSK_TRAD.srt
 *   {SRC}_{TGT}_REPORT.md
 */
'use strict';

var fs   = require('fs');
var path = require('path');
var { getTranslateTextPrompt, getCleanTextPrompt } = require('./prompts');

// ── Args ──────────────────────────────────────────────────────────────────────
var args = process.argv.slice(2);
function getArg(name) {
  var i = args.indexOf('--' + name);
  return i !== -1 ? args[i + 1] : null;
}

var SRC_LANG = (getArg('src') || 'zh').toLowerCase();
var TGT_LANG = (getArg('tgt') || 'fr').toLowerCase();
var GEM_KEY  = getArg('gem-key');
var DSK_KEY  = getArg('dsk-key');
var INPUT    = getArg('input');
var OUTDIR   = getArg('outdir');

if (!INPUT) {
  console.error('Usage: node pipeline.js --src LANG --tgt LANG [--gem-key KEY] [--dsk-key KEY] --input FILE.srt [--outdir DIR]');
  console.error('Au moins --gem-key ou --dsk-key requis.');
  process.exit(1);
}
if (!GEM_KEY && !DSK_KEY) {
  console.error('Erreur : --gem-key et/ou --dsk-key requis.');
  process.exit(1);
}

// ── Constantes ────────────────────────────────────────────────────────────────
var LANG_NAMES = {
  zh: 'Chinese', ja: 'Japanese', ko: 'Korean',
  en: 'English', fr: 'French',   es: 'Spanish',
  de: 'German',  it: 'Italian',  pt: 'Portuguese',
  ru: 'Russian', ar: 'Arabic'
};

var BATCH_GEM    = 150;
var BATCH_DSK    = 75;
var RATE_LIMIT   = 1200; // ms entre batches

// ── parseSRT / buildSRT ───────────────────────────────────────────────────────
function parseSRT(srt) {
  return srt.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split(/\n\n+/).filter(function(b) {
    var l = b.trim().split('\n');
    return l.length >= 3 && /^\d+$/.test(l[0].trim()) && l[1].includes('-->');
  }).map(function(b) {
    var l = b.trim().split('\n');
    return { id: l[0].trim(), timestamp: l[1].trim(), text: l.slice(2).join('\n') };
  });
}

function buildSRT(blocks) {
  return blocks.map(function(b) {
    return b.id + '\n' + b.timestamp + '\n' + b.text;
  }).join('\n\n') + '\n';
}

// ── API call ──────────────────────────────────────────────────────────────────
async function callAI(engine, apiKey, prompt) {
  var url, headers, body;
  if (engine === 'deepseek') {
    url     = 'https://api.deepseek.com/v1/chat/completions';
    headers = { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey };
    body    = JSON.stringify({
      model: 'deepseek-chat',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 8192
    });
  } else {
    url     = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + apiKey;
    headers = { 'Content-Type': 'application/json' };
    body    = JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: 8192 }
    });
  }

  var resp = await fetch(url, { method: 'POST', headers: headers, body: body });
  if (!resp.ok) {
    var e = await resp.json().catch(function() { return {}; });
    throw new Error(engine + ' HTTP ' + resp.status + ': ' + ((e.error && e.error.message) || resp.statusText));
  }
  var data = await resp.json();
  if (engine === 'deepseek') {
    return ((data.choices[0].message.content) || '').trim();
  }
  return (((data.candidates[0].content.parts[0].text) || ''))
    .replace(/^```[a-z]*\r?\n?/im, '').replace(/```\s*$/m, '').trim();
}

// ── runBatches — approche [N] text ────────────────────────────────────────────
async function runBatches(engine, apiKey, blocks, getPrompt, batchSize, label) {
  var texts = blocks.map(function(b) { return b.text; });
  var total = Math.ceil(blocks.length / batchSize);

  for (var b = 0; b < total; b++) {
    var start = b * batchSize;
    var batch = blocks.slice(start, start + batchSize);
    process.stdout.write('    [' + label + '] batch ' + (b + 1) + '/' + total + ' (' + batch.length + ' blocs)...');

    var lines  = batch.map(function(blk, j) {
      return '[' + (start + j + 1) + '] ' + blk.text.replace(/\n/g, ' | ');
    });
    var prompt = getPrompt() + '\n\n' + lines.join('\n');

    try {
      var aiText  = await callAI(engine, apiKey, prompt);
      var lineRx  = /^\[(\d+)\]\s*(.*)/gm;
      var m, hits = 0;
      while ((m = lineRx.exec(aiText)) !== null) {
        var idx = parseInt(m[1]) - 1;
        if (idx >= 0 && idx < blocks.length) {
          var corrected = m[2].replace(/ \| /g, '\n').trim();
          if (corrected) { texts[idx] = corrected; hits++; }
        }
      }
      console.log(' OK (' + hits + ' modifiés)');
    } catch (e) {
      console.log(' ERR: ' + e.message + ' (originaux conservés)');
    }

    if (b < total - 1) await new Promise(function(r) { setTimeout(r, RATE_LIMIT); });
  }

  return blocks.map(function(blk, i) {
    return { id: blk.id, timestamp: blk.timestamp, text: texts[i] };
  });
}

// ── runPipeline pour un moteur ────────────────────────────────────────────────
async function runPipeline(engine, apiKey, rawBlocks, srcLang, tgtLang) {
  var srcName   = LANG_NAMES[srcLang] || srcLang;
  var tgtName   = LANG_NAMES[tgtLang] || tgtLang;
  var batchSize = (engine === 'deepseek') ? BATCH_DSK : BATCH_GEM;

  console.log('\n  ── ' + engine.toUpperCase() + ' ──');

  // BRUT : traduction RAW_GROQ → tgtLang
  console.log('  BRUT : ' + srcName + ' → ' + tgtName);
  var brutBlocks = await runBatches(engine, apiKey, rawBlocks,
    function() { return getTranslateTextPrompt(srcName, tgtName, tgtLang, srcLang); },
    batchSize, 'BRUT');

  // IA : nettoyage BRUT en tgtLang
  console.log('  IA : cleanAI (' + tgtName + ')');
  var iaBlocks = await runBatches(engine, apiKey, brutBlocks,
    function() { return getCleanTextPrompt(tgtLang); },
    batchSize, 'IA');

  // TRAD : récupération résiduel étranger dans IA
  console.log('  TRAD : récupération résiduel étranger');
  var tradBlocks = await runBatches(engine, apiKey, iaBlocks,
    function() { return getTranslateTextPrompt(srcName, tgtName, tgtLang, srcLang); },
    batchSize, 'TRAD');

  return {
    brut: buildSRT(brutBlocks),
    ia:   buildSRT(iaBlocks),
    trad: buildSRT(tradBlocks)
  };
}

// ── Métriques ─────────────────────────────────────────────────────────────────
function metrics(srt) {
  var blocks = parseSRT(srt);
  var n   = blocks.length;
  var cjk = blocks.filter(function(b) { return /[\u3040-\u9fff\uac00-\ud7af]/.test(b.text); }).length;
  var nPfx   = blocks.filter(function(b) { return /^\[\d+\]/.test(b.text.trim()); }).length;
  var ellips = blocks.filter(function(b) { return /^\[\.{3}\]$|^\[\.\.\.\]$/.test(b.text.trim()); }).length;
  var tsText = blocks.filter(function(b) { return /\d{2}:\d{2}:\d{2}[,.]/.test(b.text); }).length;
  var FR = /\b(le|la|les|un|une|des|je|tu|il|elle|nous|vous|que|qui|dans|avec|pour|sur|et|est|pas|mais|ou|ce|ne|en|du|au)\b/i;
  var fr = blocks.filter(function(b) { return FR.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text); }).length;
  return { n: n, cjk: cjk, cjkPct: n ? Math.round(cjk / n * 100) : 0, nPfx: nPfx, ellips: ellips, tsText: tsText, fr: fr };
}

function diffCount(srt1, srt2) {
  var b1 = parseSRT(srt1), b2 = parseSRT(srt2);
  var changed = 0, n = Math.min(b1.length, b2.length);
  for (var i = 0; i < n; i++) if (b1[i].text !== b2[i].text) changed++;
  return { changed: changed, total: n };
}

// ── Rapport Markdown ──────────────────────────────────────────────────────────
function buildReport(date, srcLang, tgtLang, rawSrt, gem, dsk) {
  var mRaw = metrics(rawSrt);
  var lines = [
    '# SubWhisper Benchmark — ' + srcLang.toUpperCase() + '→' + tgtLang.toUpperCase() + ' — ' + date,
    '',
    '**Pipeline** : RAW_GROQ → BRUT → IA → TRAD  ',
    '**Moteurs** : Gemini + DeepSeek  ',
    '**Source** : `' + srcLang.toUpperCase() + '` → `' + tgtLang.toUpperCase() + '`',
    '',
    '## RAW_GROQ',
    '- Blocs : **' + mRaw.n + '**',
    '- CJK   : ' + mRaw.cjk + ' (' + mRaw.cjkPct + '%)',
    ''
  ];

  function engineSection(label, result) {
    lines.push('## ' + label);
    lines.push('');
    if (!result) {
      lines.push('*Non exécuté — clé API manquante*');
      lines.push('');
      return;
    }
    var mB = metrics(result.brut);
    var mI = metrics(result.ia);
    var mT = metrics(result.trad);
    var dI = diffCount(result.brut, result.ia);
    var dT = diffCount(result.ia, result.trad);

    lines.push('| Étape | Blocs | CJK | CJK% | FR | [N]bug | [...]inv | TS/texte | Δ modifiés |');
    lines.push('|-------|-------|-----|------|----|--------|----------|----------|------------|');
    lines.push('| BRUT  | ' + mB.n + ' | ' + mB.cjk + ' | ' + mB.cjkPct + '% | ' + mB.fr + ' | ' + mB.nPfx + ' | ' + mB.ellips + ' | ' + mB.tsText + ' | — |');
    lines.push('| IA    | ' + mI.n + ' | ' + mI.cjk + ' | ' + mI.cjkPct + '% | ' + mI.fr + ' | ' + mI.nPfx + ' | ' + mI.ellips + ' | ' + mI.tsText + ' | ' + dI.changed + '/' + dI.total + ' |');
    lines.push('| TRAD  | ' + mT.n + ' | ' + mT.cjk + ' | ' + mT.cjkPct + '% | ' + mT.fr + ' | ' + mT.nPfx + ' | ' + mT.ellips + ' | ' + mT.tsText + ' | ' + dT.changed + '/' + dT.total + ' |');
    lines.push('');

    var verdict = mT.cjk === 0
      ? '✅ Parfait — 0 résiduel'
      : mT.cjkPct <= 2
        ? '🟡 Acceptable — ' + mT.cjk + ' blocs (' + mT.cjkPct + '%)'
        : '🔴 Problème — ' + mT.cjk + ' blocs (' + mT.cjkPct + '%)';
    lines.push('**Résiduel final** : ' + verdict);
    lines.push('');
  }

  engineSection('Gemini', gem);
  engineSection('DeepSeek', dsk);

  // Comparaison et recommandations
  if (gem && dsk) {
    var gT = metrics(gem.trad);
    var dT = metrics(dsk.trad);
    var winner = gT.cjk < dT.cjk ? 'Gemini' : dT.cjk < gT.cjk ? 'DeepSeek' : 'Ex-aequo';

    lines.push('## Comparaison finale');
    lines.push('');
    lines.push('|             | Gemini | DeepSeek |');
    lines.push('|-------------|--------|----------|');
    lines.push('| CJK résiduel | ' + gT.cjk + ' (' + gT.cjkPct + '%) | ' + dT.cjk + ' (' + dT.cjkPct + '%) |');
    lines.push('| [N] bug     | ' + gT.nPfx   + ' | ' + dT.nPfx   + ' |');
    lines.push('| [...] inv   | ' + gT.ellips  + ' | ' + dT.ellips  + ' |');
    lines.push('| TS/texte    | ' + gT.tsText  + ' | ' + dT.tsText  + ' |');
    lines.push('');
    lines.push('**Vainqueur** : ' + winner);
    lines.push('');

    // Recommandations prompt
    var recs = [];
    if (gT.cjk > 0)    recs.push('**Gemini** : ' + gT.cjk + ' blocs CJK résiduels → renforcer règle 7 source `' + srcLang.toUpperCase() + '` dans `getTranslateTextPrompt`');
    if (dT.cjk > 0)    recs.push('**DeepSeek** : ' + dT.cjk + ' blocs CJK résiduels → idem');
    if (gT.ellips > 0) recs.push('**Gemini** : ' + gT.ellips + ' [...] invalides → renforcer règle FORBIDDEN [...] pour blocs entiers');
    if (dT.ellips > 0) recs.push('**DeepSeek** : ' + dT.ellips + ' [...] invalides → idem');
    if (gT.nPfx > 0)   recs.push('**Gemini** : ' + gT.nPfx + ' [N] prefix non strippés → vérifier parsing réponse');
    if (dT.nPfx > 0)   recs.push('**DeepSeek** : ' + dT.nPfx + ' [N] prefix → idem');
    if (gT.tsText > 0) recs.push('**Gemini** : ' + gT.tsText + ' timestamps dans texte → renforcer règle STRUCTURE');
    if (dT.tsText > 0) recs.push('**DeepSeek** : ' + dT.tsText + ' timestamps dans texte → idem');

    lines.push('## Recommandations prompt');
    lines.push('');
    if (recs.length) {
      recs.forEach(function(r) { lines.push('- ' + r); });
    } else {
      lines.push('✅ Aucune régression détectée — prompts OK pour `' + srcLang.toUpperCase() + '→' + tgtLang.toUpperCase() + '`');
    }
    lines.push('');
  }

  return lines.join('\n');
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  var rawSrt    = fs.readFileSync(INPUT, 'utf8');
  var rawBlocks = parseSRT(rawSrt);
  var prefix    = SRC_LANG.toUpperCase() + '_' + TGT_LANG.toUpperCase();
  var outDir    = OUTDIR || path.dirname(path.resolve(INPUT));
  var date      = new Date().toISOString().slice(0, 10);
  var engines   = [GEM_KEY ? 'Gemini' : null, DSK_KEY ? 'DeepSeek' : null].filter(Boolean);

  console.log('SubWhisper Pipeline v1.0 — ' + prefix + ' — ' + date);
  console.log('RAW_GROQ : ' + rawBlocks.length + ' blocs');
  console.log('Moteurs  : ' + engines.join(' + '));
  console.log('Sortie   : ' + outDir);
  console.log('='.repeat(60));

  var gemResult = null, dskResult = null;

  if (GEM_KEY) {
    gemResult = await runPipeline('gemini', GEM_KEY, rawBlocks, SRC_LANG, TGT_LANG);
    fs.writeFileSync(path.join(outDir, prefix + '_GEM_BRUT.srt'), gemResult.brut);
    fs.writeFileSync(path.join(outDir, prefix + '_GEM_IA.srt'),   gemResult.ia);
    fs.writeFileSync(path.join(outDir, prefix + '_GEM_TRAD.srt'), gemResult.trad);
    console.log('\n  ✓ Gemini : 3 fichiers écrits');
  }

  if (DSK_KEY) {
    dskResult = await runPipeline('deepseek', DSK_KEY, rawBlocks, SRC_LANG, TGT_LANG);
    fs.writeFileSync(path.join(outDir, prefix + '_DSK_BRUT.srt'), dskResult.brut);
    fs.writeFileSync(path.join(outDir, prefix + '_DSK_IA.srt'),   dskResult.ia);
    fs.writeFileSync(path.join(outDir, prefix + '_DSK_TRAD.srt'), dskResult.trad);
    console.log('  ✓ DeepSeek : 3 fichiers écrits');
  }

  var report = buildReport(date, SRC_LANG, TGT_LANG, rawSrt, gemResult, dskResult);
  fs.writeFileSync(path.join(outDir, prefix + '_REPORT.md'), report);
  console.log('  ✓ Rapport : ' + prefix + '_REPORT.md');

  console.log('='.repeat(60));
  console.log('Terminé.');
}

main().catch(function(e) { console.error('Fatal :', e.message); process.exit(1); });
