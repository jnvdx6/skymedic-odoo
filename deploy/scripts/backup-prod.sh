#!/bin/bash
set -euo pipefail

# =============================================
# Backup PRODUCTION database and filestore
# Usage: ./backup-prod.sh
# Recommended: Run daily via cron
# =============================================

BACKUP_DIR="/opt/odoo/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="skymedic_prod"
FILESTORE_DIR="/opt/odoo/filestore/prod"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "══════════════════════════════════════"
echo "  BACKUP PRODUCTION"
echo "  Timestamp: $TIMESTAMP"
echo "══════════════════════════════════════"

# 1. Database dump
echo ""
echo "[1/3] Dumping database..."
pg_dump -U odoo -h 127.0.0.1 -Fc "$DB_NAME" > "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
echo "  Database dump: ${DB_NAME}_${TIMESTAMP}.dump ($(du -h "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump" | cut -f1))"

# 2. Filestore backup
echo ""
echo "[2/3] Archiving filestore..."
tar -czf "${BACKUP_DIR}/filestore_${TIMESTAMP}.tar.gz" -C "$FILESTORE_DIR" . 2>/dev/null || true
echo "  Filestore archive: filestore_${TIMESTAMP}.tar.gz"

# 3. Cleanup old backups
echo ""
echo "[3/3] Cleaning backups older than ${RETENTION_DAYS} days..."
DELETED=$(find "$BACKUP_DIR" -name "*.dump" -o -name "*.tar.gz" -mtime +"$RETENTION_DAYS" -delete -print | wc -l)
echo "  Deleted $DELETED old backup files."

echo ""
echo "══════════════════════════════════════"
echo "  BACKUP COMPLETE"
echo "  Location: $BACKUP_DIR"
echo "══════════════════════════════════════"
ls -lh "$BACKUP_DIR"/*"$TIMESTAMP"* 2>/dev/null
