# Etapa 1: gera o site a partir de site/ e reprova o build se alguma página depender da internet
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json site.config.json ./
COPY tools ./tools
COPY vendor ./vendor
COPY site ./site
RUN node tools/build/build-site.mjs && node tools/build/check-offline.mjs

# Etapa 2: só o resultado, servido pelo Caddy
FROM caddy:2.8-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
