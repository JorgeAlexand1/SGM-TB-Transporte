# Guía de Trabajo de Campo: Traccar, Rutas Reales, Recorridos y Evidencias

Esta guía cubre lo que falta del proyecto y requiere el teléfono: actividades **A2** (conectividad externa),
**A3** (integración con datos reales), **A4** (rutas reales), **A5** (≥ 10 recorridos documentados) y las
fotos de evidencia de **A6** y **A8**. El software ya está terminado y probado; aquí solo se configura, se sale
a recorrer y se captura.

**Estado al 20/11/2026:** §1 y §2 **ya están hechos** en la PC del servidor: Traccar tiene administrador y dos
dispositivos (`sgmtb-bus01` → `TB-DEMO-01`, `sgmtb-bus02` → `TB-DEMO-02`), Odoo está conectado y la
sincronización automática corre cada minuto sin errores. El túnel rápido de Cloudflare se probó desde Internet
(Traccar respondió a través de Cloudflare). Hay 0 posiciones reales: falta salir con el teléfono (§3 en adelante). Las rutas `DEMO-RUT-*` son de
demostración (nombres y tiempos ficticios) y **no** se usan para los recorridos reales.

---

## 0. Qué se puede hacer ya, sin salir a la calle

| Tarea | Quién | Sección |
| :--- | :--- | :--- |
| ~~Configurar Traccar (admin, dispositivos) y conectarlo a Odoo~~ **hecho** | — | §1, §2 |
| Prueba de escritorio con `curl` (valida toda la cadena sin teléfono) | misma persona | §4 |
| Elegir las 3 rutas reales y tomar las coordenadas de las paradas | todo el equipo | §5 |
| Análisis SonarQube | cualquiera | `docs/CALIDAD_SOFTWARE.md` |
| Instalar Traccar Client en 1–2 teléfonos | dueños de los teléfonos | §3 |

---

## 1. Preparar Traccar (una sola vez) — HECHO el 20/11/2026

Las credenciales del administrador y los identificadores están en `config/traccar_credenciales.local` de la PC
del servidor (archivo ignorado por git: **no lo suban**). Los pasos siguientes quedan como referencia por si hay
que rehacer el servidor.

1. Abrir `http://localhost:8082`.
   - Si pide registrarse: el **primer usuario que se registra queda como administrador**. Usen un correo del
     equipo y una contraseña fuerte, y no la suban al repositorio.
   - Si ya existe un usuario (lo creó el Integrante 3 al probar el módulo), pídanle las credenciales.
2. **Crear los dispositivos**, uno por bus, en *Dispositivos ▸ +*:

   | Nombre | Identificador (lo escriben en el teléfono) | Bus en Odoo |
   | :--- | :--- | :--- |
   | `Bus TB-DEMO-01` | `sgmtb-bus01` | `TB-DEMO-01` (ID interno 1) |
   | `Bus TB-DEMO-02` | `sgmtb-bus02` | `TB-DEMO-02` (ID interno 2) |

   El enunciado pide 2 vehículos registrados. Con **un solo teléfono** se puede simular el otro bus: se cambia
   el *Identificador* en Traccar Client antes de cada recorrido (un dispositivo solo puede estar en un bus).
3. **Anotar el ID interno** de cada dispositivo: es un número (1, 2, …), distinto del identificador. Se ve en
   `http://localhost:8082/api/devices` con la sesión iniciada, o en la URL al editar el dispositivo.
4. *(Opcional; ahora Odoo usa usuario y contraseña)* **Generar un token de API:** menú de usuario ▸ *Configuración / Cuenta* ▸ *Token* ▸ generar (con una fecha de
   expiración posterior a la defensa) y copiarlo.

📸 **Evidencia A2-03:** lista de dispositivos en Traccar.

## 2. Conectar Odoo con Traccar — HECHO el 20/11/2026

Odoo quedó con URL `http://traccar:8082` y el usuario/contraseña del administrador de Traccar. Solo falta revisar
la zona horaria (paso 4) y tomar las capturas.

1. En Odoo: **Transporte en Buses ▸ Telemetría GPS ▸ Ajustes Traccar**.
   - *URL de Traccar*: `http://traccar:8082`. Es el nombre interno del contenedor, así que **no** se usa el túnel ni `localhost`.
   - *Token de API*: el del paso 1.4.
   - *Minutos para marcar sin señal*: 5. *Detección de paradas*: **Tramo entre muestras**.
   - Guardar.
2. **Flota y Personal ▸ Buses de Pasajeros ▸ TB-DEMO-01** ▸ pestaña *GPS / Traccar* ▸ *ID de dispositivo
   Traccar* = ID interno del paso 1.3. Repetir con `TB-DEMO-02`.
