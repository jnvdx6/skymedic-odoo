# Guia de Tailscale
## Odoo Enterprise On-Premise - Skymedic

---

## Que es Tailscale

Tailscale crea una red privada (mesh VPN) entre tus dispositivos usando WireGuard.
En este proyecto se usa para:

1. **Funnel**: Exponer Odoo Prod a internet SIN abrir puertos en el router
2. **VPN mesh**: Acceso privado a Dev, Staging y Grafana desde cualquier lugar

---

## Como funciona Funnel

```
Cliente publico (cualquier persona en internet)
  |
  v https://tu-servidor.tu-tailnet.ts.net
  |
  v Tailscale relay servers (SSL automatico)
  |
  v Tu servidor -> Nginx :443 -> Odoo Prod :8069
```

- Tu IP real nunca se expone a internet
- No necesitas abrir puertos en tu router
- SSL gestionado automaticamente por Tailscale
- Solo el puerto 443 es publico, el resto es privado

---

## Instalacion en Dispositivos

### Linux

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### macOS

Descargar desde https://tailscale.com/download/mac

### Windows

Descargar desde https://tailscale.com/download/windows

### iOS / Android

Descargar "Tailscale" desde App Store / Google Play

---

## Verificacion

### En el servidor

```bash
# Ver estado
tailscale status

# Ver hostname
tailscale status --json | jq -r '.Self.DNSName'

# Ver Funnel
tailscale funnel status

# Ver IP Tailscale
tailscale ip -4
```

### En tu dispositivo

1. Instalar Tailscale
2. Conectarse a tu tailnet
3. Verificar que puedes hacer ping al servidor:
   ```bash
   ping tu-servidor.tu-tailnet.ts.net
   ```
4. Abrir en el navegador:
   - Dev: `https://tu-servidor.ts.net:8443`
   - Staging: `https://tu-servidor.ts.net:9443`
   - Grafana: `https://tu-servidor.ts.net:3443`

---

## Dominio Personalizado (Opcional)

Si quieres `odoo.skymedic.es` en vez de `tu-servidor.tu-tailnet.ts.net`:

1. Anadir CNAME en el DNS de skymedic.es:
   ```
   odoo.skymedic.es.  CNAME  tu-servidor.tu-tailnet.ts.net.
   ```

2. Instalar certbot para obtener certificados para el dominio personalizado:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d odoo.skymedic.es
   ```

3. Actualizar `server_name` en `/etc/nginx/sites-available/odoo-prod`

---

## Troubleshooting

### No se conecta

```bash
# Verificar estado
sudo tailscale status

# Reconectar
sudo tailscale down
sudo tailscale up
```

### Funnel no funciona

1. Verificar ACLs en Admin Console (atributo `funnel`)
2. Verificar que MagicDNS esta activo
3. Verificar que HTTPS certificates estan habilitados
4. Reiniciar: `sudo tailscale funnel --bg reset && sudo tailscale funnel --bg 443`

### Certificados expirados

```bash
sudo /opt/odoo/scripts/renew-certs.sh
```
