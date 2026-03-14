/**
 * Analyse Gemini — run JP yyy
 */
'use strict';
const fs = require('fs');
const path = require('path');

const DIR = 'D:/Download/10-brut sub/srt source JP/Gemini';

const jpRaw  = path.join(DIR, 'yyy_JP.RAW_GROQ.srt');
const jpBrut = path.join(DIR, 'yyy_JP.srt BRUT');
const jpIA   = path.join(DIR, 'yyy_JP.srt IA.srt');
const jpTrad = path.join(DIR, 'yyy_JP.srt TRAD.srt');

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
  return parseSRT(srt).filter(b => /[\u3040-\u9fff]/.test(b.text)).length;
}
function countHangul(srt) {
  return parseSRT(srt).filter(b => /[\uac00-\ud7af]/.test(b.text)).length;
}
function countFR(srt) {
  var FR = /\b(le|la|les|un|une|des|je|tu|il|elle|nous|vous|que|qui|dans|avec|pour|sur|et|est|pas|mais|ou|ce|ne|en|du|au|ça|c'est|j'ai|n'est)\b/i;
  return parseSRT(srt).filter(b => FR.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text)).length;
}
function countEN(srt) {
  var EN = /\b(the|this|that|when|what|with|you|your|and|for|are|was|not|can|will|have|been|they|from|is|it|do|let|come|look|feel|like|want|so|go|I'm|don't|can't)\b/i;
  var FR = /\b(le|la|les|un|une|des|je|tu|il|elle|nous|vous|que|qui|dans|avec|pour|sur|et|est|pas|mais)\b/i;
  return parseSRT(srt).filter(b => EN.test(b.text) && !FR.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text)).length;
}

function countHalluc(srt) {
  var blocks = parseSRT(srt);
  var cnt = 0;
  blocks.forEach(function(b) {
    var ws = b.text.split(/\s+/);
    for (var i = 0; i < ws.length - 2; i++) {
      if (ws[i] && ws[i] === ws[i+1] && ws[i+1] === ws[i+2] && ws[i].length <= 5) { cnt++; break; }
    }
    if (/([啊哦嗯唉哎喔哟哈呀]{1})\1{2,}/.test(b.text)) cnt++;
    if (/[\uac00-\ud7af]{2,}.*[\uac00-\ud7af]{2,}/.test(b.text) && !/[\u3040-\u9fff]/.test(b.text)) cnt++;
  });
  return cnt;
}

function countNPrefixBug(srt) {
  // Blocs dont le texte commence par [N] (préfixe IA non strippé)
  return parseSRT(srt).filter(b => /^\[\d+\]/.test(b.text.trim())).length;
}

function countEllipsisInvalid(srt) {
  // [...] couvrant tout un bloc (censure invalide)
  return parseSRT(srt).filter(b => /^\[\.{3}\]$/.test(b.text.trim()) || /^\[\.\.\.\]$/.test(b.text.trim())).length;
}

function countTimestampInText(srt) {
  return parseSRT(srt).filter(b => /\d{2}:\d{2}:\d{2}[,.]/.test(b.text)).length;
}

function diffCount(srt1, srt2) {
  var b1 = parseSRT(srt1), b2 = parseSRT(srt2);
  var changed = 0, n = Math.min(b1.length, b2.length);
  for (var i = 0; i < n; i++) { if (b1[i].text !== b2[i].text) changed++; }
  return { changed, total: n };
}

// Samples helper
function sampleBlocks(blocks, filterFn, n) {
  return blocks.filter(filterFn).slice(0, n)
    .map(b => '  [' + b.id + '] ' + b.text.replace(/\n/g, ' / ').substring(0, 80))
    .join('\n');
}

var raw  = fs.readFileSync(jpRaw,  'utf8');
var brut = fs.readFileSync(jpBrut, 'utf8');
var ia   = fs.readFileSync(jpIA,   'utf8');
var trad = fs.readFileSync(jpTrad, 'utf8');

console.log('\n====================================================');
console.log('   ANALYSE — Gemini all-in (JP yyy)');
console.log('====================================================');

console.log('\n--- Block counts ---');
console.log('RAW_GROQ :', countBlocks(raw),  'blocs');
console.log('BRUT     :', countBlocks(brut), 'blocs');
console.log('IA       :', countBlocks(ia),   'blocs');
console.log('TRAD     :', countBlocks(trad), 'blocs');

