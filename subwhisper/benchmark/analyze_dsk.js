/**
 * Analyse comparée Gemini vs DeepSeek — run ZH zzz
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { scoreBrut, scoreTranslation, score } = require('./score.js');

const DIR = 'D:/Download/10-brut sub/srt source ZH/Deepseek';
const GEMDIR = 'D:/Download/10-brut sub/srt source ZH'; // Gemini files (previous run)

const dskRaw  = path.join(DIR, 'zzz_ZH.RAW_GROQ.srt');
const dskBrut = path.join(DIR, 'zzz_ZH.srt BRUT');
const dskIA   = path.join(DIR, 'zzz_ZH.srt IA');
const dskTrad = path.join(DIR, 'zzz_ZH.srt TRAD');

// Gemini files from last session (in parent dir)
const gemFiles = fs.readdirSync(GEMDIR).filter(f => f !== 'Deepseek' && !f.includes('.'));

function parseSRT(srt) {
  return srt.split(/\n\n+/).filter(b => {
    var lines = b.trim().split('\n');
    return lines.length >= 3 && /^\d+$/.test(lines[0].trim()) && lines[1].includes('-->');
  }).map(b => {
    var lines = b.trim().split('\n');
    return { id: lines[0].trim(), timestamp: lines[1].trim(), text: lines.slice(2).join('\n') };
  });
}

function countBlocks(srt) { return parseSRT(srt).length; }

function countCJK(srt) {
  var blocks = parseSRT(srt);
  return blocks.filter(b => /[\u3040-\u9fff\uac00-\ud7af]/.test(b.text)).length;
}

function countLatin(srt) {
  var blocks = parseSRT(srt);
  var EN_HINT = /\b(the|this|that|when|what|with|you|your|and|for|are|was|not|can|will|have|been|they|from|is|it|do|let|come|look|feel|like|want|so|go|I'm|don't|can't)\b/i;
  return blocks.filter(b => EN_HINT.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text)).length;
}

function countFR(srt) {
  var blocks = parseSRT(srt);
  var FR_HINT = /\b(le|la|les|un|une|des|je|tu|il|elle|nous|vous|que|qui|dans|avec|pour|sur|et|est|pas|mais|ou|ce|ne|en|du|au|ça|c'est|j'ai|n'est)\b/i;
  return blocks.filter(b => FR_HINT.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text)).length;
}

function countHalluc(srt) {
  var blocks = parseSRT(srt);
  var cnt = 0;
  blocks.forEach(function(b) {
    var ws = b.text.split(/\s+/);
    for (var i = 0; i < ws.length - 2; i++) {
      if (ws[i] && ws[i] === ws[i+1] && ws[i+1] === ws[i+2] && ws[i].length <= 5) { cnt++; break; }
    }
    if (/([啊哦嗯唉哎喔哟哈呀噫]{1})\1{2,}/.test(b.text)) cnt++;
    var CJK = /[\u3040-\u9fff\uac00-\ud7af]/;
    if (CJK.test(b.text) && b.text.trim().length <= 3) cnt++;
  });
  return cnt;
}

// Diff blocks between two SRTs
function diffCount(srt1, srt2) {
  var b1 = parseSRT(srt1);
  var b2 = parseSRT(srt2);
  var changed = 0;
  var n = Math.min(b1.length, b2.length);
  for (var i = 0; i < n; i++) {
    if (b1[i].text !== b2[i].text) changed++;
  }
  return { changed, total: n };
}

var raw  = fs.readFileSync(dskRaw,  'utf8');
var brut = fs.readFileSync(dskBrut, 'utf8');
var ia   = fs.readFileSync(dskIA,   'utf8');
var trad = fs.readFileSync(dskTrad, 'utf8');

console.log('\n====================================================');
console.log('   ANALYSE — DeepSeek all-in (ZH zzz)');
console.log('====================================================');

console.log('\n--- Block counts ---');
console.log('RAW_GROQ :', countBlocks(raw), 'blocs');
console.log('BRUT     :', countBlocks(brut), 'blocs');
console.log('IA       :', countBlocks(ia), 'blocs');
console.log('TRAD     :', countBlocks(trad), 'blocs');

console.log('\n--- RAW_GROQ : hallucinations phonétiques ---');
console.log('Hallucinations  :', countHalluc(raw));

console.log('\n--- BRUT (ZH→FR traduction directe) ---');
var bBrut = parseSRT(brut);
var brutCJK = countCJK(brut);
var brutFR  = countFR(brut);
var brutEN  = countLatin(brut) - brutFR;
console.log('Total blocs  :', bBrut.length);
console.log('CJK résiduel :', brutCJK, '(' + Math.round(brutCJK/bBrut.length*100) + '%)');
console.log('FR détectés  :', brutFR,  '(' + Math.round(brutFR/bBrut.length*100) + '%)');
console.log('EN résiduel  :', Math.max(0, brutEN), '(approx)');

// Score traduction BRUT
try {
  var sbBrut = scoreTranslation(raw, brut, 'zh', 'fr');
  console.log('scoreTranslation RAW→BRUT :', JSON.stringify(sbBrut));
} catch(e) { console.log('scoreTranslation err:', e.message); }

console.log('\n--- IA (cleanAI sur BRUT) ---');
var diffIA = diffCount(brut, ia);
console.log('Blocs modifiés par cleanAI :', diffIA.changed, '/', diffIA.total);
var iaCJK = countCJK(ia);
var iaFR  = countFR(ia);
console.log('CJK résiduel :', iaCJK);
console.log('FR détectés  :', iaFR);

// Score cleanAI
try {
  var sIA = score(dskBrut, ia, 'fr');
  console.log('score(BRUT→IA) :', JSON.stringify(sIA));
} catch(e) { console.log('score err:', e.message); }

console.log('\n--- TRAD (TRAD hybride sur IA) ---');
var diffTrad = diffCount(ia, trad);
console.log('Blocs modifiés par TRAD :', diffTrad.changed, '/', diffTrad.total);
var tradCJK = countCJK(trad);
var tradFR  = countFR(trad);
var tradEN  = countLatin(trad);
console.log('CJK résiduel :', tradCJK, '(' + Math.round(tradCJK/parseSRT(trad).length*100) + '%)');
console.log('FR détectés  :', tradFR);
console.log('Latin total  :', tradEN);

// Score traduction TRAD (brut→trad)
try {
  var sTrad = scoreTranslation(raw, trad, 'zh', 'fr');
  console.log('scoreTranslation RAW→TRAD :', JSON.stringify(sTrad));
} catch(e) { console.log('scoreTranslation err:', e.message); }

console.log('\n--- SAMPLES : blocs encore CJK après TRAD ---');
var tBlocks = parseSRT(trad);
var cjkBlocks = tBlocks.filter(b => /[\u3040-\u9fff\uac00-\ud7af]/.test(b.text));
cjkBlocks.slice(0, 8).forEach(b => console.log('[' + b.id + '] ' + b.text));

console.log('\n--- SAMPLES : blocs EN résiduel après TRAD ---');
var EN_HINT = /\b(the|this|that|when|what|with|you|your|and|for|are|was|not|can|will|have|been|they|from|is|it|do|let|come|look|feel|like|want|so|go|I'm|don't|can't)\b/i;
var enBlocks = tBlocks.filter(b => EN_HINT.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text));
enBlocks.slice(0, 8).forEach(b => console.log('[' + b.id + '] ' + b.text));

console.log('\n====================================================');
console.log('SYNTHÈSE comparée (Gemini session précédente)');
console.log('Gemini BRUT : 613 blocs, ~185 halluc RAW, 48 CJK résiduel après TRAD');
console.log('DeepSeek   : voir chiffres ci-dessus');
console.log('====================================================\n');
