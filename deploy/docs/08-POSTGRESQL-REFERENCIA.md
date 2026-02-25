# PostgreSQL - Referencia de Configuracion
## Odoo Enterprise On-Premise - Skymedic

---

## Configuracion Optimizada

La configuracion se aplica automaticamente por `setup-postgresql.sh`.
Se adapta a la RAM del servidor.

### Parametros clave

| Parametro | Formula | Ejemplo (32GB RAM) |
|---|---|---|
| `shared_buffers` | RAM / 4 | 8 GB |
| `effective_cache_size` | RAM * 3/4 | 24 GB |
| `work_mem` | Fijo | 64 MB |
| `maintenance_work_mem` | Fijo | 2 GB |
| `wal_buffers` | Fijo | 64 MB |

### postgresql.conf completo de referencia

```ini
# === Conexiones ===
listen_addresses = '127.0.0.1'
max_connections = 200
superuser_reserved_connections = 3

# === Memoria (ajustar segun RAM) ===
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 64MB
maintenance_work_mem = 2GB
wal_buffers = 64MB

# === WAL ===
wal_level = replica
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min

# === SSD ===
random_page_cost = 1.1
effective_io_concurrency = 200
default_statistics_target = 100

# === Logging ===
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_checkpoints = on
log_lock_waits = on

# === Autovacuum ===
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 30s
autovacuum_vacuum_scale_factor = 0.05
autovacuum_analyze_scale_factor = 0.025

timezone = 'Europe/Madrid'
```

### pg_hba.conf

```
local   all   all                 peer
host    all   odoo  127.0.0.1/32  scram-sha-256
```

---

## Comandos Utiles

### Conexion

```bash
# Como usuario odoo
psql -U odoo -h 127.0.0.1 -d skymedic_prod

# Como superuser
sudo -u postgres psql
```

### Bases de datos

```bash
# Listar
psql -U odoo -h 127.0.0.1 -l

# Crear
sudo -u postgres createdb -O odoo nombre_bd

# Eliminar
sudo -u postgres dropdb nombre_bd

# Clonar (para staging/dev)
sudo -u postgres createdb -O odoo -T skymedic_prod skymedic_staging
```

### Backup y Restore

```bash
# Backup
pg_dump -U odoo -h 127.0.0.1 -Fc skymedic_prod > backup.dump

# Restore
pg_restore -U odoo -h 127.0.0.1 -d skymedic_prod backup.dump
```

### Diagnostico

```bash
# Queries activas
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "
  SELECT pid, now() - query_start AS duration, state, query
  FROM pg_stat_activity
  WHERE state != 'idle'
  ORDER BY duration DESC;"

# Tamano de tablas
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables
  ORDER BY pg_total_relation_size(relid) DESC
  LIMIT 20;"

# Tamano de bases de datos
psql -U odoo -h 127.0.0.1 -c "
  SELECT datname, pg_size_pretty(pg_database_size(datname))
  FROM pg_database
  WHERE datname LIKE 'skymedic%'
  ORDER BY pg_database_size(datname) DESC;"

# Conexiones por base de datos
psql -U odoo -h 127.0.0.1 -c "
  SELECT datname, count(*)
  FROM pg_stat_activity
  GROUP BY datname
  ORDER BY count DESC;"

# Locks
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "
  SELECT l.pid, l.mode, l.granted,
         a.query_start, a.state, substring(a.query, 1, 80)
  FROM pg_locks l
  JOIN pg_stat_activity a ON l.pid = a.pid
  WHERE NOT l.granted;"

# Matar una query lenta
psql -U odoo -h 127.0.0.1 -c "SELECT pg_cancel_backend(PID);"

# Forzar desconexion
psql -U odoo -h 127.0.0.1 -c "SELECT pg_terminate_backend(PID);"
```

### Mantenimiento

```bash
# VACUUM manual
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "VACUUM ANALYZE;"

# REINDEX
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "REINDEX DATABASE skymedic_prod;"

# Ver estado del autovacuum
psql -U odoo -h 127.0.0.1 -d skymedic_prod -c "
  SELECT relname, last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
  FROM pg_stat_user_tables
  ORDER BY last_autovacuum DESC NULLS LAST
  LIMIT 20;"
```
