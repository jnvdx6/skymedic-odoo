# Checklist de Puesta en Marcha
## Odoo Enterprise On-Premise - Skymedic

---

## Fase 1: Base del sistema
- [ ] Ubuntu 24.04 LTS instalado
- [ ] `install-system.sh` ejecutado
- [ ] Re-login tras instalar Docker
- [ ] `setup-directories.sh` ejecutado

## Fase 2: Tailscale
- [ ] Tailscale instalado y autenticado (`sudo tailscale up`)
- [ ] MagicDNS activado en Admin Console
- [ ] HTTPS certificates habilitados en Admin Console
- [ ] Funnel habilitado en ACLs
- [ ] `setup-tailscale.sh` ejecutado
- [ ] Certificados en `/etc/nginx/ssl/`
- [ ] Cron de renovacion configurado
- [ ] Tailscale instalado en dispositivos de acceso

## Fase 3: PostgreSQL
- [ ] `setup-postgresql.sh` ejecutado
- [ ] Contrasena guardada en gestor seguro
- [ ] Contrasena actualizada en todos los .conf
- [ ] Bases de datos creadas (prod, dev, staging)
- [ ] `pg_hba.conf` configurado
- [ ] Servicio reiniciado y funcionando

## Fase 4: Entorno Dev
- [ ] `setup-dev-env.sh` ejecutado
- [ ] Codigo Odoo Community clonado
- [ ] Codigo Enterprise clonado (requiere credenciales)
- [ ] Custom addons copiados
- [ ] Virtualenv creado con dependencias
- [ ] `odoo-dev.conf` con contrasena correcta
- [ ] Servicio systemd activo
- [ ] Aliases anadidos a `.bashrc`
- [ ] VS Code `launch.json` instalado

## Fase 5: Entornos Prod / Staging
- [ ] Dockerfile creado
- [ ] Imagen construida con `build-image.sh`
- [ ] `docker-compose.yml` en su lugar
- [ ] Configs de Odoo (prod y staging) con contrasenas correctas
- [ ] Produccion levantada y funcionando
- [ ] Staging levantada y funcionando

## Fase 6: Nginx
- [ ] `setup-nginx.sh` ejecutado
- [ ] Sites creados (prod, dev, staging, grafana, nginx-status)
- [ ] `nginx -t` pasa sin errores
- [ ] Rate limiting en nginx.conf

## Fase 7: Verificar accesos
- [ ] `https://HOST.ts.net` -> Odoo Prod (publico)
- [ ] `https://HOST.ts.net:8443` -> Odoo Dev (Tailscale)
- [ ] `https://HOST.ts.net:9443` -> Staging (Tailscale)
- [ ] `https://HOST.ts.net:3443` -> Grafana (Tailscale)

## Fase 8: Monitorizacion
- [ ] `setup-monitoring.sh` ejecutado
- [ ] Prometheus arrancado
- [ ] node-exporter recogiendo metricas
- [ ] cAdvisor recogiendo metricas Docker
- [ ] postgres-exporter recogiendo metricas PG
- [ ] nginx-exporter recogiendo metricas
- [ ] Grafana accesible con dashboard Overview
- [ ] Dashboards comunidad importados (1860, 14282, 9628, 12708)
- [ ] Alertas configuradas

## Fase 9: Flujo DevOps
- [ ] `build-image.sh` probado
- [ ] `promote-to-staging.sh` probado end-to-end
- [ ] `deploy-to-prod.sh` probado
- [ ] `rollback-prod.sh` probado
- [ ] `clone-prod-to-dev.sh` probado

## Fase 10: Seguridad
- [ ] `setup-security.sh` ejecutado
- [ ] UFW habilitado
- [ ] Fail2ban activo con reglas Odoo + Nginx
- [ ] `list_db = False` en prod y staging
- [ ] Passwords en gestor seguro
- [ ] `/web/database/` bloqueado en Nginx prod
- [ ] Tailscale ACLs configurados

## Fase 11: Backups
- [ ] `backup-prod.sh` probado manualmente
- [ ] `restore-prod.sh` probado (en staging)
- [ ] Cron de backup diario configurado
- [ ] Verificar que backups se generan

## Fase 12: Documentacion
- [ ] Team informado de URLs de acceso
- [ ] Contrasenas documentadas en gestor seguro
- [ ] Procedimiento de rollback conocido
- [ ] Contacto de emergencia definido
