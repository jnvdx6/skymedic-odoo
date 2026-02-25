#!/bin/bash
set -euo pipefail

# =============================================
# Restore PRODUCTION from backup
# Usage: ./restore-prod.sh <dump_file> [filestore_archive]
# =============================================

DUMP_FILE=${1:?"Usage: ./restore-prod.sh <dump_file> [filestore_archive]"}
FILESTORE_ARCHIVE=${2:-""}
DB_NAME="skymedic_prod"
FILESTORE_DIR="/opt/odoo/filestore/prod"

echo "══════════════════════════════════════"
echo "  RESTORE PRODUCTION"
echo "══════════════════════════════════════"
echo ""
echo "  Dump file: $DUMP_FILE"
echo "  Filestore: ${FILESTORE_ARCHIVE:-none}"
echo ""
echo "  WARNING: This will REPLACE the current production database!"
echo ""
read -p "  Type YES to confirm: " CONFIRM
[ "$CONFIRM" != "YES" ] && echo "  Cancelled." && exit 0

# Stop production
echo ""
echo "[1/4] Stopping production..."
cd /opt/odoo/docker
docker compose --profile prod stop

# Restore database
echo "[2/4] Restoring database..."
sudo -u postgres psql -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}';" 2>/dev/null || true
sudo -u postgres dropdb --if-exists "$DB_NAME"
sudo -u postgres createdb -O odoo "$DB_NAME"
pg_restore -U odoo -h 127.0.0.1 -d "$DB_NAME" "$DUMP_FILE"
echo "  Database restored."

# Restore filestore
if [ -n "$FILESTORE_ARCHIVE" ]; then
    echo "[3/4] Restoring filestore..."
    rm -rf "${FILESTORE_DIR}/${DB_NAME}"
    mkdir -p "${FILESTORE_DIR}/${DB_NAME}"
    tar -xzf "$FILESTORE_ARCHIVE" -C "${FILESTORE_DIR}/${DB_NAME}"
    echo "  Filestore restored."
else
    echo "[3/4] Skipping filestore restore (no archive provided)."
fi

# Restart production
echo "[4/4] Starting production..."
docker compose --profile prod up -d

echo ""
echo "══════════════════════════════════════"
echo "  PRODUCTION RESTORED"
echo "══════════════════════════════════════"
