# Build from this directory:  docker build services/copilot-runtime
# Node 24 runs the TypeScript source directly (type stripping); no build step.
FROM node:24-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY src src
ENV NODE_ENV=production COPILOTKIT_TELEMETRY_DISABLED=1
USER node
EXPOSE 4000
CMD ["node", "src/server.ts"]
