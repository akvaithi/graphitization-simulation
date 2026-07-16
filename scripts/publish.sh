#!/usr/bin/env bash
# Build the data-baked dashboard image and push it to the PRIVATE GHCR package.
# Run from a machine that HAS DATA/ present (dev box / lab store), not from CI.
#
#   ./scripts/publish.sh
#
# Auth: uses the GitHub CLI token if available; needs the `write:packages` scope
# (run `gh auth refresh -s write:packages,read:packages` once if the push is
# denied), or set GHCR_TOKEN to a PAT with write:packages.
set -euo pipefail

IMAGE="ghcr.io/akvaithi/graphitization-simulation:latest"
USER="akvaithi"
cd "$(dirname "$0")/.."

if [ ! -f "DATA/Yield Data Measurements.xlsx" ]; then
  echo "ERROR: DATA/ not found — this image bakes the real dataset in. Add DATA/ first." >&2
  exit 1
fi

TOKEN="${GHCR_TOKEN:-$(gh auth token)}"
echo "$TOKEN" | docker login ghcr.io -u "$USER" --password-stdin

docker build -t "$IMAGE" .
docker push "$IMAGE"

echo "Pushed $IMAGE (private). On the server: docker compose pull && docker compose up -d"
