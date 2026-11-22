# Pasos exactos: del servidor al teléfono con Traccar (checklist)

Esta es la versión **corta y en orden** para conectar los teléfonos (los «buses») al servidor y recibir sus
posiciones en Odoo. Las explicaciones largas, las rutas reales, el plan de 10 recorridos y la lista de capturas
están en `docs/GUIA_TRABAJO_CAMPO.md`.

```
Teléfono (Traccar Client, datos 4G/5G) ──HTTPS──► Cloudflare ◄──túnel saliente── cloudflared_gps ──► traccar:5055
                                                                                                   │
                                                          Odoo (cada 1 min, API interna) ◄── traccar:8082
```

- Los teléfonos **no** están en la misma red que el servidor: solo necesitan Internet. El túnel le da al servidor
  una dirección pública HTTPS sin abrir puertos ni tener IP pública.
- Odoo habla con Traccar por la red interna de Docker (`http://traccar:8082`). **Si cambia la URL del túnel, en
  Odoo no hay que cambiar nada**; solo en los teléfonos.

Estado al 22/11/2026: los pasos **A** (Traccar y Odoo configurados) ya están hechos en la PC del servidor. Falta
desde el paso **B**. Credenciales: `config/traccar_credenciales.local` y `config/odoo_credenciales.local` en la PC
del servidor (no están en el repositorio).

---

## A. Configuración única — HECHA (20/11/2026). Solo revisar.

| # | Comprobación | Dónde | Debe verse |
| :-: | :-- | :-- | :-- |
| A1 | Traccar tiene administrador y 2 dispositivos | `http://localhost:8082` ▸ Dispositivos | `sgmtb-bus01` (id interno 1) y `sgmtb-bus02` (id interno 2) |
| A2 | Odoo apunta a Traccar | Odoo ▸ Telemetría GPS ▸ Ajustes Traccar | URL `http://traccar:8082`, usuario y contraseña del admin de Traccar |
| A3 | Cada bus tiene su dispositivo | Odoo ▸ Flota y Personal ▸ Buses de Pasajeros ▸ pestaña *GPS / Traccar* | `TB-DEMO-01` → 1, `TB-DEMO-02` → 2 (el **id interno**, no el identificador) |
| A4 | Zona horaria del usuario | Odoo ▸ Preferencias | `America/Guayaquil` |
| A5 | Sincronización automática sin errores | Odoo ▸ Telemetría GPS ▸ Log de sincronización | filas cada minuto, sin error |

Si hubiera que rehacer el servidor desde cero: `docs/DESPLIEGUE_EQUIPO.md` (restaura BD, Traccar y dispositivos
con los mismos IDs) y `docs/GUIA_TRABAJO_CAMPO.md` §1–§2.

## B. Levantar el servidor (cada día de recorridos)

En la PC del servidor, abrir **Docker Desktop** y esperar a que diga *running*. Luego, en Ubuntu (WSL):

```bash
cd ~/odoo16-docker
docker compose up -d                        # odoo16_web, odoo16_db, traccar_server
docker compose ps                           # todo en "Up"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8070/web/login   # 200
curl -s http://localhost:8082/api/server | head -c 80; echo                # JSON de Traccar
```

Si Odoo muestra una página en blanco o no ve los módulos después de reiniciar Windows: `docker restart odoo16_web`.

## C. Levantar el túnel y obtener la URL

```bash
docker compose --profile tunel up -d cloudflared-gps
sleep 10
docker compose logs cloudflared-gps | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1
```

- Copiar la URL (ej. `https://palabras-al-azar.trycloudflare.com`) y enviarla al grupo del equipo.
- **La URL cambia cada vez que el túnel se reinicia.** No apagar la PC ni reiniciar el contenedor durante la jornada.
- La PC debe quedar encendida, con Internet y sin suspenderse (Windows ▸ Energía ▸ «Nunca» suspender).

📸 A2-01 `docker compose ps` · A2-02 la línea del log con la URL.

## D. Probar el túnel sin teléfono (2 minutos)

Desde **otra red** (por ejemplo, un portátil conectado al hotspot de un teléfono):

```bash
URL=https://<la-url>.trycloudflare.com
curl -i "$URL/?id=sgmtb-bus01&lat=-1.2690&lon=-78.6250&speed=0&timestamp=$(date -u +%s)"
```

| Resultado | Significa |
| :-- | :-- |
| `HTTP/2 200` | El túnel llega a Traccar. Seguir. |
| `HTTP/2 400` | Llega a Traccar pero el identificador no existe: revisar que sea `sgmtb-bus01` |
| `502` / `530` / sin respuesta | El túnel está caído o la URL es vieja: repetir C |

⚠️ Esta prueba crea **una posición real** del dispositivo en ese punto. Hacerla con el teléfono en el lugar o
borrarla después en Traccar si se usan coordenadas inventadas; nunca dejarla dentro de un viaje evaluado.

📸 A2-06 la respuesta `200`.

## E. Configurar Traccar Client en cada teléfono

