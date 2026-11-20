# Reglas de Detección e Indicadores (Actividades 6 y 7)

Todo se calcula **en vivo** desde la base de datos (`transporte.calidad.dashboard.get_dashboard_data`) y con
la lógica pura de `addons/transporte_calidad/lib/reglas.py`. No hay valores estáticos: al registrar nuevos
recorridos el dashboard cambia (prueba automática `test_dashboard_se_actualiza_con_nuevos_recorridos`).

> **Resultados de la §3:** BD `transporte_universitario_gc`, 10 recorridos de prueba **SIMULADOS** del 19/11/2026
> (plan de escenarios de `lib/simulador.py`). Se presentan para demostrar la lógica; los recorridos reales
> con Traccar Client se agregan a la misma tabla y el dashboard permite filtrar «Solo reales».

---

## 1. Reglas de detección (A6)

Cada recorrido iniciado se evalúa al finalizar o cancelar, al llegar posiciones GPS y cada 5 min (cron).
Las incidencias se sincronizan de forma idempotente (clave: tipo + parada del viaje).

| Regla / incidencia | Condición | Severidad |
| :--- | :--- | :--- |
| Retraso en parada | `llegada_real − hora_programada > tol_retraso` | media ≤ 2·tol, alta ≤ 4·tol, crítica > 4·tol |
| Adelanto en parada | `llegada_real − hora_programada < −tol_adelanto` | baja |
| Retraso en la salida | `salida_real − salida_programada > tol_retraso` | igual que retraso |
| Retraso en la llegada | `llegada a destino − llegada_programada > tol_retraso` (solo si se llegó al destino) | igual que retraso |
| Parada omitida | parada sin llegada registrada al finalizar el viaje | alta |
| Recorrido incompleto | destino no alcanzado, o viaje cancelado después de iniciar | alta |
| Diferencia de tiempo | recorrido completo y `|real − estimada| > tol_duración %` **y** `> tol_retraso` min | media |
| Desviación de la ruta | ≥ N posiciones **consecutivas** a más de *corredor* m del trazado de referencia | media; alta si > 3·corredor |
| Pérdida de señal GPS | hueco entre reportes > *gap* min dentro de [salida real, llegada] (incluye bordes) | media; alta si > 3·gap |

**Detección de paradas (geocerca):** una parada queda *visitada* si una posición cae dentro de su
`radio_deteccion` **o** si el tramo entre dos posiciones consecutivas pasa por dentro del radio (hora interpolada
en el punto más cercano; no se interpola a través de huecos > 360 s). Ver `docs/MEJORA_CONTINUA.md`.

**Trazado de referencia:** el JSON `trazado_referencia` de la ruta (fijado desde un recorrido que cumple con
el botón «Usar como trazado de referencia»); si no existe, la polilínea que une las paradas en orden.

**Veredicto del recorrido:** *Cumple* = completo ∧ sin paradas omitidas ∧ sin desvío ∧ todas las paradas
puntuales ∧ llegada dentro de tolerancia. La pérdida de señal se registra pero no hace incumplir el viaje.

## 2. Tolerancias y justificación

| Parámetro | Valor | Justificación |
| :--- | :---: | :--- |
| Retraso tolerado | 5 min | Valor del enunciado (08:15 + 5 → 08:23 es retraso de 8 min); estándar habitual de puntualidad en transporte urbano. |
| Adelanto tolerado | 2 min | Un bus adelantado deja estudiantes en la parada; ventana OTP clásica [−2, +5]. |
| Radio de parada | 30–50 m (por parada) | Precisión típica del GPS de un teléfono (5–20 m) + longitud del bus + bahía de la parada. |
| Corredor de ruta | 150 m | Media cuadra en Ambato (~100 m) más el error GPS; con trazado de paradas recto, absorbe la curvatura de las calles. |
| Posiciones fuera seguidas | 3 | Con reportes cada 10–30 s son 30–90 s fuera: descarta saltos aislados del GPS (multipath). |
| Hueco de señal | 3 min | Con intervalo recomendado de 30 s son ≥ 6 reportes perdidos: no es ruido. |
| Diferencia de duración | 20 % y 5 min | Evita alertar en recorridos cortos por diferencias de 1–2 min. |
| Intervalo de Traccar Client | ≤ 30 s | Resultado de la mejora PDCA: con 30 s la detección de paradas es 100 % a 20 km/h. |

Todas se modifican en **Calidad del Servicio ▸ Ajustes de calidad** y se reaplican con «Guardar y reevaluar».

## 3. Indicadores (A7)

### 3.1 Métricas de transporte

