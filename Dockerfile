# --- stage 1: build the self-contained dashboard HTML ---------------------
# Bakes the real dataset + the engine-fit into the page, so the resulting image
# is self-contained (the server just pulls & runs; no DATA needed at runtime).
# DATA/ is gitignored, so build from a checkout that has it (e.g. your dev
# machine / lab store), then push to the PRIVATE GHCR package. CI cannot build
# this image because the repo has no DATA — publishing is a local/scripted step.
FROM python:3.12-slim AS build
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole build context (.dockerignore excludes .git/.venv/outputs/dist/
# tests/native/windows/docs/SIMULATION_HANDOFF.md, but KEEPS DATA/).
COPY . .
RUN test -f "DATA/Yield Data Measurements.xlsx" || { \
      echo "ERROR: DATA/ is missing from the build context."; \
      echo "This image bakes your real dataset into the dashboard, so place DATA/"; \
      echo "(the .xy scans + 'Yield Data Measurements.xlsx') in the repo before"; \
      echo "building. See the README 'Docker / deploy on your server' section."; \
      exit 1; }

# regenerate the fit + ground truth, then render the dashboard, so the image is
# always built from the current model rather than a stale committed artifact.
RUN python -m sim fit && python dashboard/build.py

# --- stage 2: serve the static page with nginx ----------------------------
FROM nginx:1.27-alpine AS serve
COPY --from=build /app/dashboard/dist/index.html /usr/share/nginx/html/index.html
COPY dashboard/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK CMD wget -q --spider http://localhost/ || exit 1
