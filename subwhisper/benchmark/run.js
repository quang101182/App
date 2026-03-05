/**
 * SubWhisper Benchmark — Runner principal
 * Usage: node run.js --engine gemini --key YOUR_KEY [--testdir PATH] [--file NAME]
 *
 * Lit tous les *_BRUT.srt du dossier test-files/ (ou --testdir)
 * Appelle l'IA avec le prompt cleanAI
 * Score chaque résultat vs BRUT
 * Génère un rapport Markdown dans results/
 *
 * --file "aaa.EN_BRUT.srt"  Traite uniquement ce fichier (nom exact, sans path)
 *                            Compatible avec --score-only
 */

var fs   = require('fs');
var path = require('path');
var { getCleanTextPrompt } = require('./prompts');
var { score, scoreBrut, parseSRT } = require('./score');

// ── Parse args ────────────────────────────────────────────
var args = process.argv.slice(2);
function getArg(name) {
  var i = args.indexOf('--' + name);
  return i !== -1 ? args[i+1] : null;
}
var ENGINE     = getArg('engine') || 'gemini'; // gemini | deepseek
var API_KEY    = getArg('key');
var TEST_DIR   = getArg('testdir') || path.join(__dirname, 'test-files');
var SCORE_ONLY = args.includes('--score-only');
var FILE_FILTER = getArg('file') || null; // nom de fichier exact (sans path)
var BATCH_SIZE = 200; // blocs par appel API

if (!SCORE_ONLY && !API_KEY) {
  console.error('Usage: node run.js --engine gemini|deepseek --key YOUR_KEY [--testdir PATH] [--file NAME]');
  console.error('       node run.js --engine gemini|deepseek --score-only [--testdir PATH] [--file NAME]');
  process.exit(1);
}

// ── API call ──────────────────────────────────────────────
async function callAI(prompt) {
  var https = require('https');
  var body, url, headers;
  if (ENGINE === 'deepseek') {
    url = 'https://api.deepseek.com/v1/chat/completions';
    headers = { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API_KEY };
    body = JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], max_tokens: 8192 });
  } else {
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + API_KEY;
    headers = { 'Content-Type': 'application/json' };
    body = JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { maxOutputTokens: 8192 } });
  }
  var resp = await fetch(url, { method: 'POST', headers: headers, body: body });
  if (!resp.ok) { var e = await resp.json().catch(()=>({})); throw new Error(ENGINE + ' ' + resp.status + ': ' + (e.error?.message || resp.statusText)); }
  var data = await resp.json();
  if (ENGINE === 'deepseek') return (data.choices[0].message.content || '').trim();
  return ((data.candidates[0].content.parts[0].text) || '').replace(/^```[a-z]*\r?\n?/im,'').replace(/```\s*$/m,'').trim();
}

// ── Score-only mode : utilise les fichiers _AI.srt existants ──────────────
async function scoreOnlyFile(filePath) {
  var fileName = path.basename(filePath);
  var langMatch = fileName.match(/_([A-Z]{2,3})_BRUT/i);
  var srcLang = langMatch ? langMatch[1].toLowerCase() : 'fr';

  // Score BRUT
  var brutResult = scoreBrut(filePath, srcLang);
  console.log('\n[BRUT] ' + fileName + ' — Score pipeline: ' + brutResult.score + '/100');

  // Find AI output
  var aiFileName = fileName.replace('_BRUT.srt', '_' + ENGINE.toUpperCase() + '_AI.srt');
  var aiPath = path.join(path.dirname(filePath), aiFileName);

  if (!fs.existsSync(aiPath)) {
    console.log('  [SKIP] Fichier AI introuvable: ' + aiFileName);
    return null;
  }

  var aiContent = fs.readFileSync(aiPath, 'utf8');
  var result = score(filePath, aiContent, srcLang);
  result.brutScore = brutResult.score;
  result.brutIssues = brutResult.issues;
  result.brutRecs = brutResult.recommendations;
  result.brutStats = brutResult.stats;
  console.log('  [' + ENGINE.toUpperCase() + '] Score AI: ' + result.score + '/100 | Issues: ' + result.issues.length);
  return result;
}

