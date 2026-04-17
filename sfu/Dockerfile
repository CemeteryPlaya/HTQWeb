# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Mediasoup SFU Server
#
# Multi-stage build:
# 1. Build TypeScript → JavaScript + compile mediasoup C++ worker
# 2. Production image with only compiled JS + runtime dependencies
#
# Mediasoup requires:
# - Python 3 (for node-gyp)
# - GCC/G++ (for C++ worker compilation)
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Build ──
FROM node:20-bullseye AS builder

# Mediasoup native dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies (layer caching)
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts=false

# Copy source and build
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

# ── Stage 2: Production ──
FROM node:20-bullseye-slim

# Runtime dependencies for Mediasoup C++ worker
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built artifacts and production dependencies
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Mediasoup worker binary
COPY --from=builder /app/node_modules/mediasoup/worker/out/Release/mediasoup-worker \
     ./node_modules/mediasoup/worker/out/Release/

# Environment
ENV NODE_ENV=production
ENV SFU_PORT=4443

# Signaling port
EXPOSE 4443
# WebRTC media port (single-port mode via WebRtcServer)
EXPOSE 44444/udp
EXPOSE 44444/tcp

CMD ["node", "dist/server.js"]
