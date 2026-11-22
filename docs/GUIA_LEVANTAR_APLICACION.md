# Guía 1 — Levantar y probar la aplicación en la PC servidor (Windows)

Para quien administra la PC donde corren Odoo, Traccar y el túnel. El teléfono se configura en
[`GUIA_CLIENTE_CELULAR.md`](GUIA_CLIENTE_CELULAR.md). Esta guía se verificó el 22/11/2026 en Windows 11 con
Docker Desktop.

## 1. Requisitos

| Qué | Cómo comprobarlo |
| :--- | :--- |
| Docker Desktop **abierto** y con el motor corriendo | `docker info` no debe dar error |
| Git Bash (viene con Git for Windows) | Usar **Git Bash** para los comandos de esta guía |
| Python 3 (solo para las pruebas automáticas) | `python --version` |
| Puertos libres: **8070** (Odoo), **8082** (Traccar web/API), **5055** (GPS) | `netstat -ano \| grep -E ':(8070\|8082\|5055) '` sin resultados |
| ~8 GB de RAM libre y ~10 GB de disco | — |

> ⚠️ En Git Bash ejecute antes `export MSYS_NO_PATHCONV=1`. Sin eso convierte `/entrypoint.sh` en una ruta de
> Windows y `docker exec` falla.

## 2. Arranque

```bash
cd /c/Users/User/Desktop/SGM-TB-Transporte
export MSYS_NO_PATHCONV=1
cp -n .env.example .env              # solo la primera vez; luego definir contraseñas locales
docker compose up -d                 # Odoo, PostgreSQL y Traccar
docker compose ps                    # los 3 contenedores deben estar «Up»
```

Primera vez en una PC sin base de datos: crear la BD con los 4 módulos (un solo comando; `transporte_ui` arrastra
a los otros tres):
```bash
docker exec odoo16_web /entrypoint.sh odoo -d transporte_dev -i transporte_ui --no-http --stop-after-init
docker restart odoo16_web
```

Comprobaciones rápidas:

| Qué | Cómo | Esperado |
| :--- | :--- | :--- |
| Odoo | abrir http://localhost:8070 | pantalla de login SGM-TB |
| Traccar | abrir http://localhost:8082 | pantalla de Traccar |
| Módulos | `docker exec odoo16_db psql -U odoo -d transporte_dev -tAc "select name,state from ir_module_module where name like 'transporte%'"` | 4 filas `installed` |

**Usuario de Odoo:** `admin`. Si no recuerda la contraseña, restablézcala:
```bash
echo "env['res.users'].search([('login','=','admin')]).password='NUEVA_CLAVE'; env.cr.commit()" | \
 docker exec -i odoo16_web bash -c 'odoo shell -d transporte_dev --no-http --db_host=$HOST --db_user=$USER --db_password=$PASSWORD --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons'
```
No suba contraseñas al repositorio.

### Ajustes que no se pueden olvidar
1. **Zona horaria `America/Guayaquil`** en *Preferencias* del usuario (Odoo y Traccar guardan en UTC; con otra
   zona todo se ve ±5 h y los viajes salen «atrasados»).
2. **`db_name` en `config/odoo.conf`** (archivo local, no se sube a git): `db_name = transporte_dev`. Sin esto,
   tras reiniciar el contenedor los procesos automáticos (sincronizar Traccar cada minuto) no corren hasta que
   alguien abre la web.
3. **Traccar ↔ Odoo:** *Telemetría GPS ▸ Ajustes Traccar*: URL `http://traccar:8082` (nombre interno del
   contenedor; **no** `localhost` ni el túnel) y el usuario/contraseña del administrador de Traccar.

### Dispositivos GPS (ya creados en esta PC)

| Bus en Odoo | Dispositivo en Traccar | Identificador (lo escribe el teléfono) | ID interno |
| :--- | :--- | :--- | :-: |
| TB-DEMO-01 | Bus TB-DEMO-01 | `sgmtb-bus01` | 1 |
| TB-DEMO-02 | Bus TB-DEMO-02 | `sgmtb-bus02` | 2 |

El vínculo se ve en Odoo: *Flota y Personal ▸ Buses de Pasajeros ▸ bus ▸ pestaña GPS / Traccar ▸ ID de
dispositivo Traccar*.

## 3. Túnel de Cloudflare (para que el teléfono envíe por datos móviles)

```bash
docker compose --profile tunel up -d cloudflared-gps
docker compose logs cloudflared-gps | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1
```
- Esa URL `https://…trycloudflare.com` es la que se escribe en el teléfono. **Cambia cada vez que el túnel se
  reinicia.** No apague la PC durante los recorridos.
- Detener el túnel cuando no se use: `docker compose --profile tunel stop cloudflared-gps`.
- No levante `cloudflared-odoo` salvo que sea necesario: expone el login de Odoo a Internet.

