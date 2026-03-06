'use strict';

/**
 * SubWhisper Batch Lab — Générateur de rapport HTML
 * generateHTML(opts) → string HTML statique
 *
 * opts = {
 *   step: 1|2|3|4,
 *   fileName: string,
 *   srcLang: string,
 *   tgtLang: string|null,
 *   runId: string,
 *   date: string,
 *   inputSRT: string,
 *   inputBlocks: [{id, ts, text}],
 *   gemini: { score: {score, issues, stats, ...}, output: string } | null,
 *   deepseek: { score: {score, issues, stats, ...}, output: string } | null,
 *   groq: { score, issues, stats, recommendations } | null,  // step 1 only
 *   history: [{id, date, step, gemini, deepseek, userNote, edgeCase}]
 * }
 */

var { parseSRT } = require('../score');

var STEP_NAMES = { 1: 'Groq Analysis', 2: 'Traduction', 3: 'CleanAI', 4: 'TRAD Hybride' };
var SEV_COLOR  = { CRITICAL: '#ff4444', HIGH: '#ff8c00', MEDIUM: '#ffd700', LOW: '#aaaaaa', INFO: '#666' };

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function scoreColor(s) {
  if (s >= 95) return '#22c55e';
  if (s >= 85) return '#84cc16';
  if (s >= 70) return '#eab308';
  if (s >= 50) return '#f97316';
  return '#ef4444';
}

function scoreEmoji(s) {
  if (s >= 95) return '🟢';
  if (s >= 85) return '🟡';
  if (s >= 70) return '🟠';
  return '🔴';
}

function renderScoreCard(engine, result, label) {
  if (!result) return '<div class="score-card empty"><div class="engine-name">' + escHtml(label) + '</div><div class="score-na">N/A</div><p>Pas de clé API fournie</p></div>';
  var sc = result.score || result;
  var score = typeof sc === 'object' ? sc.score : sc;
  var issues = (typeof sc === 'object' && sc.issues) ? sc.issues : [];
  var stats = (typeof sc === 'object' && sc.stats) ? sc.stats : {};
  var col = scoreColor(score);

  var issuesHtml = '';
  if (issues.length === 0) {
    issuesHtml = '<div class="no-issues">✓ Aucun problème détecté</div>';
  } else {
    issuesHtml = '<div class="issues-list">';
    issues.slice(0, 20).forEach(function(iss) {
      var sevCol = SEV_COLOR[iss.sev] || '#aaa';
      issuesHtml += '<div class="issue-item"><span class="issue-sev" style="color:' + sevCol + '">[' + escHtml(iss.sev) + ']</span> <span class="issue-type">' + escHtml(iss.type) + '</span><div class="issue-msg">' + escHtml(iss.msg.split('\n')[0]) + '</div></div>';
    });
    if (issues.length > 20) issuesHtml += '<div class="issue-more">+ ' + (issues.length - 20) + ' autres...</div>';
    issuesHtml += '</div>';
  }

  var statsHtml = '';
  var statKeys = Object.keys(stats);
  if (statKeys.length > 0) {
    statsHtml = '<div class="stats-grid">';
    statKeys.forEach(function(k) {
      if (stats[k] > 0) {
        statsHtml += '<div class="stat-item"><span class="stat-val">' + stats[k] + '</span><span class="stat-key">' + escHtml(k) + '</span></div>';
      }
    });
    statsHtml += '</div>';
  }

  return '<div class="score-card"><div class="engine-name">' + escHtml(label) + '</div>' +
    '<div class="score-big" style="color:' + col + '">' + score + '<span class="score-max">/100</span></div>' +
    statsHtml + issuesHtml + '</div>';
}

function renderDiffTable(inputBlocks, gemOutput, dskOutput) {
  var gemBlocks = gemOutput ? parseSRT(gemOutput) : null;
  var dskBlocks = dskOutput ? parseSRT(dskOutput) : null;
  var maxLen = inputBlocks.length;

  var rows = '';
  for (var i = 0; i < maxLen; i++) {
    var inp = inputBlocks[i];
    var gem = gemBlocks ? gemBlocks[i] : null;
    var dsk = dskBlocks ? dskBlocks[i] : null;

    var inpText  = inp ? escHtml(inp.text) : '<em>—</em>';
    var gemText  = gem ? escHtml(gem.text) : '<em class="missing">—</em>';
    var dskText  = dsk ? escHtml(dsk.text) : '<em class="missing">—</em>';

    // Marquer les blocs modifiés
    var gemChanged = gem && inp && gem.text !== inp.text;
    var dskChanged = dsk && inp && dsk.text !== inp.text;
    var gemClass = gemChanged ? ' changed' : '';
    var dskClass = dskChanged ? ' changed' : '';

    // Marquer les divergences Gem vs DSK
    var diverge = gem && dsk && gem.text !== dsk.text;
    var rowClass = diverge ? ' diverge' : '';

    rows += '<tr class="diff-row' + rowClass + '">' +
      '<td class="block-num">' + (i+1) + '<div class="ts">' + escHtml(inp ? inp.ts.split(' --> ')[0] : '') + '</div></td>' +
      '<td class="col-input">' + inpText.replace(/\n/g, '<br>') + '</td>' +
      '<td class="col-gemini' + gemClass + '">' + gemText.replace(/\n/g, '<br>') + '</td>' +
      '<td class="col-deepseek' + dskClass + '">' + dskText.replace(/\n/g, '<br>') + '</td>' +
      '</tr>';
  }

  return '<table class="diff-table">' +
    '<thead><tr>' +
    '<th class="block-num">#</th>' +
    '<th>Input</th>' +
    '<th>Gemini</th>' +
    '<th>DeepSeek</th>' +
    '</tr></thead>' +
    '<tbody>' + rows + '</tbody>' +
    '</table>';
}

