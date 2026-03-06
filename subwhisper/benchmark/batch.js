/**
 * SubWhisper Batch Lab — Runner v1.0
 * Amélioration continue de chaque étape du pipeline SubWhisper
 * Toujours Gemini vs DeepSeek côte à côte
 *
 * Usage:
 *   node batch.js --step 1 --file video_ZH_BRUT.srt [--src zh]
 *   node batch.js --step 2 --file video_ZH_BRUT.srt --src zh --out fr --gem-key KEY --dsk-key KEY
 *   node batch.js --step 3 --file video_FR_BRUT.srt --out fr --gem-key KEY --dsk-key KEY
 *   node batch.js --step 4 --file video_ZH_BRUT.srt --out fr --gem-key KEY --dsk-key KEY
 *   node batch.js --history [--step N] [--file NAME]
 *
 * Steps:
 *   1 = Analyse Groq (scoreBrut, aucun appel IA)
 *   2 = Traduction (src→out, Gemini + DeepSeek)
 *   3 = CleanAI (nettoyage, Gemini + DeepSeek)
 *   4 = TRAD hybride (mélange langues→out, Gemini + DeepSeek)
 */

'use strict';
var fs      = require('fs');
var path    = require('path');
var crypto  = require('crypto');

var { getCleanTextPrompt, getTranslateTextPrompt } = require('./prompts');
var { score, scoreBrut, scoreTranslation, parseSRT } = require('./score');
var { generateHTML } = require('./reporters/html');

// ── Parse args ─────────────────────────────────────────────────────────────────
var args = process.argv.slice(2);
function getArg(name) {
  var i = args.indexOf('--' + name);
  return (i !== -1 && args[i+1] !== undefined) ? args[i+1] : null;
}
function hasFlag(name) { return args.includes('--' + name); }

var STEP      = parseInt(getArg('step') || '0');
var FILE_ARG  = getArg('file');
var SRC_LANG  = getArg('src') || 'auto';
var OUT_LANG  = getArg('out') || 'fr';
var GEM_KEY   = getArg('gem-key');
var DSK_KEY   = getArg('dsk-key');
var SHOW_HIST = hasFlag('history');

var BENCH_DIR   = __dirname;
var HIST_DIR    = path.join(BENCH_DIR, 'history');
var RESULTS_DIR = path.join(BENCH_DIR, 'results');

// Créer les dossiers si besoin
[HIST_DIR, RESULTS_DIR].forEach(function(d) {
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
});

var HIST_FILE = path.join(HIST_DIR, 'index.json');

// ── History ────────────────────────────────────────────────────────────────────
function loadHistory() {
  if (!fs.existsSync(HIST_FILE)) return { runs: [] };
  try { return JSON.parse(fs.readFileSync(HIST_FILE, 'utf8')); }
  catch(e) { return { runs: [] }; }
}

function saveHistory(hist) {
  fs.writeFileSync(HIST_FILE, JSON.stringify(hist, null, 2));
}

function addHistoryEntry(entry) {
  var hist = loadHistory();
  hist.runs.unshift(entry);
  saveHistory(hist);
}

function showHistory(filterStep, filterFile) {
  var hist = loadHistory();
  var runs = hist.runs;
  if (filterStep) runs = runs.filter(function(r) { return r.step === filterStep; });
  if (filterFile) runs = runs.filter(function(r) { return r.file.includes(filterFile); });
  if (!runs.length) { console.log('Aucun run trouvé.'); return; }
  console.log('\nSubWhisper Batch Lab — Historique');
  console.log('='.repeat(80));
  console.log(' Date              | Step | Fichier              | Gemini | DeepSeek | Note');
  console.log('-'.repeat(80));
  runs.slice(0, 30).forEach(function(r) {
    var gScore = r.gemini && r.gemini.score !== undefined ? (typeof r.gemini.score === 'object' ? r.gemini.score.score : r.gemini.score) : '--';
    var dScore = r.deepseek && r.deepseek.score !== undefined ? (typeof r.deepseek.score === 'object' ? r.deepseek.score.score : r.deepseek.score) : '--';
    var date   = (r.date || '').substring(0,16).replace('T',' ');
    var file   = (r.file || '').substring(0,20).padEnd(20);
    var note   = r.edgeCase ? '⚠ edge' : (r.userNote ? r.userNote.substring(0,20) : '');
    console.log(' ' + date + ' | ' + String(r.step).padEnd(4) + ' | ' + file + ' | ' + String(gScore).padStart(6) + ' | ' + String(dScore).padStart(8) + ' | ' + note);
  });
  console.log('='.repeat(80));
  console.log('Total: ' + runs.length + ' runs');
}

