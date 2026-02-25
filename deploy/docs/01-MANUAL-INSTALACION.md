# Manual de Instalacion Completo
## Odoo Enterprise On-Premise - Skymedic

---

## Requisitos Previos

- **SO**: Ubuntu Server 24.04 LTS
- **RAM**: Minimo 16 GB (recomendado 32 GB)
- **Disco**: SSD con minimo 100 GB libres
- **CPU**: Minimo 4 cores (recomendado 8)
- **Cuenta Tailscale**: Registrada en https://login.tailscale.com
- **Licencia Odoo Enterprise**: Acceso al repositorio enterprise

---

## Paso 1: Preparacion del Sistema

```bash
# Clonar/copiar el directorio odoo-skymedic al servidor
cd /home/tu-usuario
# (copiar odoo-skymedic/ aqui)

# Hacer ejecutables todos los scripts
chmod +x /home/tu-usuario/odoo-skymedic/scripts/*.sh
```

## Paso 2: Instalacion de Paquetes Base

```bash
sudo /home/tu-usuario/odoo-skymedic/scripts/install-system.sh
```

Esto instala:
- Paquetes del sistema (build tools, librerias, wkhtmltopdf, nginx)
- Docker
- PostgreSQL 16
- Tailscale
- Actualizaciones automaticas de seguridad

**IMPORTANTE**: Cierra sesion y vuelve a entrar despues de este paso (para que el grupo docker se aplique).

## Paso 3: Estructura de Directorios

```bash
/home/tu-usuario/odoo-skymedic/scripts/setup-directories.sh
```

Crea la estructura en `/opt/odoo/`:

```
/opt/odoo/
├── docker/           # Docker compose y configs
│   ├── config-prod/
│   └── config-staging/
├── dev/              # Entorno desarrollo
│   ├── config/
│   └── venv/
├── filestore/        # Almacen de archivos Odoo
│   ├── prod/
│   ├── dev/
│   └── staging/
├── monitoring/       # Grafana + Prometheus
├── scripts/          # Scripts operativos
├── src/              # Codigo fuente
│   ├── odoo/
│   ├── enterprise/
│   └── custom-addons/
└── backups/          # Backups de BD
```

## Paso 4: Tailscale

```bash
# Autenticarse
sudo tailscale up

# Configurar certificados y Funnel
sudo /home/tu-usuario/odoo-skymedic/scripts/setup-tailscale.sh
```

### Configuracion en el Admin Console de Tailscale

1. Ir a https://login.tailscale.com/admin
2. **DNS > MagicDNS** > Activar
3. **DNS > HTTPS Certificates** > Activar
4. **Access Controls** > Anadir al JSON:

```json
{
  "nodeAttrs": [
    {
      "target": ["autogroup:member"],
      "attr": ["funnel"]
    }
  ]
}
```

### Cron de renovacion de certificados

```bash
(crontab -l 2>/dev/null; echo "0 3 1 * * /opt/odoo/scripts/renew-certs.sh >> /var/log/cert-renew.log 2>&1") | crontab -
```

## Paso 5: PostgreSQL

```bash
sudo /home/tu-usuario/odoo-skymedic/scripts/setup-postgresql.sh
```

Te pedira la contrasena para el usuario `odoo`. **Guarda esta contrasena** - la necesitaras en todos los archivos de configuracion de Odoo.

**IMPORTANTE**: Actualiza la contrasena en estos archivos:
- `/opt/odoo/dev/config/odoo-dev.conf`
- `/opt/odoo/docker/config-prod/odoo.conf`
- `/opt/odoo/docker/config-staging/odoo.conf`
- `/opt/odoo/monitoring/docker-compose.yml` (postgres-exporter)

## Paso 6: Entorno de Desarrollo

```bash
sudo /home/tu-usuario/odoo-skymedic/scripts/setup-dev-env.sh
```

### Clonar Enterprise (manual - requiere credenciales)

```bash
cd /opt/odoo/src
git clone --depth 1 --branch 18.0 https://github.com/odoo/enterprise.git enterprise
```

### Copiar custom addons del entorno actual

```bash
cp -r /home/omegaserver02/odoo19-dev/custom-addons/* /opt/odoo/src/custom-addons/
```

### Configurar aliases

```bash
cp /home/tu-usuario/odoo-skymedic/dev/bashrc-aliases.sh /opt/odoo/dev/
echo 'source /opt/odoo/dev/bashrc-aliases.sh' >> ~/.bashrc
source ~/.bashrc
```

### Iniciar Dev

```bash
od-start
od-logs   # Verificar que arranca correctamente
```

## Paso 7: Entornos Docker (Prod / Staging)

### Copiar configuraciones

```bash
cp /home/tu-usuario/odoo-skymedic/docker/Dockerfile /opt/odoo/docker/
cp /home/tu-usuario/odoo-skymedic/docker/docker-compose.yml /opt/odoo/docker/
cp /home/tu-usuario/odoo-skymedic/docker/.env /opt/odoo/docker/
# Las configs ya se copiaron con setup-dev-env o manualmente
```

### Construir imagen

```bash
/opt/odoo/scripts/build-image.sh
```

### Levantar produccion

```bash
cd /opt/odoo/docker
docker compose --profile prod up -d
docker compose logs -f odoo-prod
```

### Levantar staging

```bash
docker compose --profile staging up -d
```

## Paso 8: Nginx

```bash
sudo /home/tu-usuario/odoo-skymedic/scripts/setup-nginx.sh
```

Verificar:
```bash
sudo nginx -t
curl -sk https://127.0.0.1/web/health    # Prod
curl -sk https://127.0.0.1:8443/web/health  # Dev (desde Tailscale)
```

## Paso 9: Monitorizacion

```bash
/home/tu-usuario/odoo-skymedic/scripts/setup-monitoring.sh
```

Despues, en Grafana (https://HOST:3443):
1. Login con admin / GRAFANA_PASSWORD_SEGURO
2. Ir a Dashboards > Import
3. Importar IDs: 1860, 14282, 9628, 12708
4. Seleccionar datasource "Prometheus"

## Paso 10: Seguridad

```bash
sudo /home/tu-usuario/odoo-skymedic/scripts/setup-security.sh
```

### Instalar Tailscale en dispositivos de acceso

Para acceder a dev/staging/grafana, instala Tailscale en:
- Tu portatil / PC
- Tu movil
- Cualquier dispositivo que necesite acceder

## Paso 11: Verificacion Final

```bash
/opt/odoo/scripts/health-check.sh
```

---

## URLs de Acceso

| Servicio | URL | Acceso |
|---|---|---|
| **Odoo Prod** | `https://TU-HOST.ts.net` | Publico (internet) |
| Odoo Dev | `https://TU-HOST.ts.net:8443` | Solo Tailscale |
| Odoo Staging | `https://TU-HOST.ts.net:9443` | Solo Tailscale |
| Grafana | `https://TU-HOST.ts.net:3443` | Solo Tailscale |
