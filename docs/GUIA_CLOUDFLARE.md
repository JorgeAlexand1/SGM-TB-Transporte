# Conectividad Externa con Cloudflare Tunnel y Traccar Client (Actividad 2)

Objetivo: que el teléfono envíe posiciones **por datos móviles** (no por la Wi-Fi local) a Traccar, sin IP pública
ni puertos abiertos en el router.

```
Teléfono (Traccar Client) --HTTPS 443--> Cloudflare --túnel saliente--> cloudflared_gps --HTTP--> traccar:5055 (OsmAnd)
Odoo (web) --HTTP interno--> traccar:8082 (API REST)          [no necesita túnel: misma red Docker]
```

## 1. Levantar el túnel
```bash
docker compose up -d                       # odoo, postgres, traccar
docker compose --profile tunel up -d       # cloudflared_gps (+ cloudflared_odoo, opcional)
docker compose logs cloudflared-gps | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com'
```
La URL del túnel rápido cambia en cada arranque. Para la defensa conviene un **túnel con nombre** (URL fija):
crear el túnel en *Cloudflare Zero Trust ▸ Networks ▸ Tunnels*, publicar `gps.<dominio> → http://traccar:5055`
(y opcionalmente `odoo.<dominio> → http://web:8069`), copiar el token a `.env` (`CLOUDFLARE_TUNNEL_TOKEN=`) y
ejecutar `docker compose --profile tunel-fijo up -d`.

## 2. Protocolo y mecanismo de publicación (validación pedida en A2)
- Traccar Client usa el protocolo **OsmAnd**: peticiones HTTP `GET/POST /?id=<identificador>&lat=..&lon=..&timestamp=..&speed=..`
  que Traccar escucha en el puerto **5055**.
- Cloudflare termina **HTTPS** en el puerto 443 y lo reenvía por el túnel como HTTP al 5055: el teléfono habla
  HTTPS, Traccar recibe HTTP. Comprobación desde cualquier red:
  ```bash
  curl -i "https://<url-del-tunel>/?id=<identificador>&lat=-1.2384&lon=-78.6215&speed=0&timestamp=$(date -u +%s)"
  # Esperado: HTTP/2 200 y la posición visible en Traccar (http://localhost:8082)
  ```

## 3. Configurar Traccar Client (estándar del proyecto, resultado del PDCA)
| Campo | Valor |
| :--- | :--- |
| Identificador del dispositivo | el mismo «Identificador» del dispositivo en Traccar |
| Dirección del servidor | `https://<url-del-tunel>` (sin puerto) |
| Precisión de ubicación | Alta |
| Frecuencia | **30 s** (o 15 s); nunca el valor por defecto de 300 s |
| Distancia / Ángulo | 0 |
| Ahorro de batería | desactivado para la app |

En Odoo: **Transporte ▸ Flota y Personal ▸ Buses** → pestaña GPS → *ID de dispositivo Traccar* = id numérico
interno del dispositivo (Traccar ▸ Dispositivos). **Telemetría GPS ▸ Ajustes Traccar**: URL `http://traccar:8082`
y token o usuario/contraseña de Traccar.

## 4. Evidencias a capturar
1. `docker compose ps` con odoo, db, traccar y cloudflared en *Up*.
2. Log de cloudflared con la URL del túnel.
3. Teléfono con **Wi-Fi apagado** (indicador 4G/5G visible) y Traccar Client en *Servicio iniciado*.
4. Traccar web: el dispositivo *Online* y sus posiciones.
5. Odoo: **Telemetría GPS ▸ Log de sincronización** (nuevas posiciones, 0 duplicados), **Mapa de Buses** con el
   bus en verde, y el viaje con paradas *atendidas* por *GPS*.
6. **Calidad del Servicio ▸ Verificar exactitud Traccar** con el resultado (%).
