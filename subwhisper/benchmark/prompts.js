/**
 * SubWhisper — Prompts centralisés
 * Source unique : modifié ici → copié dans index.html
 * Version : v8.70
 */

function getCleanPrompt(srtTextLang, blockCount) {
  var isCJK = /^(zh|ja|ko)$/.test(srtTextLang);
  var isFR  = srtTextLang === 'fr';
  var langLine = srtTextLang ? 'The subtitle TEXT language is "' + srtTextLang + '". ' : '';
  var typoC = isFR
    ? '\n- FRENCH TYPOGRAPHY: Preserve spaces before ? ! : ; — mandatory in French. NEVER remove them.'
    : (isCJK ? '\n- CJK: Fix wrong characters with similar pronunciation. Do NOT convert Traditional/Simplified.' : '');
  var foreignC = isCJK
    ? '\n- Repeated sequences of only numbers or single incoherent characters are hallucinations — replace with [...]'
    : '\n- Foreign words MAY be intentional (song lyrics, foreign character). Only replace with [...] if clearly incoherent garbled noise.';

  var countLine = blockCount ? '⚠ THIS BATCH HAS EXACTLY ' + blockCount + ' BLOCKS. Your output MUST also have exactly ' + blockCount + ' blocks — no more, no less.\n' : '';
  return 'You are a professional subtitle editor. ' + langLine + 'Clean up this subtitle file.\n' +
    countLine +
    '⚠ BLOCK COUNT RULE (mandatory): NEVER merge two blocks into one, NEVER delete a block, NEVER split a block. If a block is noise or unclear, copy it UNCHANGED.\n' +
    '1. STRUCTURE: Each block = index line + timestamp line (HH:MM:SS,mmm --> HH:MM:SS,mmm) + text line(s). Copy index and timestamp lines VERBATIM. NEVER copy a timestamp into the text content of any block.\n' +
    '2. PROPER NOUNS: Never alter character names, place names, invented terms. Any capitalized word not starting a sentence is likely a proper noun — leave it unchanged.\n' +
    '3. [...] USAGE: ONLY for partial unintelligible noise WITHIN a line — e.g. "Je vais [...] chercher". NEVER replace an entire block with [...]. Short exclamations (Hé, Oh, Ha, Eï, Ouh, Bah, Tss, Yeah, Kiii, etc.) are VALID content — NEVER replace with [...]. Foreign words are VALID — keep them.\n' +
    '4. TRUNCATED LINES: Lines ending without punctuation or with ... are intentionally cut — NEVER add words.' +
    foreignC + typoC + '\n' +
    '5. CORRECTIONS: Fix spelling errors, missing apostrophes, obvious Whisper mishearing only.\n' +
    '6. Return ONLY corrected SRT. Block count in = block count out. No explanation, no markdown.';
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

/**
 * getCleanTextPrompt — Approche [N] v8.65 : règles spécifiques par langue
 * ZH : 的/地/得, 在/再, 他/她/它
 * JA : hiragana/katakana, register です/ます vs だ
 * KO : Hangul phonétique, register 요/습니다 vs 야/다
 * FR : apostrophes + U+00A0 avant ?!:;
 */
function getCleanTextPrompt(lang) {
  var isZH = lang === 'zh';
  var isJA = lang === 'ja';
  var isKO = lang === 'ko';
  var isCJK = isZH || isJA || isKO;
  var langLine = lang ? 'The subtitle text language is "' + lang + '". ' : '';

  var langSpecificRule = '';
  if (isZH) {
    langSpecificRule = '\n5. CHINESE: Fix common homophones — 的/地/得 (grammar particle), 在/再 (at/again), 他/她/它 (he/she/it). Do NOT convert Traditional↔Simplified — keep characters exactly as transcribed.';
  } else if (isJA) {
    langSpecificRule = '\n5. JAPANESE: Fix obvious hiragana/katakana confusion and misheard kanji only. Preserve speech register — do NOT convert です/ます (polite) to だ/である (casual) or vice versa.';
  } else if (isKO) {
    langSpecificRule = '\n5. KOREAN: Fix phonetically similar Hangul characters only. Preserve speech register — do NOT convert 요/습니다 (formal) to 야/다 (casual) or vice versa.';
  } else if (lang === 'fr') {
    langSpecificRule = '\n5. FRENCH: Fix missing apostrophes (c est→c\'est, j ai→j\'ai, qu il→qu\'il, s il→s\'il, n est→n\'est, l homme→l\'homme, etc.). Add non-breaking space (U+00A0) before ? ! : ; if missing — mandatory French typography.';
  }

  var bracketsRule = isCJK
    ? '\n4. NEVER output [...] for ANY reason. If a line is noise, garbled, or incoherent — COPY IT EXACTLY UNCHANGED. [...] is FORBIDDEN in your output.'
    : '\n4. [...] FORBIDDEN for entire blocks. If a line contains garbled tokens, foreign words, or mixed-language noise — COPY IT EXACTLY AS-IS. Only [...] is allowed INSIDE a line for partial unintelligible noise (e.g. "Je vais [...] chercher").';

  return 'You are a professional subtitle editor. ' + langLine + '\n' +
    'Each line is [N] subtitle_text. Return EACH line as [N] corrected_text.\n' +
    '1. NEVER skip a number. If text is already correct, return it UNCHANGED.\n' +
    '2. PROPER NOUNS: Never alter character names, place names, invented terms. Capitalized word not starting a sentence = likely proper noun.\n' +
    '3. INTERJECTIONS & TRUNCATED: Short exclamations (Hé, Oh, Ha, Eï, Ouh, Bah, Tss, Yeah, Kiii, etc.) are VALID — NEVER replace. Lines ending without punctuation are intentionally cut — never add words.\n' +
    bracketsRule + langSpecificRule + '\n' +
    '6. CORRECTIONS: Fix spelling errors, missing apostrophes, obvious Whisper mishearing only.\n' +
    'Return ONLY the numbered lines [N] text. No SRT structure, no timestamps, no explanation.';
}

/**
 * getTranslateTextPrompt — Approche [N] v8.65 : règles spécifiques par langue source
 * srcName : 'Chinese', 'Japanese', 'Korean', etc.
 * tgtName : 'French', 'English', etc.
 * tgtLang : 'fr', 'en', etc.
 * srcLang : 'zh', 'ja', 'ko', etc. (NOUVEAU v8.65 — règles per-source)
 */
function getTranslateTextPrompt(srcName, tgtName, tgtLang, srcLang) {
  var typoRule = (tgtLang === 'fr')
    ? '\n6. FRENCH TYPOGRAPHY: Add mandatory non-breaking space (U+00A0) before ? ! : ; in French.'
    : '';

  var srcSpecificRule = '';
  if (srcLang === 'zh') {
    srcSpecificRule = '\n7. CHINESE SOURCE: Romanized names (Xiao Ming, Li Wei, etc.) — adapt naturally in context or keep as-is. Chinese onomatopoeia/interjections (哈哈, 啊, 哟, 哦) → convert to natural equivalent in ' + tgtName + '.';
  } else if (srcLang === 'ja') {
    srcSpecificRule = '\n7. JAPANESE SOURCE: Honorifics (-san, -kun, -chan, -sama, -sensei) — keep UNCHANGED after the name. Keigo → translate as formal/polite ' + tgtName + '. Short Japanese exclamations (すごい, あー, おやすみ, パンパン, etc.) are common expressions — ALWAYS translate them, they are NOT proper nouns. Korean (Hangul) characters in this file are speech recognition errors — translate them phonetically or give best approximation in ' + tgtName + '.';
  } else if (srcLang === 'ko') {
    srcSpecificRule = '\n7. KOREAN SOURCE: Relationship address terms (oppa, unnie, noona, hyung) — keep UNCHANGED as-is (they are culturally specific, not translatable). Speech levels → match formal/casual register in ' + tgtName + '.';
  }

  return 'You are a professional subtitle translator. Translate ALL text to ' + tgtName + '.\n' +
    'Source is primarily ' + srcName + ' but MAY contain English or other languages — translate EVERYTHING to ' + tgtName + '.\n' +
    'Each line is [N] source_text. Return EACH line as [N] translated_text.\n' +
    '1. NEVER skip a number. Return ALL [N] lines.\n' +
    '2. PROPER NOUNS: Keep character names, place names, invented terms in original form.\n' +
    '3. COMPLETE TRANSLATION: Translate EVERY line regardless of source language. NEVER output [...]. If uncertain, give best translation.\n' +
    '4. SONG LYRICS: Text clearly song lyrics in a third language — keep unchanged.\n' +
    '5. TRUNCATED: Lines ending without punctuation = intentionally cut — do NOT add words.' + typoRule + srcSpecificRule + '\n' +
    'Return ONLY the numbered lines [N] text. No timestamps, no SRT structure, no explanation.';
}

module.exports = { getCleanPrompt, getCleanTextPrompt, getTranslatePrompt, getTranslateTextPrompt };