3. Botón **Sincronizar ahora** en el bus. Debe decir «Posiciones sincronizadas correctamente». Si falla, el
   mensaje indica si el problema es la URL o el token.
4. **Zona horaria:** en *Preferencias* del usuario debe estar `America/Guayaquil`. Si no, las horas programadas
   de las paradas se ven desplazadas.

📸 **Evidencia A3-01:** ajustes de Traccar en Odoo (con el token oculto). **A3-02:** pestaña GPS del bus con el ID.

## 3. Túnel de Cloudflare y Traccar Client

En la PC del servidor:
```bash
cd ~/odoo16-docker
docker compose --profile tunel up -d
docker compose logs cloudflared-gps | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com'
```
- La URL **cambia cada vez que el túnel se reinicia**. No apaguen la PC durante una jornada de recorridos; si
  se reinicia, actualicen la URL en el teléfono.
- La PC debe seguir encendida y conectada mientras recorren: es el servidor.

En el teléfono, instalar **Traccar Client** (Play Store / App Store) y configurar:

| Campo | Valor |
| :--- | :--- |
| Identificador del dispositivo | `sgmtb-bus01` (o `sgmtb-bus02`) |
| URL del servidor | la URL `https://…trycloudflare.com` (sin puerto) |
| Precisión | Alta |
| Frecuencia / intervalo | **30 s**. Nunca dejen los 300 s por defecto: se pierden paradas (ver `MEJORA_CONTINUA.md`) |
| Distancia / ángulo | 0 |
| Batería | quitar la app del ahorro de batería (Android: *Ajustes ▸ Apps ▸ Traccar Client ▸ Batería ▸ Sin restricciones*) |
| Permiso de ubicación | «Permitir siempre» |

📸 **A2-01:** `docker compose ps` con odoo, db, traccar y cloudflared en *Up*. **A2-02:** log de cloudflared
con la URL. **A2-04:** pantalla de configuración de Traccar Client.

## 4. Prueba de escritorio (antes de salir)

Desde cualquier computador, **sin estar en la red de la casa** (por ejemplo, con el hotspot de otro teléfono),
simulen un reporte del teléfono por el túnel:
```bash
URL=https://<la-url>.trycloudflare.com
curl -i "$URL/?id=sgmtb-bus01&lat=-1.2690&lon=-78.6250&speed=0&timestamp=$(date -u +%s)"
```
- Respuesta esperada: `200`. En Traccar el dispositivo pasa a *Online*.
- En Odoo, en 1 minuto (o con *Sincronizar ahora*): **Telemetría GPS ▸ Posiciones GPS** muestra la posición, y
  **Log de sincronización** muestra 1 posición nueva.
- Pulsen **Sincronizar ahora** otra vez en el bus. Cada sincronización vuelve a pedir el último minuto a Traccar,
  así que el log debe mostrar **0 nuevas** y **duplicados descartados ≥ 1**. Es la evidencia de «sin duplicados».

Si esto funciona, la cadena teléfono → túnel → Traccar → Odoo está lista.

## 5. Definir las 3 rutas reales

Requisito mínimo: **3 rutas, 4 paradas (puntos de control) por ruta**, con horario programado. Recomendado:
recorridos que puedan hacer en 15–30 min (a pie, en bicicleta, en auto o en el propio bus universitario),
cerca del campus.

**Tomar las coordenadas de cada parada:**
- En el sitio: Google Maps ▸ mantener presionado el punto ▸ copiar `-1.xxxxxx, -78.xxxxxx`.
- O desde la PC: clic derecho en Google Maps ▸ copiar coordenadas.
- Use 6 decimales. Separen las paradas al menos 200 m.

**Radio de detección:** 30–40 m en calles normales; **50 m** en paradas que estén en un giro cerrado o en una
avenida rápida (lección del PDCA).

**Tiempos:** hagan un **recorrido de reconocimiento** por ruta (sin evaluar o descartado) y anoten los minutos
desde el origen hasta cada parada. Esos son los `tiempo_desde_origen_min`. Si inventan los tiempos, todo sale
«atrasado» o «adelantado».

**En Odoo** (*Rutas y Paradas*):
1. *Paradas ▸ Nuevo*: código `UTA-P01…`, nombre real, latitud, longitud, radio.
2. *Líneas y Rutas ▸ Nuevo*: código `UTA-R1…`, nombre, tipo, tiempo estimado total, secuencia de paradas con los
   minutos desde el origen. Luego pulsen *Sugerir por paradas* y ajusten la **distancia estimada** a la distancia
   real por calles (Google Maps ▸ «Cómo llegar» da los km).
