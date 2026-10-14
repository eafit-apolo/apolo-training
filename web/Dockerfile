# syntax=docker/dockerfile:1
# Imagen de la web: build de Angular con Node y resultado servido por nginx sin
# root. En producción, el nginx de borde (deploy/) publica el 443 y reparte
# /api a la API y el resto a este contenedor.

FROM node:24-alpine AS build
ENV NG_CLI_ANALYTICS=false
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
RUN npx ng build

FROM nginxinc/nginx-unprivileged:1.30-alpine
ARG VERSION=dev
LABEL org.opencontainers.image.title="apolo-training-web" \
      org.opencontainers.image.version="${VERSION}"
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/web/browser /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
