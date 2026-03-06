var {parseSRT} = require('./score');
var fs = require('fs');
var brut = parseSRT(fs.readFileSync('D:/Download/10-brut sub/20260304.ZH_BRUT.srt','utf8'));
var gem  = parseSRT(fs.readFileSync('results/2026-03-06_b4_9f24c49a_gemini.srt','utf8'));
var dsk  = parseSRT(fs.readFileSync('results/2026-03-06_b4_9f24c49a_deepseek.srt','utf8'));

var EN_WORDS = /\b(the|this|that|when|what|with|you|your|and|for|are|was|not|can|will|have|been|they|from)\b/i;
var enBlocs=0, enRemGem=0, enRemDsk=0;

brut.forEach(function(b, i) {
  if (!b) return;
  var isEn = EN_WORDS.test(b.text);
  if (!isEn) return;
  enBlocs++;
  var g = gem[i], d = dsk[i];
  if (g && EN_WORDS.test(g.text)) enRemGem++;
  if (d && EN_WORDS.test(d.text)) enRemDsk++;
});

console.log('Blocs anglais dans BRUT  :', enBlocs);
console.log('Anglais restant — Gemini :', enRemGem, '(' + Math.round(enRemGem/enBlocs*100) + '%)');
console.log('Anglais restant — DeepSeek:', enRemDsk, '(' + Math.round(enRemDsk/enBlocs*100) + '%)');

console.log('\n=== Échantillon blocs 148-170 ===');
for (var i = 148; i < 170; i++) {
  var b = brut[i], g = gem[i], d = dsk[i];
  if (!b) continue;
  var brutChanged = (g && g.text !== b.text) || (d && d.text !== b.text);
  var isEn = EN_WORDS.test(b.text);
  if (brutChanged || isEn) {
    console.log('#' + (i+1) + ' BRUT: ' + b.text.substring(0,70));
    if (g && g.text !== b.text) console.log('      GEM : ' + g.text.substring(0,70));
    if (d && d.text !== b.text) console.log('      DSK : ' + d.text.substring(0,70));
  }
}
