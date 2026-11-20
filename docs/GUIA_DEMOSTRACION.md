# Guion de Demostración y Defensa

## 0. Antes de la defensa
- `docker compose up -d && docker compose --profile tunel up -d`; Traccar Client a 30 s apuntando al túnel.
- En Odoo, el bus de prueba tiene su `ID de dispositivo Traccar` y el viaje del día está **Programado**.
- Dashboard filtrado «Solo reales» para mostrar los datos del teléfono; «Solo simulados» para los escenarios.

## 1. Flujo en vivo (≈ 10 min)
1. **Registro del vehículo:** Transporte en Buses ▸ Flota y Personal ▸ Buses ▸ bus con dispositivo GPS asociado.
2. **Rutas y paradas:** Rutas y Paradas ▸ Líneas y Rutas: origen, destino, distancia y tiempo estimados,
   secuencia de ≥ 4 paradas con minutos desde el origen; pestaña *Corredor de referencia*.
3. **Asignación:** Operación de Viajes ▸ Viajes ▸ nuevo (ruta + bus + conductor + hora) ▸ *Programar* (se congelan
   las horas de cada parada) ▸ *Iniciar recorrido*. Mostrar que el mismo bus tiene otros viajes en otras rutas.
4. **Recorrido con el teléfono** (datos móviles): Telemetría GPS ▸ Mapa de Buses (refresca cada 15 s) y
   Log de sincronización (nuevas / duplicados = 0).
5. En el viaje: paradas pasando a *Atendida (GPS)* con su hora real y retraso; pestaña *Evaluación de calidad*
   con el retraso acumulado en vivo.
6. *Finalizar viaje* → resultado **Cumple / Incumple** e incidencias generadas automáticamente; botón *Informe PDF*.
7. **Dashboard** (Calidad del Servicio ▸ Dashboard): KPIs con fórmula visible y semáforo, Pareto, comparación
   por ruta y por día, historial. Registrar un viaje nuevo y mostrar que los indicadores cambian.

## 2. Caso de cumplimiento y caso de incumplimiento
| Caso | Dónde mostrarlo | Regla que explica el resultado |
| :--- | :--- | :--- |
| Cumple | Viaje real a tiempo, o simulado «puntual» | Todas las paradas en [−2, +5] min, destino alcanzado, ninguna posición > 150 m del corredor |
| Incumple – retraso | Simulado «atrasado» | Salida +10 min → retraso de salida, de cada parada y de llegada > 5 min |
| Incumple – parada omitida | Simulado «parada omitida» | El bus pasa a 110 m de una parada de radio 35 m: ni la muestra ni el tramo entran al radio |
| Incumple – desvío | Simulado «desviación» (mapa del viaje) | ≥ 3 posiciones seguidas a más de 150 m del trazado (máx. ~450 m) |
| Incumple – incompleto | Simulado «incompleto» | Destino no alcanzado → recorrido incompleto + 3 paradas omitidas |
| Ejemplo del enunciado | Prueba `test_cp05` / explicación | 08:15 programada, tolerancia 5, llegada 08:23 → retraso de 8 min |

## 3. Respuestas a las preguntas del enunciado
| Pregunta | Dónde se responde |
| :--- | :--- |
| ¿Dónde se encuentra actualmente el vehículo? | Dashboard ▸ tabla de buses + mapa; Mapa de Buses (posición, hora, velocidad, señal) |
| ¿Qué ruta está realizando? | Dashboard ▸ columna «Ruta en curso» |
| ¿Qué paradas ha visitado? | Dashboard ▸ «Paradas visitadas» (n/m y nombres); viaje ▸ Control de paradas |
| ¿Está cumpliendo los horarios? | Dashboard ▸ «¿Horario?»; viaje ▸ puntualidad por parada |
| ¿Cuánto retraso ha acumulado? | Dashboard ▸ «Retraso acumulado» (última parada visitada) |
| ¿Se ha desviado de su ruta? | Dashboard ▸ «¿Desvío?»; viaje ▸ alejamiento máximo y % fuera del corredor |
| ¿Cuántos recorridos ha realizado? | Dashboard ▸ columna «Recorridos» por bus y KPI de recorridos evaluados |
| ¿Qué porcentaje se ha cumplido correctamente? | KPI «Cumplimiento de rutas» |
| ¿Cuáles son las incidencias más frecuentes? | Gráfico de Pareto de incidencias |
| ¿Qué tan confiable es el sistema? | KPIs de calidad del software: integridad GPS, exactitud Traccar ↔ Odoo, tiempo de respuesta, detección correcta |
| ¿Qué mejoras se realizaron? | `docs/MEJORA_CONTINUA.md`: geocerca por tramo (detección correcta 90 % → 100 %) y estándar de 30 s |

## 4. Pruebas y calidad (para la exposición)
`bash scripts/ejecutar_pruebas.sh` → 128 pytest + 89 pruebas Odoo + rendimiento + 3 de interfaz;
matriz en `docs/PLAN_PRUEBAS.md`; ISO 25010 y SonarQube en `docs/CALIDAD_SOFTWARE.md`.
