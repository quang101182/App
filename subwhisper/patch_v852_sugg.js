// patch_v852_sugg.js — SubWhisper v8.52 : bandeau suggestions contextuel
var fs = require('fs');
var content = fs.readFileSync(__dirname + '/index.html', 'utf8');
var crlf = content.includes('\r\n');
var c = content.replace(/\r\n/g, '\n');

var alreadyDone = {
  r1: c.includes('#suggBanner{display:none;'),
  r2: c.includes('<div id="suggBanner">'),
  r3: c.includes('function analyzeSRT(srtContent)'),
  r4: c.includes('showSuggBanner(analyzeSRT(srtOriginal))'),
  r5: c.includes('hideSuggBanner();\n  var raw = getCurrentSRT()')
};

// ── REMPLACEMENT 1 : CSS suggBanner après #langNotice button ──────────────
if (alreadyDone.r1) {
  console.log('R1 SKIP : CSS suggBanner déjà présent');
} else {
  var css_old = '#langNotice button{background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px;padding:2px 6px}';
  var css_new = '#langNotice button{background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px;padding:2px 6px}\n' +
  '/* ── SUGGESTIONS BANNER ──────────────────────────────── */\n' +
  '#suggBanner{display:none;align-items:center;gap:8px;flex-wrap:wrap;padding:9px 14px;margin-top:8px;background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.28);border-left:3px solid #f59e0b;border-radius:10px;font-size:12px}\n' +
  '#suggBannerLbl{color:var(--muted);white-space:nowrap;font-family:var(--mono);font-size:11px;flex-shrink:0}\n' +
  '#suggChips{display:flex;gap:6px;flex-wrap:wrap;flex:1}\n' +
  '.sugg-chip{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.38);color:#f59e0b;border-radius:8px;padding:4px 11px;cursor:pointer;font-size:11px;font-family:var(--mono);transition:background .15s;white-space:nowrap}\n' +
  '.sugg-chip:hover{background:rgba(245,158,11,.28)}\n' +
  '#suggClose{background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px;padding:2px 6px;margin-left:auto;flex-shrink:0;line-height:1}\n' +
  '#suggClose:hover{color:var(--text)}\n' +
  '@keyframes suggSlideIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}\n' +
  '@keyframes suggGlow{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0)}50%{box-shadow:0 0 0 5px rgba(245,158,11,.20)}}\n' +
  '.sugg-glow{animation:suggGlow 1.4s ease-in-out 3}\n' +
  '@keyframes btnSuggPulse{0%,100%{box-shadow:none}50%{box-shadow:0 0 0 3px rgba(245,158,11,.42)}}\n' +
  '.btn-sugg-pulse{animation:btnSuggPulse 1.2s ease-in-out infinite}';
  if (!c.includes(css_old)) { console.error('ERREUR R1 : CSS old string introuvable'); process.exit(1); }
  c = c.replace(css_old, css_new);
  console.log('R1 OK : CSS suggBanner ajouté');
}

// ── REMPLACEMENT 2 : HTML #suggBanner après #langNotice ──────────────────
if (alreadyDone.r2) {
  console.log('R2 SKIP : HTML #suggBanner déjà présent');
} else {
  var html_old = '  <div id="langNotice">\n    <span id="langNoticeTxt"></span>\n    <button onclick="closeLangNotice()" title="Fermer">&#x2715;</button>\n  </div>';
  var html_new = '  <div id="langNotice">\n    <span id="langNoticeTxt"></span>\n    <button onclick="closeLangNotice()" title="Fermer">&#x2715;</button>\n  </div>\n  <div id="suggBanner">\n    <span id="suggBannerLbl">&#x1f4a1; Suggestions :</span>\n    <div id="suggChips"></div>\n    <button id="suggClose" onclick="hideSuggBanner()" title="Fermer">&#x2715;</button>\n  </div>';
  if (!c.includes(html_old)) { console.error('ERREUR R2 : HTML old string introuvable'); process.exit(1); }
  c = c.replace(html_old, html_new);
  console.log('R2 OK : HTML #suggBanner ajouté');
}

