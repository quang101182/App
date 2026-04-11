# PromoClip FFmpeg Server — Dockerfile
# Build: node:20-alpine + ffmpeg (apk)
# Version: 1.0.0 — split from subwhisper-ffmpeg

# ---- Builder stage ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# ---- Runtime stage ----
FROM node:20-alpine AS runtime

# ffmpeg + fontconfig + DejaVu pour rendu ASS subtitles
RUN apk add --no-cache ffmpeg fontconfig ttf-dejavu && fc-cache -fv

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodeuser -u 1001 -G nodejs

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY src/ ./src/
COPY package.json ./

RUN mkdir -p /app/tmp && chown -R nodeuser:nodejs /app

USER nodeuser

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "src/server.js"]
