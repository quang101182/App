// Suno Prompt Batch Test — CLI
// Usage: node run-suno-batch.js
const GATEWAY_URL = 'https://api-gateway.quang101182.workers.dev';
const GW_SECRET = '333a33b16f8cab5aec61eb5806eeaee332a50e1172ad1b3e3d710b3d84b9cc7b';

const PROVIDERS = [
  { name: 'Claude Sonnet', provider: 'claude', model: 'claude-sonnet-4-6' },
  { name: 'Claude Haiku', provider: 'claude', model: 'claude-haiku-4-5-20251001' },
  { name: 'Gemini Flash', provider: 'gemini', model: 'gemini-2.0-flash' },
  { name: 'GPT-4o-mini', provider: 'openai', model: 'gpt-4o-mini' },
];

const MODES = ['random', 'prefs', 'artist'];
const ITERATIONS = 2; // par mode par provider
const TEST_ARTIST = 'The Weeknd';

const BANNED = /\b(fuck|shit|bitch|pussy|dick|cunt|cock|goddamn|nigga|nigger|faggot|retard|damn|hell)\b/i;

function buildPrompt(mode) {
  const modeInstr = mode === 'random'
    ? 'MODE ALÉATOIRE: genre, style, époque, culture 100% aléatoires. Surprise totale.'
    : mode === 'prefs'
    ? 'MODE MES GOÛTS: Genres préférés: electro, hip-hop, rnb, indie, K-pop. Artistes de référence: The Weeknd, Daft Punk, Stray Kids, Tame Impala, Kendrick Lamar. Époques: 2000s-actuel. Taste DNA: synthpop sombre, basses profondes, mélodies planantes, énergie K-pop.'
    : `MODE ARTISTE: génère un prompt qui sonne COMME ${TEST_ARTIST}. Analyse son style, ses caractéristiques sonores (BPM typique, tonalité, texture, production, voix), et traduis-les en tags de style Suno.`;

  return `Tu es un expert mondial en production musicale et en Suno AI v5. Tu génères des prompts OPTIMISÉS pour Suno v5.

${modeInstr}
LANGUE DES LYRICS: anglais.

Tu dois retourner un JSON avec EXACTEMENT ces 3 champs:

1. "title": Titre créatif et évocateur (2-5 mots, max 80 caractères)

2. "style": Tags de style Suno v5 optimisés, séparés par des virgules.
   RÈGLES CRITIQUES STYLE:
   - MAXIMUM 200 caractères (Suno tronque silencieusement au-delà)
   - FRONT-LOAD: les premiers mots sont les plus importants (genre + voix d'abord)
   - ORDRE PRIORITAIRE: Genre/sous-genre → Direction vocale → Mood → 1-2 instruments → BPM → Production → Exclusions négatives
   - INCLURE: Genre principal, BPM (ex: "108 BPM"), tonalité (ex: "D-Minor"), énergie, 1-2 textures sonores, type de voix
   - PROMPTING NÉGATIF: utilise "no [element]" pour exclure (ex: "no autotune, no heavy reverb")
   - PAS de références d'artistes dans le style — utilise des descripteurs d'ère
   - ÉVITER les tags contradictoires
   EXEMPLES:
   - "Indie pop, breathy female vocals, 108 BPM, nostalgic, bright guitar arpeggios, warm pads, polished mix, no autotune"
   - "Dark trap, deep male voice, 140 BPM half-time, D-Minor, 808 bass, atmospheric pads, gritty, no crowd chants"

3. "lyrics": Paroles structurées avec tags Suno v5.
   STRUCTURE: [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Outro]
   TAGS OPTIONNELS: [Whispered], [Drop], [Build], [Harmonies], [Ad-libs], [Fade Out]
   FORMAT: 30-40 lignes, 7-10 syllabes/ligne, refrain HOOK mémorable (2-3 lignes)
   ⚠️ TERMES INTERDITS SUNO: ZÉRO jurons/vulgarités (fuck, shit, bitch, damn, hell, ass, dick). Utilise des MÉTAPHORES.

RÈGLE ABSOLUE: JSON UNIQUEMENT. Zéro texte avant/après. Zéro backtick.
{"title":"...","style":"...","lyrics":"..."}`;
}