// ── REMPLACEMENT 3 : fonctions analyzeSRT / showSuggBanner / hideSuggBanner ──
if (alreadyDone.r3) {
  console.log('R3 SKIP : fonctions déjà présentes');
} else {
  var js_old = 'var _cleanAIBackup = null;\nfunction showUndoBanner(originalSrt, nbBlocks, blockLost) {';
  var js_new = 'var _cleanAIBackup = null;\n' +
  'function analyzeSRT(srtContent) {\n' +
  '  var blocks = parseSRT(srtContent);\n' +
  '  if (!blocks.length) return [];\n' +
  '  var suggestions = [];\n' +
  '  // 1. Blocs non-latins (CJK, cyrillique, hangul...)\n' +
  '  var nonFr = 0;\n' +
  '  blocks.forEach(function(b) { if (/[\\u3040-\\u9fff\\uac00-\\ud7af\\u0400-\\u04ff]/.test(b.text)) nonFr++; });\n' +
  '  if (nonFr > 0) suggestions.push({ msg: nonFr + \' bloc\' + (nonFr > 1 ? \'s\' : \'\') + \' non-fran\\u00e7ais\', action: \'TRAD\', btnId: \'translateBtn\', fn: \'translateManual\' });\n' +
  '  // 2. Apostrophes manquantes FR\n' +
  '  var missApo = 0;\n' +
  '  blocks.forEach(function(b) { if (/\\b(c est|j ai|j en|qu il|qu elle|s il|n est|l homme)\\b/i.test(b.text)) missApo++; });\n' +
  '  if (missApo > 1) suggestions.push({ msg: missApo + \' fautes apostrophe\', action: \'IA\', btnId: \'cleanAIBtn\', fn: \'cleanAI\' });\n' +
  '  // 3. Répétitions phonétiques (hallucinations)\n' +
  '  var halluc = 0;\n' +
  '  blocks.forEach(function(b) { var ws = b.text.split(/\\s+/); for (var i = 0; i < ws.length - 2; i++) { if (ws[i] && ws[i] === ws[i+1] && ws[i+1] === ws[i+2] && ws[i].length <= 5) { halluc++; break; } } });\n' +
  '  if (halluc > 2) suggestions.push({ msg: halluc + \' r\\u00e9p\\u00e9titions phon\\u00e9tiques\', action: \'IA\', btnId: \'cleanAIBtn\', fn: \'cleanAI\' });\n' +
  '  // 4. SRT propre → IA recommandé par précaution\n' +
  '  if (suggestions.length === 0 && blocks.length > 5) suggestions.push({ msg: \'Nettoyage IA recommand\\u00e9\', action: \'IA\', btnId: \'cleanAIBtn\', fn: \'cleanAI\', soft: true });\n' +
  '  return suggestions;\n' +
  '}\n' +
  'function showSuggBanner(suggestions) {\n' +
  '  var banner = document.getElementById(\'suggBanner\');\n' +
  '  var chips  = document.getElementById(\'suggChips\');\n' +
  '  var lbl    = document.getElementById(\'suggBannerLbl\');\n' +
  '  if (!banner || !suggestions || !suggestions.length) return;\n' +
  '  var actions = { cleanAI: cleanAI, translateManual: translateManual };\n' +
  '  chips.innerHTML = \'\';\n' +
  '  var pulse = [];\n' +
  '  suggestions.forEach(function(s) {\n' +
  '    var chip = document.createElement(\'button\');\n' +
  '    chip.className = \'sugg-chip\';\n' +
  '    chip.textContent = (s.action === \'IA\' ? \'\\u2728 IA\' : \'\\ud83c\\udf10 TRAD\') + \' \\u2014 \' + s.msg;\n' +
  '    chip.onclick = (function(fn) { return function() { hideSuggBanner(); if (actions[fn]) actions[fn](); }; })(s.fn);\n' +
  '    chips.appendChild(chip);\n' +
  '    if (s.btnId && !s.soft) pulse.push(s.btnId);\n' +
  '  });\n' +
  '  if (lbl) lbl.textContent = \'\\ud83d\\udca1 Suggestions :\';\n' +
  '  banner.style.display = \'flex\';\n' +
  '  banner.style.animation = \'none\';\n' +
  '  void banner.offsetWidth;\n' +
  '  banner.style.animation = \'suggSlideIn .2s ease\';\n' +
  '  banner.classList.remove(\'sugg-glow\');\n' +
  '  void banner.offsetWidth;\n' +
  '  banner.classList.add(\'sugg-glow\');\n' +
  '  pulse.forEach(function(id) {\n' +
  '    var btn = document.getElementById(id);\n' +
  '    if (btn) {\n' +
  '      btn.classList.add(\'btn-sugg-pulse\');\n' +
  '      setTimeout(function() { if (btn) btn.classList.remove(\'btn-sugg-pulse\'); }, 7000);\n' +
  '    }\n' +
  '  });\n' +
  '}\n' +
  'function hideSuggBanner() {\n' +
  '  var banner = document.getElementById(\'suggBanner\');\n' +
  '  if (banner) { banner.style.display = \'none\'; banner.classList.remove(\'sugg-glow\'); }\n' +
  '  [\'cleanAIBtn\', \'translateBtn\'].forEach(function(id) {\n' +
  '    var btn = document.getElementById(id);\n' +
  '    if (btn) btn.classList.remove(\'btn-sugg-pulse\');\n' +
  '  });\n' +
  '}\n' +
  'function showUndoBanner(originalSrt, nbBlocks, blockLost) {';
  if (!c.includes(js_old)) { console.error('ERREUR R3 : JS old string introuvable'); process.exit(1); }
  c = c.replace(js_old, js_new);
  console.log('R3 OK : fonctions analyzeSRT/showSuggBanner/hideSuggBanner ajoutées');
}