// ── API call ───────────────────────────────────────────────────────────────────
async function callAI(engine, apiKey, prompt) {
  var url, headers, body;
  if (engine === 'deepseek') {
    url = 'https://api.deepseek.com/v1/chat/completions';
    headers = { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey };
    body = JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], max_tokens: 8192 });
  } else { // gemini
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + apiKey;
    headers = { 'Content-Type': 'application/json' };
    body = JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { maxOutputTokens: 8192 } });
  }
  var resp = await fetch(url, { method: 'POST', headers: headers, body: body });
  if (!resp.ok) {
    var e = await resp.json().catch(function() { return {}; });
    throw new Error(engine + ' HTTP ' + resp.status + ': ' + (e.error && e.error.message ? e.error.message : resp.statusText));
  }
  var data = await resp.json();
  if (engine === 'deepseek') return (data.choices[0].message.content || '').trim();
  return ((data.candidates[0].content.parts[0].text) || '')
    .replace(/^```[a-z]*\r?\n?/im, '').replace(/```\s*$/m, '').trim();
}

// ── Process numbered [N] batches ───────────────────────────────────────────────
async function processNumberedBatches(engine, apiKey, blocks, getPromptFn, batchSize) {
  var correctedTexts = blocks.map(function(b) { return b.text; });
  var totalBatches = Math.ceil(blocks.length / batchSize);

  for (var b = 0; b < totalBatches; b++) {
    var batchBlocks = blocks.slice(b * batchSize, (b+1) * batchSize);
    var batchOffset = b * batchSize;
    process.stdout.write('    Batch ' + (b+1) + '/' + totalBatches + ' [' + engine.toUpperCase() + ']...');

    var promptLines = batchBlocks.map(function(blk, j) {
      return '[' + (batchOffset + j + 1) + '] ' + blk.text.replace(/\n/g, ' | ');
    });
    var prompt = getPromptFn() + '\n\n' + promptLines.join('\n');

    try {
      var aiText = await callAI(engine, apiKey, prompt);
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
    }
    if (b < totalBatches - 1) await new Promise(function(r) { setTimeout(r, 1000); });
  }
  return correctedTexts;
}

function reconstructSRT(blocks, texts) {
  return blocks.map(function(blk, i) {
    return blk.id + '\n' + blk.ts + '\n' + texts[i];
  }).join('\n\n') + '\n';
}

// ── Lang map ──────────────────────────────────────────────────────────────────
var LANG_NAMES = {
  zh:'Chinese', ja:'Japanese', ko:'Korean', en:'English', fr:'French',
  es:'Spanish', de:'German', pt:'Portuguese', it:'Italian', ru:'Russian',
  ar:'Arabic', vi:'Vietnamese', pl:'Polish', tr:'Turkish', hi:'Hindi', nl:'Dutch'
};
function langName(code) { return LANG_NAMES[code] || (code ? code.toUpperCase() : 'Unknown'); }
function detectLangFromName(fileName) {
  var m = fileName.match(/_([A-Z]{2,3})_/i);
  return m ? m[1].toLowerCase() : 'fr';
}

