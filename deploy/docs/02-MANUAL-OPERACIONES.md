# Manual de Operaciones
## Odoo Enterprise On-Premise - Skymedic

---

## 1. Comandos Diarios

### Desarrollo

```bash
# Servicio
od-start                  # Iniciar Odoo Dev
od-stop                   # Parar Odoo Dev
od-restart                # Reiniciar Odoo Dev
od-status                 # Ver estado del servicio
od-logs                   # Ver logs en tiempo real

# Modulos
od-update nombre_modulo   # Actualizar un modulo
od-install nombre_modulo  # Instalar un modulo

# Herramientas
od-shell                  # Consola interactiva Python
od-venv                   # Activar virtualenv
od-psql                   # Conectar a la BD de dev
```

### Produccion

```bash
op-start                  # Iniciar contenedor Prod
op-stop                   # Parar contenedor Prod
op-restart                # Reiniciar contenedor Prod
op-logs                   # Ver logs de Prod
```

### Staging

```bash
os-start                  # Iniciar contenedor Staging
os-stop                   # Parar contenedor Staging
os-restart                # Reiniciar contenedor Staging
os-logs                   # Ver logs de Staging
```

### Monitorizacion

```bash
mon-start                 # Iniciar stack de monitorizacion
mon-stop                  # Parar stack de monitorizacion
mon-logs                  # Ver logs de monitorizacion
```

---

## 2. Flujo DevOps: Dev -> Staging -> Prod

### Desarrollo de un modulo nuevo

1. Editar codigo en `/opt/odoo/src/custom-addons/`
2. Con `dev_mode = reload`, los cambios Python se aplican automaticamente
3. Para cambios en datos XML: `od-update nombre_modulo`
4. Probar en http://127.0.0.1:8069

### Promover a Staging

```bash
/opt/odoo/scripts/promote-to-staging.sh [modulos]
```

Esto automaticamente:
1. Construye una imagen Docker con el codigo actual
2. Clona la BD de produccion a staging
3. Desactiva crons, servidores de correo en staging
4. Despliega y actualiza modulos

Acceder a staging: `https://TU-HOST.ts.net:9443`

### Desplegar a Produccion

```bash
/opt/odoo/scripts/deploy-to-prod.sh odoo-skymedic:TAG [modulos]
```

Requiere confirmacion manual (escribir YES).

### Rollback

Si algo sale mal en produccion:

```bash
/opt/odoo/scripts/rollback-prod.sh
```

### Refrescar Dev desde Prod

```bash
/opt/odoo/scripts/clone-prod-to-dev.sh
```

---

## 3. Backups

### Backup manual

```bash
/opt/odoo/scripts/backup-prod.sh
```

Genera:
- `skymedic_prod_TIMESTAMP.dump` (BD)
- `filestore_TIMESTAMP.tar.gz` (archivos)

### Backup automatico (cron)

```bash
# Backup diario a las 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/odoo/scripts/backup-prod.sh >> /var/log/odoo-backup.log 2>&1") | crontab -
```

### Restaurar

```bash
/opt/odoo/scripts/restore-prod.sh backup.dump [filestore.tar.gz]
```

---

## 4. Monitorizacion

### Dashboards de Grafana

Acceder via `https://TU-HOST.ts.net:3443`

| Dashboard | Contenido |
|---|---|
| **Skymedic Overview** | Estado general, CPU, RAM, disco, Docker, Nginx, PG |
| Node Exporter Full (1860) | Servidor detallado |
| cAdvisor (14282) | Docker detallado |
| PostgreSQL (9628) | Base de datos detallada |
| Nginx (12708) | Proxy detallado |

### Alertas configuradas

| Alerta | Condicion | Severidad |
|---|---|---|
| HighCPU | CPU > 85% por 5min | Warning |
| HighMemory | RAM > 90% por 5min | Critical |
| DiskSpaceLow | Disco > 85% por 5min | Warning |
| DiskSpaceCritical | Disco > 95% por 2min | Critical |
| OdooProdDown | Prod caido 1min | Critical |
| PostgreSQLDown | PG caido 1min | Critical |
| NginxDown | Nginx caido 1min | Critical |
| ContainerRestarting | Contenedor reiniciado | Warning |
| HighLoginFailRate | Rate limiting activado | Warning |

### Health check rapido

```bash
/opt/odoo/scripts/health-check.sh
```

---

## 5. Mantenimiento

### Actualizar Odoo

```bash
# Dev: actualizar codigo fuente
cd /opt/odoo/src/odoo && git pull
cd /opt/odoo/src/enterprise && git pull

# Reconstruir imagen para Prod/Staging
/opt/odoo/scripts/build-image.sh

# Promover normalmente
/opt/odoo/scripts/promote-to-staging.sh all
# Probar en staging...
/opt/odoo/scripts/deploy-to-prod.sh odoo-skymedic:latest all
```

### Actualizar Docker images (monitorizacion)

```bash
cd /opt/odoo/monitoring
docker compose pull
docker compose up -d
```

### Renovar certificados manualmente

```bash
sudo /opt/odoo/scripts/renew-certs.sh
```

### Limpiar imagenes Docker antiguas

```bash
# Ver imagenes
docker images odoo-skymedic

# Eliminar una version especifica
docker rmi odoo-skymedic:TAG

# Limpiar todo lo no utilizado
docker system prune -f
```

### Limpiar backups antiguos

Los backups se limpian automaticamente (30 dias de retencion) en cada ejecucion del script de backup. Para limpiar manualmente:

```bash
find /opt/odoo/backups -mtime +30 -delete
```

---

## 6. Troubleshooting

### Odoo no arranca

```bash
# Ver logs
od-logs                    # Dev
op-logs                    # Prod

# Verificar PostgreSQL
sudo systemctl status postgresql
psql -U odoo -h 127.0.0.1 -l    # Listar BDs

# Verificar permisos filestore
ls -la /opt/odoo/filestore/
```

### Nginx devuelve 502

```bash
# Verificar que Odoo esta corriendo
curl http://127.0.0.1:8069/web/health    # Prod
curl http://127.0.0.1:8071/web/health    # Staging

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log
```

### No se puede acceder por Tailscale

```bash
# Estado de Tailscale
tailscale status

# Ver Funnel
tailscale funnel status

# Verificar que Nginx escucha
sudo ss -tlnp | grep -E '443|8443|9443|3443'
```

### Docker no arranca

```bash
# Ver estado contenedores
docker ps -a

# Ver logs del contenedor
docker logs odoo-prod

# Reiniciar Docker
sudo systemctl restart docker
```

### PostgreSQL lento

```bash
# Ver queries activas
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE state != 'idle'
  ORDER BY duration DESC;
"

# Ver tamano de tablas
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables
  ORDER BY pg_total_relation_size(relid) DESC
  LIMIT 20;
"
```
