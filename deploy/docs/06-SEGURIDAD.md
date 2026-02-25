# Manual de Seguridad
## Odoo Enterprise On-Premise - Skymedic

---

## 1. Modelo de Seguridad

### Principio: Defensa en Profundidad

```
Internet
  |
  v
[Tailscale Funnel] -- Solo puerto 443, IP oculta
  |
  v
[UFW Firewall] -- deny all incoming, allow tailscale0
  |
  v
[Nginx] -- Rate limit, security headers, /web/database/ bloqueado
  |
  v
[Fail2ban] -- Ban IPs tras intentos fallidos
  |
  v
[Odoo] -- list_db=False, admin_passwd robusto
  |
  v
[PostgreSQL] -- Solo 127.0.0.1, SCRAM-SHA-256
```

---

## 2. Firewall (UFW)

### Configuracion actual

```bash
# Ver estado
sudo ufw status verbose

# Reglas aplicadas:
# - Default: deny incoming, allow outgoing
# - Allow in on tailscale0 (Tailscale mesh + funnel)
# - Allow SSH from 192.168.1.0/24 (LAN)
```

### Modificar reglas

```bash
# Anadir regla
sudo ufw allow from 192.168.X.0/24 to any port 22

# Eliminar regla
sudo ufw delete allow from 192.168.1.0/24 to any port 22

# Ver reglas numeradas
sudo ufw status numbered
sudo ufw delete 3
```

---

## 3. Fail2ban

### Jails configurados

| Jail | Que protege | maxretry | bantime |
|---|---|---|---|
| `odoo-login` | Fuerza bruta login Odoo | 3 intentos | 2 horas |
| `nginx-limit-req` | Rate limiting Nginx | 5 intentos | 1 hora |

### Comandos

```bash
# Estado general
sudo fail2ban-client status

# Estado de un jail
sudo fail2ban-client status odoo-login

# Desbanear IP
sudo fail2ban-client set odoo-login unbanip 1.2.3.4

# Ver IPs baneadas
sudo fail2ban-client get odoo-login banned
```

---

## 4. Nginx Security

### Headers de seguridad (Prod)

| Header | Valor | Proposito |
|---|---|---|
| X-Frame-Options | SAMEORIGIN | Prevenir clickjacking |
| X-Content-Type-Options | nosniff | Prevenir MIME sniffing |
| X-XSS-Protection | 1; mode=block | Filtro XSS del navegador |
| Strict-Transport-Security | max-age=31536000 | Forzar HTTPS |
| Referrer-Policy | strict-origin-when-cross-origin | Control de referrer |

### Rate limiting

- `/web/login`: 5 peticiones/minuto por IP
- Burst de 5 peticiones adicionales
- IPs excedentes reciben HTTP 429

### Bloqueo del Database Manager

```nginx
location ~* ^/web/database/ {
    deny all;
    return 404;
}
```

### Restriccion por IP (Dev/Staging/Grafana)

```nginx
allow 100.64.0.0/10;  # Solo IPs Tailscale
deny all;
```

---

## 5. Odoo Security

### Configuracion critica

| Parametro | Prod | Staging | Dev |
|---|---|---|---|
| `list_db` | False | False | True |
| `admin_passwd` | Unico, complejo | Unico | Simple |
| `proxy_mode` | True | True | True |

### Contrasenas

- Usar contrasenas de al menos 20 caracteres
- Diferentes para cada entorno
- Almacenar en gestor de contrasenas (Bitwarden, 1Password)

---

## 6. PostgreSQL Security

- Solo escucha en `127.0.0.1` (no accesible desde la red)
- Autenticacion `scram-sha-256`
- Usuario `odoo` sin privilegios de superuser
- Cada entorno usa su propia base de datos

---

## 7. Tailscale Security

### ACLs recomendados

En https://login.tailscale.com/admin/acls :

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["*:*"]
    }
  ],
  "nodeAttrs": [
    {
      "target": ["autogroup:member"],
      "attr": ["funnel"]
    }
  ]
}
```

Para entornos mas restrictivos:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["group:admin"],
      "dst": ["tag:odoo-server:8443,9443,3443"]
    },
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["tag:odoo-server:443"]
    }
  ]
}
```

---

## 8. Respuesta a Incidentes

### Fuerza bruta detectada

1. Verificar Fail2ban: `sudo fail2ban-client status odoo-login`
2. Verificar rate limiting en Nginx: `sudo tail /var/log/nginx/error.log`
3. Si persiste, banear IP manualmente: `sudo ufw deny from IP`

### Servicio comprometido

1. Desconectar de internet: `sudo tailscale funnel --bg reset`
2. Revisar logs: `docker logs odoo-prod`, `journalctl -u odoo-dev`
3. Cambiar todas las contrasenas
4. Restaurar desde backup limpio
5. Reconectar Funnel tras verificar

### Disco lleno

1. Limpiar backups: `find /opt/odoo/backups -mtime +7 -delete`
2. Limpiar Docker: `docker system prune -f`
3. Verificar logs: `du -sh /var/log/*`
4. Verificar filestore: `du -sh /opt/odoo/filestore/*`
