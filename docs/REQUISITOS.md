# Documento de Análisis y Requisitos (Actividad 1)
## Sistema de Monitoreo y Evaluación de Rutas de Transporte Universitario — SGM-TB

**Plataforma:** Odoo 16 Community + Traccar + Cloudflare Tunnel · **BD:** `transporte_universitario_gc`
**Módulos:** `transporte_core` (núcleo), `transporte_gps_traccar` (telemetría), `transporte_calidad` (incidencias, KPIs, dashboard)

---

## 1. Análisis del problema

| Necesidad detectada (enunciado) | Respuesta del sistema |
| :--- | :--- |
| No se conoce la ubicación de los buses | Sincronización Traccar → Odoo (cron 1 min + webhook), mapa en vivo y estado de señal |
| No se verifica el cumplimiento de rutas/horarios | Evaluación automática de cada recorrido contra paradas, horarios y corredor de la ruta |
| Retrasos en paradas | Retraso por parada = llegada real − hora programada, con tolerancia configurable |
| Desviaciones del recorrido | Distancia de cada posición GPS al trazado de referencia (corredor) |
| Falta de historial | Posiciones, viajes, paradas e incidencias persistidas en PostgreSQL |
| Sin detección automática de incumplimientos | 9 reglas automáticas que generan incidencias idempotentes |
| No se compara tiempo estimado vs real | Duración real vs estimada por viaje y promedio por ruta |
| Sin métricas de calidad del servicio | 8 KPIs de transporte + 4 de calidad del software calculados en vivo |
| Datos GPS inconsistentes | Rechazo de duplicados (UNIQUE), marcado de posiciones inválidas, señal desactualizada, verificación de exactitud contra Traccar |

**Actores:** Administrador de operaciones (grupo *Administrador de Operaciones*), usuario de consulta (*Usuario / Consulta*), conductor (Traccar Client en su teléfono), Traccar Server (sistema externo).

---

## 2. Requisitos funcionales

Prioridad: **A** = imprescindible para la evaluación, **M** = deseable. La columna *Verificación* remite a la matriz de pruebas (`docs/PLAN_PRUEBAS.md`).

| ID | Requisito | Prioridad | Criterios de aceptación | Verificación |
| :--- | :--- | :---: | :--- | :--- |
| RF-01 | **Gestión de vehículos**: registrar buses (placa, capacidad, tipo, estado operativo) sobre `fleet.vehicle`. | A | (1) No se acepta capacidad total ≤ 0 en un bus de pasajeros. (2) Solo buses *Disponibles* se pueden programar. (3) Mínimo 2 buses registrados. | CP-01, tests core |
| RF-02 | **Asociación bus ↔ dispositivo GPS** (`traccar_device_id`). | A | (1) Un dispositivo no puede estar en dos buses (restricción de exclusión). (2) Id negativo rechazado. | tests GPS |
| RF-03 | **Administración de múltiples rutas** con código, origen, destino, distancia estimada y tiempo estimado. | A | (1) Código único. (2) Origen/destino se derivan de la primera/última parada. (3) Distancia estimada ≥ 0 (botón «Sugerir por paradas»). (4) Mínimo 3 rutas. | CP-02 |
| RF-04 | **Registro de paradas (puntos de control)** con coordenadas WGS84 y radio de detección. | A | (1) Latitud ∈ [-90, 90], longitud ∈ [-180, 180]. (2) Radio > 0 m. (3) Mínimo 4 paradas por ruta. | CP-03, tests core |
| RF-05 | **Horarios programados**: minutos desde el origen por parada; la hora programada de cada parada se congela al programar el viaje. | A | Hora programada parada = salida programada + minutos desde origen; modificar la ruta no altera viajes ya programados. | tests core |
| RF-06 | **Asignación de recorridos**: ruta + bus + conductor + fecha/hora. Un mismo bus puede hacer distintas rutas en distintos horarios. | A | (1) Se rechaza solapamiento horario del bus o del conductor. (2) Licencia vencida rechazada. (3) Ruta sin paradas rechazada. | CP-04, tests core |
| RF-07 | **Seguimiento GPS**: sincronizar posiciones desde Traccar (API REST y webhook) sin duplicados. | A | (1) 3 sincronizaciones seguidas → 0 duplicados. (2) Webhook sin token → 401. (3) Posición (0,0) o fuera de rango → guardada como inválida, no mueve el bus. | CP-14, tests GPS |
| RF-08 | **Última posición y fecha de actualización** de cada bus; detección de datos desactualizados. | A | Bus sin posiciones en > N min (defecto 5) → *Sin señal*. | tests GPS |
| RF-09 | **Historial de posiciones y recorridos** consultable por bus y por viaje. | A | Cada posición queda asociada al viaje en curso del bus si su fecha GPS ≥ salida real. | tests GPS |
| RF-10 | **Registro automático de paradas visitadas** por geocerca (radio + tramo entre muestras). | A | (1) Posición dentro del radio → parada *atendida* con hora GPS y método *gps*. (2) Paso entre dos muestras se detecta e interpola (modo *segmento*). (3) No se interpola a través de huecos > 360 s. | CP-12 |
| RF-11 | **Detección de retrasos**: por parada, salida y llegada. | A | Ejemplo del enunciado: programada 08:15, tolerancia 5 min, llegada 08:23 → retraso de **8 min** e incidencia *Retraso en parada*. Límite inclusivo (5,0 min = puntual). | CP-05, CP-06 |
| RF-12 | **Detección de paradas omitidas y recorridos incompletos**. | A | Parada sin llegada al finalizar → *Parada omitida*. Destino no alcanzado o cancelación en ruta → *Recorrido incompleto*. | CP-07, CP-08 |
| RF-13 | **Diferencia tiempo estimado vs real**. | A | Recorrido completo con \|diferencia\| > 20 % **y** > 5 min → incidencia *Diferencia de tiempo*. | CP-09 |
| RF-14 | **Detección de desviaciones** contra un corredor de referencia. | A | ≥ 3 posiciones consecutivas a más del corredor (defecto 150 m) del trazado → *Desviación de la ruta*. Un salto aislado no cuenta. | CP-10 |
| RF-15 | **Detección de pérdida de señal GPS** durante el recorrido. | A | Hueco entre reportes > 3 min dentro del viaje (incluye bordes) → *Pérdida de señal*. | CP-10b |
| RF-16 | **Registro de incidencias** automáticas (idempotentes) y manuales, con estado y severidad. | A | (1) Reevaluar no duplica. (2) Una incidencia ya gestionada no se borra. (3) Las automáticas no se eliminan a mano (se descartan). | CP-15 |
| RF-17 | **Generación de métricas**: 8 de transporte y 4 de calidad del software, calculadas desde la BD. | A | Los valores del dashboard coinciden con los registros (prueba automática) y cambian al agregar recorridos. | CP-11, CP-16 |
| RF-18 | **Dashboard en Odoo** con ubicación de buses, rutas, historial, cumplimiento, puntualidad, retrasos, distancias, incidencias y comparación por ruta/periodo. | A | Renderiza sin errores JS en navegador headless; filtros por fecha/ruta/bus/origen de datos. | CP-17 (UI) |
| RF-19 | **Mapas**: posición actual de buses y trazado de un viaje con sus paradas. | A | Mapa Leaflet con trazado, radio de cada parada y color por estado. | tests GPS, manual |
| RF-20 | **Reportes**: informe PDF por recorrido, vistas pivot/gráfico de recorridos e incidencias. | M | Informe con horarios, paradas, desvío e incidencias. | CP-17 |
| RF-21 | **Recorridos de prueba simulados** identificados como tales. | M | Todo viaje/posición/incidencia simulada lleva `simulado = True`, cinta «SIMULADO» y filtro «Solo reales» en el dashboard; posiciones con id negativo. | CP-13 |
| RF-22 | **Tolerancias configurables** (retraso, adelanto, corredor, señal, duración). | A | Cambiar la tolerancia y «reevaluar» actualiza resultados e incidencias. | CP-15 |

