# Frontend Next.js — multi-stage, output standalone
FROM node:20-slim AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:20-slim AS builder
WORKDIR /app
RUN corepack enable && apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Aset MediaPipe (WASM + model) di-host dari public/.
RUN bash -lc 'cp -f node_modules/@mediapipe/tasks-vision/wasm/* public/mediapipe/wasm/ 2>/dev/null || true; \
  mkdir -p public/mediapipe/models; \
  [ -f public/mediapipe/models/hand_landmarker.task ] || \
  curl -sSL -o public/mediapipe/models/hand_landmarker.task \
    https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
ENV NEXT_TELEMETRY_DISABLED=1
# URL backend di-bake ke bundle browser (client-side). Override saat build:
#   docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.com ...
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
RUN pnpm build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
# server.js standalone tidak menyalin public & static secara default.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
