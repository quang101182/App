'use strict';
const fs = require('fs');

const DSK_DIR = 'D:/Download/10-brut sub/srt source JP/Auto/Deepseek';
const GEM_DIR = 'D:/Download/10-brut sub/srt source JP/Auto/Gemini';

var dsk = {
  raw:  fs.readFileSync(DSK_DIR + '/yyy_JP.RAW_GROQ.srt',  'utf8'),
  brut: fs.readFileSync(DSK_DIR + '/yyy_JP.srt BRUT',       'utf8'),
  ia:   fs.readFileSync(DSK_DIR + '/yyy_JP.srt IA.srt',     'utf8'),
  trad: fs.readFileSync(DSK_DIR + '/yyy_JP.srt TRAD.srt',   'utf8'),
};
var gem = {
  raw:  fs.readFileSync(GEM_DIR + '/yyy_JP.RAW_GROQ.srt',  'utf8'),
  brut: fs.readFileSync(GEM_DIR + '/yyy_JP.srt BRUT',       'utf8'),
  ia:   fs.readFileSync(GEM_DIR + '/yyy_JP.srt IA.srt',     'utf8'),
  trad: fs.readFileSync(GEM_DIR + '/yyy_JP.srt TRAD.srt',   'utf8'),
};

function parseSRT(srt) {
  return srt.split(/\n\n+/).filter(function(b) {
    var l = b.trim().split('\n');
    return l.length >= 3 && /^\d+$/.test(l[0].trim()) && l[1].includes('-->');
  }).map(function(b) {
    var l = b.trim().split('\n');
    return { id: l[0].trim(), timestamp: l[1].trim(), text: l.slice(2).join('\n') };
  });
}

var NonLatin = /[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0400-\u04ff]/;
var FR_RX = /\b(le|la|les|un|une|des|je|tu|il|elle|nous|vous|que|qui|dans|avec|pour|sur|et|est|pas|mais|ou|ce|ne|en|du|au)\b/i;
var EN_RX = /\b(the|this|that|when|what|with|you|your|and|for|are|was|not|can|will|have|been|they|from|is|it|do|let|come|look)\b/i;

function cnt(s)     { return parseSRT(s).length; }
function cjk(s)     { return parseSRT(s).filter(function(x){ return /[\u3040-\u9fff]/.test(x.text); }).length; }
function hangul(s)  { return parseSRT(s).filter(function(x){ return /[\uac00-\ud7af]/.test(x.text); }).length; }
function frFn(s)    { return parseSRT(s).filter(function(x){ return FR_RX.test(x.text) && !NonLatin.test(x.text); }).length; }
function enFn(s)    { return parseSRT(s).filter(function(x){ return EN_RX.test(x.text) && !FR_RX.test(x.text) && !NonLatin.test(x.text); }).length; }
function nprefix(s) { return parseSRT(s).filter(function(x){ return /^\[\d+\]/.test(x.text.trim()); }).length; }
function ellips(s)  { return parseSRT(s).filter(function(x){ return /^\[\.{3}\]$|^\[\.\.\.\]$/.test(x.text.trim()); }).length; }
function diffCnt(a, b) {
  var b1 = parseSRT(a), b2 = parseSRT(b), c = 0, n = Math.min(b1.length, b2.length);
  for (var i = 0; i < n; i++) if (b1[i].text !== b2[i].text) c++;
  return { changed: c, total: n };
}
function sample(s, fn, n) {
  return parseSRT(s).filter(fn).slice(0, n)
    .map(function(x){ return '  [' + x.id + '] ' + x.text.replace(/\n/g, ' / ').substring(0, 75); })
    .join('\n');
}

console.log('\n====================================================');
console.log('  ANALYSE COMPAREE -- JP yyy  (DeepSeek vs Gemini)');
console.log('====================================================');

console.log('\n--- Block counts ---');
console.log('           DSK    GEM');
console.log('RAW_GROQ : ' + cnt(dsk.raw)  + '   ' + cnt(gem.raw));
console.log('BRUT     : ' + cnt(dsk.brut) + '   ' + cnt(gem.brut));
console.log('IA       : ' + cnt(dsk.ia)   + '   ' + cnt(gem.ia));
console.log('TRAD     : ' + cnt(dsk.trad) + '   ' + cnt(gem.trad));

console.log('\n--- RAW_GROQ ---');
console.log('CJK (JP) : DSK ' + cjk(dsk.raw) + ' / GEM ' + cjk(gem.raw));
console.log('Hangul   : DSK ' + hangul(dsk.raw) + ' / GEM ' + hangul(gem.raw));

console.log('\n--- BRUT (JP->FR) ---');
console.log('CJK residuel : DSK ' + cjk(dsk.brut) + ' / GEM ' + cjk(gem.brut));
console.log('Hangul resid : DSK ' + hangul(dsk.brut) + ' / GEM ' + hangul(gem.brut));
console.log('FR detectes  : DSK ' + frFn(dsk.brut) + ' / GEM ' + frFn(gem.brut));
console.log('[N] prefix   : DSK ' + nprefix(dsk.brut) + ' / GEM ' + nprefix(gem.brut));
console.log('[...] inv    : DSK ' + ellips(dsk.brut) + ' / GEM ' + ellips(gem.brut));

