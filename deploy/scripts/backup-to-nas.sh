#!/bin/bash
set -euo pipefail

# =====================================================================
# ODOO SKYMEDIC - Backup to QNAP NAS
# Backs up all databases, filestores, and code to NAS
# Schedule: Every 12 hours via cron
# Retention: 4 days (8 backups max)
# NAS: 192.212.16.230 (SKYMEDIC NAS1) -> share "sky"
# =====================================================================

# --- Configuration ---
NAS_MOUNT="/mnt/qnap-skymedic"
BACKUP_BASE="${NAS_MOUNT}/OdooSkymedic/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_LABEL=$(date +%Y-%m-%d_%H%M)
RETENTION_DAYS=4
LOG_FILE="/var/log/odoo-backup-nas.log"

# Database settings
DB_HOST="127.0.0.1"
DB_PORT="5432"
DB_USER="odoo"

# Databases to backup
declare -A DATABASES=(
    ["prod"]="skymedic_prod"
    ["staging"]="skymedic_staging"
    ["dev"]="skymedic2"
)

# Filestore paths
declare -A FILESTORES=(
    ["prod"]="/opt/odoo/filestore/prod"
    ["staging"]="/opt/odoo/filestore/staging"
    ["dev"]="/opt/odoo/filestore/dev"
)

# Source code paths
declare -A CODE_PATHS=(
    ["repo"]="/home/omegaserver02/skymedic-odoo"
    ["prod"]="/opt/odoo/src/prod"
    ["staging"]="/opt/odoo/src/staging"
    ["dev"]="/opt/odoo/src/dev"
)

# --- Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

check_nas_mount() {
    if ! mountpoint -q "$NAS_MOUNT" 2>/dev/null; then
        log "NAS not mounted. Attempting to mount..."
        mount "$NAS_MOUNT" 2>/dev/null || {
            log_error "Failed to mount NAS at $NAS_MOUNT. Aborting backup."
            exit 1
        }
        log "NAS mounted successfully."
    fi
    # Verify write access
    if ! touch "${BACKUP_BASE}/.write_test" 2>/dev/null; then
        log_error "Cannot write to NAS backup directory. Aborting."
        exit 1
    fi
    rm -f "${BACKUP_BASE}/.write_test"
}

backup_databases() {
    log "--- DATABASE BACKUPS ---"
    for env in "${!DATABASES[@]}"; do
        local db_name="${DATABASES[$env]}"
        local dump_dir="${BACKUP_BASE}/databases/${env}"
        local dump_file="${dump_dir}/${db_name}_${TIMESTAMP}.dump"

        mkdir -p "$dump_dir"

        log "  Backing up database: ${db_name} (${env})..."

        if pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -Fc "$db_name" > "$dump_file" 2>>"$LOG_FILE"; then
            local size=$(du -h "$dump_file" | cut -f1)
            log "  OK: ${db_name} -> ${size}"
        else
            log_error "  FAILED: Could not dump ${db_name}"
            rm -f "$dump_file"
        fi
    done
}

backup_filestores() {
    log "--- FILESTORE BACKUPS ---"
    for env in "${!FILESTORES[@]}"; do
        local fs_path="${FILESTORES[$env]}"
        local fs_dir="${BACKUP_BASE}/filestores/${env}"
        local archive="${fs_dir}/filestore_${env}_${TIMESTAMP}.tar.gz"

        mkdir -p "$fs_dir"

        if [ -d "$fs_path" ] && [ "$(ls -A "$fs_path" 2>/dev/null)" ]; then
            log "  Backing up filestore: ${env} (${fs_path})..."
            if tar -czf "$archive" -C "$fs_path" . 2>>"$LOG_FILE"; then
                local size=$(du -h "$archive" | cut -f1)
                log "  OK: filestore_${env} -> ${size}"
            else
                log_error "  FAILED: Could not archive filestore ${env}"
                rm -f "$archive"
            fi
        else
            log "  SKIP: filestore ${env} is empty or does not exist"
        fi
    done
}

