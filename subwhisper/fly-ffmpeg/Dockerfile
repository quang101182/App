# SubWhisper FFmpeg Server — Dockerfile
# Build: node:20-alpine + ffmpeg (apk)
# Version: 1.0.0

# ---- Builder stage ----
FROM node:20-alpine AS builder

WORKDIR /app

# Copier uniquement les fichiers de dépendances d'abord (cache layer)
COPY package.json ./

# Installer les dépendances de production uniquement
RUN npm install --omit=dev --no-audit --no-fund

# ---- Runtime stage ----
FROM node:20-alpine AS runtime

# Installer FFmpeg depuis les dépôts Alpine
# ffmpeg inclut les codecs audio nécessaires (pcm_s16le, wav)
RUN apk add --no-cache ffmpeg

# Créer un utilisateur non-root pour la sécurité
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodeuser -u 1001 -G nodejs

WORKDIR /app

# Copier les node_modules depuis le builder
COPY --from=builder /app/node_modules ./node_modules

# Copier le code source
COPY src/ ./src/
COPY package.json ./

# Créer un dossier tmp pour les fichiers temporaires (accessible par nodeuser)
RUN mkdir -p /app/tmp && chown -R nodeuser:nodejs /app

USER nodeuser

# Variables d'environnement par défaut
ENV NODE_ENV=production
ENV PORT=3000

# Exposer le port
EXPOSE 3000

# Health check intégré (Fly.io peut aussi le faire via fly.toml)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

# Commande de démarrage
CMD ["node", "src/server.js"]
