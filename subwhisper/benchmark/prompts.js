/**
 * SubWhisper — Prompts centralisés
 * Source unique : modifié ici → copié dans index.html
 * Version : v8.45
 */

function getCleanPrompt(srtTextLang) {
  var isCJK = /^(zh|ja|ko)$/.test(srtTextLang);
  var isFR  = srtTextLang === 'fr';
  var langLine = srtTextLang ? 'The subtitle TEXT language is "' + srtTextLang + '". ' : '';
  var typoC = isFR
    ? '\n- FRENCH TYPOGRAPHY: Preserve spaces before ? ! : ; — mandatory in French. NEVER remove them.'
    : (isCJK ? '\n- CJK: Fix wrong characters with similar pronunciation. Do NOT convert Traditional/Simplified.' : '');
  var foreignC = isCJK
    ? '\n- Repeated sequences of only numbers or single incoherent characters are hallucinations — replace with [...]'
    : '\n- Foreign words MAY be intentional (song lyrics, foreign character). Only replace with [...] if clearly incoherent garbled noise.';

  return 'You are a professional subtitle editor. ' + langLine + 'Clean up this subtitle file.\n' +
    '1. STRUCTURE: Timestamp lines (HH:MM:SS,mmm --> HH:MM:SS,mmm) and index lines EXACTLY as-is. NEVER insert timestamp text into subtitle content lines.\n' +
    '2. PROPER NOUNS: Never alter character names, place names, invented terms. Any capitalized word not starting a sentence is likely a proper noun — leave it unchanged.\n' +
    '3. [...] USAGE: Only for truly unintelligible noise. Short exclamations (Hé, Oh, Ha, Eï, Ouh, Bah, Tss, Yeah, Kiii, etc.) are VALID content — NEVER replace with [...]. Slang and non-standard words are also valid.\n' +
    '4. TRUNCATED LINES: Lines ending without punctuation or with ... are intentionally cut — NEVER add words.' +
    foreignC + typoC + '\n' +
    '5. CORRECTIONS: Fix spelling errors, missing apostrophes, obvious Whisper mishearing only.\n' +
    '6. Return ONLY corrected SRT, SAME block count, no explanation, no markdown.';
}

function getTranslatePrompt(srcName, tgtName) {
  var typoT = tgtName.toLowerCase().includes('french') || tgtName === 'fr'
    ? '\n- FRENCH TYPOGRAPHY: Include mandatory space before ? ! : ; in French.'
    : '';
  return 'You are a professional subtitle translator. Translate from ' + srcName + ' to ' + tgtName + '.\n' +
    '1. STRUCTURE: Timestamp (HH:MM:SS,mmm --> HH:MM:SS,mmm) and index lines EXACTLY as-is. NEVER insert timestamp text into subtitle content.\n' +
    '2. PROPER NOUNS: Keep character names, place names, invented terms in ORIGINAL form. Capitalized word not starting a sentence = likely proper noun, do not alter.\n' +
    '3. COMPLETE TRANSLATION: Translate EVERY line. NEVER output [...] — if uncertain give best translation. Do not skip or merge blocks.\n' +
    '4. SONG LYRICS: Text clearly song lyrics in a third language — keep unchanged.\n' +
    '5. STYLE: Match register and tone. Preserve short exclamations exactly.\n' +
    '6. TRUNCATED: Lines ending without punctuation or ... = intentionally cut. Do NOT add words.' + typoT + '\n' +
    '7. Return ONLY translated SRT, SAME block count, no explanation, no markdown.';
}

module.exports = { getCleanPrompt, getTranslatePrompt };