3. Después del primer recorrido bueno de cada ruta: abrir el viaje ▸ **Usar como trazado de referencia**. Desde
   ahí, las desviaciones se miden contra las calles reales y no contra líneas rectas.

Plantilla para llenar en equipo:

| Ruta | Parada | Nombre | Latitud | Longitud | Radio (m) | Min. desde origen |
| :-- | :-: | :-- | :-- | :-- | :-: | :-: |
| UTA-R1 | 1 | | | | | 0 |
| UTA-R1 | 2 | | | | | |
| UTA-R1 | 3 | | | | | |
| UTA-R1 | 4 | | | | | |
| UTA-R2 | 1 … 4 | | | | | |
| UTA-R3 | 1 … 4 | | | | | |

📸 **A4-01:** lista de rutas (origen, destino, distancia, tiempo). **A4-02:** formulario de una ruta con sus 4+
paradas. **A4-03:** lista de paradas con coordenadas.

## 6. Plan de recorridos reales (≥ 10)

El enunciado pide recorridos normales **y** con incumplimientos. La mayoría de escenarios se pueden provocar a
propósito en la calle:

| # | Ruta | Bus | Escenario | Cómo provocarlo | Resultado esperado en Odoo |
| :-: | :-- | :-- | :-- | :-- | :-- |
| 1 | R1 | 01 | Puntual | Salir a la hora y seguir la ruta | Cumple, sin incidencias |
| 2 | R2 | 02 | Puntual | Igual | Cumple |
| 3 | R3 | 01 | Puntual | Igual (mismo bus, otra ruta y otro horario) | Cumple |
| 4 | R1 | 02 | Salida tarde | Programar 8:00 y pulsar *Iniciar* a las 8:10 | Retraso salida + paradas + llegada |
| 5 | R2 | 01 | Lento | Esperar ~3 min en cada parada | Retrasos crecientes + diferencia de tiempo |
| 6 | R3 | 02 | Parada omitida | Pasar por una calle paralela a > 100 m de la parada 2 | Parada omitida |
| 7 | R1 | 01 | Desvío | Tomar una calle a > 200 m de la ruta durante ≥ 2 min | Desviación de la ruta |
| 8 | R2 | 02 | Incompleto | Llegar solo a la parada 3 y pulsar *Finalizar* | Incompleto + paradas omitidas |
| 9 | R3 | 01 | Pérdida de señal | En mitad de un tramo, **Detener servicio** en Traccar Client 5 min y volver a iniciarlo | Pérdida de señal GPS |
| 10 | R1 | 02 | Puntual (2.º bus) | Igual que el 1 | Cumple |

⚠️ **Pérdida de señal:** el *modo avión* **no** sirve. Traccar Client guarda las posiciones sin conexión y las
envía después, así que no queda hueco. Hay que **detener el servicio** en la app.

Si algún escenario no se puede hacer físicamente, el enunciado permite usar datos simulados identificados como
tales: ya existen 10 en el sistema (filtro «Solo simulados»).

## 7. Procedimiento de cada recorrido (checklist)

**Antes**
- [ ] PC del servidor encendida, `docker compose ps` todo *Up*, URL del túnel vigente en el teléfono.
- [ ] Teléfono con **Wi-Fi apagado**, datos móviles activos y batería > 40 %.
- [ ] En Odoo: *Viajes y Despachos ▸ Nuevo*. Ruta, bus, conductor, fecha, **hora de salida = la hora real a la
      que van a salir**. En *Observaciones* anotar «Recorrido real #N – escenario: …». ▸ **Programar Despacho**.

**Al salir (estando en la parada 1)**
- [ ] Traccar Client ▸ **Iniciar servicio**.
- [ ] En Odoo, en el viaje ▸ **Iniciar Recorrido**. Solo se asocian al viaje las posiciones posteriores a este clic.

**Durante**
- [ ] Seguir la ruta y provocar el escenario si corresponde.
- [ ] Alguien en la PC puede mostrar el *Mapa de Buses* y el viaje (paradas pasando a *Atendida – GPS*).

**Al terminar (en la última parada o donde corte el escenario)**
- [ ] En Odoo ▸ **Finalizar Viaje**. Se evalúa solo y aparece *Cumple / Incumple* con sus incidencias.
- [ ] Traccar Client ▸ Detener servicio.
- [ ] Tomar las capturas de §8.3 de este recorrido.

## 8. Evidencias (capturas)

Guárdenlas con el prefijo de la actividad, por ejemplo `A5-R04-incidencias.png`, en una carpeta compartida (no en
el repositorio, salvo las que vayan al informe).

