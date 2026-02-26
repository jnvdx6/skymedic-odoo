# Backup a NAS QNAP - Guia de Configuracion

## Resumen

Sistema de backups automatizados que copia las bases de datos, filestores y codigo fuente
del servidor Odoo al NAS QNAP de Skymedic cada 12 horas, con retencion de 4 dias.

## Infraestructura

| Componente | Detalle |
|------------|---------|
| NAS | QNAP "SKYMEDIC NAS1" |
| IP | 192.212.16.230 |
| Protocolo | SMB/CIFS v3.0 |
| Share | "sky" (Carpeta Raiz Principal) |
| Mount point | /mnt/qnap-skymedic |
| Credenciales | /etc/cifs-credentials-qnap (chmod 600) |

## Que se respalda

- **Bases de datos** (pg_dump formato custom):
  - skymedic_prod (produccion)
  - skymedic_staging (staging)
  - skymedic2 (desarrollo)
- **Filestores** (tar.gz):
  - /opt/odoo/filestore/prod/
  - /opt/odoo/filestore/staging/
  - /opt/odoo/filestore/dev/
- **Codigo fuente**:
  - Repositorio git completo (sin .git, node_modules, __pycache__)
  - Configs de despliegue (prod, staging, scripts)

## Estructura en el NAS

```
/mnt/qnap-skymedic/OdooSkymedic/backups/
  databases/
    prod/     -> skymedic_prod_YYYYMMDD_HHMMSS.dump
    staging/  -> skymedic_staging_YYYYMMDD_HHMMSS.dump
    dev/      -> skymedic2_YYYYMMDD_HHMMSS.dump
  filestores/
    prod/     -> filestore_prod_YYYYMMDD_HHMMSS.tar.gz
    staging/  -> filestore_staging_YYYYMMDD_HHMMSS.tar.gz
    dev/      -> filestore_dev_YYYYMMDD_HHMMSS.tar.gz
  code/
    skymedic-odoo_repo_YYYYMMDD_HHMMSS.tar.gz
    prod_deployment_YYYYMMDD_HHMMSS.tar.gz
```

## Programacion

- **Cron:** cada 12 horas a las 6:00 y 18:00
- **Retencion:** 4 dias (maximo ~8 copias por tipo)
- **Tamano estimado por ejecucion:** ~1.1 GB
- **Tamano maximo en disco:** ~8.8 GB (4 dias)

```cron
0 6,18 * * * /opt/odoo/scripts/backup-to-nas.sh >> /var/log/odoo-backup-nas.log 2>&1
```

## Montaje persistente (fstab)

```
//192.212.16.230/sky /mnt/qnap-skymedic cifs credentials=/etc/cifs-credentials-qnap,vers=3.0,uid=1000,gid=1000,file_mode=0775,dir_mode=0775,_netdev,nofail 0 0
```

## Restauracion

```bash
# Restaurar base de datos
pg_restore -U odoo -h 127.0.0.1 -d skymedic_prod --clean --if-exists /path/to/dump.dump

# Restaurar filestore
tar -xzf /path/to/filestore.tar.gz -C /opt/odoo/filestore/prod/filestore/skymedic_prod/

# Restaurar codigo
tar -xzf /path/to/repo.tar.gz -C /home/omegaserver02/
```

## Logs

- Log principal: /var/log/odoo-backup-nas.log
- Rotacion: /etc/logrotate.d/odoo-backup-nas (semanal, 4 rotaciones, comprimido)

## Dependencias

- Paquetes: cifs-utils, smbclient
- PostgreSQL: .pgpass configurado en /home/omegaserver02/.pgpass
