/**
 * Patch index.html v8.47 → v8.48
 * Ajoute batchCountLine (count explicite du batch) dans le prompt cleanAI
 * Utilise String.fromCharCode(10) pour éviter tout problème d'échappement LF
 */
var fs = require('fs');
var buf = fs.readFileSync(__dirname + '/index.html');

// Insérer avant "var prompt ="  la variable batchCountLine
// Utilise String.fromCharCode(10) = LF sans jamais écrire \n
var INSERT_BEFORE = Buffer.from('var prompt =');
var searchFrom = 200000;
var idx = buf.indexOf(INSERT_BEFORE, searchFrom);
if (idx === -1) { console.error('var prompt = not found'); process.exit(1); }

// La ligne à insérer — pas de \n escape, on concatène avec String.fromCharCode(10)
var LINE = "var batchCountLine = '\u26a0 THIS BATCH HAS EXACTLY ' + batches[b].length + ' BLOCKS. Output MUST have exactly ' + batches[b].length + ' blocks.' + String.fromCharCode(10);\r\n      ";
var INSERT = Buffer.from(LINE, 'utf8');

buf = Buffer.concat([buf.slice(0, idx), INSERT, buf.slice(idx)]);

// Remplacer "var prompt = 'You are" par "var prompt = batchCountLine + 'You are"
var OLD_START = Buffer.from("var prompt = 'You are");
var NEW_START = Buffer.from("var prompt = batchCountLine + 'You are");
var idx2 = buf.indexOf(OLD_START, searchFrom);
if (idx2 === -1) { console.error('var prompt start not found'); process.exit(1); }
buf = Buffer.concat([buf.slice(0, idx2), NEW_START, buf.slice(idx2 + OLD_START.length)]);

// Mettre à jour la version
var content = buf.toString('utf8');
content = content.replace(/v8\.47/g, 'v8.48');
fs.writeFileSync(__dirname + '/index.html', content);

// Vérification
var check = Buffer.from(content, 'utf8');
var hasBatchCount = content.indexOf('batchCountLine') > -1;
var hasFromCharCode = content.indexOf('fromCharCode(10)') > -1;
var rogueLF = check.indexOf(Buffer.from("blocks.'\n")) > -1 ||
              check.indexOf(Buffer.from('blocks.\n\'')) > -1;
console.log('batchCountLine:', hasBatchCount, '| fromCharCode:', hasFromCharCode, '| rogue LF:', rogueLF);
console.log('OK');