---

## 3. Requisitos no funcionales

| ID | Característica ISO/IEC 25010 | Requisito | Criterio de aceptación | Verificación |
| :--- | :--- | :--- | :--- | :--- |
| RNF-01 | Seguridad – confidencialidad | Control de acceso por roles. | *Usuario / Consulta* solo lee; no puede crear incidencias (AccessError). | CP-18 |
| RNF-02 | Seguridad – autenticidad | Webhook autenticado. | Sin `Authorization: Bearer <secreto>` válido → HTTP 401; comparación en tiempo constante. | tests GPS |
| RNF-03 | Eficiencia – comportamiento temporal | Tiempo de respuesta. | Consultas de recorridos, mapa y métricas < **3 s** con 60 recorridos / 8 600 posiciones. | CP-16 (rendimiento) |
| RNF-04 | Fiabilidad – integridad de datos | Sin duplicados GPS. | UNIQUE(`traccar_position_id`); carrera cron/webhook no aborta la transacción (savepoint). | tests GPS |
| RNF-05 | Fiabilidad – tolerancia a fallos | Traccar caído no rompe Odoo. | Error de conexión → log de sincronización con error, sin excepción al usuario del cron. | tests GPS |
| RNF-06 | Adecuación funcional – exactitud | Datos sincronizados idénticos a Traccar. | Verificación de exactitud ≥ 99 % (lat/lon a 1e-6, fecha, velocidad). | CP-19 |
| RNF-07 | Mantenibilidad – modularidad | Dependencias unidireccionales. | `transporte_core` no depende de GPS ni calidad; la lógica de reglas es pura (sin Odoo). | revisión, SonarQube |
| RNF-08 | Mantenibilidad – capacidad de prueba | Pruebas automatizadas. | Cobertura de la lógica pura ≥ 90 %; suites Odoo con 0 fallos. | `scripts/ejecutar_pruebas.sh` |
| RNF-09 | Seguridad – secretos | Sin credenciales en el repositorio. | Contraseñas/tokens solo en `.env`/`odoo.conf` locales (ignorados) o en Ajustes de Odoo. | auditoría git |
| RNF-10 | Portabilidad – instalabilidad | Despliegue reproducible. | `docker compose up -d` + instalación de 3 módulos; túnel con `--profile tunel`. | `docs/GUIA_INSTALACION.md` |
| RNF-11 | Compatibilidad – interoperabilidad | Protocolo de Traccar Client. | Traccar Client publica por OsmAnd (HTTP) a través de HTTPS del túnel desde datos móviles. | `docs/GUIA_CLOUDFLARE.md` |
| RNF-12 | Usabilidad – reconocibilidad | Datos simulados nunca se presentan como reales. | Cinta/insignia «SIMULADO», contador real vs simulado en el dashboard. | CP-17 |

---

## 4. Restricciones y supuestos
- No se usa un bus institucional ni IP pública: el teléfono con Traccar Client representa al bus y la conectividad externa se obtiene con Cloudflare Tunnel.
- Odoo guarda fechas en UTC; la interfaz las muestra en la zona del usuario (America/Guayaquil).
- Las reglas GPS (desvío, señal) solo se aplican a viajes con telemetría; un viaje manual se evalúa por horarios y paradas.
- La pérdida de señal es una incidencia de **calidad de datos**: no convierte por sí sola un recorrido en incumplido.
