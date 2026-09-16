# Next.js frontend — the all-Fly topology's web app (docs/deploy.md).
# Build context: repo root, so docs/methodology.md is available to the
# prebuild content sync.
FROM node:22-slim AS build
WORKDIR /repo/atlas/web
COPY atlas/web/package.json atlas/web/package-lock.json ./
RUN npm ci
COPY atlas/docs/ /repo/atlas/docs/
COPY atlas/web/ ./
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /repo/atlas/web/.next/standalone* ./standalone/
COPY --from=build /repo/atlas/web/.next ./.next
COPY --from=build /repo/atlas/web/node_modules ./node_modules
COPY --from=build /repo/atlas/web/package.json ./
COPY --from=build /repo/atlas/web/content ./content
COPY --from=build /repo/atlas/web/public ./public
# ATLAS_API_URL points at the API's PRIVATE address (http://atlas-api.flycast:8000)
EXPOSE 3000
CMD ["./node_modules/.bin/next", "start", "-p", "3000"]