// ── Process one file ──────────────────────────────────────
async function processFile(filePath) {
  var fileName = path.basename(filePath);
  // Extract source language from filename: name_ZH_BRUT.srt → zh
  var langMatch = fileName.match(/_([A-Z]{2,3})_BRUT/i);
  var srcLang = langMatch ? langMatch[1].toLowerCase() : 'fr';
  // For cleanAI, the text is already in French (translated output)
  var srtTextLang = 'fr';

  // ── Score BRUT (pipeline qualité) ────────────────────
  var brutResult = scoreBrut(filePath, srcLang);
  console.log('\n[BRUT] ' + fileName + ' — Score pipeline: ' + brutResult.score + '/100');
  if (brutResult.issues.length) brutResult.issues.forEach(function(iss) { console.log('  ⚠ [' + iss.sev + '] ' + iss.msg.split('\n')[0]); });
  if (brutResult.recommendations.length) brutResult.recommendations.forEach(function(r) { console.log('  → ' + r); });

  console.log('\n[' + ENGINE.toUpperCase() + '] Processing: ' + fileName + ' (src=' + srcLang + ')');

  var content = fs.readFileSync(filePath, 'utf8');
  var blocks = parseSRT(content);
  console.log('  Blocks: ' + blocks.length);

  // Approche v8.50 : texte numéroté [N] — block count garanti par reconstruction algo
  var correctedTexts = blocks.map(function(b) { return b.text; });
  var totalBatches = Math.ceil(blocks.length / BATCH_SIZE);

  for (var b = 0; b < totalBatches; b++) {
    var batchBlocks = blocks.slice(b * BATCH_SIZE, (b+1) * BATCH_SIZE);
    var batchOffset = b * BATCH_SIZE;
    process.stdout.write('  Batch ' + (b+1) + '/' + totalBatches + '...');

    var promptLines = batchBlocks.map(function(blk, j) {
      return '[' + (batchOffset + j + 1) + '] ' + blk.text.replace(/\n/g, ' | ');
    });
    var prompt = getCleanTextPrompt(srtTextLang) + '\n\n' + promptLines.join('\n');

    try {
      var aiText = await callAI(prompt);
      var lineRx = /^\[(\d+)\]\s*(.*)/gm;
      var m;
      while ((m = lineRx.exec(aiText)) !== null) {
        var idx = parseInt(m[1]) - 1;
        if (idx >= 0 && idx < blocks.length) {
          var corrected = m[2].replace(/ \| /g, '\n').trim();
          if (corrected) correctedTexts[idx] = corrected;
        }
      }
      console.log(' OK');
    } catch(e) {
      console.log(' ERROR: ' + e.message);
      // textes originaux conservés pour ce batch
    }
    // Rate limit throttle
    if (b < totalBatches - 1) await new Promise(r => setTimeout(r, 1000));
  }

  // Reconstruction SRT depuis structure originale (timestamps intouchés)
  var aiContent = blocks.map(function(blk, i) {
    return blk.id + '\n' + blk.timestamp + '\n' + correctedTexts[i];
  }).join('\n\n') + '\n';
  var result = score(filePath, aiContent, srcLang);
  result.brutScore = brutResult.score;
  result.brutIssues = brutResult.issues;
  result.brutRecs = brutResult.recommendations;
  result.brutStats = brutResult.stats;

  // Save AI output
  var outName = fileName.replace('_BRUT.srt', '_' + ENGINE.toUpperCase() + '_AI.srt');
  var outPath = path.join(path.dirname(filePath), outName);
  fs.writeFileSync(outPath, aiContent);
  console.log('  Score: ' + result.score + '/100 | Penalties: ' + result.penalties + ' | Issues: ' + result.issues.length);

  return result;
}