async function callAI(provider, model, sys, msg, temp) {
  let url, headers, body;
  if (provider === 'claude') {
    url = GATEWAY_URL + '/api/claude';
    headers = { 'Authorization': 'Bearer ' + GW_SECRET, 'Content-Type': 'application/json' };
    body = JSON.stringify({ model, max_tokens: 1500, temperature: temp, system: sys, messages: [{ role: 'user', content: msg }] });
  } else if (provider === 'gemini') {
    url = GATEWAY_URL + '/api/gemini';
    headers = { 'Authorization': 'Bearer ' + GW_SECRET, 'Content-Type': 'application/json' };
    body = JSON.stringify({ model, contents: [{ role: 'user', parts: [{ text: sys + '\n\n' + msg }] }], generationConfig: { temperature: temp, maxOutputTokens: 1500 } });
  } else {
    url = GATEWAY_URL + '/api/openai';
    headers = { 'Authorization': 'Bearer ' + GW_SECRET, 'Content-Type': 'application/json' };
    body = JSON.stringify({ model, max_tokens: 1500, temperature: temp, messages: [{ role: 'system', content: sys }, { role: 'user', content: msg }] });
  }
  const r = await fetch(url, { method: 'POST', headers, body });
  if (!r.ok) throw new Error(`API ${r.status}: ${(await r.text()).substring(0, 200)}`);
  const d = await r.json();
  if (provider === 'claude') return (d.content || [])[0]?.text || '';
  if (provider === 'gemini') return d.candidates?.[0]?.content?.parts?.[0]?.text || '';
  return d.choices?.[0]?.message?.content || '';
}

