# VoiceBox — Spécification technique complète
## Bot Telegram de transcription vocale IA
### Version: 0.1.0 (pré-dev) — 2026-03-14

---

## 1. Architecture

```
User Telegram
    │
    ▼ (envoie vocal OGG/OPUS)
Telegram Bot API
    │ webhook POST + header X-Telegram-Bot-Api-Secret-Token
    ▼
bot.js (Fly.io, app "voicebox-bot", région cdg)
    │
    ├─► Telegram getFile → télécharge audio OGG (< 20 MB)
    ├─► api-gateway /api/groq → Whisper transcription (OGG accepté nativement)
    ├─► api-gateway /api/gemini → résumé + traduction (optionnel)
    │
    ├─► SQLite /data/bot.db (quotas, users, logs)
    │
    └─► Répond dans le chat Telegram
```

### Isolation totale
- **Nouveau bot Telegram** : token dédié via @BotFather
- **Nouvelle app Fly.io** : `voicebox-bot` (séparée de `subwhisper-ffmpeg`)
- **Gateway existant** : appels en lecture seule vers `/api/groq` et `/api/gemini`
- **Aucune modif** sur api-gateway, n8n, SubWhisper, VoxSplit, VideoGrab

---

## 2. Faisabilité vérifiée

| Composant | Statut | Détails |
|---|---|---|
| Telegram reçoit audio OGG/OPUS | ✅ OK | Format natif des vocaux Telegram |
| Download fichier vocal | ✅ OK | `getFile` API, max 20 MB (vocaux = 60-100 KB/min) |
| Webhook sécurisé | ✅ OK | `secret_token` natif Telegram, header `X-Telegram-Bot-Api-Secret-Token` |
| User ID stable | ✅ OK | `user.id` = entier 64-bit permanent, jamais change |
| Rate limits Telegram | ✅ OK | ~30 msg/s broadcast, 1:1 = aucun problème |
| Groq Whisper accepte OGG | ✅ OK | Formats: flac, mp3, mp4, ogg, wav, webm — zéro conversion |
| Groq free tier | ⚠️ Limité | 20 RPM, 2000 RPD, 8h audio/jour — suffisant pour MVP |
| LemonSqueezy HMAC | ✅ OK | `X-Signature` = HMAC-SHA256(secret, body) |
| Fly.io + SQLite | ✅ OK | Volume persistant, single-instance, snapshots auto |

### Limites Groq (à surveiller)
- **Free tier** : 20 requêtes/min, 2000/jour, 8h audio/jour
- **Dev tier** : $0.04/h audio (whisper-large-v3-turbo) — passer si > ~200 users actifs/jour
- **Facturation minimum** : 10 secondes par requête

---

## 3. Sécurité & Anti-abus

### 3.1 Webhook Telegram
- `setWebhook` avec `secret_token` (256 chars, [A-Za-z0-9_-])
- Chaque requête vérifiée via header `X-Telegram-Bot-Api-Secret-Token`
- Mismatch → HTTP 403

### 3.2 Paiement (LemonSqueezy)
- Zéro donnée bancaire côté bot
- Webhook signé HMAC-SHA256 : header `X-Signature`
- Vérification constant-time (`crypto.timingSafeEqual`)
- Events gérés : `subscription_created`, `subscription_expired`, `subscription_payment_failed`

### 3.3 Quotas & Rate limiting
| Protection | Free | Pro (€3/mois) |
|---|---|---|
| Vocaux/jour | 5 | Illimité |
| Durée max/vocal | 5 min | 60 min |
| Traduction | ❌ | ✅ |
| Résumé IA | ❌ | ✅ |
| Rate limit | 1 req/10s | 1 req/5s |

### 3.4 Anti-contournement
- Tracking par `user.id` (pas `chat.id`) — stable même si multi-conversations
- `user.id` = entier 64-bit, stocker en INTEGER SQLite (pas 32-bit)
- Acceptation pragmatique : coût d'un vocal gratuit ≈ $0 (Groq free), pas critique
- Blacklist manuelle si abus flagrant

### 3.5 Protection infrastructure
| Menace | Protection |
|---|---|
| Spam massif | Rate limit par user + queue FIFO |
| Fichiers malveillants | Audio envoyé à Groq API, jamais exécuté localement |
| Token bot volé | `fly secrets set BOT_TOKEN=xxx` (jamais dans le code) |
| Webhook forgé | Vérification `secret_token` sur chaque requête |
| Abus coûteux Groq | Circuit breaker : compteur global, couper si > seuil/jour |
| Perte données SQLite | Snapshots Fly auto (1x/jour) + backup périodique optionnel |

---

## 4. Stack technique

### 4.1 Fichiers
```
App/voicebox/
├── bot.js              ← Serveur Express + logique bot
├── db.js               ← SQLite wrapper (better-sqlite3)
├── package.json
├── Dockerfile
├── fly.toml
└── SPEC.md             ← Ce fichier
```

### 4.2 Dépendances
```json
{
  "express": "^4.x",
  "better-sqlite3": "^11.x",
  "node-fetch": "^3.x"
}
```
- Pas de framework bot (grammy/telegraf) → appels HTTP directs = contrôle total, zéro dépendance lourde

