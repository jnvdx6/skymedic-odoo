# Guia de Grafana y Monitorizacion
## Odoo Enterprise On-Premise - Skymedic

---

## Acceso

- **URL**: `https://TU-HOST.ts.net:3443` (requiere Tailscale)
- **Usuario**: admin
- **Password**: (definido en monitoring/docker-compose.yml)

---

## Dashboards

### Dashboard Overview (auto-provisionado)

Paneles incluidos:
1. **Estado de servicios** - UP/DOWN de todos los servicios
2. **CPU %** - Uso de CPU en tiempo real
3. **RAM %** - Uso de memoria
4. **Disco** - Gauge de uso de disco con umbrales
5. **PG Conexiones** - Conexiones por base de datos
6. **PG Tamano BDs** - Tamano de bases de datos Skymedic
7. **Docker CPU** - CPU por contenedor
8. **Docker Memoria** - Memoria por contenedor
9. **Nginx req/s** - Peticiones por segundo
10. **Nginx Conexiones** - Conexiones activas
11. **Red Trafico** - Trafico de red entrada/salida

### Dashboards de la Comunidad

Importar en: Dashboards > Import > Enter ID > Prometheus datasource

| ID | Nombre | Que muestra |
|---|---|---|
| **1860** | Node Exporter Full | CPU, RAM, disco, red, systemd detallado |
| **14282** | cAdvisor Container | CPU, memoria, red, I/O por contenedor |
| **9628** | PostgreSQL Database | Queries, conexiones, locks, cache hit |
| **12708** | Nginx Overview | Requests, status codes, conexiones |

---

## Alertas

### Alertas configuradas en Prometheus

Las alertas se evaluan cada 15 segundos y se definen en `alert-rules.yml`:

**Servidor:**
- CPU > 85% por 5min
- RAM > 90% por 5min
- Disco > 85% por 5min
- Disco > 95% por 2min (CRITICO)

**Servicios:**
- Odoo Prod caido > 1min (CRITICO)
- Odoo Staging caido > 5min
- PostgreSQL caido > 1min (CRITICO)
- Nginx caido > 1min (CRITICO)

**PostgreSQL:**
- Conexiones > 150/200

**Docker:**
- CPU contenedor > 80% por 5min
- Contenedor reiniciado

**Seguridad:**
- Rate limiting activado (posible fuerza bruta)

### Ver alertas activas

1. En Grafana: Alerting > Alert Rules
2. En Prometheus: `http://127.0.0.1:9090/alerts`

### Configurar notificaciones (opcional)

En Grafana > Alerting > Contact Points, puedes configurar:
- Email (requiere SMTP)
- Slack webhook
- Telegram bot
- Discord webhook

---

## Queries utiles de Prometheus

### Sistema

```promql
# CPU uso total
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# RAM uso
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Disco uso
(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100

# Uptime
node_time_seconds - node_boot_time_seconds
```

### Docker

```promql
# CPU por contenedor
rate(container_cpu_usage_seconds_total{name=~"odoo.*"}[5m]) * 100

# Memoria por contenedor
container_memory_usage_bytes{name=~"odoo.*"}

# Red por contenedor
rate(container_network_receive_bytes_total{name=~"odoo.*"}[5m])
```

### PostgreSQL

```promql
# Conexiones activas
pg_stat_activity_count

# Tamano de BD
pg_database_size_bytes{datname=~"skymedic.*"}

# Cache hit ratio
pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)
```

### Nginx

```promql
# Requests por segundo
irate(nginx_http_requests_total[5m])

# Conexiones activas
nginx_connections_active

# Conexiones aceptadas por segundo
irate(nginx_connections_accepted[5m])
```

---

## Mantenimiento

### Actualizar contenedores de monitorizacion

```bash
cd /opt/odoo/monitoring
docker compose pull
docker compose up -d
```

### Limpiar datos antiguos

Prometheus retiene 90 dias por defecto (configurado en `--storage.tsdb.retention.time=90d`).

Para cambiar:
1. Editar `/opt/odoo/monitoring/docker-compose.yml`
2. Modificar `--storage.tsdb.retention.time=30d`
3. `docker compose up -d prometheus`

### Backup de Grafana

Los dashboards provisionados se restauran automaticamente.
Para dashboards creados manualmente:

```bash
# Export via API
curl -s http://admin:password@127.0.0.1:3000/api/dashboards/uid/DASHBOARD_UID | jq '.dashboard' > backup.json
```
