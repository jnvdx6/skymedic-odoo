#!/bin/bash
set -euo pipefail

# =============================================
# Renew Tailscale HTTPS certificates
# Runs monthly via cron
# =============================================

HOSTNAME=$(tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//')

echo "[$(date)] Renewing certificates for $HOSTNAME..."

sudo tailscale cert "$HOSTNAME"
sudo cp "/var/lib/tailscale/certs/${HOSTNAME}.crt" /etc/nginx/ssl/server.crt
sudo cp "/var/lib/tailscale/certs/${HOSTNAME}.key" /etc/nginx/ssl/server.key
sudo nginx -s reload

echo "[$(date)] Certificates renewed successfully for $HOSTNAME"
