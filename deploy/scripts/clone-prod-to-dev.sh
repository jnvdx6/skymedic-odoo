#!/bin/bash
set -euo pipefail

# =============================================
# Clone PRODUCTION -> DEV
# Refreshes dev database with production data
# Usage: ./clone-prod-to-dev.sh
# =============================================

echo "══════════════════════════════════════"
echo "  CLONE PROD -> DEV"
echo "══════════════════════════════════════"

echo ""
echo "[1/5] Stopping dev service..."
sudo systemctl stop odoo-dev

echo "[2/5] Terminating existing connections..."
sudo -u postgres psql -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='skymedic_dev';" 2>/dev/null || true

echo "[3/5] Cloning database..."
sudo -u postgres dropdb --if-exists skymedic_dev
sudo -u postgres createdb -O odoo -T skymedic_prod skymedic_dev
echo "  Database cloned."

echo "[4/5] Copying filestore..."
rm -rf /opt/odoo/filestore/dev/skymedic_dev
cp -a /opt/odoo/filestore/prod/skymedic_prod /opt/odoo/filestore/dev/skymedic_dev 2>/dev/null || true

echo "[5/5] Neutralizing dev environment..."
HOSTNAME=$(tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//')
psql -U odoo -d skymedic_dev -c "
  UPDATE ir_cron SET active = false;
  UPDATE ir_mail_server SET active = false;
  UPDATE fetchmail_server SET active = false;
  UPDATE ir_config_parameter
    SET value = 'https://${HOSTNAME}:8443'
    WHERE key = 'web.base.url';
  UPDATE res_company SET name = name || ' [DEV]' WHERE id = 1;
"

echo ""
echo "  Starting dev service..."
sudo systemctl start odoo-dev

echo ""
echo "══════════════════════════════════════"
echo "  DEV REFRESHED FROM PROD"
echo "  URL: https://${HOSTNAME}:8443"
echo "══════════════════════════════════════"