backup_code() {
    log "--- CODE BACKUPS ---"
    local code_dir="${BACKUP_BASE}/code"
    mkdir -p "$code_dir"

    # Backup the main git repository (custom addons + config)
    local repo_archive="${code_dir}/skymedic-odoo_repo_${TIMESTAMP}.tar.gz"
    log "  Backing up git repository..."
    if tar -czf "$repo_archive" \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='venv' \
        -C "$(dirname "${CODE_PATHS[repo]}")" \
        "$(basename "${CODE_PATHS[repo]}")" 2>>"$LOG_FILE"; then
        local size=$(du -h "$repo_archive" | cut -f1)
        log "  OK: repository -> ${size}"
    else
        log_error "  FAILED: Could not archive repository"
        rm -f "$repo_archive"
    fi

    # Backup production custom addons and config (deployed version)
    local prod_archive="${code_dir}/prod_deployment_${TIMESTAMP}.tar.gz"
    log "  Backing up production deployment configs..."
    if tar -czf "$prod_archive" \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='enterprise' \
        --exclude='.git' \
        -C /opt/odoo \
        docker/config-prod \
        docker/config-staging \
        dev/config \
        scripts 2>>"$LOG_FILE"; then
        local size=$(du -h "$prod_archive" | cut -f1)
        log "  OK: deployment configs -> ${size}"
    else
        log_error "  FAILED: Could not archive deployment configs"
        rm -f "$prod_archive"
    fi
}

cleanup_old_backups() {
    log "--- CLEANUP (>${RETENTION_DAYS} days) ---"
    local deleted=0

    # Clean up database backups
    for env in "${!DATABASES[@]}"; do
        local dir="${BACKUP_BASE}/databases/${env}"
        local count=$(find "$dir" -name "*.dump" -mtime +"$RETENTION_DAYS" -delete -print 2>/dev/null | wc -l)
        deleted=$((deleted + count))
    done

    # Clean up filestore backups
    for env in "${!FILESTORES[@]}"; do
        local dir="${BACKUP_BASE}/filestores/${env}"
        local count=$(find "$dir" -name "*.tar.gz" -mtime +"$RETENTION_DAYS" -delete -print 2>/dev/null | wc -l)
        deleted=$((deleted + count))
    done

    # Clean up code backups
    local code_count=$(find "${BACKUP_BASE}/code" -name "*.tar.gz" -mtime +"$RETENTION_DAYS" -delete -print 2>/dev/null | wc -l)
    deleted=$((deleted + code_count))

    log "  Deleted $deleted old backup files"
}

show_summary() {
    log "═══════════════════════════════════════════════════"
    log "  BACKUP SUMMARY - ${DATE_LABEL}"
    log "═══════════════════════════════════════════════════"

    log "  Databases:"
    for env in "${!DATABASES[@]}"; do
        local dir="${BACKUP_BASE}/databases/${env}"
        local count=$(find "$dir" -name "*.dump" 2>/dev/null | wc -l)
        local total=$(du -sh "$dir" 2>/dev/null | cut -f1)
        log "    ${env}: ${count} backups (${total})"
    done

    log "  Filestores:"
    for env in "${!FILESTORES[@]}"; do
        local dir="${BACKUP_BASE}/filestores/${env}"
        local count=$(find "$dir" -name "*.tar.gz" 2>/dev/null | wc -l)
        local total=$(du -sh "$dir" 2>/dev/null | cut -f1)
        log "    ${env}: ${count} backups (${total})"
    done

    log "  Code:"
    local code_count=$(find "${BACKUP_BASE}/code" -name "*.tar.gz" 2>/dev/null | wc -l)
    local code_total=$(du -sh "${BACKUP_BASE}/code" 2>/dev/null | cut -f1)
    log "    ${code_count} backups (${code_total})"

    local grand_total=$(du -sh "${BACKUP_BASE}" 2>/dev/null | cut -f1)
    log "  Total NAS usage: ${grand_total}"
    log "═══════════════════════════════════════════════════"
}

# --- Main Execution ---
log "═══════════════════════════════════════════════════"
log "  STARTING ODOO SKYMEDIC BACKUP TO NAS"
log "  Timestamp: ${TIMESTAMP}"
log "═══════════════════════════════════════════════════"

# Step 1: Verify NAS mount
check_nas_mount

# Step 2: Backup databases
backup_databases

# Step 3: Backup filestores
backup_filestores

# Step 4: Backup code
backup_code

# Step 5: Clean old backups
cleanup_old_backups

# Step 6: Summary
show_summary

log "BACKUP COMPLETED SUCCESSFULLY"
