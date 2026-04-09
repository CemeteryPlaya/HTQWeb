FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# API calls go to relative /api/ — nginx proxies to backend:8000
ARG VITE_API_BASE_URL=/api/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Second stage: just holds the built dist files
FROM alpine:3.20
COPY --from=builder /app/dist /dist
# Copy files into the shared volume mount point on startup
ENTRYPOINT ["sh", "-c", "cp -r /dist/. /html/ && echo 'Frontend dist ready'"]