// ── Run engine pair (Gemini + DeepSeek) ────────────────────────────────────────
async function runEnginePair(blocks, getPromptFn, batchSize, scoreInput, scoreInputSRT, srcLang, tgtLang, runId, stepNum) {
  var gemResult = null, dskResult = null;
  var gemOutput = null, dskOutput = null;

  if (GEM_KEY) {
    console.log('\n  → Gemini...');
    try {
      var gemTexts = await processNumberedBatches('gemini', GEM_KEY, blocks, getPromptFn, batchSize);
      gemOutput = reconstructSRT(blocks, gemTexts);
      gemResult = stepNum === 3
        ? score(scoreInput, gemOutput, tgtLang)
        : scoreTranslation(scoreInputSRT, gemOutput, srcLang, tgtLang);
      gemResult.engine = 'gemini';
      var gemFile = runId + '_gemini.srt';
      fs.writeFileSync(path.join(RESULTS_DIR, gemFile), gemOutput);
      gemResult.outputFile = gemFile;
      console.log('  Gemini: ' + gemResult.score + '/100 (' + gemResult.issues.length + ' issues)');
    } catch(e) { console.error('  Gemini FAILED: ' + e.message); }
  }

  if (DSK_KEY) {
    console.log('\n  → DeepSeek...');
    try {
      var dskTexts = await processNumberedBatches('deepseek', DSK_KEY, blocks, getPromptFn, batchSize);
      dskOutput = reconstructSRT(blocks, dskTexts);
      dskResult = stepNum === 3
        ? score(scoreInput, dskOutput, tgtLang)
        : scoreTranslation(scoreInputSRT, dskOutput, srcLang, tgtLang);
      dskResult.engine = 'deepseek';
      var dskFile = runId + '_deepseek.srt';
      fs.writeFileSync(path.join(RESULTS_DIR, dskFile), dskOutput);
      dskResult.outputFile = dskFile;
      console.log('  DeepSeek: ' + dskResult.score + '/100 (' + dskResult.issues.length + ' issues)');
    } catch(e) { console.error('  DeepSeek FAILED: ' + e.message); }
  }

  return { gemResult, dskResult, gemOutput, dskOutput };
}

// ── STEP 1 : Analyse Groq ──────────────────────────────────────────────────────
async function runStep1(filePath) {
  var fileName = path.basename(filePath);
  var srcLang  = SRC_LANG !== 'auto' ? SRC_LANG : detectLangFromName(fileName);
  console.log('\n[STEP 1 — Groq Analysis] ' + fileName + ' (src=' + srcLang.toUpperCase() + ')');

  var content  = fs.readFileSync(filePath, 'utf8');
  var result   = scoreBrut(filePath, srcLang);
  console.log('Score pipeline: ' + result.score + '/100');
  result.issues.forEach(function(iss) { console.log('  ⚠ [' + iss.sev + '] ' + iss.msg.split('\n')[0]); });
  result.recommendations.forEach(function(r) { console.log('  → ' + r); });

  var fileHash = crypto.createHash('md5').update(content).digest('hex').substring(0,8);
  var runId    = new Date().toISOString().slice(0,10) + '_b1_' + fileHash;
  var date     = new Date().toISOString();

  var reportPath = path.join(RESULTS_DIR, runId + '.html');
  var html = generateHTML({
    step: 1, fileName, srcLang, tgtLang: null, runId, date,
    inputSRT: content, inputBlocks: parseSRT(content),
    gemini: null, deepseek: null, groq: result,
    history: loadHistory().runs.filter(function(r) { return r.file === fileName && r.step === 1; }).slice(0,10)
  });
  fs.writeFileSync(reportPath, html);

  var entry = {
    id: runId, date, step: 1, stepName: 'groq-analysis',
    file: fileName, fileHash, src: srcLang,
    groq: { score: result.score, issues: result.issues, stats: result.stats, recommendations: result.recommendations },
    gemini: null, deepseek: null, reportFile: path.basename(reportPath), userNote: '', edgeCase: false
  };
  addHistoryEntry(entry);
  console.log('\nRapport: ' + reportPath);
}