| # | Indicador | Fórmula | Fuente de datos | Unidad | Resultado (simulado) | Interpretación |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- |
| 1 | Cumplimiento de rutas | viajes con `cumple_ruta` / viajes evaluados × 100 | `transporte.viaje` (`cumple_ruta`, `resultado`) | % | **70,0** (7/10) | 3 viajes incumplen la ruta: parada omitida, desvío e incompleto. |
| 2 | Puntualidad | paradas puntuales / paradas visitadas × 100 (y viajes puntuales / evaluados) | `transporte.viaje.parada.puntualidad`, `transporte.viaje.puntual` | % | **80,7** (46/57) · viajes 70,0 | 11 llegadas fuera de [−2, +5] min, todas en los escenarios atrasado y congestión. |
| 3 | Retraso promedio | Σ retraso promedio por viaje / nº viajes; retraso por viaje = promedio de max(0, real − programada) en sus paradas | `transporte.viaje.retraso_promedio_min` | min | **2,24** | Por debajo de la tolerancia, aunque concentrado en 2 viajes. |
| 4 | Paradas cumplidas | paradas visitadas / paradas programadas × 100 | `transporte.viaje.paradas_atendidas`, `total_paradas_viaje` | % | **93,44** (57/61) | 4 paradas no visitadas (1 omitida + 3 del recorrido incompleto). |
| 5 | Desviación de la ruta | promedio del % de posiciones fuera del corredor por viaje; además viajes desviados y alejamiento máximo | `transporte.viaje.porcentaje_fuera_corredor`, `max_desviacion_m` | % / m | **1,38 %**, 1 viaje, máx. 448 m | Un solo viaje se salió del corredor (desvío de ~450 m). |
| 6 | Diferencia distancia estimada vs recorrida | promedio de (recorrida − estimada) / estimada × 100 | `transporte.ruta.distancia_estimada_km`, `transporte.viaje.distancia_recorrida_km` | % / km | **−24,7 %** (−2,06 km) | Los recorridos simulados siguen la recta entre paradas, mientras la estimada incluye 25 % de tortuosidad: ajustar la estimada con el primer recorrido real. |
| 7 | Tiempo promedio de recorrido | Σ (llegada a destino − salida real) / viajes completos | `transporte.viaje.duracion_real_min` (y `duracion_estimada_min`) | min | **42,9** (estimado 41,1) | +4,4 % sobre lo planificado, empujado por el escenario de congestión. |
| 8 | Número y frecuencia de incidencias | conteo en el periodo; por cada 100 viajes y por día; Pareto por tipo | `transporte.incidencia` (no descartadas) | nº, nº/100 viajes, nº/día | **22**; 220/100 viajes | Pareto: *Retraso en parada* concentra el 50 %, y junto con *Parada omitida* el 68 %. |

### 3.2 Métricas de calidad del software

| # | Indicador | Fórmula | Fuente | Unidad | Resultado | Interpretación |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- |
| 1 | Integridad de los registros GPS | posiciones válidas / posiciones almacenadas × 100 (+ duplicados descartados en logs) | `transporte.gps.posicion.valida`, `transporte.gps.sync.log` | % | **100** (1 444/1 444, simuladas) | Con datos reales refleja fixes inválidos y (0,0) del teléfono. |
| 2 | Exactitud Traccar ↔ Odoo | posiciones idénticas (lat/lon a 1e-6, fecha, velocidad) / verificadas × 100 | `verificar_exactitud_sync()` → `transporte.calidad.medicion` (tipo exactitud) | % | *pendiente de ejecutar con datos reales del teléfono* | Probado con Traccar simulado: 2 de 4 idénticas, 1 distinta y 1 faltante → 50 %. |
| 3 | Tiempo de respuesta | promedio y p95 de las mediciones de dashboard, consultas, mapa y rendimiento (30 días); duración media de sincronización | `transporte.calidad.medicion.duracion_ms`, `transporte.gps.sync.log.duracion_ms` | ms | dashboard 11–48 ms; JSON-RPC máx. 49 ms | Muy por debajo del umbral de 3 s (RNF-03). Ver `docs/PLAN_PRUEBAS.md §4`. |
| 4 | Detección correcta de incidencias | recorridos cuyo conjunto de incidencias detectadas = esperado / recorridos con escenario × 100 | `transporte.viaje.deteccion_correcta` (`incidencias_esperadas`) | % | **100** (10/10; 60/60 en 6 días con semillas distintas) | Antes de la mejora PDCA el escenario de muestreo disperso fallaba (falsa parada omitida). |

## 4. Consultas de verificación (PostgreSQL)

```sql
-- 1. Cumplimiento de rutas y 3. retraso promedio (viajes evaluados de un periodo)
SELECT count(*) FILTER (WHERE cumple_ruta) * 100.0 / count(*) AS cumplimiento_pct,
       avg(retraso_promedio_min) FILTER (WHERE paradas_atendidas > 0) AS retraso_promedio_min,
       count(*) FILTER (WHERE puntual) * 100.0 / count(*) AS viajes_puntuales_pct
FROM transporte_viaje
WHERE resultado IN ('cumple','incumple') AND fecha_viaje BETWEEN '2026-11-19' AND '2026-11-19';

-- 2. Puntualidad y 4. paradas cumplidas
SELECT sum(paradas_puntuales) * 100.0 / sum(paradas_atendidas) AS puntualidad_pct,
       sum(paradas_atendidas) * 100.0 / sum(total_paradas_viaje) AS paradas_cumplidas_pct
FROM transporte_viaje WHERE resultado IN ('cumple','incumple');

-- Retraso de cada parada (ejemplo 08:15 -> 08:23 = 8 min)
SELECT v.name, p.secuencia, p.hora_planificada, p.hora_llegada_real, p.retraso_min, p.puntualidad
FROM transporte_viaje_parada p JOIN transporte_viaje v ON v.id = p.viaje_id ORDER BY v.name, p.secuencia;

-- 8. Pareto de incidencias
SELECT tipo, count(*) n, round(100.0 * sum(count(*)) OVER (ORDER BY count(*) DESC, tipo)
       / sum(count(*)) OVER (), 2) AS pct_acumulado
FROM transporte_incidencia WHERE estado <> 'descartada' GROUP BY tipo ORDER BY n DESC;

-- SW 1. Integridad GPS
SELECT count(*) FILTER (WHERE valida) * 100.0 / count(*) AS integridad_pct, count(*) total,
       count(*) FILTER (WHERE simulado) simuladas FROM transporte_gps_posicion;

-- SW 4. Detección correcta
SELECT deteccion_correcta, count(*) FROM transporte_viaje
WHERE deteccion_correcta IN ('correcta','incorrecta') GROUP BY 1;
```

Ejecutar con: `docker exec -it odoo16_db psql -U odoo -d transporte_universitario_gc`.
