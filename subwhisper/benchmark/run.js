/**
 * SubWhisper Benchmark — Runner principal
 * Usage: node run.js --engine gemini --key YOUR_KEY [--testdir PATH]
 *
 * Lit tous les *_BRUT.srt du dossier test-files/ (ou --testdir)
 * Appelle l'IA avec le prompt cleanAI
 * Score chaque résultat vs BRUT
 * Génère un rapport Markdown dans results/
 */

var fs   = require('fs');
var path = require('path');
var { getCleanPrompt } = require('./prompts');
var { score, parseSRT } = require('./score');

// ── Parse args ────────────────────────────────────────────
var args = process.argv.slice(2);
function getArg(name) {
  var i = args.indexOf('--' + name);
  return i !== -1 ? args[i+1] : null;
}
var ENGINE  = getArg('engine') || 'gemini'; // gemini | deepseek
var API_KEY = getArg('key');
var TEST_DIR = getArg('testdir') || path.join(__dirname, 'test-files');
var BATCH_SIZE = 200; // blocs par appel API

if (!API_KEY) {
  console.error('Usage: node run.js --engine gemini|deepseek --key YOUR_KEY [--testdir PATH]');
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

// ── Process one file ──────────────────────────────────────
async function processFile(filePath) {
  var fileName = path.basename(filePath);
  // Extract source language from filename: name_ZH_BRUT.srt → zh
  var langMatch = fileName.match(/_([A-Z]{2,3})_BRUT/i);
  var srcLang = langMatch ? langMatch[1].toLowerCase() : 'fr';
  // For cleanAI, the text is already in French (translated output)
  var srtTextLang = 'fr';

  console.log('\n[' + ENGINE.toUpperCase() + '] Processing: ' + fileName + ' (src=' + srcLang + ')');

  var content = fs.readFileSync(filePath, 'utf8');
  var blocks = parseSRT(content);
  console.log('  Blocks: ' + blocks.length);

  // Split into batches
  var allBlocks = content.trim().split(/\r?\n\r?\n/).filter(b => b.trim());
  var batches = [];
  for (var i = 0; i < allBlocks.length; i += BATCH_SIZE) batches.push(allBlocks.slice(i, i+BATCH_SIZE));

  var results = [];
  for (var b = 0; b < batches.length; b++) {
    process.stdout.write('  Batch ' + (b+1) + '/' + batches.length + '...');
    var batchSrt = batches[b].join('\n\n');
    var prompt = getCleanPrompt(srtTextLang) + '\n\n' + batchSrt;
    try {
      var text = await callAI(prompt);
      results.push(text);
      console.log(' OK');
    } catch(e) {
      console.log(' ERROR: ' + e.message);
      results.push(batchSrt); // keep original on error
    }
    // Rate limit throttle
    if (b < batches.length - 1) await new Promise(r => setTimeout(r, 1000));
  }

  var aiContent = results.join('\n\n') + '\n';
  var result = score(filePath, aiContent, srcLang);

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

  console.log('SubWhisper Benchmark — Engine: ' + ENGINE.toUpperCase());
  console.log('Files: ' + files.length);
  console.log('='.repeat(60));

  var allResults = [];
  for (var f of files) {
    try { allResults.push(await processFile(f)); }
    catch(e) { console.error('  FAILED: ' + e.message); }
  }

  // ── Generate report ───────────────────────────────────
  var date = new Date().toISOString().slice(0,10);
  var reportLines = [
    '# SubWhisper Benchmark — ' + ENGINE.toUpperCase() + ' — ' + date,
    '',
    '## Résumé',
    '',
    '| Fichier | Src | Blocs BRUT | Blocs AI | Score | Issues |',
    '|---------|-----|-----------|---------|-------|--------|',
  ];

  var totalScore = 0;
  allResults.forEach(function(r) {
    reportLines.push('| ' + r.file + ' | ' + r.srcLang.toUpperCase() + ' | ' + r.brutBlocks + ' | ' + r.aiBlocks + ' | **' + r.score + '/100** | ' + r.issues.length + ' |');
    totalScore += r.score;
  });

  var avg = allResults.length ? Math.round(totalScore / allResults.length) : 0;
  reportLines.push('', '**Score moyen : ' + avg + '/100**', '');

  // Detail per file
  allResults.forEach(function(r) {
    reportLines.push('## ' + r.file);
    reportLines.push('Score: ' + r.score + '/100 | Penalties: ' + r.penalties + ' | Bonuses: ' + r.bonuses);
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