// ── Main ──────────────────────────────────────────────────
async function main() {
  var files = fs.readdirSync(TEST_DIR)
    .filter(f => f.endsWith('_BRUT.srt'))
    .map(f => path.join(TEST_DIR, f));

  if (!files.length) {
    // Also check parent test-files folder
    var defaultDir = path.join(__dirname, 'test-files');
    if (fs.existsSync(defaultDir)) {
      files = fs.readdirSync(defaultDir).filter(f => f.endsWith('_BRUT.srt')).map(f => path.join(defaultDir, f));
    }
  }

  if (!files.length) { console.error('No *_BRUT.srt files found in ' + TEST_DIR); process.exit(1); }

  // ── Filtre --file ──────────────────────────────────────
  if (FILE_FILTER) {
    var filterName = path.basename(FILE_FILTER); // sécurité : ignorer tout path éventuel
    files = files.filter(f => path.basename(f) === filterName);
    if (!files.length) {
      console.error('--file "' + filterName + '" introuvable dans ' + TEST_DIR);
      process.exit(1);
    }
  }

  console.log('SubWhisper Benchmark — Engine: ' + ENGINE.toUpperCase());
  console.log('Files: ' + files.length);
  console.log('='.repeat(60));

  var allResults = [];
  if (SCORE_ONLY) {
    console.log('Mode: --score-only (aucun appel API)');
    for (var f of files) {
      try {
        var r = await scoreOnlyFile(f);
        if (r) allResults.push(r);
      } catch(e) { console.error('  FAILED: ' + e.message); }
    }
  } else {
    for (var f of files) {
      try { allResults.push(await processFile(f)); }
      catch(e) { console.error('  FAILED: ' + e.message); }
    }
  }

  // ── Generate report ───────────────────────────────────
  var date = new Date().toISOString().slice(0,10);
  var reportLines = [
    '# SubWhisper Benchmark — ' + ENGINE.toUpperCase() + ' — ' + date,
    '',
    '## Résumé',
    '',
    '| Fichier | Src | Score BRUT | Score AI | Issues AI | Recommandations |',
    '|---------|-----|-----------|---------|-----------|----------------|',
  ];

  var totalScore = 0, totalBrutScore = 0;
  allResults.forEach(function(r) {
    var brutEmoji = r.brutScore >= 90 ? '🟢' : r.brutScore >= 70 ? '🟡' : '🔴';
    var aiEmoji   = r.score >= 90 ? '🟢' : r.score >= 70 ? '🟡' : '🔴';
    var recs = r.brutRecs && r.brutRecs.length ? r.brutRecs[0].substring(0,40)+'...' : '—';
    reportLines.push('| ' + r.file.substring(0,35) + ' | ' + r.srcLang.toUpperCase() + ' | ' + brutEmoji + ' **' + r.brutScore + '** | ' + aiEmoji + ' **' + r.score + '** | ' + r.issues.length + ' | ' + recs + ' |');
    totalScore += r.score;
    totalBrutScore += (r.brutScore || 0);
  });

  var avg = allResults.length ? Math.round(totalScore / allResults.length) : 0;
  var avgBrut = allResults.length ? Math.round(totalBrutScore / allResults.length) : 0;
  reportLines.push('', '**Score moyen BRUT (pipeline) : ' + avgBrut + '/100**');
  reportLines.push('**Score moyen AI (cleanAI) : ' + avg + '/100**', '');

  // Detail per file
  allResults.forEach(function(r) {
    reportLines.push('## ' + r.file);
    reportLines.push('');
    reportLines.push('### Pipeline BRUT — Score: ' + r.brutScore + '/100');
    reportLines.push('Stats: ' + JSON.stringify(r.brutStats));
    if (r.brutIssues && r.brutIssues.length) {
      r.brutIssues.forEach(function(iss) { reportLines.push('- ⚠ **[' + iss.sev + '] ' + iss.type + '** : ' + iss.msg); });
    } else { reportLines.push('✓ Pipeline propre'); }
    if (r.brutRecs && r.brutRecs.length) {
      reportLines.push(''); reportLines.push('**Recommandations pipeline :**');
      r.brutRecs.forEach(function(rec) { reportLines.push('- → ' + rec); });
    }
    reportLines.push('');
    reportLines.push('### AI CleanAI — Score: ' + r.score + '/100');
    reportLines.push('Penalties: ' + r.penalties + ' | Bonuses: ' + r.bonuses);
    reportLines.push('Stats: ' + JSON.stringify(r.stats));
    reportLines.push('');
    if (r.issues.length) {
      r.issues.forEach(function(iss) {
        reportLines.push('- **[' + iss.sev + '] ' + iss.type + '** : ' + iss.msg);
      });
    } else {
      reportLines.push('✓ Aucun problème détecté');
    }
    reportLines.push('');
  });

  var reportPath = path.join(__dirname, 'results', date + '_' + ENGINE + '_score.md');
  fs.writeFileSync(reportPath, reportLines.join('\n'));

  console.log('\n' + '='.repeat(60));
  console.log('Score moyen : ' + avg + '/100');
  console.log('Rapport : ' + reportPath);
}

main().catch(function(e) { console.error('Fatal:', e.message); process.exit(1); });