## 4. Qué probar (checklist de aceptación del servidor)

| # | Prueba | Cómo | Resultado esperado |
| :-: | :--- | :--- | :--- |
| 1 | Servicios arriba | `docker compose ps` | odoo16_web, odoo16_db y traccar_server en *Up* |
| 2 | Login y pantalla de Inicio | http://localhost:8070 | Inicio con 4 KPIs, buses en ruta e incidencias frecuentes |
| 3 | Catálogo (A4) | *Rutas y Paradas ▸ Líneas y Rutas* | 3 rutas, cada una con ≥ 4 paradas, origen, destino, distancia y tiempo |
| 4 | Buses con GPS (A4) | *Flota y Personal ▸ Buses de Pasajeros* | TB-DEMO-01 y TB-DEMO-02 con su ID de dispositivo Traccar |
| 5 | Cadena GPS sin teléfono (A2/A3) | `curl "http://localhost:5055/?id=sgmtb-bus01&lat=-1.2690&lon=-78.6250&speed=0&timestamp=$(date -u +%s)"` | HTTP `200`; en ≤ 1 min aparece en *Telemetría GPS ▸ Posiciones GPS* |
| 6 | Sin duplicados (A3) | En el bus pulsar *Sincronizar ahora* dos veces; mirar *Log de sincronización* | 1.ª vez: 1 nueva; 2.ª: **0 nuevas** y duplicados descartados ≥ 1 |
| 7 | Túnel desde Internet (A2) | Desde otra red (hotspot de otro teléfono): `curl -i "https://<url>/?id=sgmtb-bus01&lat=-1.2690&lon=-78.6250&speed=0&timestamp=$(date -u +%s)"` | HTTP `200` |
| 8 | Viaje completo (A4–A6) | *Operación de Viajes ▸ Viajes ▸ Nuevo* → *Programar* → *Iniciar* → enviar posiciones sobre las paradas → *Finalizar* | Paradas *Atendida (GPS)*, resultado *Cumple/Incumple* e incidencias automáticas |
| 9 | Mapas (A3/A8) | *Telemetría GPS ▸ Mapa de Buses*; *Calidad del Servicio ▸ Mapa de rutas*; mapa dentro de un viaje | Posición/trazado visibles (sin Internet el fondo es gris pero los puntos se dibujan) |
| 10 | Dashboard (A7/A8) | *Calidad del Servicio ▸ Dashboard* (5 pestañas) | 8 KPIs de transporte + 4 de calidad del software; botón **Fórmulas**; cambian al registrar un viaje nuevo |
| 11 | Datos simulados identificados | Dashboard ▸ filtro «Solo simulados» / «Solo reales» | Los 10 recorridos simulados llevan etiqueta SIMULADO; nada simulado se muestra como real |
| 12 | Informe PDF | En un viaje finalizado: botón *Informe PDF* | PDF con paradas, retrasos e incidencias |

> 🧹 Las pruebas 5–7 dejan posiciones «reales» de prueba. Antes de la defensa, bórrelas en *Posiciones GPS*
> (filtro «Solo reales») para que el filtro «Solo reales» muestre únicamente datos del teléfono.

## 5. Pruebas automáticas (opcional, ~5 min)

```bash
bash scripts/ejecutar_pruebas.sh        # usa una BD desechable (sgmtb_test); no toca transporte_dev
```
Resultado esperado el 22/11/2026: pytest OK, 102 pruebas Odoo, rendimiento OK (máx. ~350 ms), 7 de interfaz y 2 de
integración en vivo con Traccar, y la última línea `RESULTADO: OK`.

Las pruebas de interfaz necesitan Chromium dentro del contenedor. Si el contenedor se recrea hay que reinstalarlo
(comando en [`PLAN_PRUEBAS.md`](PLAN_PRUEBAS.md) §1).

## 6. Problemas frecuentes

| Síntoma | Causa y solución |
| :--- | :--- |
| `failed to connect to the docker API` | Docker Desktop cerrado: ábralo y espere a «Engine running» |
| `docker exec … /entrypoint.sh` → «C:/Program Files/Git/entrypoint.sh» | Falta `export MSYS_NO_PATHCONV=1` |
| No llegan posiciones nuevas a Odoo | Cron parado (falta `db_name`, §2) o URL de Traccar mal en *Ajustes Traccar* |
| Horas desplazadas ~5 h | Zona horaria del usuario ≠ `America/Guayaquil` |
| El teléfono no conecta | La URL del túnel cambió: obtenga la nueva (§3) y actualícela en el teléfono |
| Un bus «no está Disponible» al programar | Tiene otro viaje *En curso* sin terminar: finalícelo o cancélelo |
| Pruebas de interfaz «omitidas» | Falta Chromium o `python3-websocket` en el contenedor |
