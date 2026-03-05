/**
 * Patch index.html v8.49 → v8.50
 * Nouvelle architecture cleanAI :
 * - Approche texte numéroté [N] text (block count garanti par algo)
 * - L'IA ne reçoit QUE les textes, sans timestamps
 * - Reconstruction SRT depuis structure originale → fusion impossible
 */
var fs = require('fs');
var content = fs.readFileSync(__dirname + '/index.html', 'utf8');
var crlf = content.includes('\r\n');
var c = content.replace(/\r\n/g, '\n');

// Trouver les bornes de la fonction cleanAI par comptage d'accolades
var startMarker = 'async function cleanAI() {\n';
var startIdx = c.indexOf(startMarker);
if (startIdx === -1) { console.error('cleanAI start not found'); process.exit(1); }

var pos = startIdx + startMarker.length;
var depth = 1;
while (pos < c.length && depth > 0) {
  if (c[pos] === '{') depth++;
  else if (c[pos] === '}') depth--;
  pos++;
}
console.log('Old cleanAI found, ends at pos', pos, '— depth check:', depth);
if (depth !== 0) { console.error('Brace mismatch!'); process.exit(1); }

// Nouvelle fonction cleanAI
// NOTE: dans ce template literal, \\n -> \n dans le fichier généré (escape JS string)
//       \\[ \\d \\s -> \[ \d \s dans le fichier généré (regex)
var newFn = `async function cleanAI() {
  var raw = getCurrentSRT();
  if (!raw || !raw.trim()) { toast('Aucun SRT à nettoyer'); return; }
  var engine = getAIEngine();
  var hasKey = engine === 'deepseek' ? !!getDeepSeekKey() : !!getGeminiKey();
  if (!hasKey) { toast('⚠ Clé ' + (engine === 'deepseek' ? 'DeepSeek' : 'Gemini') + ' requise'); return; }
  var engineName = engine === 'deepseek' ? 'DeepSeek' : 'Gemini';
  var origBlocks = parseSRT(raw);
  if (!origBlocks.length) { toast('SRT invalide'); return; }
  var srtTextLang = (function() {
    var out = document.getElementById('outLangMain').value;
    if (out && out !== 'same') return out;
    return detectedLang || document.getElementById('srcLangMain').value || '';
  })();
  var BATCH = 200;
  var btn = document.getElementById('cleanAIBtn');
  var btnOrig = btn ? btn.innerHTML : '';
  if (btn) btn.disabled = true;
  try {
    var batches = [];
    for (var i = 0; i < origBlocks.length; i += BATCH) batches.push(origBlocks.slice(i, i + BATCH));
    // Textes corrigés — par défaut = originaux (fallback si IA rate un bloc)
    var correctedTexts = origBlocks.map(function(b) { return b.text; });
    for (var b = 0; b < batches.length; b++) {
      var label = batches.length > 1 ? '✨ Nettoyage ' + engineName + ' ' + (b+1) + '/' + batches.length + '...' : '✨ Nettoyage ' + engineName + '...';
      toastPersist(label);
      if (btn) btn.innerHTML = batches.length > 1 ? '✨ IA ' + (b+1) + '/' + batches.length : '✨ IA...';
      var batchBlocks = batches[b];
      var batchOffset = b * BATCH;
      var isCJK_c = /^(zh|ja|ko)$/.test(srtTextLang);
      var langLine = srtTextLang ? 'The subtitle text language is "' + srtTextLang + '". ' : '';
      var typoRule = srtTextLang === 'fr'
        ? '\\n5. FRENCH: Fix missing apostrophes (c est->c\\'est, j ai->j\\'ai, qu il->qu\\'il, s il->s\\'il, etc.). Add space before ? ! : ; if missing.'
        : (isCJK_c ? '\\n5. CJK: Fix wrong characters with similar pronunciation only. Do NOT convert Traditional/Simplified.' : '');
      var bracketsRule = isCJK_c
        ? '\\n4. Incoherent sequences = hallucination — replace inline with [...] only if partial. NEVER entire line.'
        : '\\n4. Foreign words MAY be intentional. Only [...] for partial unintelligible noise inline. NEVER entire line.';
      // Construire lignes numérotées — texte multiligne joint avec ' | '
      var promptLines = batchBlocks.map(function(blk, j) {
        return '[' + (batchOffset + j + 1) + '] ' + blk.text.replace(/\\n/g, ' | ');
      });
      var prompt = 'You are a professional subtitle editor. ' + langLine + '\\n' +
        'Each line is [N] subtitle_text. Return EACH line as [N] corrected_text.\\n' +
        '1. NEVER skip a number. If text is already correct, return it UNCHANGED.\\n' +
        '2. PROPER NOUNS: Never alter character names, place names, invented terms. Capitalized word not starting a sentence = likely proper noun.\\n' +
        '3. INTERJECTIONS & TRUNCATED: Short exclamations (Hé, Oh, Ha, Eï, Ouh, Bah, Tss, Yeah, Kiii, etc.) are VALID — NEVER replace. Lines ending without punctuation are intentionally cut — never add words.\\n' +
        bracketsRule + typoRule + '\\n' +
        '6. CORRECTIONS: Fix spelling errors, missing apostrophes, obvious Whisper mishearing only.\\n' +
        'Return ONLY the numbered lines [N] text. No SRT structure, no timestamps, no explanation.\\n\\n' +
        promptLines.join('\\n');
      try {
        var aiText = await callAIText(prompt);
        // Parser les marqueurs [N] dans la réponse IA
        var lineRx = /^\\[(\\d+)\\]\\s*(.*)/gm;
        var m;
        while ((m = lineRx.exec(aiText)) !== null) {
          var idx = parseInt(m[1]) - 1;
          if (idx >= 0 && idx < origBlocks.length) {
            var corrected = m[2].replace(/ \\| /g, '\\n').trim();
            if (corrected) correctedTexts[idx] = corrected;
          }
        }
      } catch(e2) {
        console.warn('Batch ' + b + ' erreur (textes originaux conservés):', e2.message);
      }
    }
    // Reconstruire SRT depuis structure originale (timestamps intouchés) → block count garanti
    var cleaned = origBlocks.map(function(blk, i) {
      return blk.id + '\\n' + blk.timestamp + '\\n' + correctedTexts[i];
    }).join('\\n\\n') + '\\n';
    srtOriginal = cleaned; srtTxt = cleaned;
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
    toast('✨ Nettoyage IA terminé — ' + origBlocks.length + ' blocs');
    showUndoBanner(raw, origBlocks.length, 0);
    validateSRT(true);
    checkLangMismatch(srtOriginal, document.getElementById('outLangMain').value || null);
  } catch(e) {
    toastClear();
    toast('Erreur nettoyage IA : ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = btnOrig; }
  }
}`;

c = c.slice(0, startIdx) + newFn + c.slice(pos);

// Version
var before = (c.match(/v8\.49/g) || []).length;
c = c.replace(/v8\.49/g, 'v8.50');
console.log('Version bumps v8.49->v8.50:', before);

// Restaurer CRLF
if (crlf) c = c.replace(/\n/g, '\r\n');
fs.writeFileSync(__dirname + '/index.html', c);
console.log('OK - v8.50');