console.log('\n--- RAW_GROQ : contenu ---');
var rawBlocks = parseSRT(raw);
console.log('CJK (JP hiragana/kanji) :', countCJK(raw));
console.log('Hangul (KO — halluc)    :', countHangul(raw));
console.log('Hallucinations répétées :', countHalluc(raw));

console.log('\n  Samples Hangul (Groq KO hallucinations) :');
console.log(sampleBlocks(rawBlocks, b => /[\uac00-\ud7af]/.test(b.text), 5));

console.log('\n--- BRUT (JP→FR traduction directe) ---');
var bBrut = parseSRT(brut);
console.log('Total blocs  :', bBrut.length);
console.log('CJK résiduel :', countCJK(brut));
console.log('Hangul résid :', countHangul(brut));
console.log('FR détectés  :', countFR(brut));
console.log('EN résiduel  :', countEN(brut));
console.log('[N] prefix bug:', countNPrefixBug(brut));
console.log('[...] invalides:', countEllipsisInvalid(brut));
console.log('Timestamp dans texte:', countTimestampInText(brut));

console.log('\n  Samples CJK résiduel BRUT :');
console.log(sampleBlocks(bBrut, b => /[\u3040-\u9fff]/.test(b.text), 5));

console.log('\n--- IA (cleanAI Gemini sur BRUT) ---');
var bIA = parseSRT(ia);
var diffIA = diffCount(brut, ia);
console.log('Blocs modifiés par cleanAI :', diffIA.changed, '/', diffIA.total);
console.log('CJK résiduel :', countCJK(ia));
console.log('Hangul résid :', countHangul(ia));
console.log('FR détectés  :', countFR(ia));
console.log('[N] prefix bug:', countNPrefixBug(ia));
console.log('[...] invalides:', countEllipsisInvalid(ia));
console.log('Timestamp dans texte:', countTimestampInText(ia));

console.log('\n--- TRAD (translateManual Gemini sur IA) ---');
var bTrad = parseSRT(trad);
var diffTrad = diffCount(ia, trad);
console.log('Blocs modifiés par TRAD :', diffTrad.changed, '/', diffTrad.total);
console.log('CJK résiduel :', countCJK(trad), '(' + Math.round(countCJK(trad)/bTrad.length*100) + '%)');
console.log('Hangul résid :', countHangul(trad), '(' + Math.round(countHangul(trad)/bTrad.length*100) + '%)');
console.log('FR détectés  :', countFR(trad));
console.log('EN résiduel  :', countEN(trad));
console.log('[N] prefix bug:', countNPrefixBug(trad));
console.log('[...] invalides:', countEllipsisInvalid(trad));
console.log('Timestamp dans texte:', countTimestampInText(trad));

console.log('\n  Samples [N] prefix bug dans TRAD :');
console.log(sampleBlocks(bTrad, b => /^\[\d+\]/.test(b.text.trim()), 8));

console.log('\n  Samples CJK résiduel après TRAD :');
console.log(sampleBlocks(bTrad, b => /[\u3040-\u9fff]/.test(b.text), 8));

console.log('\n  Samples Hangul résiduel après TRAD :');
console.log(sampleBlocks(bTrad, b => /[\uac00-\ud7af]/.test(b.text), 8));

console.log('\n  Samples EN résiduel après TRAD :');
var EN_HINT = /\b(the|this|that|when|what|with|you|your|and|for|are|was|not|can|will|have|been|they|from|is|it|do|let|come|look|feel|like|want|so|go|I'm|don't|can't)\b/i;
var FR_HINT = /\b(le|la|les|un|une|des|je|tu|il|elle|nous|vous|que|qui|dans|avec|pour|sur|et|est|pas|mais)\b/i;
console.log(sampleBlocks(bTrad, b => EN_HINT.test(b.text) && !FR_HINT.test(b.text) && !/[\u3040-\u9fff\uac00-\ud7af]/.test(b.text), 8));

console.log('\n====================================================');
console.log('SYNTHÈSE');
var nPfx = countNPrefixBug(trad);
console.log('[N] prefix bug TRAD  : ' + nPfx + ' blocs → FIX v8.68 appliqué');
console.log('CJK résiduel TRAD    : ' + countCJK(trad) + ' (' + Math.round(countCJK(trad)/bTrad.length*100) + '%)');
console.log('Hangul résiduel TRAD : ' + countHangul(trad) + ' (' + Math.round(countHangul(trad)/bTrad.length*100) + '%)');
console.log('FR détectés TRAD     : ' + countFR(trad));
console.log('EN résiduel TRAD     : ' + countEN(trad));
console.log('====================================================\n');
