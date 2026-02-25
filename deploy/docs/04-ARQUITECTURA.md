# Arquitectura del Sistema
## Odoo Enterprise On-Premise - Skymedic

---

## Diagrama General

```
    INTERNET (publico)                     TAILSCALE MESH (privado)
          |                                        |
          v                                        v
+---------------------+                +----------------------+
|  Tailscale FUNNEL   |                |  Tailscale VPN       |
|  Puerto 443 publico |                |  Solo tus devices    |
+---------+-----------+                +----------+-----------+
          |                                        |
          +-------------------+--------------------+
                              v
                    +-------------------+
                    |   Nginx (host)    |
                    +---------+---------+
                              |
         +--------------------+--------------------+
         |                    |                    |
  +------v--------+   +------v-------+   +--------v-------+
  | PROD (Docker) |   |STAGING(Docker)|  |  DEV (Nativo)  |
  |   :8069       |   |   :8071      |   |    :8069       |
  | Publico       |   | Privado      |   | Privado        |
  +------+--------+   +------+-------+   +--------+-------+
         |                    |                    |
         +--------------------+--------------------+
                              |
                    +---------v----------+
                    |  PostgreSQL 16      |
                    |  (nativo, host)     |
                    +--------------------+

  +----------------------------------------------------------+
  |                     MONITORIZACION                        |
  |  Prometheus <- node_exporter <- cAdvisor <- pg_exporter  |
  |             <- nginx_exporter <- Odoo health endpoints   |
  |  Grafana -> Dashboards completos                         |
  +----------------------------------------------------------+
```

---

## Filosofia del Diseno

| Aspecto | PROD / STAGING | DEV |
|---|---|---|
| Runtime | Docker (imagen fija, inmutable) | Python venv nativo |
| Codigo | Dentro de la imagen, versionado | Editable en caliente |
| Debugging | Solo logs | pdb, --dev=reload, IDE |
| PostgreSQL | Compartido (nativo en host) | Mismo PostgreSQL |
| Acceso | Prod publico / Staging privado | Solo Tailscale |

---

## Seguridad por Capas

### Capa 1: Red
- Tailscale Funnel expone SOLO el puerto 443
- La IP real del servidor NUNCA se expone
- No se abren puertos en el router
- UFW bloquea todo excepto Tailscale

### Capa 2: Nginx
- Rate limiting en login (5 intentos/min)
- `/web/database/` bloqueado en produccion
- Security headers (HSTS, X-Frame-Options, CSP)
- HTTPS forzado (redirect 80 -> 443)
- Dev/Staging solo accesibles desde IPs Tailscale

### Capa 3: Aplicacion
- `list_db = False` en produccion
- Passwords de admin unicos por entorno
- Crons y mail desactivados en staging/dev

### Capa 4: Base de Datos
- PostgreSQL solo escucha en 127.0.0.1
- Autenticacion SCRAM-SHA-256
- Sin acceso remoto

### Capa 5: Host
- Fail2ban con reglas Odoo y Nginx
- Actualizaciones automaticas de seguridad
- Todos los exporters en 127.0.0.1

---

## Flujo de Datos

### Peticion web publica (Prod)

```
Cliente internet
  -> Tailscale Relay (SSL termination)
  -> tailscale0 interface en el servidor
  -> Nginx :443 (security headers, rate limit, cache)
  -> Odoo Prod :8069 (aplicacion)
  -> PostgreSQL :5432 (datos)
```

### Peticion Tailscale (Dev/Staging/Grafana)

```
Dispositivo con Tailscale
  -> Tailscale mesh (WireGuard, cifrado E2E)
  -> tailscale0 interface
  -> Nginx :8443/:9443/:3443 (allow 100.64.0.0/10)
  -> Servicio correspondiente
```

---

## Componentes de Monitorizacion

| Componente | Rol | Puerto |
|---|---|---|
| Prometheus | Recolector de metricas, evaluador de alertas | 9090 |
| Grafana | Visualizacion de dashboards | 3000 |
| node-exporter | Metricas del servidor (CPU, RAM, disco, red) | 9100 |
| cAdvisor | Metricas de contenedores Docker | 8080 |
| postgres-exporter | Metricas de PostgreSQL | 9187 |
| nginx-exporter | Metricas de Nginx | 9113 |
