# syntax=docker/dockerfile:1

# Vite builds and serves the SPA (preview server) and proxies /auth + /ws to
# the backend service on the compose network.
FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV VITE_PROXY_TARGET=http://backend:8000

EXPOSE 80

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "80"]