// ── STEP 2 : Traduction ────────────────────────────────────────────────────────
async function runStep2(filePath) {
  var fileName = path.basename(filePath);
  var srcLang  = SRC_LANG !== 'auto' ? SRC_LANG : detectLangFromName(fileName);
  var tgtLang  = OUT_LANG;
  if (!GEM_KEY && !DSK_KEY) { console.error('Step 2 nécessite --gem-key et/ou --dsk-key'); process.exit(1); }
  console.log('\n[STEP 2 — Traduction] ' + fileName);
  console.log(langName(srcLang) + ' → ' + langName(tgtLang));

  var content  = fs.readFileSync(filePath, 'utf8');
  var blocks   = parseSRT(content);
  var fileHash = crypto.createHash('md5').update(content).digest('hex').substring(0,8);
  var runId    = new Date().toISOString().slice(0,10) + '_b2_' + fileHash;
  var date     = new Date().toISOString();
  console.log('Blocs: ' + blocks.length);

  var promptFn = function() { return getTranslateTextPrompt(langName(srcLang), langName(tgtLang), tgtLang, srcLang); };
  var { gemResult, dskResult, gemOutput, dskOutput } = await runEnginePair(blocks, promptFn, 150, filePath, content, srcLang, tgtLang, runId, 2);

  var reportPath = path.join(RESULTS_DIR, runId + '.html');
  var html = generateHTML({
    step: 2, fileName, srcLang, tgtLang, runId, date,
    inputSRT: content, inputBlocks: blocks,
    gemini: gemResult ? { score: gemResult, output: gemOutput } : null,
    deepseek: dskResult ? { score: dskResult, output: dskOutput } : null,
    groq: null, history: loadHistory().runs.filter(function(r) { return r.file === fileName && r.step === 2; }).slice(0,10)
  });
  fs.writeFileSync(reportPath, html);

  addHistoryEntry({ id: runId, date, step: 2, stepName: 'translation', file: fileName, fileHash, src: srcLang, out: tgtLang, gemini: gemResult, deepseek: dskResult, reportFile: path.basename(reportPath), userNote: '', edgeCase: false });
  console.log('\nRapport: ' + reportPath);
}

// ── STEP 3 : CleanAI ──────────────────────────────────────────────────────────
async function runStep3(filePath) {
  var fileName = path.basename(filePath);
  var tgtLang  = OUT_LANG;
  if (!GEM_KEY && !DSK_KEY) { console.error('Step 3 nécessite --gem-key et/ou --dsk-key'); process.exit(1); }
  console.log('\n[STEP 3 — CleanAI] ' + fileName + ' (lang=' + tgtLang.toUpperCase() + ')');

  var content  = fs.readFileSync(filePath, 'utf8');
  var blocks   = parseSRT(content);
  var fileHash = crypto.createHash('md5').update(content).digest('hex').substring(0,8);
  var runId    = new Date().toISOString().slice(0,10) + '_b3_' + fileHash;
  var date     = new Date().toISOString();
  console.log('Blocs: ' + blocks.length);

  var promptFn = function() { return getCleanTextPrompt(tgtLang); };
  var { gemResult, dskResult, gemOutput, dskOutput } = await runEnginePair(blocks, promptFn, 200, filePath, content, tgtLang, tgtLang, runId, 3);

  var reportPath = path.join(RESULTS_DIR, runId + '.html');
  var html = generateHTML({
    step: 3, fileName, srcLang: tgtLang, tgtLang, runId, date,
    inputSRT: content, inputBlocks: blocks,
    gemini: gemResult ? { score: gemResult, output: gemOutput } : null,
    deepseek: dskResult ? { score: dskResult, output: dskOutput } : null,
    groq: null, history: loadHistory().runs.filter(function(r) { return r.file === fileName && r.step === 3; }).slice(0,10)
  });
  fs.writeFileSync(reportPath, html);

  addHistoryEntry({ id: runId, date, step: 3, stepName: 'cleanai', file: fileName, fileHash, src: tgtLang, out: tgtLang, gemini: gemResult, deepseek: dskResult, reportFile: path.basename(reportPath), userNote: '', edgeCase: false });
  console.log('\nRapport: ' + reportPath);
}