// ── REMPLACEMENT 4 : appel showSuggBanner dans showRes après checkLangMismatch ──
// Cible uniquement la ligne checkLangMismatch, insère showSuggBanner après
if (alreadyDone.r4) {
  console.log('R4 SKIP : showSuggBanner déjà appelé dans showRes');
} else {
  var showres_old = '  setTimeout(function() { checkLangMismatch(srtOriginal, _expectedLang); }, 300);\n  // Avertissement';
  var showres_new = '  setTimeout(function() { checkLangMismatch(srtOriginal, _expectedLang); }, 300);\n  setTimeout(function() { showSuggBanner(analyzeSRT(srtOriginal)); }, 500);\n  // Avertissement';
  if (!c.includes(showres_old)) { console.error('ERREUR R4 : showRes old string introuvable'); process.exit(1); }
  c = c.replace(showres_old, showres_new);
  console.log('R4 OK : appel showSuggBanner ajouté dans showRes');
}

// ── REMPLACEMENT 5 : hideSuggBanner() au début de cleanAI ──────────────────
if (alreadyDone.r5) {
  console.log('R5 SKIP : hideSuggBanner() déjà présent dans cleanAI');
} else {
  var cleanai_old = '  var raw = getCurrentSRT();\n  if (!raw || !raw.trim()) { toast(\'Aucun SRT \u00e0 nettoyer\'); return; }\n  var engine = getAIEngine();\n  var hasKey = engine === \'deepseek\' ? !!getDeepSeekKey() : !!getGeminiKey();\n  if (!hasKey) { toast(\'\u26a0 Cl\u00e9 \' + (engine === \'deepseek\' ? \'DeepSeek\' : \'Gemini\') + \' requise\'); return; }\n  var engineName';
  var cleanai_new = '  hideSuggBanner();\n  var raw = getCurrentSRT();\n  if (!raw || !raw.trim()) { toast(\'Aucun SRT \u00e0 nettoyer\'); return; }\n  var engine = getAIEngine();\n  var hasKey = engine === \'deepseek\' ? !!getDeepSeekKey() : !!getGeminiKey();\n  if (!hasKey) { toast(\'\u26a0 Cl\u00e9 \' + (engine === \'deepseek\' ? \'DeepSeek\' : \'Gemini\') + \' requise\'); return; }\n  var engineName';
  if (!c.includes(cleanai_old)) { console.error('ERREUR R5 : cleanAI old string introuvable'); process.exit(1); }
  c = c.replace(cleanai_old, cleanai_new);
  console.log('R5 OK : hideSuggBanner() ajouté au début de cleanAI');
}

// ── VERSION : mise à jour v8.51 → v8.52 ──────────────────────────────────
var ver_old_title = '<title>SubWhisper v8.51</title>';
var ver_new_title = '<title>SubWhisper v8.52</title>';
var ver_old_badge = '<span class="ver-badge">v8.51</span>';
var ver_new_badge = '<span class="ver-badge">v8.52</span>';

if (c.includes(ver_old_title)) {
  c = c.replace(ver_old_title, ver_new_title);
  console.log('VER OK : title v8.51 → v8.52');
} else if (c.includes('<title>SubWhisper v8.52</title>')) {
  console.log('VER SKIP : title déjà v8.52');
} else {
  // Chercher version courante
  var m = c.match(/<title>SubWhisper (v[\d.]+)<\/title>/);
  console.log('VER INFO : version title trouvée = ' + (m ? m[1] : 'inconnue'));
}
if (c.includes(ver_old_badge)) {
  c = c.replace(ver_old_badge, ver_new_badge);
  console.log('VER OK : badge v8.51 → v8.52');
} else if (c.includes('<span class="ver-badge">v8.52</span>')) {
  console.log('VER SKIP : badge déjà v8.52');
} else {
  var mb = c.match(/<span class="ver-badge">(v[\d.]+)<\/span>/);
  console.log('VER INFO : badge trouvé = ' + (mb ? mb[1] : 'inconnu'));
}

// ── ÉCRITURE ──────────────────────────────────────────────────────────────
if (crlf) c = c.replace(/\n/g, '\r\n');
fs.writeFileSync(__dirname + '/index.html', c);
console.log('PATCH v8.52 OK — index.html mis à jour');
