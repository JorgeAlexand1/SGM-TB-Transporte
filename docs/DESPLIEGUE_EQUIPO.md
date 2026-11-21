# Despliegue para el equipo: qué instalar, para qué sirve cada cosa y cómo quedar igual al servidor

Esta guía deja la PC de cualquier integrante **idéntica** a la PC servidor del proyecto: mismo código, mismos
módulos, mismos datos (rutas, paradas, buses, viajes, incidencias) y mismas credenciales.

> 🔒 **Las contraseñas NO están en este repositorio** (es público). Están en `CREDENCIALES.txt`, dentro del
> paquete que el responsable del servidor comparte por un canal privado del equipo. Nunca las suban a GitHub,
> ni en un commit, ni en un issue, ni en un PR.

---

## 1. Qué se despliega exactamente

**Se instala un solo módulo: `transporte_ui`.** Arrastra automáticamente a los otros tres (y a `fleet` de Odoo):

```
transporte_ui  ──►  transporte_calidad  ──►  transporte_gps_traccar  ──►  transporte_core  ──►  fleet (Odoo)
```

| Módulo | Para qué sirve | Qué se ve en Odoo |
| :--- | :--- | :--- |
| `transporte_core` | Buses (sobre **Flota** de Odoo), conductores, rutas (origen, destino, distancia), paradas con coordenadas y radio, horarios y viajes (asignar ruta + bus + fecha/hora). | *Flota y Personal*, *Rutas y Paradas*, *Viajes* |
| `transporte_gps_traccar` | Conexión con Traccar: trae las posiciones cada minuto sin duplicados, detecta buses sin señal, marca paradas visitadas por geocerca y dibuja el mapa. | *Telemetría GPS* (Mapa de Buses, Posiciones GPS, Log de sincronización, Ajustes Traccar) |
| `transporte_calidad` | Reglas de incumplimiento (retrasos, paradas omitidas, desviación, recorrido incompleto, pérdida de señal), incidencias, las 12 métricas, dashboard, mapa de rutas, informe PDF y generador de recorridos **simulados**. | *Calidad del Servicio* (Dashboard, Mapa de rutas, Incidencias, Análisis de recorridos, Calidad del software, Verificar exactitud Traccar, Generar recorridos simulados) |
| `transporte_ui` | La cara del sistema: pantalla **Inicio** con indicadores en vivo, login SGM-TB, colores y menú simplificado. | *Inicio* (primera pantalla al entrar) |

**No instalen** otros addons que tengan en su carpeta `addons/` (`math_operations`, `taller2_gc`,
`techstore_sonarqube`, `practicaUnidad4`…): son de otras materias y no forman parte del proyecto.

## 2. Para qué sirve cada servicio (`docker compose`)

| Contenedor | Puerto en la PC | Para qué sirve | ¿Siempre encendido? |
| :--- | :--- | :--- | :--- |
| `odoo16_web` | `8070` | Odoo 16 con los 4 módulos: lo que usan los usuarios y lo que se muestra en la defensa. | Sí |
| `odoo16_db` | — (interno) | PostgreSQL 15: guarda todo (la BD del proyecto es `transporte_universitario_gc`). | Sí |
| `traccar_server` | `8082` (web/API), `5055` (GPS) | Recibe las posiciones del teléfono (Traccar Client, protocolo OsmAnd) y Odoo las consulta por su API. | Sí |
| `cloudflared_gps` | — | **Túnel de Cloudflare** que publica el puerto GPS en una URL `https://…trycloudflare.com`, para que el teléfono envíe por **datos móviles** sin IP pública. Perfil `tunel`. | Solo en recorridos y en la defensa |
| `cloudflared_odoo` | — | Túnel opcional para abrir Odoo desde fuera de la casa. Perfil `tunel`. ⚠️ Expone el login de Odoo a Internet. | Solo si hace falta |
| `cloudflared_fijo` | — | Túnel con nombre propio (requiere cuenta Cloudflare y `CLOUDFLARE_TUNNEL_TOKEN`). Perfil `tunel-fijo`. | Opcional |

**Una sola PC es el servidor oficial** de los recorridos: el teléfono envía a la URL del túnel de esa PC, y
solo esa BD recibe las posiciones reales. Las copias del resto del equipo sirven para desarrollar, probar y
ensayar la demostración.

## 3. Paquete que entrega el responsable del servidor

Carpeta `SGM-TB_paquete_equipo` (se comparte por Drive/WhatsApp del equipo, **no** por GitHub):

| Archivo | Contenido |
| :--- | :--- |
| `transporte_universitario_gc.dump` | Copia de la BD del proyecto (formato `pg_dump -Fc`). |
| `filestore_transporte_universitario_gc.tar.gz` | Archivos adjuntos de esa BD (imágenes, informes, recursos). |
| `CREDENCIALES.txt` | Usuario y contraseña de Odoo y de Traccar, e identificadores de los dispositivos. |

Para regenerarlo con datos nuevos (en la PC servidor, dentro de `~/odoo16-docker`):
```bash
OUT=~/SGM-TB_paquete_equipo && mkdir -p $OUT   # cualquier carpeta sirve
docker exec odoo16_db pg_dump -U odoo -Fc transporte_universitario_gc > $OUT/transporte_universitario_gc.dump
docker exec odoo16_web tar czf - -C /var/lib/odoo/filestore transporte_universitario_gc \
  > $OUT/filestore_transporte_universitario_gc.tar.gz
```