1. Instalar **Traccar Client** (Play Store / App Store; autor: Anton Tananaev).
2. Abrir la app y llenar:

   | Campo | Teléfono del bus 1 | Teléfono del bus 2 |
   | :-- | :-- | :-- |
   | Identificador del dispositivo | `sgmtb-bus01` | `sgmtb-bus02` |
   | URL del servidor | la URL del paso C, **sin puerto** | igual |
   | Precisión de ubicación | Alta | Alta |
   | Frecuencia (intervalo) | **30** segundos | **30** |
   | Distancia | 0 | 0 |
   | Ángulo | 0 | 0 |
   | Almacenamiento sin conexión (*offline buffering*) | activado | activado |

3. Permisos: ubicación **«Permitir siempre»**; quitar la app del ahorro de batería
   (Android: Ajustes ▸ Apps ▸ Traccar Client ▸ Batería ▸ **Sin restricciones**).
4. **Apagar el Wi-Fi** y dejar solo datos móviles (el enunciado pide red externa).
5. Activar **Servicio** (interruptor en la app). Debe decir «Servicio iniciado» y luego «Ubicación enviada».

Con un solo teléfono: se cambia el identificador entre `sgmtb-bus01` y `sgmtb-bus02` según el bus del recorrido.

📸 A2-04 pantalla de configuración · A2-05 barra de estado con 4G/5G y sin Wi-Fi + servicio iniciado.

## F. Verificar que los datos llegan (antes de salir)

| # | Dónde | Debe verse (≤ 1 minuto) |
| :-: | :-- | :-- |
| F1 | Traccar `http://localhost:8082` | El dispositivo **Online** (verde) y su punto en el mapa |
| F2 | Odoo ▸ Telemetría GPS ▸ Log de sincronización | Una fila con *nuevas ≥ 1* |
| F3 | Odoo ▸ Telemetría GPS ▸ Posiciones GPS | Las posiciones con lat, lon, velocidad y hora |
| F4 | Odoo ▸ Flota y Personal ▸ Buses de Pasajeros ▸ el bus | *Estado de señal* = **Con señal**, última posición y fecha |
| F5 | Odoo ▸ el bus ▸ **Sincronizar ahora** (2 veces) | La 2.ª vez: *0 nuevas* y *duplicados descartados ≥ 1* (evidencia de «sin duplicados») |

📸 A2-03 Traccar con el dispositivo Online · A3-03 log de sincronización · A3-04 posiciones.

## G. Hacer un recorrido

1. Odoo ▸ **Operación de Viajes ▸ Viajes y Despachos ▸ Nuevo**: ruta, bus, conductor, fecha y **hora de salida = la hora real
   a la que van a salir**. En *Observaciones*: «Recorrido real #N – escenario: …». ▸ **Programar Despacho**.
2. En la parada 1: Traccar Client con el servicio iniciado.
3. Odoo ▸ el viaje ▸ **Iniciar Recorrido**. Solo cuentan las posiciones posteriores a este clic.
4. Durante el recorrido, en la PC: **En vivo** (línea con el bus, próxima parada y cuenta regresiva con el punto
   **verde** = GPS en vivo), o *Telemetría GPS ▸ Mapa de Buses*. Las paradas pasan a *Atendida – GPS*.
5. En la última parada: Odoo ▸ **Finalizar Viaje**. Se evalúa solo: *Cumple / Incumple* + incidencias.
6. Traccar Client ▸ detener el servicio.

Escenarios de incumplimiento (salida tarde, parada omitida, desvío, pérdida de señal…): tabla en
`docs/GUIA_TRABAJO_CAMPO.md` §6. Para «pérdida de señal» se **detiene el servicio** 5 min (el modo avión no sirve:
la app guarda y reenvía).

## H. Al terminar la jornada

1. Odoo ▸ Calidad del Servicio ▸ **Verificar exactitud Traccar** (📸 A3-06).
2. Dashboard con el filtro **Datos: Solo reales** (📸 A8-01).
3. Apagar el túnel si no se va a usar: `docker compose stop cloudflared-gps`.
4. Respaldar la BD: `docker exec odoo16_db pg_dump -U odoo -Fc transporte_universitario_gc > backups/transporte_universitario_gc_campo_$(date +%Y%m%d).dump`

## Problemas frecuentes

| Síntoma | Solución |
| :-- | :-- |
| El teléfono dice «error al enviar» | URL vieja (el túnel se reinició): repetir C y actualizar la app. URL con `http://` o con puerto: debe ser `https://…` sin puerto |
| Traccar recibe pero Odoo no | El bus tiene el identificador (`sgmtb-bus01`) en vez del id interno (1); revisar el log de sincronización |
| Llegan posiciones pero el viaje no avanza | Se pulsó *Iniciar Recorrido* tarde, o el viaje no está *En Ruta* |
| Todas las paradas «omitidas» | Intervalo de la app en 300 s (poner 30), lat/lon invertidas o radio de parada muy pequeño |
| Todo «atrasado» ~5 h | Zona horaria del usuario distinta de `America/Guayaquil` |
| Odoo en blanco tras reiniciar Windows | `docker restart odoo16_web` |
