# Build from this directory:  docker build apps/web
FROM node:24-slim AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

# nginx serves the SPA and is the single entry point behind the Cloudflare
# tunnel: it routes /api/copilotkit to the runtime and /api to the API.
FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/fuse /usr/share/nginx/html
EXPOSE 8080