function renderHistory(history, currentRunId) {
  if (!history || history.length === 0) return '<p class="no-hist">Aucun run précédent pour ce fichier.</p>';
  var rows = history.map(function(r) {
    var gScore = r.gemini && r.gemini.score !== undefined ? (typeof r.gemini.score === 'object' ? r.gemini.score.score : r.gemini.score) : '—';
    var dScore = r.deepseek && r.deepseek.score !== undefined ? (typeof r.deepseek.score === 'object' ? r.deepseek.score.score : r.deepseek.score) : '—';
    var isCurrent = r.id === currentRunId;
    var gCol = typeof gScore === 'number' ? scoreColor(gScore) : '#666';
    var dCol = typeof dScore === 'number' ? scoreColor(dScore) : '#666';
    return '<tr' + (isCurrent ? ' class="current-run"' : '') + '>' +
      '<td>' + escHtml((r.date || '').substring(0,16).replace('T',' ')) + '</td>' +
      '<td><span style="color:' + gCol + '">' + gScore + '</span></td>' +
      '<td><span style="color:' + dCol + '">' + dScore + '</span></td>' +
      '<td>' + escHtml(r.userNote || '') + '</td>' +
      '<td>' + (r.edgeCase ? '⚠ Edge case' : '') + '</td>' +
      '</tr>';
  });
  return '<table class="hist-table">' +
    '<thead><tr><th>Date</th><th>Gemini</th><th>DeepSeek</th><th>Note</th><th>Flag</th></tr></thead>' +
    '<tbody>' + rows.join('') + '</tbody>' +
    '</table>';
}

function generateHTML(opts) {
  var { step, fileName, srcLang, tgtLang, runId, date, inputSRT, inputBlocks,
        gemini, deepseek, groq, history } = opts;

  var stepName = STEP_NAMES[step] || 'Step ' + step;
  var dateStr = (date || '').substring(0,19).replace('T', ' ');
  var langStr = tgtLang ? (srcLang || '?').toUpperCase() + ' → ' + tgtLang.toUpperCase() : (srcLang || '?').toUpperCase();

  // Step 1 : affichage spécial (groq only)
  var scoresHtml = '';
  if (step === 1 && groq) {
    scoresHtml = renderScoreCard('groq', groq, 'Groq Pipeline');
  } else {
    scoresHtml = '<div class="scores-row">' +
      renderScoreCard('gemini', gemini ? gemini.score : null, 'Gemini') +
      renderScoreCard('deepseek', deepseek ? deepseek.score : null, 'DeepSeek') +
      '</div>';
  }

  var diffHtml = '';
  if (step !== 1 && inputBlocks) {
    diffHtml = '<section class="section diff-section">' +
      '<h2>Comparaison côte à côte <span class="block-count">(' + inputBlocks.length + ' blocs)</span></h2>' +
      '<div class="diff-legend"><span class="legend-changed">■ modifié</span> <span class="legend-diverge">■ Gemini ≠ DeepSeek</span></div>' +
      renderDiffTable(inputBlocks, gemini ? gemini.output : null, deepseek ? deepseek.output : null) +
      '</section>';
  }

  var histHtml = '<section class="section hist-section">' +
    '<h2>Historique des runs (ce fichier, step ' + step + ')</h2>' +
    renderHistory(history, runId) +
    '</section>';

  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SubWhisper Batch Lab — ${escHtml(stepName)} — ${escHtml(fileName)}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f1117;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;line-height:1.5}
