# Verificación de cumplimiento del enunciado (Proyecto Final Integrador)

Contrastado el 22/11/2026 contra `proyectoFinal_GC.pdf` (10 actividades, restricción del §5, resultado esperado
del §6, entregables del §7, defensa del §8 y rúbrica de 100 puntos), con el sistema corriendo en la PC servidor.

**Leyenda:** ✅ cumplido y comprobado · 🟡 cumplido con datos simulados, falta el dato real del teléfono ·
⛔ pendiente (requiere salir con el teléfono).

## 1. Resumen

| Estado | Qué |
| :-: | :--- |
| ✅ | Todo el software, la documentación, las pruebas, SonarQube, ISO 25010, mejora continua y la presentación |
| 🟡 | Los 10 recorridos documentados son **simulados** (el enunciado lo permite si están identificados) |
| ⛔ | **Recorridos reales con Traccar Client por datos móviles**: es lo que exige la defensa (§8) y la evidencia de A2/A3/A5 |

Mientras no haya posiciones reales del teléfono, las partes de la rúbrica de *infraestructura* (10), *integración
GPS* (15) y *defensa* (5) quedan a medias en la parte demostrable; el resto es verificable hoy.

## 2. Actividad por actividad

| Act. | Qué pide el enunciado | Estado | Evidencia / dónde verlo |
| :-: | :--- | :-: | :--- |
| 1 | Requisitos funcionales y no funcionales con criterios de aceptación; mínimo: vehículos, rutas, paradas y horarios, GPS, históricos, retrasos y desviaciones, incidencias, métricas, mapas, seguridad/integridad/rendimiento | ✅ | `REQUISITOS.md`: 22 RF + 12 RNF con criterios de aceptación |
| 2 | Odoo 16 + **Fleet**; Traccar Server; Traccar Client; Cloudflare Tunnel; validar protocolo HTTP/HTTPS; datos móviles, no solo Wi-Fi | ✅ / ⛔ | Odoo 16 y Fleet instalados; Traccar 6.x en Docker; túnel probado el 22/11: una posición enviada por la URL pública `https://…trycloudflare.com` dio HTTP 200 (protocolo OsmAnd sobre HTTPS). **Falta** la captura desde el teléfono en datos móviles (`GUIA_CLIENTE_CELULAR.md` §3) |
| 3 | Asociar dispositivo↔vehículo; última posición; fecha/hora; historial; recorridos; registrar en Odoo; mapa; sin duplicados; detectar datos desactualizados | ✅ / ⛔ | Campo *ID de dispositivo Traccar* en el bus (ambos buses vinculados); cron cada minuto; log de sincronización con duplicados descartados; estado «sin señal»; mapas Leaflet. Prueba en vivo contra Traccar real: exactitud 100 % (CP-24). **Falta** demostrarlo con posiciones reales del teléfono |
| 4 | ≥ 2 vehículos, ≥ 3 rutas, ≥ 4 puntos de control por ruta, horarios, asociación vehículo–ruta–dispositivo; un mismo bus en varias rutas/horarios | ✅ | 2 buses con GPS (TB-DEMO-01/02); 3 rutas con 7, 6 y 5 paradas; viajes con fecha y hora; cada bus simulado hizo las 3 rutas en horarios distintos (TB-DEMO-01: 3 rutas, TB-DEMO-02: 3 rutas) |
| 5 | Conservar vehículo/ruta, fecha, coordenadas, velocidad, hora programada y real de inicio y llegada, distancia estimada y recorrida, paradas visitadas, incidencias; **≥ 10 recorridos documentados**, normales e incumplimientos | 🟡 / ⛔ | 10 recorridos **SIMULADOS** (puntual, atrasado, parada omitida, desvío, incompleto, congestión…) con todos esos campos; marcados SIMULADO. Los recorridos reales siguen pendientes (`GUIA_TRABAJO_CAMPO.md` §6) |
| 6 | Reglas: retraso, punto de control, desvío, incompleto, tiempo estimado vs real, pérdida de señal; tolerancias definidas y justificadas; radio de proximidad; corredor de referencia | ✅ | `METRICAS.md` §2; ejemplo del enunciado 08:15 + 5 min, llegada 08:23 = 8 min de retraso (CP-05); 31 incidencias generadas en la BD actual |
| 7 | 8 métricas de transporte + 4 de calidad del software, con fórmula, fuente, unidad, resultado e interpretación; calculadas, no estáticas | ✅ | `METRICAS.md` §3 y consultas SQL §4; dashboard con botón *Fórmulas*. La **exactitud Traccar↔Odoo con datos reales** se mide con *Verificar exactitud Traccar* tras los recorridos reales |
| 8 | Dashboard en Odoo (alternativa A): ubicación, rutas, historial, cumplimiento, puntualidad, retrasos, distancias, incidencias, comparaciones por ruta y período; se actualiza con nuevos recorridos | ✅ | *Calidad del Servicio ▸ Dashboard* (5 pestañas), *Mapa de rutas*, pantalla *Inicio* y *En vivo*; prueba CP-22 (Inicio = registros). Se eligió Odoo, no Power BI |
| 9 | Caja negra, caja blanca, integración, rendimiento, automatizadas (pytest), SonarQube, ISO 25010; ≥ 10 casos documentados | ✅ | 27 casos en `PLAN_PRUEBAS.md`; ejecución del 22/11: pytest OK, 102 Odoo, rendimiento máx. ~350 ms, 7 UI, 2 en vivo; `CALIDAD_SOFTWARE.md` y `docs/evidencias/sonarqube_*.json` (Quality Gate aprobado, 0 bugs, 0 vulnerabilidades) |
| 10 | Problema relevante + Ishikawa, Pareto y PDCA con comparación antes/después | ✅ | `MEJORA_CONTINUA.md`: geocerca por tramo (detección correcta 90 % → 100 %, `pdca_deteccion_paradas.csv`) y refactor (complejidad 46 → ≤ 15) |