// ── STEP 4 : TRAD hybride ─────────────────────────────────────────────────────
async function runStep4(filePath) {
  var fileName = path.basename(filePath);
  var srcLang  = SRC_LANG !== 'auto' ? SRC_LANG : detectLangFromName(fileName);
  var tgtLang  = OUT_LANG;
  if (!GEM_KEY && !DSK_KEY) { console.error('Step 4 nécessite --gem-key et/ou --dsk-key'); process.exit(1); }
  console.log('\n[STEP 4 — TRAD Hybride] ' + fileName);
  console.log(langName(srcLang) + ' mélangé → ' + langName(tgtLang));

  var content  = fs.readFileSync(filePath, 'utf8');
  var blocks   = parseSRT(content);
  var fileHash = crypto.createHash('md5').update(content).digest('hex').substring(0,8);
  var runId    = new Date().toISOString().slice(0,10) + '_b4_' + fileHash;
  var date     = new Date().toISOString();
  console.log('Blocs: ' + blocks.length);

  var promptFn = function() { return getTranslateTextPrompt(langName(srcLang), langName(tgtLang), tgtLang, srcLang); };
  var { gemResult, dskResult, gemOutput, dskOutput } = await runEnginePair(blocks, promptFn, 150, filePath, content, srcLang, tgtLang, runId, 4);

  var reportPath = path.join(RESULTS_DIR, runId + '.html');
  var html = generateHTML({
    step: 4, fileName, srcLang, tgtLang, runId, date,
    inputSRT: content, inputBlocks: blocks,
    gemini: gemResult ? { score: gemResult, output: gemOutput } : null,
    deepseek: dskResult ? { score: dskResult, output: dskOutput } : null,
    groq: null, history: loadHistory().runs.filter(function(r) { return r.file === fileName && r.step === 4; }).slice(0,10)
  });
  fs.writeFileSync(reportPath, html);

  addHistoryEntry({ id: runId, date, step: 4, stepName: 'trad-hybrid', file: fileName, fileHash, src: srcLang, out: tgtLang, gemini: gemResult, deepseek: dskResult, reportFile: path.basename(reportPath), userNote: '', edgeCase: false });
  console.log('\nRapport: ' + reportPath);
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  if (SHOW_HIST) { showHistory(STEP || null, FILE_ARG); return; }

  if (!STEP || STEP < 1 || STEP > 4) {
    console.log('SubWhisper Batch Lab v1.0');
    console.log('');
    console.log('Usage: node batch.js --step N --file PATH [options]');
    console.log('       node batch.js --history [--step N] [--file NAME]');
    console.log('');
    console.log('Steps:');
    console.log('  1  Groq Analysis  — scoreBrut, aucun appel IA (pas de clé requise)');
    console.log('  2  Traduction     — src→out, Gemini + DeepSeek');
    console.log('  3  CleanAI        — nettoyage SRT, Gemini + DeepSeek');
    console.log('  4  TRAD Hybride   — mélange langues→out, Gemini + DeepSeek');
    console.log('');
    console.log('Options:');
    console.log('  --file PATH    Fichier SRT (absolu, ou relatif à cwd, ou dans test-files/)');
    console.log('  --src LANG     Langue source: zh ja ko en fr es...');
    console.log('  --out LANG     Langue cible (défaut: fr)');
    console.log('  --gem-key KEY  Clé API Gemini');
    console.log('  --dsk-key KEY  Clé API DeepSeek');
    return;
  }

  if (!FILE_ARG) { console.error('--file requis'); process.exit(1); }

  // Résoudre le chemin
  var filePath = path.isAbsolute(FILE_ARG) ? FILE_ARG : path.resolve(process.cwd(), FILE_ARG);
  if (!fs.existsSync(filePath)) {
    var altPath = path.join(BENCH_DIR, 'test-files', path.basename(FILE_ARG));
    if (fs.existsSync(altPath)) { filePath = altPath; }
    else { console.error('Fichier introuvable: ' + FILE_ARG); process.exit(1); }
  }

  console.log('SubWhisper Batch Lab v1.0 — Step ' + STEP);
  console.log('='.repeat(60));

  switch(STEP) {
    case 1: await runStep1(filePath); break;
    case 2: await runStep2(filePath); break;
    case 3: await runStep3(filePath); break;
    case 4: await runStep4(filePath); break;
  }
}

main().catch(function(e) { console.error('\nFatal:', e.message); if (process.env.DEBUG) console.error(e.stack); process.exit(1); });