a{color:#60a5fa}

/* Header */
.header{background:linear-gradient(135deg,#1e293b,#0f172a);padding:20px 24px;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.header-left h1{font-size:20px;font-weight:700;color:#f1f5f9}
.header-left h1 span{color:#818cf8}
.header-meta{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px}
.meta-chip{background:#1e293b;border:1px solid #334155;padding:3px 10px;border-radius:12px;font-size:11px;color:#94a3b8}
.meta-chip strong{color:#e2e8f0}
.run-id{font-family:monospace;font-size:10px;color:#475569;margin-top:6px}

/* Sections */
.section{padding:20px 24px;border-bottom:1px solid #1e293b}
.section h2{font-size:14px;font-weight:600;color:#94a3b8;margin-bottom:14px;text-transform:uppercase;letter-spacing:.05em}
.block-count{font-size:12px;color:#475569;font-weight:400;text-transform:none;letter-spacing:0}

/* Scores */
.scores-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:600px){.scores-row{grid-template-columns:1fr}}
.score-card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px}
.score-card.empty{opacity:.5}
.engine-name{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#64748b;margin-bottom:8px}
.score-big{font-size:48px;font-weight:800;line-height:1;margin-bottom:12px}
.score-max{font-size:20px;color:#475569;font-weight:400}
.score-na{font-size:32px;color:#475569;font-weight:700;margin:12px 0}
.stats-grid{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.stat-item{background:#0f172a;border-radius:6px;padding:4px 8px;text-align:center;min-width:60px}
.stat-val{display:block;font-size:18px;font-weight:700;color:#f97316}
.stat-key{font-size:10px;color:#64748b}
.issues-list{display:flex;flex-direction:column;gap:6px;max-height:300px;overflow-y:auto}
.issue-item{background:#0f172a;border-radius:6px;padding:6px 8px;border-left:2px solid #334155}
.issue-sev{font-size:10px;font-weight:700}
.issue-type{font-size:11px;font-weight:600;color:#e2e8f0;margin-left:4px}
.issue-msg{font-size:11px;color:#94a3b8;margin-top:2px;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.issue-more{font-size:11px;color:#475569;padding:4px 8px;text-align:center}
.no-issues{font-size:12px;color:#22c55e;padding:8px 0}

/* Diff table */
.diff-legend{display:flex;gap:16px;margin-bottom:10px;font-size:11px}
.legend-changed{color:#fbbf24}
.legend-diverge{color:#f97316}
.diff-table{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed}
.diff-table th{background:#1e293b;color:#64748b;font-weight:600;padding:6px 8px;text-align:left;position:sticky;top:0;font-size:11px;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #334155}
.diff-table td{padding:5px 8px;vertical-align:top;border-bottom:1px solid #1a2234;word-break:break-word}
.diff-table th:nth-child(1),.diff-table td:nth-child(1){width:72px;color:#475569}
.diff-table th:nth-child(2),.diff-table td:nth-child(2){width:28%}
.diff-table th:nth-child(3),.diff-table td:nth-child(3){width:34%}
.diff-table th:nth-child(4),.diff-table td:nth-child(4){width:34%}
.block-num{text-align:right;font-variant-numeric:tabular-nums;font-family:monospace;color:#475569;font-size:11px}
.block-num .ts{font-size:10px;color:#334155;margin-top:2px}
.col-input{color:#94a3b8}
.col-gemini,.col-deepseek{color:#e2e8f0}
.col-gemini.changed{background:#1c2510;color:#bbf7d0}
.col-deepseek.changed{background:#1c1a10;color:#fef3c7}
.diff-row.diverge{background:#1a1410}
.missing{color:#475569!important;font-style:italic}

/* History */
.hist-table{width:100%;border-collapse:collapse;font-size:12px}
.hist-table th{background:#1e293b;color:#64748b;font-weight:600;padding:6px 10px;text-align:left;border-bottom:1px solid #334155;font-size:11px}
.hist-table td{padding:6px 10px;border-bottom:1px solid #1e293b;font-family:monospace}
.hist-table tr.current-run td{background:#1e3a2f;color:#86efac}
.no-hist{color:#475569;font-style:italic;padding:8px 0}

/* Groq step 1 */
.groq-recs{margin-top:12px;padding:10px 12px;background:#1c1a10;border:1px solid #92400e;border-radius:8px;font-size:12px;color:#fcd34d}
.groq-recs h4{color:#f59e0b;margin-bottom:6px;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.groq-recs li{margin-left:16px;margin-top:4px}

/* Scrollbar */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0f172a}
::-webkit-scrollbar-thumb{background:#334155;border-radius:3px}
</style>
</head>
<body>
<header class="header">
  <div class="header-left">
    <h1>SubWhisper Batch Lab — <span>Step ${step}: ${escHtml(stepName)}</span></h1>
    <div class="header-meta">
      <div class="meta-chip"><strong>Fichier:</strong> ${escHtml(fileName)}</div>
      <div class="meta-chip"><strong>Langues:</strong> ${escHtml(langStr)}</div>
      <div class="meta-chip"><strong>Date:</strong> ${escHtml(dateStr)}</div>
      ${inputBlocks ? '<div class="meta-chip"><strong>Blocs:</strong> ' + inputBlocks.length + '</div>' : ''}
    </div>
    <div class="run-id">Run ID: ${escHtml(runId)}</div>
  </div>
</header>

<section class="section">
  <h2>Scores</h2>
  ${scoresHtml}
  ${step === 1 && groq && groq.recommendations && groq.recommendations.length ? '<div class="groq-recs"><h4>Recommandations pipeline</h4><ul>' + groq.recommendations.map(function(r) { return '<li>' + escHtml(r) + '</li>'; }).join('') + '</ul></div>' : ''}
</section>

${diffHtml}
${histHtml}

</body>
</html>`;
}

module.exports = { generateHTML };
