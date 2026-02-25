#!/bin/bash

# =============================================
# Health check for all Skymedic services
# Usage: ./health-check.sh
# =============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name="$1"
    local check_cmd="$2"

    if eval "$check_cmd" > /dev/null 2>&1; then
        echo -e "  ${GREEN}[OK]${NC} $name"
        return 0
    else
        echo -e "  ${RED}[FAIL]${NC} $name"
        return 1
    fi
}

check_url() {
    local name="$1"
    local url="$2"

    HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ] || [ "$HTTP_CODE" = "302" ]; then
        echo -e "  ${GREEN}[OK]${NC} $name (HTTP $HTTP_CODE)"
        return 0
    else
        echo -e "  ${RED}[FAIL]${NC} $name (HTTP ${HTTP_CODE:-timeout})"
        return 1
    fi
}

echo "══════════════════════════════════════"
echo "  SKYMEDIC HEALTH CHECK"
echo "  $(date)"
echo "══════════════════════════════════════"

ERRORS=0

echo ""
echo "--- System Services ---"
check_service "PostgreSQL" "systemctl is-active --quiet postgresql" || ((ERRORS++))
check_service "Nginx" "systemctl is-active --quiet nginx" || ((ERRORS++))
check_service "Tailscale" "tailscale status > /dev/null 2>&1" || ((ERRORS++))
check_service "Odoo Dev (systemd)" "systemctl is-active --quiet odoo-dev" || ((ERRORS++))

echo ""
echo "--- Docker Containers ---"
check_service "odoo-prod" "docker ps --format '{{.Names}}' | grep -q '^odoo-prod$'" || ((ERRORS++))
check_service "odoo-staging" "docker ps --format '{{.Names}}' | grep -q '^odoo-staging$'" || ((ERRORS++))
check_service "prometheus" "docker ps --format '{{.Names}}' | grep -q '^prometheus$'" || ((ERRORS++))
check_service "grafana" "docker ps --format '{{.Names}}' | grep -q '^grafana$'" || ((ERRORS++))
check_service "node-exporter" "docker ps --format '{{.Names}}' | grep -q '^node-exporter$'" || ((ERRORS++))
check_service "cadvisor" "docker ps --format '{{.Names}}' | grep -q '^cadvisor$'" || ((ERRORS++))
check_service "postgres-exporter" "docker ps --format '{{.Names}}' | grep -q '^postgres-exporter$'" || ((ERRORS++))
check_service "nginx-exporter" "docker ps --format '{{.Names}}' | grep -q '^nginx-exporter$'" || ((ERRORS++))

echo ""
echo "--- HTTP Endpoints ---"
check_url "Odoo Prod (8069)" "http://127.0.0.1:8069/web/health" || ((ERRORS++))
check_url "Odoo Dev (8069)" "http://127.0.0.1:8069/web/health" || ((ERRORS++))
check_url "Odoo Staging (8071)" "http://127.0.0.1:8071/web/health" || ((ERRORS++))
check_url "Grafana (3000)" "http://127.0.0.1:3000/api/health" || ((ERRORS++))
check_url "Prometheus (9090)" "http://127.0.0.1:9090/-/healthy" || ((ERRORS++))

echo ""
echo "--- Disk Usage ---"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 70 ]; then
    echo -e "  ${GREEN}[OK]${NC} Disk: ${DISK_USAGE}% used"
elif [ "$DISK_USAGE" -lt 85 ]; then
    echo -e "  ${YELLOW}[WARN]${NC} Disk: ${DISK_USAGE}% used"
else
    echo -e "  ${RED}[CRITICAL]${NC} Disk: ${DISK_USAGE}% used"
    ((ERRORS++))
fi

echo ""
echo "--- Memory ---"
MEM_USAGE=$(free | awk '/^Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -lt 80 ]; then
    echo -e "  ${GREEN}[OK]${NC} Memory: ${MEM_USAGE}% used"
elif [ "$MEM_USAGE" -lt 90 ]; then
    echo -e "  ${YELLOW}[WARN]${NC} Memory: ${MEM_USAGE}% used"
else
    echo -e "  ${RED}[CRITICAL]${NC} Memory: ${MEM_USAGE}% used"
    ((ERRORS++))
fi

echo ""
echo "══════════════════════════════════════"
if [ "$ERRORS" -eq 0 ]; then
    echo -e "  ${GREEN}All checks passed!${NC}"
else
    echo -e "  ${RED}$ERRORS check(s) failed!${NC}"
fi
echo "══════════════════════════════════════"

exit $ERRORS
