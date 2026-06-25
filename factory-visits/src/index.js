/**
 * factory-visits — Ebook Funnel Factory : compteur de visites/événements ISOLÉ
 * URL : https://factory-visits.quang101182.workers.dev
 *
 * Remplace le comptage /api/visit de api-gateway-pro pour les niches Factory,
 * avec une vraie défense anti-bot CÔTÉ SERVEUR. L'ancien compteur ne filtrait
 * que par User-Agent + une dédup sessionStorage CLIENT → contournable par un
 * headless furtif. Résultat : 235 visites cumulées quasi toutes non-humaines
 * (0 téléchargement sur 235 = preuve du bruit bot, verdict forensic 22/06/2026).
 *
 * Worker ISOLÉ : ne touche PAS api-gateway-pro (revenue prod). KV neuf → on
 * repart de 0 et on mesure le VRAI trafic humain à partir de maintenant.
 *
 * Contrat (IDENTIQUE à l'ancien, pour ne rien casser côté landings/dashboard) :
 *   GET  /api/visit?page=<slug>  → { page, total, today }   (lecture pure)
 *   POST /api/visit?page=<slug>  → { page, total, today }   (incrément si humain)
 *   GET  /health                 → { status, version, service }
 *
 * Trois barrières server-side (POST uniquement) :
 *   1. Denylist User-Agent (isBotUA) — NE matche PAS le webview TikTok (cibles).
 *   2. Denylist ASN datacenter (request.cf.asOrganization) — tue les headless cloud.
 *   3. Empreinte hash(IP+UA) en KV, TTL 24h — pas de double comptage.
 *
 * Binding KV : FACTORY_VISITS_KV (namespace dédié, vierge).
 */

const VERSION = '1.0.0';

// Slugs autorisés (whitelist stricte — pas de création de compteur arbitraire).
const SLUGS = new Set([
  'tuc', 'tuc-buy', 'tuc-dl',
  'aea', 'aea-buy', 'aea-dl',
  'lpp', 'lpp-buy', 'lpp-dl',
]);

// ── Barrière 1 : denylist User-Agent ────────────────────────────────────────
// Repris à l'identique de api-gateway-pro. CRITIQUE : ne doit PAS matcher le
// webview TikTok (BytedanceWebview / musical_ly / trill) = nos vrais users.
const BOT_UA_RE = /bot\b|crawl|spider|slurp|scrape|headless|phantom|puppeteer|playwright|selenium|python|curl|wget|libwww|httpclient|okhttp|go-http|java\/|axios|node-fetch|bytespider|gptbot|claudebot|ccbot|amazonbot|applebot|googlebot|bingbot|baiduspider|semrush|ahrefs|mj12|dotbot|petalbot|dataforseo|facebookexternalhit|telegrambot|whatsapp|discordbot|slackbot|embedly|skypeuripreview|censys|masscan|zgrab|expanse/i;
function isBotUA(ua) {
  if (!ua) return true; // UA vide = scanner/bot
  return BOT_UA_RE.test(ua);
}

// ── Barrière 2 : denylist ASN datacenter / hébergeur ────────────────────────
// Cible les crawlers headless tournant en cloud (l'IP source ne ment pas).
// Volontairement SANS Cloudflare (WARP = vrais users) ni carriers mobiles
// (Orange / SFR / Free / Bouygues = webview TikTok réel → doivent compter).
const DC_ORG_RE = /amazon|aws|google|microsoft|azure|oracle\b|ovh|hetzner|digitalocean|linode|akamai|vultr|scaleway|contabo|leaseweb|choopa|datacamp|\bm247\b|cogent|gcore|tencent|alibaba|aliyun|huawei/i;
function isDatacenterCf(cf) {
  if (!cf) return false; // pas d'info CF (dev local) → ne pas filtrer ici
  const org = String(cf.asOrganization || '');
  if (!org) return false;
  return DC_ORG_RE.test(org);
}

// ── Barrière 3 : empreinte hash(IP+UA) ──────────────────────────────────────
async function fingerprint(ip, ua) {
  const data = new TextEncoder().encode(`${ip}|${ua}|factory-visits-v1`);
  const buf = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(buf)].slice(0, 12)
    .map((b) => b.toString(16).padStart(2, '0')).join('');
}

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    if (method === 'OPTIONS') return new Response(null, { headers: CORS });

    if (method === 'GET' && path === '/health') {
      return json({ status: 'ok', version: VERSION, service: 'factory-visits' });
    }

    if (path === '/api/visit') {
      const page = url.searchParams.get('page') || '';
      if (!SLUGS.has(page)) return json({ error: 'unknown_page', page }, 400);

      const today = new Date().toISOString().slice(0, 10);
      const prefix = `stats:visits:${page}`;
      const [totalRaw, todayRaw] = await Promise.all([
        env.FACTORY_VISITS_KV.get(`${prefix}:total`),
        env.FACTORY_VISITS_KV.get(`${prefix}:${today}`),
      ]);
      let total = parseInt(totalRaw) || 0;
      let todayCount = parseInt(todayRaw) || 0;

      if (method === 'POST') {
        const ua = request.headers.get('user-agent') || '';
        const ip = request.headers.get('CF-Connecting-IP') || '';

        let counted = false;
        if (!isBotUA(ua) && !isDatacenterCf(request.cf)) {
          // dédup empreinte 24h : une même IP+UA ne compte qu'une fois / slug / 24h
          const fp = await fingerprint(ip, ua);
          const seenKey = `seen:${page}:${fp}`;
          const seen = await env.FACTORY_VISITS_KV.get(seenKey);
          if (!seen) {
            await env.FACTORY_VISITS_KV.put(seenKey, '1', { expirationTtl: 86400 });
            counted = true;
          }
        }

        if (counted) {
          total++;
          todayCount++;
          ctx.waitUntil(Promise.all([
            env.FACTORY_VISITS_KV.put(`${prefix}:total`, String(total)),
            env.FACTORY_VISITS_KV.put(`${prefix}:${today}`, String(todayCount), { expirationTtl: 90 * 86400 }),
          ]));
        }
      }
      return json({ page, total, today: todayCount });
    }

    return json({ error: 'not_found' }, 404);
  },
};