### 2.1 Mínimos de la Actividad 4 en la base real (`transporte_dev`, 22/11/2026)

| Mínimo | Requerido | Encontrado |
| :--- | :-: | :--- |
| Vehículos con dispositivo GPS | 2 | 2 (TB-DEMO-01 → id 1 `sgmtb-bus01`; TB-DEMO-02 → id 2 `sgmtb-bus02`) |
| Rutas | 3 | 3 (DEMO-RUT-01, -02, -03) |
| Puntos de control por ruta | 4 | 7, 6 y 5 |
| Recorridos | 10 | 10 simulados + 0 reales |
| Incidencias detectadas | — | 31 automáticas (retraso en parada, parada omitida, retraso de inicio/llegada, incompleto, pérdida de señal, diferencia de tiempo, desvío) |

## 3. Restricción del §5 y preguntas del §6

| Exigencia | Estado | Cómo se cumple |
| :--- | :-: | :--- |
| No solo instalar y mostrar un vehículo en un mapa | ✅ | Múltiples rutas, historial, evaluación automática y métricas verificables |
| Sin dashboards estáticos | ✅ | Los KPIs se calculan de los registros (CP-11, CP-22); cambian al registrar un viaje |
| Sin datos ficticios presentados como reales | ✅ | Todo lo simulado lleva `simulado = True`, cinta SIMULADO, filtro «Solo reales/simulados» y aviso en Inicio. Las rutas `DEMO-*` tienen nombres de demostración |
| Métricas comprobables | ✅ | Consultas SQL en `METRICAS.md` §4 |

Las 10 preguntas del §6 y dónde responderlas están en `GUIA_DEMOSTRACION.md` §3 (dónde está el bus, ruta,
paradas visitadas, horario, retraso, desvío, nº de recorridos, % cumplido, incidencias frecuentes, confiabilidad
y mejoras).

## 4. Entregables del §7

