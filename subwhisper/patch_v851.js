/**
 * Patch index.html v8.50 → v8.51
 * translateManual() — mode sélectif FR :
 * quand SORTIE = fr, traduit uniquement les blocs non-français → français
 * (approche texte numéroté [N], block count garanti)
 * Mode classique conservé pour toute autre langue cible
 */
var fs = require('fs');
var content = fs.readFileSync(__dirname + '/index.html', 'utf8');
var crlf = content.includes('\r\n');
var c = content.replace(/\r\n/g, '\n');

// Trouver les bornes de translateManual()
var startMarker = 'async function translateManual() {\n';
var startIdx = c.indexOf(startMarker);
if (startIdx === -1) { console.error('translateManual start not found'); process.exit(1); }

var pos = startIdx + startMarker.length;
var depth = 1;
while (pos < c.length && depth > 0) {
  if (c[pos] === '{') depth++;
  else if (c[pos] === '}') depth--;
  pos++;
}
console.log('translateManual found, ends at pos', pos, '— depth check:', depth);
if (depth !== 0) { console.error('Brace mismatch!'); process.exit(1); }

var newFn = `async function translateManual() {
  var raw = getCurrentSRT();
  if (!raw || !raw.trim()) { toast('Aucun SRT à traduire'); return; }
  var src = detectedLang || document.getElementById('srcLangMain').value || '';
  var tgt = document.getElementById('outLangMain').value;
  if (!tgt || tgt === 'same') { toast('⚠ Sélectionne une langue SORTIE dans la barre'); return; }
  // Mode sélectif FR autorise src===fr (patch des blocs non-fr restants)
  if (tgt !== 'fr' && src && src === tgt) { toast('⚠ SOURCE et SORTIE sont identiques'); return; }
  var hasKey = getGeminiKey() || getDeepSeekKey() || getAzureKey() || getDeeplxUrl();
  if (!hasKey) { toast('⚠ Clé IA requise (Gemini, DeepSeek ou Azure)'); return; }
  var btn = document.getElementById('translateBtn');
  var btnOrig = btn ? btn.innerHTML : '';
  if (btn) btn.disabled = true;
  var engine = getAIEngine() === 'deepseek' ? 'DeepSeek' : 'Gemini';
  try {
    var translated, nbBlocks = 0;
    if (tgt === 'fr') {
      // Mode sélectif : l'IA détecte et traduit uniquement les blocs non-français
      var blocks = parseSRT(raw);
      nbBlocks = blocks.length;
      var correctedTexts = blocks.map(function(b) { return b.text; });
      var BATCH = 200;
      var totalBatches = Math.ceil(blocks.length / BATCH);
      for (var b = 0; b < totalBatches; b++) {
        var batchBlocks = blocks.slice(b * BATCH, (b+1) * BATCH);
        var batchOffset = b * BATCH;
        var bLabel = totalBatches > 1
          ? '🌐 Patch FR ' + engine + ' ' + (b+1) + '/' + totalBatches + '...'
          : '🌐 Patch FR ' + engine + '...';
        toastPersist(bLabel);
        if (btn) btn.innerHTML = totalBatches > 1 ? '🌐 ' + (b+1) + '/' + totalBatches : '🌐 ...';
        var promptLines = batchBlocks.map(function(blk, j) {
          return '[' + (batchOffset + j + 1) + '] ' + blk.text.replace(/\\n/g, ' | ');
        });
        var prompt = 'You are a professional subtitle translator. Target language: French.\\n' +
          'Each line is [N] subtitle_text.\\n' +
          '1. If the text is ALREADY in French: return it UNCHANGED as [N] text.\\n' +
          '2. If the text is in ANY OTHER language: translate it to French as [N] French_text.\\n' +
          '3. NEVER skip a number. Return ALL lines.\\n' +
          '4. PROPER NOUNS: Keep character names, place names in their original form.\\n' +
          '5. TRUNCATED: Lines ending without punctuation are intentionally cut — never add words.\\n' +
          '6. FRENCH TYPOGRAPHY: Add mandatory space before ? ! : ; if missing.\\n' +
          'Return ONLY the numbered lines [N] text. No SRT structure, no timestamps, no explanation.\\n\\n' +
          promptLines.join('\\n');
        try {
          var aiText = await callAIText(prompt);
          var lineRx = /^\\[(\\d+)\\]\\s*(.*)/gm;
          var m;
          while ((m = lineRx.exec(aiText)) !== null) {
            var idx = parseInt(m[1]) - 1;
            if (idx >= 0 && idx < blocks.length) {
              var corrected = m[2].replace(/ \\| /g, '\\n').trim();
              if (corrected) correctedTexts[idx] = corrected;
            }
          }
        } catch(e2) {
          console.warn('Batch ' + b + ' erreur:', e2.message);
        }
        if (b < totalBatches - 1) await new Promise(function(r) { setTimeout(r, 500); });
      }
      translated = blocks.map(function(blk, i) {
        return blk.id + '\\n' + blk.timestamp + '\\n' + correctedTexts[i];
      }).join('\\n\\n') + '\\n';
    } else {
      // Mode classique : traduction complète vers la langue cible
      toastPersist('🌐 Traduction ' + engine + ' en cours...');
      if (btn) btn.innerHTML = '🌐 ...';
      translated = await translateSRT(raw, src, tgt);
    }
    if (!translated || translated === raw) {
      toastClear(); toast('⚠ Traduction identique — vérifie les clés et la langue source'); return;
    }
    srtOriginal = translated; srtTxt = translated;
    var withOffset = currentOffset !== 0 ? shiftSRT(srtOriginal, currentOffset) : srtOriginal;
    document.getElementById('sp').value = withOffset;
    if (previewVttUrl) {
      URL.revokeObjectURL(previewVttUrl);
      var vttBlob = new Blob([srtToVtt(withOffset)], { type: 'text/vtt' });
      previewVttUrl = URL.createObjectURL(vttBlob);
      clearTimeout(offsetReloadTimer);
      offsetReloadTimer = setTimeout(function() { document.getElementById('previewTrack').src = previewVttUrl; }, 50);
    }
    toastClear();
    toast(tgt === 'fr'
      ? '🌐 Patch FR terminé (' + engine + ') — ' + nbBlocks + ' blocs'
      : '🌐 Traduit (' + engine + ') → ' + tgt.toUpperCase());
    validateSRT(true);
    checkLangMismatch(srtOriginal, tgt);
  } catch(e) {
    toastClear();
    toast('Erreur traduction : ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = btnOrig; }
  }
}`;

c = c.slice(0, startIdx) + newFn + c.slice(pos);

// Version
var before = (c.match(/v8\.50/g) || []).length;
c = c.replace(/v8\.50/g, 'v8.51');
console.log('Version bumps v8.50->v8.51:', before);

if (crlf) c = c.replace(/\n/g, '\r\n');
fs.writeFileSync(__dirname + '/index.html', c);
console.log('OK - v8.51');