### 8.1 Infraestructura (una vez)
| Código | Captura |
| :-- | :-- |
| A2-01 | `docker compose ps` con todos los servicios *Up* |
| A2-02 | Log de cloudflared con la URL `trycloudflare.com` |
| A2-03 | Traccar: dispositivos *Online* |
| A2-04 | Teléfono: configuración de Traccar Client (URL https, 30 s) |
| A2-05 | Teléfono: barra de estado **sin Wi-Fi y con 4G/5G** + Traccar Client con servicio iniciado (prueba de red externa) |
| A2-06 | Respuesta `200` del `curl` por el túnel (§4) |

### 8.2 Integración (una vez)
| Código | Captura |
| :-- | :-- |
| A3-01 | Ajustes Traccar en Odoo (token oculto) |
| A3-02 | Bus con ID de dispositivo, última posición, fecha de actualización y estado de señal |
| A3-03 | *Log de sincronización* con nuevas posiciones y duplicados descartados = evidencia de no duplicados |
| A3-04 | *Posiciones GPS* reales (lat, lon, velocidad, fecha) |
| A3-05 | Bus en *Sin señal* después de > 5 min sin reportes (datos desactualizados) |
| A3-06 | *Verificar exactitud Traccar* después de los recorridos: notificación con el % |

### 8.3 Por cada recorrido (×10)
| Código | Captura |
| :-- | :-- |
| A5-Rnn-viaje | Formulario del viaje: ruta, bus, horas programadas y reales, estado |
| A5-Rnn-paradas | Pestaña *Control de paradas*: hora real, retraso, puntualidad, método GPS |
| A5-Rnn-mapa | Botón *Ver mapa GPS*: trazado y paradas en color |
| A5-Rnn-evaluacion | Pestaña *Evaluación de calidad* (resultado, retrasos, distancias, desvío) |
| A6-Rnn-incidencias | Incidencias generadas, con la regla aplicada (solo los de incumplimiento) |
| A5-Rnn-pdf | Botón *Informe PDF* (guardar el PDF) |

### 8.4 Dashboard e indicadores (al final)
| Código | Captura |
| :-- | :-- |
| A8-01 | Dashboard filtro **Solo reales**: KPIs de transporte y de calidad del software |
| A8-02 | Tabla de buses (ubicación, ruta en curso, paradas, retraso, desvío) **durante** un recorrido |
| A8-03 | Comparación entre rutas y evolución por día |
| A8-04 | Pareto de incidencias |
| A8-05 | Dashboard antes y después de registrar un recorrido nuevo (los indicadores cambian) |
| A7-01 | *Análisis de recorridos* (pivot) y consultas SQL de `docs/METRICAS.md §4` coincidiendo con el dashboard |

## 9. Después de los recorridos
1. **Calidad del Servicio ▸ Verificar exactitud Traccar:** calcula la exactitud real Traccar ↔ Odoo.
2. Actualizar `docs/METRICAS.md §3` con los valores del dashboard filtrado **Solo reales**, sin mezclarlos
   con los simulados.
3. Llenar la tabla de SonarQube en `docs/CALIDAD_SOFTWARE.md`.
4. Agregar a `docs/MEJORA_CONTINUA.md` (PDCA, «Próximo ciclo») cómo funcionó el intervalo de 30 s en la calle.
5. Ensayar el guion de `docs/GUIA_DEMOSTRACION.md` (en la defensa se hace 1 recorrido en vivo).

## 10. Problemas frecuentes
| Síntoma | Causa / solución |
| :-- | :-- |
| Traccar no recibe nada del teléfono | URL vieja del túnel (cambia al reiniciar); ¿Wi-Fi desactivado y datos activos?; servicio de la app iniciado |
| Traccar recibe, pero Odoo no | Bus sin *ID de dispositivo* o con el identificador en lugar del ID interno; URL de Odoo debe ser `http://traccar:8082`; token vencido. Revisar *Log de sincronización* |
| Las posiciones llegan, pero no al viaje | Se pulsó *Iniciar Recorrido* después de moverse, o el viaje no está *En Ruta* |
| Todas las paradas «omitidas» | Intervalo de la app en 300 s; coordenadas mal copiadas (lat/lon invertidas); radio muy pequeño |
| Todo sale «atrasado» por ~5 h | Zona horaria del usuario de Odoo distinta de `America/Guayaquil` |
| Todo sale «atrasado» por unos minutos | Los minutos desde el origen de la ruta no se midieron con el recorrido de reconocimiento |
| Desvío en un recorrido normal | Aún no se fijó el trazado de referencia (se compara contra líneas rectas): usar *Usar como trazado de referencia* con un recorrido bueno, o subir el corredor de la ruta |
| No se puede programar el viaje | El bus no está *Disponible*, la licencia del conductor está vencida o hay solapamiento con otro viaje del mismo bus |
