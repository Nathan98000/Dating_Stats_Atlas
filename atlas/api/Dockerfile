# Ranking API — single process, cubes in memory, loopback-posture preserved
# in production by the platform's PRIVATE networking (never a public
# address; see docs/deploy.md and D04). Build context: repo root.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY atlas/ ./atlas/

# The build artifact is NOT baked into the image: mount it (volume) or sync
# it at boot, then point BUILD_DIR at it. A new build is a new mount + a
# restart — deploys stay atomic, rollback is a config change.
ENV BUILD_DIR=/data/build
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "atlas.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