### 4.3 Base de données SQLite
```sql
CREATE TABLE users (
  telegram_id INTEGER PRIMARY KEY,    -- user.id (64-bit)
  username TEXT,
  first_name TEXT,
  plan TEXT DEFAULT 'free',           -- 'free' | 'pro'
  daily_count INTEGER DEFAULT 0,
  last_reset TEXT,                    -- ISO date 'YYYY-MM-DD'
  banned INTEGER DEFAULT 0,
  lemon_customer_id TEXT,
  lemon_subscription_id TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE usage_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id INTEGER,
  timestamp TEXT DEFAULT (datetime('now')),
  duration_sec INTEGER,
  type TEXT,                          -- 'transcribe' | 'translate' | 'summary'
  status TEXT,                        -- 'ok' | 'error'
  FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);
```

### 4.4 Fly.io config
```toml
app = "voicebox-bot"
primary_region = "cdg"

[build]
  dockerfile = "Dockerfile"

[mounts]
  source = "data"
  destination = "/data"

[http_service]
  internal_port = 3000
  force_https = true

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

### 4.5 Secrets Fly.io
```
BOT_TOKEN          → token @BotFather
WEBHOOK_SECRET     → secret_token pour vérification Telegram
GATEWAY_URL        → https://api-gateway.quang101182.workers.dev
GATEWAY_KEY        → clé gateway existante
LEMON_WEBHOOK_SECRET → secret LemonSqueezy pour HMAC
```

---

## 5. Flux détaillés

### 5.1 Réception d'un vocal
```
1. Telegram POST /webhook → vérifier secret_token header
2. Extraire message.voice (file_id, duration, user.id)
3. Upsert user dans SQLite (créer si nouveau)
4. Vérifier quota : daily_count < limite du plan
5. Vérifier durée : duration < limite du plan
6. Rate limit : last_request_time > cooldown
7. Si OK → télécharger audio via getFile
8. Envoyer à gateway /api/groq (Whisper)
9. Répondre avec transcription
10. Logger dans usage_logs, incrémenter daily_count
```

### 5.2 Commandes bot
| Commande | Action |
|---|---|
| `/start` | Message d'accueil + instructions |
| `/plan` | Afficher plan actuel + usage du jour |
| `/pro` | Lien de paiement LemonSqueezy |
| `/lang XX` | Changer langue de traduction (Pro) |
| `/help` | Aide |

### 5.3 Paiement
```
1. User tape /pro → bot envoie lien LemonSqueezy avec ?checkout[custom][telegram_id]=XXX
2. User paie sur LemonSqueezy
3. Webhook POST /lemon → vérifier HMAC signature
4. Extraire telegram_id du custom field
5. UPDATE users SET plan='pro' WHERE telegram_id=XXX
6. Bot envoie message de confirmation au user
```

### 5.4 Expiration/Échec paiement
```
1. Webhook event: subscription_expired ou subscription_payment_failed
2. UPDATE users SET plan='free' WHERE lemon_subscription_id=XXX
3. Bot notifie le user
```

---

## 6. Étapes de développement

### Phase 1 — MVP (transcription seule)
1. [ ] Créer bot via @BotFather → récupérer token
2. [ ] Coder bot.js (webhook, getFile, appel Groq, réponse)
3. [ ] Coder db.js (SQLite, users, quotas)
4. [ ] Dockerfile + fly.toml
5. [ ] Déployer sur Fly.io (`fly launch`)
6. [ ] Configurer webhook (`setWebhook` avec secret_token)
7. [ ] Tester : envoyer vocal → recevoir transcription

### Phase 2 — Traduction + Résumé (Pro)
8. [ ] Ajouter appel gateway /api/gemini pour résumé
9. [ ] Ajouter traduction via gateway /api/gemini
10. [ ] Commandes /lang, /plan
11. [ ] Tester features Pro

### Phase 3 — Monétisation
12. [ ] Configurer produit LemonSqueezy (€3/mois)
13. [ ] Endpoint /lemon pour webhooks paiement
14. [ ] Vérification HMAC
15. [ ] Activation/désactivation Pro automatique
16. [ ] Tester flux paiement complet

### Phase 4 — Polish
17. [ ] Messages multilingues (FR/EN au minimum)
18. [ ] Stats admin (nombre users, usage, revenus)
19. [ ] Circuit breaker Groq (coût monitoring)
20. [ ] Page de présentation (optionnel)

---

## 7. Coûts estimés

| Poste | Coût |
|---|---|
| Fly.io (shared-cpu-1x, 256MB) | ~$0/mois (free tier) ou ~$2/mois |
| Volume 1GB | ~$0.15/mois |
| Groq Whisper (free tier) | $0 (2000 req/jour) |
| Groq Whisper (dev tier) | $0.04/h audio |
| Gemini (free tier) | $0 |
| LemonSqueezy | 5% + $0.50/transaction |
| **Total MVP** | **~$0-2/mois** |

### Seuil de rentabilité
- 1 client Pro (€3/mois) = couvre les frais d'infra
- 10 clients Pro = ~€25/mois net
- 100 clients Pro = ~€250/mois net

---

## 8. Risques identifiés

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Groq change pricing/limite | Moyenne | Haut | Fallback vers AssemblyAI ou Whisper self-hosted |
| Peu d'adoption | Haute | Moyen | Coût quasi-nul, pas de perte |
| Telegram bloque le bot | Faible | Haut | Respecter ToS, pas de spam |
| Abus massif free tier | Faible | Faible | Coût ≈ $0, rate limit suffit |
