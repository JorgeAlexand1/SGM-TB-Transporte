# Plan, Matriz y Resultados de Pruebas (Actividad 9)

## 1. Estrategia

| Tipo | Herramienta | Qué valida | Ubicación |
| :--- | :--- | :--- | :--- |
| Caja blanca (lógica pura) | **pytest** + pytest-cov | Reglas de retraso, desvío, señal, KPIs, geocerca, simulador, parser/cliente Traccar | `addons/*/tests/pytest/` |
| Funcional / caja negra | Runner de Odoo (`TransactionCase`) | Entradas válidas, inválidas y valores límite sobre modelos reales | `addons/*/tests/test_*.py` |
| Integración Traccar ↔ Odoo | Odoo + mocks de la API + Traccar real (contenedor) | Sincronización, duplicados, webhook, exactitud | `transporte_gps_traccar/tests`, `test_calidad.py` |
| Rendimiento | Odoo (tag `rendimiento`) + `scripts/prueba_rendimiento.py` (JSON-RPC) | Tiempos con 10/30/60 recorridos y 1 400–8 700 posiciones | `test_rendimiento.py` |
| Interfaz | `HttpCase` + Chromium headless (tag `ui`) | Inicio, dashboard, mapa de rutas, formulario e informe sin errores JS | `test_ui.py`, `transporte_ui/tests` |
| Calidad de código | SonarQube | Defectos, duplicación, mantenibilidad, seguridad | `sonar-project.properties` |

**Ejecutar todo:** `bash scripts/ejecutar_pruebas.sh` (crea la BD desechable `sgmtb_test`; nunca toca la BD de transporte).

Para las pruebas de interfaz se necesitan Chromium **y** `python3-websocket` en el contenedor (Debian 11 está
archivado). Sin `python3-websocket` Odoo marca las pruebas de navegador como *saltadas* —no como fallidas—, por lo
que `ejecutar_pruebas.sh` trata cualquier prueba de interfaz saltada como fallo (defecto D-07):
```bash
docker exec -u root odoo16_web bash -c 'printf "deb http://archive.debian.org/debian bullseye main\ndeb http://archive.debian.org/debian-security bullseye-security main\n" > /etc/apt/sources.list && apt-get -o Acquire::Check-Valid-Until=false update && apt-get install -y --no-install-recommends chromium fonts-liberation python3-websocket'
```

## 2. Matriz de casos de prueba

Ejecutados el **20/11/2026**. *Evidencia* = prueba automatizada que lo comprueba (log en `backups/odoo_tests.log`).

