# ── Dependencies ──────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --omit=dev=false

# ── Build ─────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# BACKEND_URL is read by next.config.js rewrites() at BUILD time (Next.js
# freezes it into the built config), so it must be a build arg. docker
# compose passes .env values through as build args automatically.
ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

# ── Runner ────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Don't run as root.
RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

# Standalone output: self-contained server.js (no node_modules install needed).
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
