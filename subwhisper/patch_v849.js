/**
 * Patch index.html v8.48 → v8.49
 * Guard block count dans cleanAI + warning orange si >5% blocs perdus
 */
var fs = require('fs');
var content = fs.readFileSync(__dirname + '/index.html', 'utf8');

// Normalise les fins de ligne pour les recherches, puis restaure
var crlf = content.includes('\r\n');
var c = content.replace(/\r\n/g, '\n');

// 1. Guard block count dans le toast post-cleanAI
var OLD = "    toastClear();\n    toast('\\u2728 Nettoyage IA termin\\u00e9 \\u2014 ' + validBlocks.length + ' blocs');\n    showUndoBanner(raw, validBlocks.length);";
var NEW = "    toastClear();\n    var origBlocks = parseSRT(raw);\n    var blockLost = origBlocks.length - validBlocks.length;\n    var blockLostPct = origBlocks.length > 0 ? blockLost / origBlocks.length : 0;\n    if (blockLostPct > 0.05) {\n      toast('\\u26a0 CleanAI a fusionn\\u00e9 des blocs (' + origBlocks.length + '\\u2192' + validBlocks.length + ', -' + Math.round(blockLostPct*100) + '%) \\u2014 timings affect\\u00e9s');\n    } else {\n      toast('\\u2728 Nettoyage IA termin\\u00e9 \\u2014 ' + validBlocks.length + ' blocs');\n    }\n    showUndoBanner(raw, validBlocks.length, blockLost);";

if (!c.includes(OLD)) { console.error('OLD not found'); process.exit(1); }
c = c.replace(OLD, NEW);

// 2. Modifier showUndoBanner signature + affichage warning orange
var OLD2 = "function showUndoBanner(originalSrt, nbBlocks) {\n  _cleanAIBackup = originalSrt;\n  var banner = document.getElementById('undoBanner');\n  var txt    = document.getElementById('undoBannerTxt');\n  if (!banner) return;\n  if (txt) txt.textContent = '\\u2728 Nettoyage IA appliqu\\u00e9 (' + nbBlocks + ' blocs) \\u2014 v\\u00e9rifiez le r\\u00e9sultat';\n  banner.style.display = 'flex';\n}";
var NEW2 = "function showUndoBanner(originalSrt, nbBlocks, blockLost) {\n  _cleanAIBackup = originalSrt;\n  var banner = document.getElementById('undoBanner');\n  var txt    = document.getElementById('undoBannerTxt');\n  if (!banner) return;\n  if (blockLost && blockLost > 0) {\n    if (txt) txt.textContent = '\\u26a0 ' + blockLost + ' blocs fusionn\\u00e9s par l\\'IA \\u2014 timings affect\\u00e9s, pensez \\u00e0 annuler';\n    banner.style.background = 'rgba(255,160,50,.12)';\n    banner.style.borderColor = 'rgba(255,160,50,.4)';\n  } else {\n    if (txt) txt.textContent = '\\u2728 Nettoyage IA appliqu\\u00e9 (' + nbBlocks + ' blocs) \\u2014 v\\u00e9rifiez le r\\u00e9sultat';\n    banner.style.background = '';\n    banner.style.borderColor = '';\n  }\n  banner.style.display = 'flex';\n}";

if (!c.includes(OLD2)) { console.error('OLD2 not found'); process.exit(1); }
c = c.replace(OLD2, NEW2);

// 3. Version
c = c.replace(/v8\.48/g, 'v8.49');

// Restaurer CRLF si nécessaire
if (crlf) c = c.replace(/\n/g, '\r\n');
fs.writeFileSync(__dirname + '/index.html', c);
console.log('OK - v8.49');
