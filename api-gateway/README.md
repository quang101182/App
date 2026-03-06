# api-gateway

Cloudflare Worker v1.0 — Proxy centralisé pour les APIs IA et traduction.

**URL** : `https://api-gateway.quang101182.workers.dev`
**Repo** : `github.com/quang101182` → `App/api-gateway/`

---

## Architecture

```
Client (GitHub Pages app)
  └─ Authorization: Bearer WORKER_SECRET
       └─ POST /api/<service>  →  Cloudflare Worker
                                      ├─ Rate limit check (KV)
                                      ├─ Resolve API key (KV → env secret)
                                      └─ Proxy vers upstream API
```

Les clés API ne transitent jamais côté client. Elles sont stockées dans KV (`GATEWAY_KV`) ou en tant que secrets Wrangler et injectées par le Worker.

---

## 1. Setup

### Prérequis

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) installé et connecté (`wrangler login`)
- KV namespace déjà créé (id : `3c23ec572c86471cbdce68e3ba4fdd1c`)

### Configurer les secrets

```bash
wrangler secret put WORKER_SECRET   # token partagé pour /api/*
wrangler secret put ADMIN_TOKEN     # token admin pour /admin/*
```

Les clés API (Gemini, Groq, etc.) se gèrent via les routes `/admin/keys/set` — pas besoin de les mettre en secret Wrangler (mais c'est supporté en fallback).

### Déployer

```bash
wrangler deploy
```

---

## 2. Routes API

Toutes les routes `POST /api/*` requièrent :

```
Authorization: Bearer <WORKER_SECRET>
Content-Type: application/json
```

**Rate limit** : 20 req/min par IP.

---

### POST /api/gemini/*

Proxy vers `https://generativelanguage.googleapis.com`.

Le sous-chemin après `/api/gemini` est transmis tel quel. Par défaut : `/v1beta/models/gemini-pro:generateContent`.

```bash
# Modèle par défaut (gemini-pro)
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/gemini \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'

# Modèle spécifique
curl -s -X POST "https://api-gateway.quang101182.workers.dev/api/gemini/v1beta/models/gemini-2.0-flash:generateContent" \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

---

### POST /api/groq

Proxy vers `https://api.groq.com/openai/v1/chat/completions`.

Le header `X-Api-Path` surcharge le chemin upstream.

```bash
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/groq \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3-8b-8192","messages":[{"role":"user","content":"Hello"}]}'

# Chemin alternatif (ex: liste des modèles)
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/groq \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "X-Api-Path: /openai/v1/models"
```

---

### POST /api/openai

Proxy vers `https://api.openai.com/v1/chat/completions`.

Le header `X-Api-Path` surcharge le chemin upstream.

```bash
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/openai \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'

# Endpoint alternatif
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/openai \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "X-Api-Path: /v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-3-small","input":"Hello"}'
```

---

### POST /api/deepl

Proxy vers `https://api-free.deepl.com/v2/translate` (compte gratuit).
Header `X-Api-Variant: pro` bascule vers `https://api.deepl.com` (compte pro).

```bash
# Compte gratuit (défaut)
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/deepl \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"text":["Hello world"],"target_lang":"FR"}'

# Compte pro
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/deepl \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "X-Api-Variant: pro" \
  -H "Content-Type: application/json" \
  -d '{"text":["Hello world"],"target_lang":"FR"}'
```

---

### POST /api/assemblyai

Proxy vers `https://api.assemblyai.com/v2/transcript`.

Le header `X-Api-Path` surcharge le chemin upstream.

```bash
# Soumettre une transcription
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/assemblyai \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"audio_url":"https://example.com/audio.mp3"}'

# Récupérer le résultat
curl -s -X POST https://api-gateway.quang101182.workers.dev/api/assemblyai \
  -H "Authorization: Bearer $WORKER_SECRET" \
  -H "X-Api-Path: /v2/transcript/<transcript_id>"
```

---

## 3. Routes Admin

Toutes les routes `POST /admin/*` requièrent :

```
Authorization: Bearer <ADMIN_TOKEN>
Content-Type: application/json
```

**Rate limit** : 10 req/min par IP.

**KNOWN_KEYS** : `GEMINI_KEY`, `GROQ_KEY`, `OPENAI_KEY`, `DEEPL_KEY`, `ASSEMBLYAI_KEY`

---

### POST /admin/keys/list

Retourne l'état de chaque clé (présente ou non, longueur).

```bash
curl -s -X POST https://api-gateway.quang101182.workers.dev/admin/keys/list \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Réponse :
```json
{
  "GEMINI_KEY": "set (39 chars)",
  "GROQ_KEY": "not set",
  "OPENAI_KEY": "set (51 chars)",
  "DEEPL_KEY": "not set",
  "ASSEMBLYAI_KEY": "not set"
}
```

---

### POST /admin/keys/set

Stocke ou met à jour une clé dans KV.

```bash
curl -s -X POST https://api-gateway.quang101182.workers.dev/admin/keys/set \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key":"GEMINI_KEY","value":"AIzaSy..."}'
```

Réponse : `{"ok":true,"key":"GEMINI_KEY"}`

---

### POST /admin/keys/delete

Supprime une clé de KV.

```bash
curl -s -X POST https://api-gateway.quang101182.workers.dev/admin/keys/delete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key":"GROQ_KEY"}'
```

Réponse : `{"ok":true,"key":"GROQ_KEY"}`

---

### POST /admin/keys/status

Pinge chaque API upstream avec la clé configurée pour vérifier qu'elle est valide.

```bash
curl -s -X POST https://api-gateway.quang101182.workers.dev/admin/keys/status \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Réponse :
```json
{
  "statuses": {
    "GEMINI_KEY":     { "ok": true,  "status": 200 },
    "GROQ_KEY":       { "ok": false, "status": "not configured" },
    "OPENAI_KEY":     { "ok": true,  "status": 200 },
    "DEEPL_KEY":      { "ok": true,  "status": 200, "variant": "free" },
    "ASSEMBLYAI_KEY": { "ok": false, "status": 401 }
  }
}
```

---

## 4. Commandes Telegram (via n8n)

Le bot Telegram transmet les commandes `/keys` au Worker via n8n.

| Commande | Action |
|---|---|
| `/keys list` | Affiche l'état de toutes les clés |
| `/keys set GEMINI AIzaSy...` | Stocke ou met à jour GEMINI_KEY |
| `/keys add GROQ gsk_...` | Alias de `set` |
| `/keys delete OPENAI` | Supprime OPENAI_KEY |
| `/keys status` | Pinge les APIs et affiche les statuts |

---

## 5. Rate Limits

| Route | Limite | Fenêtre |
|---|---|---|
| `/api/*` | 20 req/min | par IP |
| `/admin/*` | 10 req/min | par IP |

Dépassement → `429 Too Many Requests` + header `Retry-After: 60`.

Les compteurs sont stockés dans KV avec TTL 70s.

---

## 6. Intégration depuis une app GitHub Pages

```js
const GATEWAY = 'https://api-gateway.quang101182.workers.dev';
const TOKEN   = 'your_worker_secret'; // ne pas exposer en clair en prod

// Appel Gemini
async function callGemini(prompt) {
  const res = await fetch(`${GATEWAY}/api/gemini/v1beta/models/gemini-2.0-flash:generateContent`, {
    method : 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type' : 'application/json',
    },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
  });
  return res.json();
}

// Appel Groq
async function callGroq(messages) {
  const res = await fetch(`${GATEWAY}/api/groq`, {
    method : 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type' : 'application/json',
    },
    body: JSON.stringify({ model: 'llama3-8b-8192', messages }),
  });
  return res.json();
}

// Traduction DeepL
async function translate(text, targetLang = 'FR') {
  const res = await fetch(`${GATEWAY}/api/deepl`, {
    method : 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type' : 'application/json',
    },
    body: JSON.stringify({ text: [text], target_lang: targetLang }),
  });
  return res.json();
}
```

> **Note sécurité** : Pour les apps publiques GitHub Pages, stocker `WORKER_SECRET` dans une variable d'environnement de build ou utiliser un backend intermédiaire. Ne jamais le mettre en dur dans le code source public.

---

## 7. Debugging

### Logs en temps réel

```bash
wrangler tail
```

### Health check

```bash
curl https://api-gateway.quang101182.workers.dev/health
```

Réponse : `{"ok":true,"version":"1.0","ts":1709123456789}`

### Codes d'erreur courants

| Code | Cause |
|---|---|
| `401` | `Authorization` header manquant ou token invalide |
| `429` | Rate limit atteint — attendre 60s |
| `503` | Clé API non configurée (KV vide + pas de secret Wrangler) |
| `503` | `WORKER_SECRET` ou `ADMIN_TOKEN` non défini dans l'env |

### Résolution de clé

Le Worker résout les clés dans cet ordre :
1. KV namespace `GATEWAY_KV` (clé `key:<NAME>`) — gérable via `/admin/keys/set`
2. Secret Wrangler (`env.<NAME>`) — fallback statique

---

## Structure du projet

```
api-gateway/
├── src/
│   └── index.js        # Worker principal (v1.0)
└── wrangler.toml       # Config Cloudflare (KV binding, compatibility flags)
```