| # | Entregable | Estado | Archivo |
| :-: | :--- | :-: | :--- |
| 1 | Análisis y requisitos | ✅ | `REQUISITOS.md` |
| 2 | Arquitectura y modelo de datos | ✅ | `ARQUITECTURA.md` (módulos y ERD) |
| 3 | Odoo 16 integrado con Traccar | ✅ | `addons/transporte_gps_traccar` |
| 4 | Conectividad externa funcional | ✅ / ⛔ | Túnel verificado; falta evidencia desde datos móviles (`GUIA_CLOUDFLARE.md`) |
| 5 | Módulo para administrar rutas | ✅ | `addons/transporte_core` |
| 6 | Historial de recorridos y datos GPS | ✅ / ⛔ | 10 simulados; reales pendientes |
| 7 | Indicadores y dashboard en Odoo | ✅ | `addons/transporte_calidad`, `transporte_ui` |
| 8 | Matriz y evidencias de pruebas | ✅ | `PLAN_PRUEBAS.md`, `backups/*.log` (se regeneran con `ejecutar_pruebas.sh`) |
| 9 | Análisis SonarQube | ✅ | `docs/evidencias/sonarqube_20261120*.json`, `sonar-project.properties` |
| 10 | Informe de mejora continua y código fuente | ✅ | `MEJORA_CONTINUA.md`, repositorio |

## 5. Defensa (§8)

| Se verificará | Estado |
| :--- | :-: |
| Registro del vehículo, asignación de ruta, consulta de posiciones, historial e indicadores | ✅ (guion en `GUIA_DEMOSTRACION.md`) |
| Demostrar con información GPS obtenida mediante **Traccar Client** | ⛔ pendiente de recorrido real |
| Un caso de cumplimiento y uno de incumplimiento, con sus reglas | ✅ simulado · ⛔ real |
| Diseño, resultados de calidad y mejoras | ✅ presentación de 15 diapositivas en `docs/presentacion/` |

## 6. Rúbrica (100 puntos)

| # | Criterio | Pts | Estado | Qué lo respalda / qué falta |
| :-: | :--- | :-: | :-: | :--- |
| 1 | Análisis y requisitos | 10 | ✅ | `REQUISITOS.md` |
| 2 | Arquitectura e infraestructura | 10 | 🟡 | Todo corre y el túnel responde; falta mostrar el envío desde datos móviles |
| 3 | Integración Odoo–Traccar | 15 | 🟡 | Integración probada en vivo (100 % exactitud); falta con el teléfono |
| 4 | Rutas, paradas y recorridos | 10 | ✅ | §2.1 |
| 5 | Historial e incidencias | 10 | ✅ | 31 incidencias automáticas sobre 10 recorridos |
| 6 | Métricas y dashboard | 15 | ✅ | 12 indicadores con fórmula y consultas |
| 7 | Pruebas | 10 | ✅ | 27 casos + ejecución completa |
| 8 | Calidad (ISO 25010 + SonarQube) | 10 | ✅ | `CALIDAD_SOFTWARE.md` |
| 9 | Mejora continua | 5 | ✅ | Ishikawa, Pareto y PDCA con antes/después |
| 10 | Presentación y defensa | 5 | 🟡 | Presentación lista; las capturas son simuladas y la demo en vivo necesita el teléfono |

## 7. Lo que falta para cerrar (en orden)

1. Levantar el túnel y configurar el teléfono ([`GUIA_CLIENTE_CELULAR.md`](GUIA_CLIENTE_CELULAR.md)).
2. Probar conectividad **con Wi-Fi apagado** y tomar las capturas A2-04, A2-05 y A3.
3. Crear 3 rutas reales con 4 paradas (`GUIA_TRABAJO_CAMPO.md` §5) y hacer **≥ 10 recorridos reales** (puntual,
   atrasado, parada omitida, desvío, incompleto y pérdida de señal), documentándolos.
4. Ejecutar *Verificar exactitud Traccar* con esos datos y anotar el resultado en `METRICAS.md` §3.2 (fila 2).
5. Reemplazar las capturas simuladas de `docs/presentacion/` por las reales y regenerar el PDF.
6. Borrar las posiciones «reales» de prueba (curl) antes de la defensa para que «Solo reales» muestre solo el
   teléfono.
7. Mejora sugerida a partir de los datos reales: ajustar la distancia estimada de cada ruta (la métrica 6 sale
   −24,7 % con datos simulados porque estos siguen la recta entre paradas).