function analyze(result) {
  const checks = [];
  // Style length
  checks.push(result.style.length <= 200 ? `✅ Style ${result.style.length}c` : `❌ Style ${result.style.length}c TROP LONG`);
  // BPM
  checks.push(/\d+\s*BPM/i.test(result.style) ? '✅ BPM' : '⚠️ No BPM');
  // Tonality
  checks.push(/[A-G][#b]?\s*-?\s*(Major|Minor)/i.test(result.style) ? '✅ Tonalité' : '⚠️ No tonalité');
  // Vocal
  checks.push(/(vocal|voice|tenor|soprano|baritone|breathy|raspy|falsetto)/i.test(result.style) ? '✅ Voix' : '⚠️ No voix');
  // Front-loading
  const first30 = result.style.substring(0, 30).toLowerCase();
  const genreWords = ['pop', 'rock', 'hip-hop', 'trap', 'house', 'techno', 'ambient', 'folk', 'jazz', 'r&b', 'metal', 'synthwave', 'lo-fi', 'indie', 'electro', 'soul', 'funk', 'edm', 'k-pop', 'drill', 'phonk', 'dark', 'melodic', 'alternative', 'neo', 'synth'];
  checks.push(genreWords.some(g => first30.includes(g)) ? '✅ Front-load' : '⚠️ Genre pas en tête');
  // Negative prompting
  if (/\bno\s+\w/i.test(result.style)) checks.push('✅ Neg prompt');
  // Banned words
  if (result.lyrics && BANNED.test(result.lyrics)) checks.push('❌ MOT INTERDIT: ' + result.lyrics.match(BANNED)[0]);
  else checks.push('✅ Clean');
  // Structure
  if (result.lyrics) {
    const hasV = /\[Verse/i.test(result.lyrics);
    const hasC = /\[Chorus/i.test(result.lyrics);
    const hasB = /\[Bridge/i.test(result.lyrics);
    const hasI = /\[Intro/i.test(result.lyrics);
    const n = [hasV, hasC, hasB, hasI].filter(Boolean).length;
    checks.push(n >= 3 ? `✅ Structure ${n}/4` : n >= 2 ? `⚠️ Structure ${n}/4` : `❌ Structure ${n}/4`);
    const lines = result.lyrics.split('\n').filter(l => l.trim()).length;
    checks.push(lines >= 20 && lines <= 55 ? `✅ ${lines} lignes` : `⚠️ ${lines} lignes`);
  }
  return checks;
}

async function main() {
  console.log('🎹 SUNO PROMPT BATCH TEST');
  console.log(`${PROVIDERS.length} providers × ${MODES.length} modes × ${ITERATIONS} iter = ${PROVIDERS.length * MODES.length * ITERATIONS} tests\n`);

  const results = [];
  let totalSuccess = 0, totalFail = 0;

  for (const prov of PROVIDERS) {
    console.log(`\n${'═'.repeat(60)}`);
    console.log(`📡 ${prov.name} (${prov.model})`);
    console.log('═'.repeat(60));

    for (const mode of MODES) {
      for (let i = 0; i < ITERATIONS; i++) {
        const t0 = Date.now();
        const label = `[${prov.name}] ${mode} #${i + 1}`;
        try {
          const sys = buildPrompt(mode);
          const msg = `Génère un prompt Suno v5. Mode: ${mode}.${mode === 'artist' ? ' Artiste: ' + TEST_ARTIST : ''}`;
          const temp = mode === 'random' ? 1.0 : mode === 'artist' ? 0.75 : 0.85;
          const raw = await callAI(prov.provider, prov.model, sys, msg, temp);
          const cleaned = raw.replace(/```json\s*/gi, '').replace(/```\s*/g, '').trim();
          const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
          if (!jsonMatch) throw new Error('No JSON in response');
          const result = JSON.parse(jsonMatch[0]);
          if (!result.title || !result.style) throw new Error('Missing title/style');
          const elapsed = Date.now() - t0;
          const checks = analyze(result);
          const score = checks.filter(c => c.startsWith('✅')).length;
          const total = checks.length;
          results.push({ provider: prov.name, mode, iteration: i + 1, title: result.title, style: result.style, lyricsLen: (result.lyrics || '').length, elapsed, score, total, checks, error: null });
          totalSuccess++;
          console.log(`  ${label} — ${elapsed}ms — ${score}/${total} — "${result.title}"`);
          console.log(`    Style: ${result.style.substring(0, 80)}...`);
          checks.filter(c => !c.startsWith('✅')).forEach(c => console.log(`    ${c}`));
        } catch (err) {
          const elapsed = Date.now() - t0;
          results.push({ provider: prov.name, mode, iteration: i + 1, title: null, style: null, elapsed, score: 0, total: 0, checks: [], error: err.message });
          totalFail++;
          console.log(`  ${label} — ❌ ${err.message.substring(0, 100)}`);
        }
        // Rate limit
        await new Promise(r => setTimeout(r, 1500));
      }
    }
  }

  // Summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log('📊 RÉSUMÉ');
  console.log('═'.repeat(60));
  console.log(`Total: ${results.length} | Succès: ${totalSuccess} | Échecs: ${totalFail}\n`);

  // Per-provider summary
  for (const prov of PROVIDERS) {
    const provResults = results.filter(r => r.provider === prov.name && !r.error);
    if (!provResults.length) { console.log(`${prov.name}: AUCUN SUCCÈS`); continue; }
    const avgScore = (provResults.reduce((a, r) => a + r.score / r.total, 0) / provResults.length * 100).toFixed(0);
    const avgTime = Math.round(provResults.reduce((a, r) => a + r.elapsed, 0) / provResults.length);
    const avgStyleLen = Math.round(provResults.reduce((a, r) => a + (r.style || '').length, 0) / provResults.length);
    const banned = provResults.filter(r => r.checks.some(c => c.includes('MOT INTERDIT'))).length;
    const genres = [...new Set(provResults.map(r => (r.style || '').split(',')[0].trim().toLowerCase()))];
    console.log(`${prov.name}:`);
    console.log(`  Score qualité: ${avgScore}% | Temps moyen: ${avgTime}ms | Style moyen: ${avgStyleLen}c`);
    console.log(`  Mots interdits: ${banned}/${provResults.length} | Genres uniques: ${genres.length} (${genres.join(', ')})`);
  }

  // Export
  const fs = require('fs');
  const path = require('path');
  const outFile = path.join(__dirname, 'suno-batch-results-' + new Date().toISOString().slice(0, 10) + '.json');
  fs.writeFileSync(outFile, JSON.stringify(results, null, 2));
  console.log(`\n💾 Résultats exportés: ${outFile}`);
}

main().catch(e => console.error('FATAL:', e));