## 4. Instalación idéntica, paso a paso

Requisitos: Docker Desktop (con WSL2 en Windows), Git y el paquete de la sección 3.

### 4.1 Código y configuración
```bash
git clone https://github.com/JorgeAlexand1/SGM-TB-Transporte.git ~/odoo16-docker
cd ~/odoo16-docker
git switch develop                       # rama con todo integrado
cp .env.example .env                     # cambien POSTGRES_PASSWORD por una propia (es local)
cp config/odoo.conf.example config/odoo.conf   # cambien admin_passwd por una propia (es local)
docker compose up -d                     # odoo16_web, odoo16_db y traccar_server
```
> Si ya habían clonado antes del 20/11/2026: el historial se reescribió. En vez de `git pull`, ejecuten
> `git fetch origin && git switch develop && git reset --hard origin/develop`.

### 4.2 Restaurar la BD del proyecto (mismos datos y mismo usuario de Odoo)
Copien los dos archivos del paquete a `~/odoo16-docker` y ejecuten:
```bash
DB=transporte_universitario_gc
docker exec odoo16_db createdb -U odoo $DB
docker exec -i odoo16_db pg_restore -U odoo -d $DB --no-owner < $DB.dump
docker exec -i odoo16_web bash -c "mkdir -p /tmp/fs && tar xzf - -C /tmp/fs && \
  mkdir -p /var/lib/odoo/filestore && rm -rf /var/lib/odoo/filestore/$DB && \
  mv /tmp/fs/$DB /var/lib/odoo/filestore/$DB && rm -rf /tmp/fs" < filestore_$DB.tar.gz
docker restart odoo16_web
```
Si `createdb` dice que la BD ya existe y quieren reemplazarla:
`docker exec odoo16_db dropdb -U odoo --force transporte_universitario_gc` (borra su copia local).

### 4.3 Dejar Traccar igual (mismo usuario y mismos dispositivos)
Su Traccar empieza vacío. Con la contraseña de `CREDENCIALES.txt` (el primer usuario que se registra queda
como administrador):
```bash
TPW='<contraseña de Traccar de CREDENCIALES.txt>'
curl -X POST http://localhost:8082/api/users -H 'Content-Type: application/json' \
  -d "{\"name\":\"Administrador SGM-TB\",\"email\":\"admin@sgmtb.local\",\"password\":\"$TPW\"}"
curl -u "admin@sgmtb.local:$TPW" -X POST http://localhost:8082/api/devices -H 'Content-Type: application/json' \
  -d '{"name":"Bus TB-DEMO-01","uniqueId":"sgmtb-bus01"}'
curl -u "admin@sgmtb.local:$TPW" -X POST http://localhost:8082/api/devices -H 'Content-Type: application/json' \
  -d '{"name":"Bus TB-DEMO-02","uniqueId":"sgmtb-bus02"}'
```
Los dispositivos deben quedar con ID interno **1** y **2** (es lo que tienen asociado los buses en la BD
restaurada). Compruébenlo en `http://localhost:8082/api/devices` con la sesión iniciada. Odoo ya trae la URL
(`http://traccar:8082`) y el usuario/contraseña de Traccar, así que no hay que configurar nada más.

### 4.4 Comprobar que quedó igual
| Comprobación | Resultado esperado |
| :--- | :--- |
| Abrir `http://localhost:8070/web/login?db=transporte_universitario_gc` | Login SGM-TB; entra con el usuario de `CREDENCIALES.txt` |
| *Rutas*, *Análisis de recorridos* e *Incidencias* | 3 rutas (4 paradas cada una), 12 viajes, 22 incidencias |
| *Telemetría GPS ▸ Log de sincronización* (esperar 1–2 min) | Registros nuevos de `cron` **sin error** |
| `bash scripts/ejecutar_pruebas.sh` (opcional, ~5 min) | `RESULTADO: OK` |

## 5. Instalación limpia (sin el paquete, solo para desarrollar)
Si no tienen el paquete, pueden partir de una BD vacía (no quedará igual al servidor):
```bash
docker exec odoo16_web /entrypoint.sh odoo -d transporte_universitario_gc -i transporte_ui \
  --no-http --stop-after-init && docker restart odoo16_web
```
Luego creen rutas/paradas/buses a mano o con *Calidad del Servicio ▸ Generar recorridos simulados*.

## 6. Problemas frecuentes
| Síntoma | Causa | Solución |
| :--- | :--- | :--- |
| `localhost:8070/web` en blanco | El navegador quedó con sesión en **otra** BD (por ejemplo, de otra materia) | Entrar con `http://localhost:8070/web/login?db=transporte_universitario_gc` |
| Aparece el selector de bases de datos | Hay más de una BD en el servidor | Usar el mismo enlace con `?db=` |
| Odoo no encuentra los módulos tras reiniciar Windows | `/mnt/extra-addons` quedó vacío | `docker restart odoo16_web` |
| *Log de sincronización* con error de autenticación | La contraseña de Traccar no coincide con la guardada en Odoo | Corregirla en *Telemetría GPS ▸ Ajustes Traccar* |
| Horas desplazadas ~5 h | Zona horaria del usuario distinta de `America/Guayaquil` | *Preferencias* del usuario ▸ Zona horaria |

## 7. Qué sigue
El software está completo y probado. Lo que falta es el **trabajo de campo** con el teléfono (recorridos
reales por datos móviles a través del túnel): `docs/GUIA_TRABAJO_CAMPO.md`, desde la sección 3.
