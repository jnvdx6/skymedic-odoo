#!/bin/bash
set -euo pipefail

VERSION=${1:-$(date +%Y%m%d_%H%M%S)}
TAG="odoo-skymedic:${VERSION}"

echo "================================================"
echo "  Building $TAG"
echo "================================================"

cd /opt/odoo/docker

echo "[1/4] Syncing Odoo source..."
rsync -a --delete --exclude='.git' /opt/odoo/src/odoo/ ./odoo-src/

echo "[2/4] Syncing enterprise addons..."
rsync -a --delete /opt/odoo/src/odoo/odoo/enterprise/ ./enterprise/

echo "[3/4] Syncing custom addons..."
rsync -a --delete /opt/odoo/src/custom-addons/ ./custom-addons/

echo "[4/4] Building Docker image..."
docker build -t "$TAG" -t "odoo-skymedic:latest" .

echo ""
echo "================================================"
echo "  Image built: $TAG"
echo "================================================"
docker images odoo-skymedic --format "  {{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
