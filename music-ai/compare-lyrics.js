// Compare lyrics quality side-by-side — same prompt, 3 providers
const GATEWAY_URL = 'https://api-gateway.quang101182.workers.dev';
const GW_SECRET = '333a33b16f8cab5aec61eb5806eeaee332a50e1172ad1b3e3d710b3d84b9cc7b';

const PROVIDERS = [
  { name: 'Claude Sonnet', provider: 'claude', model: 'claude-sonnet-4-6' },
  { name: 'Claude Haiku', provider: 'claude', model: 'claude-haiku-4-5-20251001' },
  { name: 'GPT-4o-mini', provider: 'openai', model: 'gpt-4o-mini' },
];

const PROMPT = `Tu es un expert mondial en production musicale et en Suno AI v5. Tu génères des prompts OPTIMISÉS pour Suno v5.

MODE ARTISTE: génère un prompt qui sonne COMME The Weeknd.
Analyse son style : R&B sombre, falsetto aérien, production synthwave/80s, basses profondes, ambiance nocturne, mélancolie sensuelle.
Traduis ces caractéristiques en tags Suno v5 et en lyrics qui capturent cette ESSENCE.

LANGUE DES LYRICS: anglais.

Tu dois retourner un JSON avec EXACTEMENT ces 3 champs:

1. "title": Titre créatif et évocateur (2-5 mots, max 80 caractères)

2. "style": Tags de style Suno v5 optimisés, séparés par des virgules.
   RÈGLES CRITIQUES STYLE:
   - MAXIMUM 200 caractères
   - FRONT-LOAD: genre + voix d'abord
   - INCLURE: Genre, BPM, tonalité, énergie, textures, voix
   - PROMPTING NÉGATIF: "no [element]" pour exclure
   EXEMPLE: "Dark R&B, breathy male falsetto, 92 BPM, A-Minor, 808 bass, lush synth pads, cinematic, no autotune"

3. "lyrics": Paroles structurées avec tags Suno v5.
   STRUCTURE: [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Outro]
   TAGS OPTIONNELS: [Whispered], [Falsetto], [Harmonies], [Ad-libs], [Drop], [Build], [Fade Out]
   FORMAT: 30-40 lignes, refrain HOOK mémorable, images sensorielles fortes
   ⚠️ TERMES INTERDITS SUNO: ZÉRO jurons/vulgarités. Métaphores uniquement.

RÈGLE ABSOLUE: JSON UNIQUEMENT. Zéro texte avant/après.
{"title":"...","style":"...","lyrics":"..."}`;

async function callAI(provider, model, sys, msg, temp) {
  let url, headers, body;
  if (provider === 'claude') {
    url = GATEWAY_URL + '/api/claude';
    headers = { 'Authorization': 'Bearer ' + GW_SECRET, 'Content-Type': 'application/json' };
    body = JSON.stringify({ model, max_tokens: 2000, temperature: temp, system: sys, messages: [{ role: 'user', content: msg }] });
  } else {
    url = GATEWAY_URL + '/api/openai';
    headers = { 'Authorization': 'Bearer ' + GW_SECRET, 'Content-Type': 'application/json' };
    body = JSON.stringify({ model, max_tokens: 2000, temperature: temp, messages: [{ role: 'system', content: sys }, { role: 'user', content: msg }] });
  }
  const r = await fetch(url, { method: 'POST', headers, body });
  if (!r.ok) throw new Error(`API ${r.status}`);
  const d = await r.json();
  if (provider === 'claude') return (d.content || [])[0]?.text || '';
  return d.choices?.[0]?.message?.content || '';
}

async function main() {
  console.log('🎹 COMPARAISON LYRICS — The Weeknd style — 3 providers\n');

  for (const prov of PROVIDERS) {
    console.log(`\n${'═'.repeat(70)}`);
    console.log(`📡 ${prov.name} (${prov.model})`);
    console.log('═'.repeat(70));

    const t0 = Date.now();
    try {
      const raw = await callAI(prov.provider, prov.model, PROMPT, 'Génère un prompt Suno v5 style The Weeknd.', 0.85);
      const cleaned = raw.replace(/```json\s*/gi, '').replace(/```\s*/g, '').trim();
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      const result = JSON.parse(jsonMatch[0]);
      const elapsed = Date.now() - t0;

      console.log(`⏱️  ${elapsed}ms`);
      console.log(`\n🎵 TITRE: ${result.title}`);
      console.log(`\n🎨 STYLE (${result.style.length} chars):`);
      console.log(`   ${result.style}`);
      console.log(`\n✍️  LYRICS (${result.lyrics.split('\n').filter(l=>l.trim()).length} lignes):`);
      console.log('─'.repeat(50));
      console.log(result.lyrics);
      console.log('─'.repeat(50));
    } catch (err) {
      console.log(`❌ ${err.message}`);
    }

    await new Promise(r => setTimeout(r, 2000));
  }
}

main().catch(e => console.error('FATAL:', e));