console.log('\n  Samples CJK residuel BRUT DeepSeek :');
console.log(sample(dsk.brut, function(x){ return /[\u3040-\u9fff]/.test(x.text); }, 5));
console.log('\n  Samples Hangul residuel BRUT DeepSeek :');
console.log(sample(dsk.brut, function(x){ return /[\uac00-\ud7af]/.test(x.text); }, 5));

console.log('\n--- IA (cleanAI) ---');
var dIA = diffCnt(dsk.brut, dsk.ia), gIA = diffCnt(gem.brut, gem.ia);
console.log('Blocs modifies : DSK ' + dIA.changed + '/' + dIA.total + ' / GEM ' + gIA.changed + '/' + gIA.total);
console.log('CJK residuel   : DSK ' + cjk(dsk.ia) + ' / GEM ' + cjk(gem.ia));
console.log('Hangul resid   : DSK ' + hangul(dsk.ia) + ' / GEM ' + hangul(gem.ia));
console.log('[...] inv      : DSK ' + ellips(dsk.ia) + ' / GEM ' + ellips(gem.ia));
console.log('[N] prefix     : DSK ' + nprefix(dsk.ia) + ' / GEM ' + nprefix(gem.ia));

console.log('\n  Samples [...] invalides DSK IA :');
console.log(sample(dsk.ia, function(x){ return /\[\.{3}\]|\[\.\.\.\]/.test(x.text); }, 6));

console.log('\n--- TRAD ---');
var dT = diffCnt(dsk.ia, dsk.trad), gT = diffCnt(gem.ia, gem.trad);
var total = cnt(dsk.trad);
var gTotal = cnt(gem.trad);
console.log('Blocs modifies : DSK ' + dT.changed + '/' + dT.total + ' / GEM ' + gT.changed + '/' + gT.total);
console.log('CJK residuel   : DSK ' + cjk(dsk.trad) + ' (' + Math.round(cjk(dsk.trad)/total*100) + '%) / GEM ' + cjk(gem.trad) + ' (' + Math.round(cjk(gem.trad)/gTotal*100) + '%)');
console.log('Hangul resid   : DSK ' + hangul(dsk.trad) + ' (' + Math.round(hangul(dsk.trad)/total*100) + '%) / GEM ' + hangul(gem.trad) + ' (' + Math.round(hangul(gem.trad)/gTotal*100) + '%)');
console.log('FR detectes    : DSK ' + frFn(dsk.trad) + ' / GEM ' + frFn(gem.trad));
console.log('EN residuel    : DSK ' + enFn(dsk.trad) + ' / GEM ' + enFn(gem.trad));
console.log('[N] prefix     : DSK ' + nprefix(dsk.trad) + ' / GEM ' + nprefix(gem.trad));
console.log('[...] inv      : DSK ' + ellips(dsk.trad) + ' / GEM ' + ellips(gem.trad));

console.log('\n  Samples [N] prefix DSK TRAD :');
console.log(sample(dsk.trad, function(x){ return /^\[\d+\]/.test(x.text.trim()); }, 6));
console.log('\n  Samples CJK residuel DSK TRAD :');
console.log(sample(dsk.trad, function(x){ return /[\u3040-\u9fff]/.test(x.text); }, 6));
console.log('\n  Samples Hangul residuel DSK TRAD :');
console.log(sample(dsk.trad, function(x){ return /[\uac00-\ud7af]/.test(x.text); }, 6));
console.log('\n  Samples [...] invalides DSK TRAD :');
console.log(sample(dsk.trad, function(x){ return /\[\.{3}\]|\[\.\.\.\]/.test(x.text); }, 6));

var dResid = cjk(dsk.trad) + hangul(dsk.trad);
var gResid = cjk(gem.trad) + hangul(gem.trad);

console.log('\n====================================================');
console.log('SYNTHESE COMPAREE JP yyy');
console.log('');
console.log('              DeepSeek    Gemini');
console.log('cleanAI mod : ' + dIA.changed + '           ' + gIA.changed);
console.log('TRAD modifs : ' + dT.changed + '         ' + gT.changed);
console.log('CJK final   : ' + cjk(dsk.trad) + ' (' + Math.round(cjk(dsk.trad)/total*100) + '%)      ' + cjk(gem.trad) + ' (' + Math.round(cjk(gem.trad)/gTotal*100) + '%)');
console.log('Hangul fin  : ' + hangul(dsk.trad) + ' (' + Math.round(hangul(dsk.trad)/total*100) + '%)      ' + hangul(gem.trad) + ' (' + Math.round(hangul(gem.trad)/gTotal*100) + '%)');
console.log('Residuel S  : ' + dResid + ' (' + Math.round(dResid/total*100) + '%)      ' + gResid + ' (' + Math.round(gResid/gTotal*100) + '%)');
console.log('FR detectes : ' + frFn(dsk.trad) + '         ' + frFn(gem.trad));
console.log('[N] prefix  : ' + nprefix(dsk.trad) + '            ' + nprefix(gem.trad));
console.log('[...] inv   : ' + ellips(dsk.trad) + '            ' + ellips(gem.trad));
console.log('');
var winner = dResid < gResid ? 'DeepSeek (' + dResid + ' vs ' + gResid + ')' : dResid > gResid ? 'Gemini (' + gResid + ' vs ' + dResid + ')' : 'Egalite (' + dResid + ')';
console.log('Vainqueur TRAD JP : ' + winner);
console.log('====================================================');
