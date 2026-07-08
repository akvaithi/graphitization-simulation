# --- stage 1: build the self-contained dashboard HTML ---------------------
# Needs DATA/ present in the build context (it bakes the real dataset + the
# engine-fit parameters into the page). DATA/ is gitignored, so build from a
# working checkout that has it, not from a fresh clone.
FROM python:3.12-slim AS build
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole build context (.dockerignore excludes .git/.venv/outputs/dist/
# tests/native/windows/docs/SIMULATION_HANDOFF.md). DATA/ is gitignored so it is
# only present when the server operator has placed it here; the guard fails with a
# clear message if it is missing, since the dashboard bakes the real dataset in.
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
