# Guía de Integración Odoo ↔ Traccar (`transporte_gps_traccar`)

Módulo: `addons/transporte_gps_traccar` (depende solo de `transporte_core`; el core no lo conoce).

## 1. Qué hace

| Función | Dónde |
| :--- | :--- |
| Vincular bus ↔ dispositivo (`traccar_device_id`, único) | `fleet.vehicle`, pestaña **GPS / Traccar** |
| Historial de posiciones sin duplicados (`UNIQUE(traccar_position_id)`) | `transporte.gps.posicion` |
| Sincronización incremental (cron cada 1 min, solape de 1 min) | `fleet.vehicle._cron_sincronizar_traccar` |
| Recepción en tiempo real (forward de Traccar) | `POST /api/v1/traccar/webhook?db=<bd>` |
| Posiciones → viaje en curso; llegada a parada por geocerca (Haversine, `radio_deteccion` de la parada, hora = hora GPS, `metodo_registro='gps'`) | `transporte.viaje._procesar_geocercas` |
| Distancia recorrida, velocidad máx./media por viaje | campos calculados en `transporte.viaje` |
| Estado de señal: `con_senal` / `sin_senal` (> N min) / `sin_datos` | `fleet.vehicle.estado_senal`, cron cada 1 min |
| Log de cada sincronización (nuevas, duplicados, inválidas, ms, error) | `transporte.gps.sync.log` |
| Mapa Leaflet + OpenStreetMap (buses, trazado y paradas del viaje) | menú **Telemetría GPS ▸ Mapa de Buses** y botón **Ver mapa GPS** del viaje |

Una posición es *inválida* si Traccar la marca `valid=false`, o sus coordenadas están fuera de rango o son (0, 0). Se guarda (cuenta para la métrica de integridad) pero no mueve el bus, ni suma distancia ni dispara paradas.

## 2. Configuración

1. Instalar el módulo: `docker compose exec web odoo -d <bd> -i transporte_gps_traccar --stop-after-init` (o desde Aplicaciones).
2. **Transporte ▸ Telemetría GPS ▸ Ajustes Traccar**:
   - *URL de Traccar*: la URL HTTPS del túnel hacia el puerto **8082** (API/web).
   - *Token de API* (Traccar ▸ Cuenta ▸ Token) o usuario/contraseña.
   - *Minutos para sin señal*: 5 por defecto.
3. En cada bus, pestaña **GPS / Traccar**, poner el **id interno** del dispositivo (Traccar ▸ Dispositivos; no es el "identificador" que se escribe en el teléfono). Botón **Sincronizar ahora** para probar.
4. Traccar Client (teléfono): servidor = URL HTTPS del túnel hacia el puerto **5055**; identificador = el de Traccar; intervalo 10–30 s.

### Webhook opcional
En `traccar.xml`:
```xml
<entry key='forward.enable'>true</entry>
<entry key='forward.json'>true</entry>
<entry key='forward.url'>http://odoo:8069/api/v1/traccar/webhook?db=NOMBRE_BD</entry>
<entry key='forward.header.Authorization'>Bearer SECRETO</entry>
```
El secreto se define en Ajustes (*Secreto del webhook*). Sin secreto o con token erróneo responde 401. Es idempotente: reenviar la misma posición no duplica.

## 3. Pruebas

```bash
# Lógica pura (sin Odoo): 48 tests, cobertura 100 % de lib/
python -m pytest addons/transporte_gps_traccar/tests/pytest --cov=addons/transporte_gps_traccar/lib --cov-report=term-missing

# Integración en Odoo (Traccar simulado con mocks): 28 tests
docker exec odoo16_web odoo -d <bd> -u transporte_gps_traccar --test-enable \
  --test-tags /transporte_gps_traccar --no-http --stop-after-init \
  --db_host=db --db_user=odoo --db_password=<POSTGRES_PASSWORD>
```

Casos clave: 3 sincronizaciones seguidas → 0 duplicados; posición a 30 m/80 m con radio 50 m; límite exacto del radio y de los minutos de señal; payload malformado; error de Traccar registrado en el log; viaje finalizado conserva telemetría.

## 4. Traccar local para desarrollo
`docker-compose.yml` incluye el servicio `traccar` (API/web en `localhost:8082`, protocolo OsmAnd en `localhost:5055`).

```bash
docker compose up -d traccar
# 1.er usuario registrado = administrador (servidor nuevo): crear en http://localhost:8082
# Dispositivo: Traccar web ▸ Dispositivos (anotar su id numérico); el "identificador" es lo que usa el teléfono.
# Simular un teléfono (OsmAnd):
curl -X POST "http://localhost:5055/?id=<identificador>&lat=-1.2384&lon=-78.6215&speed=0&timestamp=$(date -u +%s)"
```
Desde el contenedor de Odoo, la URL de Traccar es `http://traccar:8082` (nombre del servicio). Usuario/contraseña o token se guardan en Ajustes de Odoo (base de datos), nunca en el repositorio.

## 5. Verificación realizada
- **Traccar real (contenedor 6.17.0)**: posiciones enviadas por el puerto 5055 → sincronizadas desde Odoo por la API REST. Primera sincronización: 5 nuevas; repetidas: 0 nuevas y duplicados descartados; una posición tardía se recuperó en la siguiente sincronización por el solape de 1 min; paradas 1 y 2 del viaje demo marcadas `atendida` por `gps` con la hora del GPS; bus `con_senal`.
- El bundle `web.assets_backend` compila e incluye la acción `transporte_gps_map`, su plantilla y el módulo JS; `gps_map.js` pasa `node --check`.
- Los tests de Odoo usan ids de posición en un rango alto (`ID_BASE`) para no chocar con posiciones reales en la misma BD (el UNIQUE es global).

## 6. Límites conocidos
- **Pendiente**: validar con un teléfono físico en datos móviles a través del túnel de Cloudflare (evidencia de A2/A5; requiere Cloudflare y el teléfono).
- El mapa (OWL + Leaflet desde CDN jsDelivr) no se ha visto renderizado en un navegador; requiere Internet en el cliente.
- Una posición que llegue a Traccar con más de 1 min de retraso respecto a la última sincronizada no se recuperaría por cron (sí por webhook).
- Las paradas se marcan por proximidad en cualquier orden; las reglas de retraso e incidencias (A6) son de otro integrante.