| ID | Tipo | Requisito | Entrada | Resultado esperado | Resultado obtenido | Evidencia | Estado |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-: |
| CP-01 | Caja negra – inválida | RF-01 | Bus de pasajeros con 0 sentados y 0 de pie; capacidades negativas | `ValidationError` | ValidationError | core `test_02_rechazo_capacidades_negativas_o_cero` | ✅ |
| CP-02 | Caja negra – válida/inválida | RF-03 | Ruta con 7 paradas; luego distancia −1 | Origen = 1.ª parada, destino = última, distancia sugerida > 3 km; −1 rechazado | P1 → P7; 4,4 km; ValidationError | `TestRutaYConfiguracion.test_origen_destino_distancia` | ✅ |
| CP-03 | Valores límite | RF-04 | Latitud/longitud fuera de [−90, 90] / [−180, 180]; radio de detección 0 | Rechazo en todos los casos | ValidationError | core `test_02_validacion_coordenadas`, `test_03_validacion_radio_deteccion` | ✅ |
| CP-04 | Caja negra – inválida | RF-06 | Mismo bus (o conductor) en dos viajes solapados | Rechazo por conflicto de horario | ValidationError | core `test_06/07_prevencion_conflictos_horarios_*` | ✅ |
| CP-05 | Caja blanca + negra | RF-11 | Parada programada 08:15, tolerancia 5, llegada 08:23 | Retraso **8,0 min**, puntualidad *atrasada*, 1 incidencia *Retraso en parada*, viaje *Incumple* | 8,0 min, atrasada, 1 incidencia, incumple | `test_cp05_ejemplo_enunciado_retraso_8_min`, pytest `test_ejemplo_enunciado_0815_0823` | ✅ |
| CP-06 | Valores límite | RF-11 | Retrasos 5,00 / 5,01 / −2,0 / −2,5 min | puntual / atrasada / puntual / adelantada | Igual | pytest `test_clasificar_parada_limites` | ✅ |
| CP-07 | Caja negra | RF-12 | Viaje con la 3.ª parada sin llegada | 1 *Parada omitida*, cumplimiento 66,67 % | Igual | pytest `test_parada_omitida_y_recorrido_incompleto`, Odoo `test_cp07_cp08…` | ✅ |
| CP-08 | Caja negra | RF-12 | Viaje que no llega al destino / cancelado en ruta | *Recorrido incompleto* + omitidas; sin retraso de llegada | Igual | `test_cp07_cp08…`, `test_cancelado_en_ruta_es_incompleto` | ✅ |
| CP-09 | Caja blanca – umbral | RF-13 | Duración +40 % (12 min) y +10 % (3 min) | Solo la primera genera *Diferencia de tiempo* | Igual | pytest `test_diferencia_tiempo_umbral` | ✅ |
| CP-10 | Caja blanca | RF-14 | 3 posiciones seguidas a 300 m del trazado vs 2 aisladas | Desvío solo con la racha de 3 | Igual | pytest `test_desviacion_requiere_racha_consecutiva` | ✅ |
| CP-10b | Caja blanca | RF-15 | Posiciones a los min 1, 2, 8, 9 de un viaje de 10 min; viaje con GPS sin posiciones | Hueco de 6 min; hueco de 10 min → *Pérdida de señal* | Igual | pytest `test_detectar_huecos_incluye_bordes`, `test_viaje_gps_sin_posiciones…` | ✅ |
| CP-11 | Caja blanca – fórmulas | RF-17 | 2 viajes de valores conocidos | Cumplimiento 50 %, paradas 83,33 %, puntualidad 80 %, retraso 2,0, 3 incidencias | Igual | pytest `test_kpis_transporte_formulas`; Odoo `test_cp11_kpis_coinciden_con_registros` | ✅ |
| CP-12 | Integración – mejora | RF-10 | Recorrido reportado cada 120 s; geocerca *punto* vs *segmento* | Punto: parada omitida falsa (incorrecta); segmento: 0 omitidas, detección correcta, hora interpolada | Igual | `test_cp12_geocerca_punto_vs_segmento` | ✅ |
| CP-13 | Integración E2E | RF-06/10–15/21 | Asistente: 10 recorridos (3 rutas, 2 buses, 8 escenarios) | 10/10 con las incidencias esperadas, todo marcado simulado, ids negativos | 10/10 (60/60 en 6 días) | `test_cp13_plan_diez_recorridos_deteccion_correcta` | ✅ |
| CP-14 | Integración Traccar | RF-07 | 3 sincronizaciones seguidas con las mismas posiciones; webhook sin token | 0 duplicados; HTTP 401 | Igual | GPS `test_gps_integracion` | ✅ |
| CP-15 | Caja negra – idempotencia | RF-16/22 | Reevaluar 3 veces; luego subir tolerancia a 10 min | 1 sola incidencia; la resuelta se conserva y el viaje pasa a *Cumple* | Igual | `test_idempotencia_y_trazabilidad` | ✅ |
| CP-16 | Rendimiento | RNF-03 | 10/30/60 recorridos (1 444/4 332/8 664 posiciones) | Dashboard, consulta, mapa y reevaluación < 3 000 ms | máx. 347 ms (reevaluar 60 viajes) | `test_rendimiento.py`, `rendimiento_jsonrpc.csv` | ✅ |
| CP-17 | Interfaz | RF-18/20, RNF-12 | Abrir dashboard, formulario de viaje simulado e informe | 12 KPIs + 3 gráficos sin errores JS; cinta SIMULADO y pestaña Evaluación; informe con incidencias | Igual | `test_ui.py` (3 pruebas) | ✅ |
| CP-18 | Seguridad | RNF-01 | Usuario *Consulta* crea una incidencia / abre el dashboard | AccessError al crear; dashboard visible | Igual (antes: AccessError al leer buses → **defecto D-02 corregido**) | `TestSeguridad` | ✅ |
| CP-19 | Integración – exactitud | RNF-06 | 4 posiciones en Odoo; Traccar devuelve 1 alterada y le falta 1 | Exactitud 50 %, medición registrada con ok = False | Igual | `test_exactitud_sync_con_traccar_simulado` | ✅ |
| CP-20 | Caja negra – KPIs por ruta | RF-17, RF-19 | Ruta con 1 recorrido que cumple y 1 con parada atrasada y omitidas | 2 evaluados, cumplimiento 50 %, puntualidad = Σ puntuales / Σ atendidas | Igual | `test_indicadores_por_ruta`, `test_mapa_rutas` | ✅ |
| CP-21 | Seguridad – mapa de rutas | RNF-01 | Usuario *Consulta* abre el mapa de rutas e intenta cambiar el trazado | Ve rutas e indicadores; AccessError al escribir | Igual | `TestSeguridad` | ✅ |
| CP-22 | Caja negra – Inicio | RF-17, RF-18 | 10 recorridos simulados + 1 bus en ruta | Inicio = mismos valores que el dashboard en 7 días; el bus aparece en «En ruta ahora»; aviso de SIMULADOS | Igual | `test_inicio_coincide_con_registros` | ✅ |
| CP-23 | Seguridad – Inicio | RNF-01 | Usuario *Consulta* vs. *Responsable* | El acceso «Recorridos simulados» solo aparece al responsable | Igual | `test_accesos_segun_rol` | ✅ |

