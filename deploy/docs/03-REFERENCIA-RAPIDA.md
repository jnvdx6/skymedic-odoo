# Referencia Rapida
## Odoo Enterprise On-Premise - Skymedic

---

## Puertos y Accesos

| Servicio | Puerto | Bind | Acceso |
|---|---|---|---|
| Odoo Prod | 8069/8072 | 127.0.0.1 | Publico via Nginx 443 + Funnel |
| Odoo Dev | 8069/8072 | 127.0.0.1 | Nginx 8443 -> Tailscale |
| Odoo Staging | 8071/8074 | 127.0.0.1 | Nginx 9443 -> Tailscale |
| Grafana | 3000 | 127.0.0.1 | Nginx 3443 -> Tailscale |
| PostgreSQL | 5432 | 127.0.0.1 | Solo local |
| Prometheus | 9090 | 127.0.0.1 | Solo local |
| node-exporter | 9100 | 127.0.0.1 | Solo Prometheus |
| cAdvisor | 8080 | 127.0.0.1 | Solo Prometheus |
| postgres-exporter | 9187 | 127.0.0.1 | Solo Prometheus |
| nginx-exporter | 9113 | 127.0.0.1 | Solo Prometheus |

---

## Scripts

| Script | Proposito | Uso |
|---|---|---|
| `install-system.sh` | Instalar paquetes del SO | `sudo ./install-system.sh` |
| `setup-directories.sh` | Crear estructura /opt/odoo | `./setup-directories.sh` |
| `setup-postgresql.sh` | Configurar PostgreSQL | `sudo ./setup-postgresql.sh` |
| `setup-tailscale.sh` | Certs + Funnel | `sudo ./setup-tailscale.sh` |
| `setup-nginx.sh` | Configurar Nginx | `sudo ./setup-nginx.sh` |
| `setup-security.sh` | UFW + Fail2ban | `sudo ./setup-security.sh` |
| `setup-dev-env.sh` | Entorno desarrollo | `sudo ./setup-dev-env.sh` |
| `setup-monitoring.sh` | Grafana + Prometheus | `./setup-monitoring.sh` |
| `build-image.sh` | Build imagen Docker | `./build-image.sh [tag]` |
| `promote-to-staging.sh` | Dev -> Staging | `./promote-to-staging.sh [mods]` |
| `deploy-to-prod.sh` | Staging -> Prod | `./deploy-to-prod.sh <img> [mods]` |
| `rollback-prod.sh` | Revertir produccion | `./rollback-prod.sh` |
| `clone-prod-to-dev.sh` | Prod -> Dev | `./clone-prod-to-dev.sh` |
| `backup-prod.sh` | Backup BD + filestore | `./backup-prod.sh` |
| `restore-prod.sh` | Restaurar backup | `./restore-prod.sh <dump> [fs]` |
| `renew-certs.sh` | Renovar certificados | `sudo ./renew-certs.sh` |
| `health-check.sh` | Verificar servicios | `./health-check.sh` |

---

## Aliases (tras source bashrc-aliases.sh)

### Desarrollo
```
od-start / od-stop / od-restart / od-logs / od-status
od-update <modulo>  / od-install <modulo>
od-shell / od-venv / od-psql
```

### Produccion
```
op-start / op-stop / op-restart / op-logs
```

### Staging
```
os-start / os-stop / os-restart / os-logs
```

### Monitorizacion
```
mon-start / mon-stop / mon-logs
```

### DevOps
```
build-image / promote / deploy / rollback / clone-dev / health / backup
```

---

## Archivos de Configuracion

| Archivo | Proposito |
|---|---|
| `/opt/odoo/dev/config/odoo-dev.conf` | Config Odoo Dev |
| `/opt/odoo/docker/config-prod/odoo.conf` | Config Odoo Prod |
| `/opt/odoo/docker/config-staging/odoo.conf` | Config Odoo Staging |
| `/opt/odoo/docker/docker-compose.yml` | Docker Compose Prod/Staging |
| `/opt/odoo/monitoring/docker-compose.yml` | Docker Compose Monitorizacion |
| `/opt/odoo/monitoring/prometheus.yml` | Config Prometheus |
| `/opt/odoo/monitoring/alert-rules.yml` | Reglas de alertas |
| `/etc/nginx/sites-available/odoo-*` | Configs Nginx |
| `/etc/systemd/system/odoo-dev.service` | Servicio systemd Dev |

---

## Flujo DevOps

```
DESARROLLAR (dev nativo)
    |
    v
od-update modulo  -->  probar en https://HOST:8443
    |
    v
promote-to-staging.sh  -->  probar en https://HOST:9443
    |
    v
deploy-to-prod.sh  -->  verificar en https://HOST
    |
    v (si falla)
rollback-prod.sh  -->  volver a version anterior
```

---

## Cron Jobs

| Cron | Frecuencia | Proposito |
|---|---|---|
| `backup-prod.sh` | Diario 2:00 AM | Backup BD + filestore |
| `renew-certs.sh` | Mensual dia 1 3:00 AM | Renovar certificados |

---

## Grafana Dashboards

| ID | Dashboard | Importar en |
|---|---|---|
| built-in | Skymedic Overview | Auto-provisionado |
| 1860 | Node Exporter Full | Importar manualmente |
| 14282 | cAdvisor Container | Importar manualmente |
| 9628 | PostgreSQL Database | Importar manualmente |
| 12708 | Nginx Overview | Importar manualmente |