## 3. Resultados de ejecución

| Suite | Pruebas | Resultado |
| :--- | :---: | :--- |
| pytest `transporte_gps_traccar` | 54 | 54 aprobadas · cobertura de `lib/` **99 %** (ramas) |
| pytest `transporte_calidad` | 74 | 74 aprobadas · cobertura de `lib/` **97 %** (ramas) |
| Odoo `transporte_core` + `transporte_gps_traccar` + `transporte_calidad` + `transporte_ui` | 95 | **0 fallos, 0 errores** |
| Odoo rendimiento (`rendimiento`) | 1 (12 mediciones) | 0 fallos |
| Odoo interfaz (`ui`, Chromium headless) | 5 | 0 fallos, 0 saltadas (Inicio, dashboard, mapa de rutas, formulario, informe) |

## 4. Rendimiento

**Dentro del servidor** (tag `rendimiento`, BD de prueba):

| Recorridos / posiciones | Dashboard | Consulta recorridos | Mapa de un viaje | Reevaluar todos |
| :--- | ---: | ---: | ---: | ---: |
| 10 / 1 444 | 15 ms | 0 ms | 2 ms | 47 ms |
| 30 / 4 332 | 20 ms | 1 ms | 2 ms | 137 ms |
| 60 / 8 664 | 32 ms | 1 ms | 3 ms | 347 ms |

**Extremo a extremo por JSON-RPC** (`scripts/prueba_rendimiento.py`, 5 repeticiones, 60 recorridos):

| Operación | Promedio | Máximo |
| :--- | ---: | ---: |
| Consulta de 10 / 100 / 1 000 recorridos | 14,6 / 21,2 / 21,2 ms | 22,6 ms |
| Mapa de buses / trazado de un viaje (211 pos.) | 12,3 / 19,0 ms | 23,5 ms |
| Métricas del dashboard 1 / 7 / 30 / 90 días | 19,8 / 43,4 / 40,4 / 42,0 ms | 48,8 ms |

El crecimiento es lineal con el número de posiciones en la reevaluación (O(posiciones × tramos)); las consultas
del dashboard trabajan sobre campos almacenados y escalan con el número de viajes.

## 5. Defectos encontrados durante las pruebas

| ID | Defecto | Detectado por | Corrección |
| :-- | :-- | :-- | :-- |
| D-01 | Paradas visitadas registradas como omitidas con intervalos GPS largos | CP-12, `medir_deteccion_paradas.py` | Geocerca por tramo + intervalo ≤ 30 s (PDCA) |
| D-02 | El rol *Consulta* no podía leer `fleet.vehicle` (no veía viajes) | CP-18 | ACL de lectura en `transporte_core/security` |
| D-03 | La «última posición» de un bus podía tomarse de una posición simulada | Revisión de código | Filtro `simulado = False` en `fleet_vehicle._procesar_posiciones_nuevas` |
| D-04 | `registrar()` devolvía un recordset: falla por XML/JSON-RPC | `prueba_rendimiento.py` | Devuelve el id |
| D-05 | `config/odoo.conf` local vacío: el servidor arrancaba sin `/mnt/extra-addons` | Inspección de logs | Reconstruido desde `odoo.conf.example` |
| D-06 | Expectativa errónea: la pérdida de señal hacía «incumplir» el viaje | CP-13 | Se definió como incidencia de calidad de datos (no incumple) |
| D-07 | Las pruebas de navegador se **saltaban** en silencio (faltaba `python3-websocket`) y el resumen decía «0 fallos» | Revisión del log (`skipped … websocket-client`) | Dependencia instalada; `ejecutar_pruebas.sh` falla si hay pruebas de interfaz saltadas |
| D-08 | Los 3 mapas dependían del CDN jsDelivr: sin Internet (o en pruebas) quedaban en blanco | Capturas de pantalla automatizadas | Leaflet 1.9.4 incluido en `transporte_gps_traccar/static/lib/leaflet` (checksum npm verificado) |
| D-09 | Mapa de rutas: panel lateral de 380 px de alto y mapa invisible (`.o_action` de Odoo es columna flex) | Capturas + medición de cajas en el navegador | Contenedor propio `.o_cmr_cuerpo` en fila; prueba `test_mapa_rutas_renderiza…` |
| D-10 | `_compute_trazado_puntos` perdió `@api.depends` (edición interrumpida): el nº de puntos no se recalculaba | Revisión del `git diff` al retomar | Decorador restaurado; `test_trazado_referencia` |

## 6. Pendiente de ejecutar por el equipo (requiere hardware / servicios externos)
- Recorridos reales con Traccar Client en datos móviles a través del túnel (evidencia de A2/A5).
- Verificación de exactitud contra Traccar con esas posiciones reales (menú **Verificar exactitud Traccar**).
- Análisis SonarQube (`docs/CALIDAD_SOFTWARE.md`) y captura del informe.
